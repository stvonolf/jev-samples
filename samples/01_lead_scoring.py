"""Sample 01 - Lead scoring with composite scoring (Score + Noul + Choice).

Marketing use case: rank inbound leads for Sales and route them to the right owner.

Pattern ("composite scoring" from the Jev docs): never ask the model for one magic
"lead score". Split the judgment into small, atomic, typed questions and combine the
answers with weights *you* control in code:

    persona        Choice - prospect / student / competitor / seller / fan
    seniority      Score  - how senior is the job title?
    intent         Score  - how ready is the lead to buy?
    timeframe      Score  - when does the lead plan to buy?
    wants_demo     Noul   - does the lead ask for a demo, a call or pricing?

Structured facts (employee count, industry) are scored by plain code - the model is used
only for what code cannot do: understanding language. All five questions are answered
in ONE forward pass per lead, and persona confidence gates the disqualification.
"""
from jev_client import DecisionClient, Stopwatch, bar, header, score_fraction, top_prob

TARGET_INDUSTRIES = {"retail", "e-commerce", "financial services", "insurance", "telecom", "SaaS"}

QUESTIONS = {
    "persona": {
        "type": "choice",
        "instructions": "Who is the sender?",
        "criteria": {
            "prospect": "wants to buy or evaluate our product for their company",
            "student": "a student or academic researcher",
            "competitor": "works for a company that builds a product similar to ours",
            "seller": "pitches their own agency services or products to us",
            "fan": "only compliments, feedback or general curiosity, no project",
        },
    },
    "seniority": {
        "type": "score",
        "instructions": "How senior is the job `title` of this person?",
        "criteria": [
            "student, freelancer or individual contributor",
            "manager or team lead",
            "head of department or director",
            "vice president (VP) or C-level executive (CEO, CIO, CMO)",
        ],
    },
    "intent": {
        "type": "score",
        "instructions": "How ready is this person to buy our marketing software?",
        "criteria": ["not interested", "just researching", "evaluating vendors", "ready to buy now"],
    },
    "timeframe": {
        "type": "score",
        "instructions": "When does the lead plan to buy?",
        "criteria": ["no plans", "sometime this year or later",
                     "within the next few months", "within weeks"],
    },
    "wants_demo": {
        "type": "noul",
        "instructions": "Does the person ask for a demo, a call or pricing?",
    },
}

LEADS = [
    {"name": "Laura Fischer", "title": "VP Marketing", "company": "Northwind Retail",
     "industry": "retail", "employees": 4500,
     "message": "We are replacing our current CDP before Q1. Budget is approved - "
                "please send pricing and book a demo next week."},
    {"name": "Tomas Novak", "title": "Marketing Operations Manager", "company": "Fabrikam Cloud",
     "industry": "SaaS", "employees": 320,
     "message": "We're evaluating three vendors for lead scoring and journey orchestration."},
    {"name": "Mia Chen", "title": "Master's student", "company": "University of Vienna",
     "industry": "education", "employees": 0,
     "message": "I am writing my thesis on customer data platforms, could you share some material?"},
    {"name": "Ben Ortiz", "title": "Freelance designer", "company": "Ortiz Studio",
     "industry": "design", "employees": 1,
     "message": "Love your blog posts on email design!"},
    {"name": "Sara Lind", "title": "Product Manager", "company": "Contoso Marketing Cloud",
     "industry": "marketing software", "employees": 2000,
     "message": "We're building a similar lead-scoring product at Contoso and I'd love to "
                "compare - can you send your full feature list and API docs?"},
    {"name": "David Okafor", "title": "CIO", "company": "Woodgrove Bank",
     "industry": "financial services", "employees": 12000,
     "message": "Interesting webinar. No projects planned this year, just keeping an eye on the market."},
    {"name": "Kevin Brandt", "title": "Founder", "company": "RankRocket SEO Agency",
     "industry": "agency", "employees": 8,
     "message": "We can boost your Google rankings in 30 days! Can we schedule a call to "
                "show you our SEO packages?"},
    {"name": "Anna Weber", "title": "Head of CRM", "company": "Litware Insurance",
     "industry": "insurance", "employees": 850,
     "message": "We need to unify customer data from three systems. Our current vendor "
                "contract ends in two months, so we are shortlisting replacements now."},
]

