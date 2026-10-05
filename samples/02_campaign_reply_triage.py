"""Sample 02 - Campaign reply triage with confidence-gated routing (Choice + Noul).

Marketing use case: an outbound email campaign produces hundreds of replies in many
languages. Each reply needs a next action: book a meeting, snooze, suppress, update CRM...

Pattern ("confidence-gated routing" from the Jev docs): the answer tells you WHAT,
confidence tells you WHETHER to act.

    >= AUTO_THRESHOLD   act automatically
    >= REVIEW_THRESHOLD queue for a human (one click to approve)
    below               escalate to an LLM / human to read and draft a reply

Hard compliance rules (opt-out = suppress) are a separate Noul and override everything.
Non-English replies are routed to Laya's multilingual checkpoint automatically.
"""
from collections import Counter

from jev_client import DecisionClient, Stopwatch, header, top_prob

AUTO_THRESHOLD = 0.80
REVIEW_THRESHOLD = 0.55
OPT_OUT_THRESHOLD = 0.50  # compliance: err on the side of suppressing

QUESTIONS = {
    "intent": {
        "type": "choice",
        "instructions": "What does the sender of this reply to our marketing email want?",
        "criteria": {
            "meeting": "agrees to a call, demo or meeting, or proposes a time",
            "interested": "asks questions or wants more information, pricing or material",
            "not_now": "politely declines for now or asks to follow up later",
            "unsubscribe": "asks to stop emails or to be removed from the list",
            "out_of_office": "automatic reply: the person is away or on vacation",
            "wrong_person": "not responsible for this topic, points to a colleague",
            "complaint": "angry about the email, calls it spam",
        },
    },
    "opt_out": {
        "type": "noul",
        "instructions": "Does the sender ask us to stop contacting them or to delete their data?",
    },
}

ACTIONS = {
    "meeting": "send booking link + notify account executive",
    "interested": "send case study + create SDR follow-up task",
    "not_now": "snooze contact for 90 days",
    "unsubscribe": "suppress contact in all campaigns",
    "out_of_office": "retry after the return date",
    "wrong_person": "ask for referral + update CRM contact role",
    "complaint": "suppress contact + alert campaign owner",
}

REPLIES = [
    "Sounds great - can we do a 30 minute demo on Thursday at 10am?",
    "Thanks for reaching out. We're locked into our current tool until next year, ping me in Q3.",
    "Please remove me from your mailing list.",
    "I am out of the office until 14 October with limited access to email.",
    "I'm not the right person for this, you should talk to our CRM lead, jana.svobodova@example.com.",
    "How does your lead scoring compare to HubSpot's? Do you have pricing for 50 seats?",
    "This is the fifth unsolicited email this month. Stop spamming me!",
    "Bitte nehmen Sie mich aus Ihrem Verteiler und löschen Sie meine Daten.",
    "Dobrý den, děkuji za e-mail. Můžete mi poslat ceník a nějakou případovou studii?",
    "Hmm, maybe. Not sure this is a priority for us.",
]


def decide(answers):
    intent = answers["intent"]
    confidence = top_prob(intent)
    if answers["opt_out"]["noul"] >= OPT_OUT_THRESHOLD:
        return "AUTO", "suppress contact (compliance rule: opt-out detected)"
    if confidence >= AUTO_THRESHOLD:
        return "AUTO", ACTIONS[intent["choice"]]
    if confidence >= REVIEW_THRESHOLD:
        return "REVIEW", f"suggest '{ACTIONS[intent['choice']]}' - one-click approval"
    runner_up = sorted(intent["probabilities"].items(), key=lambda kv: kv[1])[-2][0]
    return "ESCALATE", f"unclear ({intent['choice']} vs {runner_up}) - LLM drafts reply for a human"


def main():
    # Preload both checkpoints: non-English replies are routed to the multilingual one.
    client = DecisionClient(preload=["english", "multilingual"])
    header("Sample 02 - Campaign reply triage (Choice + Noul, confidence gating)", client)
    print(f"auto >= {AUTO_THRESHOLD}   review >= {REVIEW_THRESHOLD}   "
          f"opt-out Noul >= {OPT_OUT_THRESHOLD} always suppresses\n")

    lanes = Counter()
    for reply in REPLIES:
        with Stopwatch() as sw:
            answers = client.ask(reply, QUESTIONS)
        lane, action = decide(answers)
        lanes[lane] += 1
        intent = answers["intent"]
        print(f"\"{reply[:74]}{'...' if len(reply) > 74 else ''}\"")
        print(f"   intent={intent['choice']:<13} p={top_prob(intent):.2f}  "
              f"opt_out={answers['opt_out']['noul']:.2f}  ({sw.ms:.0f} ms)")
        print(f"   [{lane:<8}] {action}\n")

    total = len(REPLIES)
    print("Summary: " + ", ".join(f"{lane} {n}/{total}" for lane, n in lanes.most_common()))
    print("Tune AUTO_THRESHOLD on a hand-labelled sample: higher = fewer mistakes, "
          "lower = less manual work.")


if __name__ == "__main__":
    main()
