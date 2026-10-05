"""Sample 06 - Jev inside an agent harness: model routing, auto mode, Jev-as-a-judge.

Inspired by LangChain's "Building a Harness with Jev": keep the LLM for open-ended
reasoning and writing, and put a fast System-One model at the decision points AROUND it.
Scenario: an AI marketing assistant inside our product. No LLM is called here - the
LLM's outputs are canned, so the sample runs offline; only the Jev decisions are real.

    1. Model routing   Choice - cheapest model that can do the task (fast vs powerful LLM)
    2. Auto mode       Choice - what kind of action is the agent's tool call?
                                 code maps the kind to allow / ask a human / block
    3. Jev-as-a-judge  Noul   - does the generated email have a call to action? any hype?
                       Choice per sentence - is it supported by the product facts?
                                 (the "citation check" pattern from the Jev cookbooks)
"""
import re

from jev_client import DecisionClient, Stopwatch, header, top_prob

GATE = 0.60          # below this confidence the harness falls back to the safe option
ROUTING_GATE = 0.55  # binary choice -> a lower bar; uncertain requests go to the powerful model

# ---------------------------------------------------------------- 1. model routing
ROUTER_QUESTION = {
    "model": {
        "type": "choice",
        "instructions": "Choose the least costly model that can complete the task.",
        "criteria": {
            "fast": "Direct lookups, extraction, translation and small localized edits.",
            "powerful": "Strategy, multi-step analysis, planning and high-stakes decisions.",
        },
    }
}
MODEL_COST = {"fast": 1, "powerful": 20}  # relative cost per request
ASSISTANT_REQUESTS = [
    "Fix the typo in this subject line: 'Your Spring offer is hear'",
    "Write a 3-month go-to-market plan for launching our CDP in the DACH region, "
    "including budget split and KPIs",
    "Translate this CTA to German: 'Book your free demo'",
    "Analyse why our Q3 email revenue dropped 18% across segments and propose fixes",
    "Shorten this sentence to under 60 characters: 'We are excited to invite you to our "
    "upcoming spring webinar about data'",
    "Design an A/B testing strategy for our pricing page, including sample sizes and "
    "statistical power",
]

# ---------------------------------------------------------------- 2. auto mode
ACTION_QUESTION = {
    "kind": {
        "type": "choice",
        "instructions": "Which kind of action is this?",
        "criteria": {
            "read": "reads or views data",
            "draft_edit": "edits a draft or sends an internal test",
            "mass_send": "sends to customers",
            "delete": "deletes data",
            "export": "exports data to an outside address",
        },
    }
}
# Policy lives in code - the model only classifies.
POLICY = {"read": "ALLOW", "draft_edit": "ALLOW", "mass_send": "ASK HUMAN",
          "delete": "ASK HUMAN", "export": "BLOCK"}
PROPOSED_TOOL_CALLS = [
    "The agent wants to read the open and click statistics of the campaign 'spring_webinar'.",
    "The agent wants to change the subject line of the draft campaign 'spring_webinar' to "
    "'Join our spring webinar'.",
    "The agent wants to send a test email of 'draft_v3' to our internal address "
    "marketing-team@acme.example.",
    "The agent wants to send the email template 'draft_v3' (not yet approved) to the segment "
    "'All contacts' with 1,200,000 recipients.",
    "The agent wants to permanently delete the segment 'Churned customers 2023' with 48,000 contacts.",
    "The agent wants to export the contact list 'VIP customers' with names and emails to "
    "jan.private@gmail.com.",
]

# ---------------------------------------------------------------- 3. Jev-as-a-judge
PRODUCT_FACTS = ("Spring webinar on 14 May, 45 minutes. Live product demo and Q&A with the "
                 "product team. AcmeCloud is used by 400 retail and finance customers.")