# Weights live in code: tune them against won/lost deals, not by re-prompting.
WEIGHTS = {"firmographics": 0.25, "seniority": 0.15, "intent": 0.30, "timeframe": 0.15, "wants_demo": 0.15}
DISQUALIFYING_PERSONAS = {"student", "competitor", "seller"}
PERSONA_CONFIDENCE = 0.60  # below this a disqualifying persona is not trusted -> human check


def to_state(lead):
    """Give the model only the text it needs; extra CRM fields add noise."""
    return {"title": lead["title"], "company": lead["company"], "message": lead["message"]}


def firmographic_fit(lead):
    """Deterministic data is scored deterministically - no model needed."""
    size = lead["employees"]
    size_fit = 1.0 if size >= 1000 else 0.7 if size >= 100 else 0.2 if size >= 10 else 0.0
    return size_fit * (1.0 if lead["industry"] in TARGET_INDUSTRIES else 0.4)


def evaluate(lead, a):
    persona, persona_p = a["persona"]["choice"], top_prob(a["persona"])
    parts = {
        "firmographics": firmographic_fit(lead),
        "seniority": score_fraction(a["seniority"]),
        "intent": score_fraction(a["intent"]),
        "timeframe": score_fraction(a["timeframe"]),
        "wants_demo": a["wants_demo"]["noul"],
    }
    score = 100.0 * sum(WEIGHTS[k] * v for k, v in parts.items())

    if persona in DISQUALIFYING_PERSONAS:
        if persona_p >= PERSONA_CONFIDENCE:
            return 0.0, "drop", f"disqualified: {persona}"
        return score, "human check", f"maybe {persona} (p={persona_p:.2f}) - verify before outreach"

    # Routing is a business rule, so it stays in code.
    if score >= 60:
        owner = "enterprise AE" if lead["employees"] >= 1000 else "mid-market AE"
    elif score >= 40:
        owner = "SDR"
    else:
        owner = "nurture"
    return score, owner, ""


def main():
    client = DecisionClient()
    header("Sample 01 - Lead scoring (Choice + Score + Noul -> composite score)", client)

    with Stopwatch() as sw:
        results = client.ask_many([to_state(lead) for lead in LEADS], QUESTIONS)
    print(f"Scored {len(LEADS)} leads x {len(QUESTIONS)} questions in {sw.ms:.0f} ms "
          f"({sw.ms / len(LEADS):.0f} ms per lead, one forward pass each)\n")

    rows = []
    for lead, a in zip(LEADS, results):
        score, owner, note = evaluate(lead, a)
        rows.append((score, lead, a, owner, note))
    rows.sort(key=lambda r: r[0], reverse=True)

    print(f"{'lead':<28}{'persona (p)':<18}{'sen':>4}{'int':>5}{'time':>5}{'demo':>6}"
          f"{'score':>7}  owner")
    print("-" * 96)
    notes = []
    for score, lead, a, owner, note in rows:
        persona = f"{a['persona']['choice']} ({top_prob(a['persona']):.2f})"
        print(f"{lead['name'] + ', ' + lead['title'][:12]:<28}{persona:<18}"
              f"{a['seniority']['score']:>4.1f}{a['intent']['score']:>5.1f}"
              f"{a['timeframe']['score']:>5.1f}{a['wants_demo']['noul']:>6.2f}"
              f"{score:>7.0f}  {owner}")
        if note:
            notes.append(f"  {lead['name']}: {note}")
    if notes:
        print("\nNotes:")
        print("\n".join(notes))

    print("\nsen/int/time = probability-weighted Score (0-3); demo = Noul P(yes).")
    print("score = 100 x (" + " + ".join(f"{w}*{k}" for k, w in WEIGHTS.items()) + ")")
    print(f"Disqualify only when persona p >= {PERSONA_CONFIDENCE}; otherwise route to a human.")

    _, top_lead, top, _, _ = rows[0]
    print(f"\nWhy is {top_lead['name']} on top? The full intent distribution:")
    for level, p in top["intent"]["probabilities"].items():
        print(f"  {top['intent']['legend'][level]:<20} {bar(p, 20)} {p:.2f}")


if __name__ == "__main__":
    main()
