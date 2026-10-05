"""Sample 05 - Natural-language command bar for marketing software (Choice-based function calling).

Inspired by the demo in "Jev Is WAY More Powerful Than We Thought" where a voice/gesture
interface lets Jev *operate* a drawing app ("make a blue square here", "move this there").
Here the app is our campaign manager:

    "pause the black friday emails"   ->  pause_campaign(campaign="black_friday_email")

There is no JSON to parse and no hallucinated function names: the function and every
argument come from closed sets (Choice questions), so the result is always a valid call.

Patterns used (from the Jev docs):
* Speculative fan-out - ask for ALL possible arguments in one pass; code keeps the ones
  the chosen function needs and ignores the rest.
* Pre-parsed values - an explicit number like "15%" is extracted by a regex (exact),
  the model only picks the amount when the user says "half" or "a bit".
* Confidence gating - if the function or a required argument is uncertain, the command
  bar asks "Did you mean ...?" instead of executing.
"""
import re

from jev_client import DecisionClient, Stopwatch, header, top_prob

CONFIDENCE = 0.50

CAMPAIGNS = {
    "black_friday_email": {"label": "Black Friday email campaign", "channel": "email", "status": "active", "budget": 5000},
    "google_search_brand": {"label": "Google Ads brand search campaign", "channel": "google ads", "status": "active", "budget": 12000},
    "linkedin_retargeting": {"label": "LinkedIn retargeting ads", "channel": "linkedin", "status": "paused", "budget": 4000},
    "meta_prospecting": {"label": "Meta (Facebook and Instagram) prospecting ads", "channel": "meta", "status": "active", "budget": 8000},
    "spring_webinar": {"label": "Spring webinar promotion", "channel": "email and linkedin", "status": "active", "budget": 2500},
}

QUESTIONS = {
    "function": {
        "type": "choice",
        "instructions": "Which command did the user give?",
        # Short labels beat long descriptions here - measured on a small labelled set.
        "criteria": {
            "pause_campaign": "pause",
            "resume_campaign": "resume / turn back on",
            "change_budget": "change budget or spend",
            "performance_report": "show performance report",
            "unclear": "unclear",
        },
    },
    # Speculative fan-out: these are asked every time, used only when relevant.
    "campaign": {
        "type": "choice",
        "instructions": "Which campaign is the user talking about?",
        "criteria": {key: c["label"] for key, c in CAMPAIGNS.items()},
    },
    "direction": {
        "type": "choice",
        "instructions": "Should the budget go up or down?",
        "criteria": {"increase": "more, bump, raise, double", "decrease": "less, cut, reduce, halve"},
    },
    "amount": {
        "type": "choice",
        "instructions": "By how much should the budget change?",
        "criteria": {"10": "a little, a bit, slightly", "25": "a quarter",
                     "50": "half, halve, in half", "100": "double, twice as much"},
    },
    "period": {
        "type": "choice",
        "instructions": "Which time period should the report cover?",
        "criteria": {"last_7_days": "last week, past few days", "last_30_days": "last month",
                     "this_quarter": "this quarter, so far this year"},
    },
}

COMMANDS = [
    "pause the black friday emails",
    "bump the google search budget by 15%",
    "turn the linkedin retargeting back on",
    "cut spend on meta prospecting in half",
    "how did our campaigns do last week?",
    "make it better",
    "reactivate the meta prospecting campaign",
    "double the budget for the spring webinar promo",
]


# ---------------------------------------------------------------- the "app" being driven
def pause_campaign(campaign):
    CAMPAIGNS[campaign]["status"] = "paused"
    return f"{CAMPAIGNS[campaign]['label']} is now PAUSED"


def resume_campaign(campaign):
    CAMPAIGNS[campaign]["status"] = "active"
    return f"{CAMPAIGNS[campaign]['label']} is now ACTIVE"


def change_budget(campaign, direction, percent):
    old = CAMPAIGNS[campaign]["budget"]
    factor = 1 + percent / 100 if direction == "increase" else 1 - min(percent, 100) / 100
    CAMPAIGNS[campaign]["budget"] = new = round(old * factor)
    return f"{CAMPAIGNS[campaign]['label']} budget {old:,} -> {new:,} EUR"


def performance_report(period):
    return f"Generating performance report for {period.replace('_', ' ')} ..."


FUNCTIONS = {
    "pause_campaign": (pause_campaign, ["campaign"]),
    "resume_campaign": (resume_campaign, ["campaign"]),
    "change_budget": (change_budget, ["campaign", "direction", "amount"]),
    "performance_report": (performance_report, ["period"]),
}


# ---------------------------------------------------------------- command bar logic
def explicit_percent(command):
    match = re.search(r"(\d{1,3})\s*(%|percent)", command)
    return int(match.group(1)) if match else None


def did_you_mean(answer):
    top2 = sorted(answer["probabilities"].items(), key=lambda kv: -kv[1])[:2]
    return " or ".join(f"'{k}' ({p:.2f})" for k, p in top2)


def handle(command, answers):
    fn_answer = answers["function"]
    if fn_answer["choice"] == "unclear" or top_prob(fn_answer) < CONFIDENCE:
        return f"🤔 Not sure what to do. Did you mean {did_you_mean(fn_answer)}?"
    fn, arg_names = FUNCTIONS[fn_answer["choice"]]

    kwargs, call = {}, []
    for name in arg_names:
        if name == "amount" and explicit_percent(command) is not None:
            kwargs["percent"] = explicit_percent(command)  # exact value from the text wins
            call.append(f"percent={kwargs['percent']} (regex)")
            continue
        arg = answers[name]
        if top_prob(arg) < CONFIDENCE:
            return f"🤔 Which {name}? Did you mean {did_you_mean(arg)}?"
        key = "percent" if name == "amount" else name
        kwargs[key] = int(arg["choice"]) if name == "amount" else arg["choice"]
        call.append(f"{key}={arg['choice']!r} ({top_prob(arg):.2f})")

    print(f"   call : {fn.__name__} [p={top_prob(fn_answer):.2f}] ({', '.join(call)})")
    return "✅ " + fn(**kwargs)


def main():
    client = DecisionClient()
    header("Sample 05 - Command bar: natural language -> typed function call (Choice)", client)
    for command in COMMANDS:
        with Stopwatch() as sw:
            answers = client.ask(command, QUESTIONS)
        print(f"> {command}")
        result = handle(command, answers)
        print(f"   {result}")
        print(f"   [{sw.ms:.0f} ms, {len(QUESTIONS)} questions in one pass]\n")

    print("Final campaign state:")
    for key, c in CAMPAIGNS.items():
        print(f"  {key:<22} {c['status']:<7} {c['budget']:>7,} EUR")


if __name__ == "__main__":
    main()