DRAFT_QUESTIONS = {
    "has_cta": {"type": "noul",
                "instructions": "Does the email contain a link the reader is asked to click?"},
    "hype": {"type": "noul",
             "instructions": "Does the email use hype like '#1', 'guaranteed' or exaggerated promises?"},
}
SENTENCE_QUESTION = {
    "grounded": {"type": "choice",
                 "instructions": "Do the `facts` support the `sentence`?",
                 "criteria": {"supported": "the facts state this",
                              "unsupported": "the facts do not state this or say something different"}},
}
LLM_DRAFTS = {  # what the (not called) LLM might have written
    "draft A": "Hi Anna, on 14 May our product team shows in 45 minutes how retailers unify "
               "customer data. Live demo and Q&A included. Save your seat: acme.example/webinar",
    "draft B": "Hi Anna, AcmeCloud is the #1 CDP worldwide, trusted by 10,000 brands. We "
               "guarantee 300% ROI in 30 days! Join our webinar on 14 May. Register now: "
               "acme.example/webinar",
    "draft C": "Hi Anna, customer data is more important than ever. In today's world, brands "
               "need to personalise everything. At AcmeCloud we think about this a lot.",
}


def route_requests(client):
    print("\n1) MODEL ROUTING - pick the cheapest LLM that can do the job")
    spent = 0
    for request in ASSISTANT_REQUESTS:
        with Stopwatch() as sw:
            answer = client.ask(request, ROUTER_QUESTION)["model"]
        # Uncertain -> fall back to the powerful model (quality first).
        model = answer["choice"] if top_prob(answer) >= ROUTING_GATE else "powerful"
        spent += MODEL_COST[model]
        print(f"   {model:<9} (p={top_prob(answer):.2f}, {sw.ms:4.0f} ms)  {request[:62]}...")
    always_powerful = MODEL_COST["powerful"] * len(ASSISTANT_REQUESTS)
    print(f"   -> cost {spent} units vs {always_powerful} if every request used the powerful "
          f"model ({100 * (1 - spent / always_powerful):.0f}% saved)")


def gate_tool_calls(client):
    print("\n2) AUTO MODE - classify every tool call before it executes")
    for call in PROPOSED_TOOL_CALLS:
        with Stopwatch() as sw:
            answer = client.ask(call, ACTION_QUESTION)["kind"]
        verdict = POLICY[answer["choice"]]
        if top_prob(answer) < GATE and verdict == "ALLOW":
            verdict = "ASK HUMAN"  # fail safe: never auto-allow an uncertain action
        icon = {"ALLOW": "✅", "ASK HUMAN": "✋", "BLOCK": "⛔"}[verdict]
        action = call.removeprefix("The agent wants to ")
        print(f"   {icon} {verdict:<9} {answer['choice']:<10} (p={top_prob(answer):.2f}, "
              f"{sw.ms:4.0f} ms)  {action[:58]}...")


def judge_drafts(client):
    print("\n3) JEV-AS-A-JUDGE - check LLM-written emails before a human sees them")
    print(f"   facts: {PRODUCT_FACTS[:92]}...")
    for name, draft in LLM_DRAFTS.items():
        with Stopwatch() as sw:
            checks = client.ask(draft, DRAFT_QUESTIONS)
            sentences = [s for s in re.split(r"(?<=[.!?])\s+", draft) if s]
            verdicts = client.ask_many([{"facts": PRODUCT_FACTS, "sentence": s} for s in sentences],
                                       SENTENCE_QUESTION)
        unsupported = [s for s, v in zip(sentences, verdicts)
                       if v["grounded"]["probabilities"]["supported"] < 0.5]
        problems = []
        if checks["has_cta"]["noul"] < 0.5:
            problems.append("no call to action")
        if checks["hype"]["noul"] >= 0.5:
            problems.append("hype")
        problems += [f"unsupported claim: \"{s}\"" for s in unsupported]

        status = "PASS" if not problems else "FAIL"
        print(f"\n   {name}: {status}  (cta={checks['has_cta']['noul']:.2f}, "
              f"hype={checks['hype']['noul']:.2f}, {len(sentences)} sentences checked, {sw.ms:.0f} ms)")
        print(f"     \"{draft[:96]}...\"")
        for problem in problems:
            print(f"     - {problem}")
        if problems:
            print("     -> sent back to the LLM with these problems as rewrite instructions")


def main():
    client = DecisionClient()
    header("Sample 06 - Jev in the agent harness: routing, auto mode, judge", client)
    route_requests(client)
    gate_tool_calls(client)
    judge_drafts(client)


if __name__ == "__main__":
    main()
