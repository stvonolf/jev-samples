"""Sample 03 - SEO internal linking at scale (Noul per page pair + Choice for anchor text).

Inspired by the demo in "Jev Is WAY More Powerful Than We Thought": Jev processed a
586-page site in 45 s, placed 584 internal links and rejected 139 candidates, for $0.21.

Internal linking is not a writing task - it is thousands of tiny yes/no decisions:
"Are these two pages closely related, so a reader of one would want the other?"
That is a Noul. Code then applies the SEO rules (threshold, max links per page), and for
every accepted link a Choice picks the anchor text from a closed set of candidates, so
the result can be written straight into the CMS without parsing anything.

Pass 1: every page pair (n*(n-1)/2 Nouls, batched).  Pass 2: anchors for accepted links only.
"""
from itertools import combinations

from jev_client import DecisionClient, Stopwatch, header, top_prob

LINK_THRESHOLD = 0.35       # P(related) needed to place a link
MAX_LINKS_PER_PAGE = 3      # SEO rule: keep the strongest links only

PAGES = [
    {"slug": "lead-scoring-guide", "title": "The complete guide to lead scoring",
     "summary": "Combine fit and intent signals into a lead score so sales works the best leads "
                "first, and hand scored leads to automated nurture journeys.",
     "anchors": ["lead scoring guide", "how to score leads", "fit and intent signals"]},
    {"slug": "predictive-lead-scoring", "title": "Predictive lead scoring with machine learning",
     "summary": "Train a machine learning model on won and lost deals to predict which new leads "
                "will convert, and compare it with rule-based lead scoring.",
     "anchors": ["predictive lead scoring", "machine learning for leads", "conversion prediction"]},
    {"slug": "email-subject-lines", "title": "50 email subject lines that get opened",
     "summary": "Tested subject lines and copywriting tips that raise email open rates, plus why "
                "good deliverability matters before any subject line can work.",
     "anchors": ["email subject lines", "subject line examples", "increase open rates"]},
    {"slug": "email-deliverability", "title": "Email deliverability checklist",
     "summary": "SPF, DKIM, DMARC, list hygiene, consent and unsubscribe handling: how to keep "
                "marketing emails out of the spam folder and protect open rates.",
     "anchors": ["deliverability checklist", "avoid the spam folder", "SPF, DKIM and DMARC"]},
    {"slug": "gdpr-email-consent", "title": "GDPR and consent for email marketing",
     "summary": "Legal basis, double opt-in, unsubscribe handling and data deletion requests for "
                "email marketing under GDPR.",
     "anchors": ["GDPR consent", "double opt-in", "handling unsubscribes"]},
    {"slug": "customer-segmentation", "title": "Customer segmentation strategies",
     "summary": "Segment customers by behaviour, RFM and lifecycle stage to personalise email "
                "campaigns and customer journeys.",
     "anchors": ["customer segmentation", "RFM segmentation", "lifecycle segments"]},
    {"slug": "marketing-attribution", "title": "Multi-touch attribution explained",
     "summary": "Compare first-touch, last-touch and data-driven attribution models to measure "
                "which marketing channels drive revenue.",
     "anchors": ["multi-touch attribution", "attribution models", "measure channel revenue"]},
    {"slug": "summer-party-2026", "title": "Our 2026 summer party recap",
     "summary": "Photos from the team barbecue, the office football match and the karaoke night.",
     "anchors": ["summer party", "team barbecue", "office culture"]},
    {"slug": "journey-orchestration", "title": "Journey orchestration (product page)",
     "summary": "Build automated customer journeys across email, SMS and ads, triggered by "
                "customer segments and lead scores.",
     "anchors": ["journey orchestration", "automated customer journeys", "multi-channel journeys"]},
]

RELATED_QUESTION = {
    "related": {
        "type": "noul",
        "instructions": "Do both pages cover the same marketing topic?",
    }
}


def describe(page):
    return f"{page['title']}. {page['summary']}"


def anchor_question(target):
    return {"anchor": {
        "type": "choice",
        "instructions": "Which anchor text best describes the target page for a reader of the source page?",
        "criteria": {anchor: None for anchor in target["anchors"]},  # null = no extra rubric
    }}


def main():
    client = DecisionClient()
    header("Sample 03 - SEO internal linking (Noul per page pair + Choice for anchor)", client)

    # ---- Pass 1: one Noul per unordered page pair -------------------------------------
    pairs = list(combinations(PAGES, 2))
    states = [f"Page A: {describe(a)}\nPage B: {describe(b)}" for a, b in pairs]
    with Stopwatch() as sw:
        results = client.ask_many(states, RELATED_QUESTION)
    print(f"Pass 1: {len(pairs)} relatedness decisions in {sw.ms / 1000:.1f} s "
          f"({len(pairs) / (sw.ms / 1000):.1f} decisions/s on this machine)\n")
    p_related = {}
    for (a, b), r in zip(pairs, results):
        p_related[(a["slug"], b["slug"])] = p_related[(b["slug"], a["slug"])] = r["related"]["noul"]

    # ---- SEO rules live in code: threshold + max links per source page ----------------
    links = []
    for source in PAGES:
        candidates = sorted(((p_related[(source["slug"], t["slug"])], t) for t in PAGES
                             if t is not source), key=lambda c: -c[0])
        links += [(source, t, p) for p, t in candidates[:MAX_LINKS_PER_PAGE] if p >= LINK_THRESHOLD]
    considered = len(PAGES) * (len(PAGES) - 1)

    short = [p["slug"][:9] for p in PAGES]
    print(" " * 24 + " ".join(f"{name:>9}" for name in short))
    linked = {(s["slug"], t["slug"]) for s, t, _ in links}
    for s in PAGES:
        cells = []
        for t in PAGES:
            if s is t:
                cells.append(f"{'-':>9}")
            else:
                p = p_related[(s["slug"], t["slug"])]
                mark = "*" if (s["slug"], t["slug"]) in linked else " "
                cells.append(f"{p:>8.2f}{mark}")
        print(f"{s['slug'][:23]:<24}" + " ".join(cells))
    print(f"\n* = link placed. {len(links)} links placed, {considered - len(links)} candidate "
          f"links rejected (P(related) >= {LINK_THRESHOLD}, max {MAX_LINKS_PER_PAGE} per page).")

    # ---- Pass 2: anchor text, only for links that passed ------------------------------
    with Stopwatch() as sw:
        anchors = [client.ask(f"Source page: {describe(s)}\nTarget page: {describe(t)}",
                              anchor_question(t))["anchor"] for s, t, _ in links]
    print(f"\nPass 2: {len(anchors)} anchor-text choices in {sw.ms / 1000:.1f} s\n")
    for (s, t, p), a in zip(links, anchors):
        print(f"  {s['slug']:<24} -> {t['slug']:<24} \"{a['choice']}\"  "
              f"(related p={p:.2f}, anchor p={top_prob(a):.2f})")


if __name__ == "__main__":
    main()
