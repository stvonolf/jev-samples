"""Sample 04 - Real-time social feed monitor: slop filter + brand listening (Noul + Score + Choice).

Inspired by the real-time "slop detector" demo in "Jev Is WAY More Powerful Than We
Thought": while you scroll, every post is labelled slop / not slop in the background.

Marketing twist - social listening for our brand. Every incoming post gets four answers
from ONE forward pass; code then decides what happens (observe -> decide -> act):

    engagement_bait  Noul   - "like / comment / repost / agree?" bait or filler -> hide it
    sentiment        Score  - negative ... positive toward the brand (a continuous index)
    topic            Choice - complaint / praise / question / feature request / news / other
    churn            Noul   - does the author cancel or threaten to cancel?

Routing to a team is a business rule, so it lives in code (TEAM_FOR_TOPIC), not in a prompt.
"""
import time

from jev_client import DecisionClient, Stopwatch, bar, header, score_fraction, top_prob

BRAND = "AcmeCloud"
SLOP_THRESHOLD = 0.55
CHURN_THRESHOLD = 0.50

QUESTIONS = {
    "engagement_bait": {
        "type": "noul",
        "instructions": "Does the post ask readers to like, comment, repost or agree?",
    },
    "sentiment": {
        "type": "score",
        "instructions": f"How does the author feel about {BRAND}?",
        "criteria": ["negative", f"neutral or does not mention {BRAND}", "positive"],
    },
    "topic": {
        "type": "choice",
        "instructions": "What kind of post is this?",
        "criteria": {
            "complaint": "reports a problem or is unhappy with a product",
            "praise": "shares a good experience or result",
            "question": "asks a question about a product",
            "feature_request": "asks for a new feature",
            "news": "announces or reports news",
            "other": "general opinion, marketing advice or engagement bait",
        },
    },
    "churn": {
        "type": "noul",
        "instructions": f"Does the author cancel or threaten to cancel their {BRAND} subscription?",
    },
}

TEAM_FOR_TOPIC = {"complaint": "support", "question": "sales", "feature_request": "product"}

FEED = [
    ("@growthguru", "🚀 10 AI marketing hacks that will 10x your growth in 2026! 🔥 Comment 'AI' "
                    "and I'll DM you the full guide 👇 #growth #marketing"),
    ("@lena_ops", f"Three months on {BRAND}'s journey builder: onboarding emails went from 18% to "
                  "31% open rate. Genuinely impressed."),
    ("@shopfounder", f"@{BRAND} your SMS sends have been failing since this morning and support "
                     "hasn't replied in 6 hours. We launch tomorrow!"),
    ("@thoughtleader", "In today's fast-paced digital landscape, leveraging cutting-edge solutions "
                       "is more important than ever. Embrace innovation and unlock your potential."),
    ("@crm_mark", f"Does {BRAND} support double opt-in for GDPR out of the box? Evaluating it "
                  "against two other tools."),
    ("@martech_news", f"{BRAND} announced a native Shopify integration today, available on all plans."),
    ("@abtester", f"Feature request for {BRAND}: please let us schedule A/B tests per timezone. "
                  "Our EU and US audiences open emails at very different hours."),
    ("@viralvibes", "Agree? 👇 Marketing is not about selling, it's about storytelling. "
                    "Repost if you agree ♻️"),
    ("@cfo_jana", f"Cancelled our {BRAND} subscription. Pricing doubled at renewal with zero "
                  "notice. Never again."),
    ("@rev_ops_tom", "Unpopular opinion: lead scoring is only as good as the sales feedback loop "
                     "behind it. We review our model monthly with the AEs."),
]

MOOD = ["😡", "😐", "😍"]


def route(answers):
    """Business rules in code: churn beats everything, then topic -> team."""
    if answers["churn"]["noul"] >= CHURN_THRESHOLD:
        return "retention", 1.0
    team = TEAM_FOR_TOPIC.get(answers["topic"]["choice"])
    if team is None:
        return None, 0.0
    # Lower sentiment = more urgent.
    return team, 1.0 - 0.5 * score_fraction(answers["sentiment"])


def main():
    client = DecisionClient()
    header(f"Sample 04 - Live feed monitor for '{BRAND}' (Noul + Score + Choice)", client)

    hidden, queue, sentiments, latencies = [], [], [], []
    for author, text in FEED:
        with Stopwatch() as sw:
            a = client.ask(f"{author}: {text}", QUESTIONS)
        latencies.append(sw.ms)

        print(f"{author:<15}{text[:60]}{'...' if len(text) > 60 else ''}")
        bait = a["engagement_bait"]["noul"]
        if bait >= SLOP_THRESHOLD:
            hidden.append(author)
            print(f"{'':<15}🗑  SLOP (bait p={bait:.2f}) -> hidden from the feed   [{sw.ms:.0f} ms]\n")
            continue

        sentiment = score_fraction(a["sentiment"])
        sentiments.append(sentiment)
        topic = a["topic"]
        line = (f"{MOOD[int(round(a['sentiment']['score']))]} sentiment={sentiment:.2f}  "
                f"topic={topic['choice']} ({top_prob(topic):.2f})")
        team, priority = route(a)
        if team:
            queue.append((priority, author, team, text))
            line += f"  -> {team.upper()} queue"
        print(f"{'':<15}{line}   [{sw.ms:.0f} ms]\n")
        time.sleep(0.2)  # pretend the user keeps scrolling

    print("-" * 78)
    index = sum(sentiments) / len(sentiments)
    print(f"Hidden as slop : {len(hidden)}/{len(FEED)} ({', '.join(hidden)})")
    print(f"Brand sentiment: {bar(index, 20)} {index:.2f}  (0 = negative, 0.5 = neutral, 1 = positive)")
    print(f"Latency        : avg {sum(latencies) / len(latencies):.0f} ms per post "
          f"({len(QUESTIONS)} questions, one forward pass)")
    print("Work queue (highest priority first):")
    for priority, author, team, text in sorted(queue, reverse=True):
        print(f"  {priority:.2f}  {team:<10} {author:<14} {text[:44]}...")


if __name__ == "__main__":
    main()
