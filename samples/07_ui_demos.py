"""Sample 07 - Interactive UI demos: two from "Jev Is WAY More Powerful Than We Thought" + one for Score.

    ..\\.venv\\Scripts\\python.exe 07_ui_demos.py        ->  http://localhost:8765

* /trolley   "The trolley problem, 100 times."  One Choice per trial (pull the lever or
             leave it alone), animated scene, 100-cell result grid, 1x then 10x playback.
* /creative  The designer demo: type a request, and every emoji in the pile gets its own
             Noul ("Is this related to: <request>?"). Emoji that stand out for that request
             fly up under the prompt as the decisions stream in - hundreds of tiny decisions.
* /score     "How hot is this message?" Four Score questions (frustration, urgency, churn
             risk, sentiment) re-evaluated while you type; gauges move between levels and
             code turns them into a priority and a route.

Stdlib-only web server on top of jev_client.DecisionClient, so it runs on local Laya by
default and on TypeSafe Jev when JEV_BASE_URL / JEV_API_KEY are set.
Creative decisions are cached in ui/.decision_cache.json, and the suggested prompts are
pre-computed in the background at start-up, so they replay instantly during a live demo.
"""
import argparse
import json
import random
import sys
import threading
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from jev_client import DecisionClient, top_prob

UI_DIR = Path(__file__).parent / "ui"
sys.path.insert(0, str(UI_DIR))
from emoji_catalog import CATALOG  # noqa: E402

CACHE_FILE = UI_DIR / ".decision_cache.json"
# P(related) levels differ a lot between prompts ("wear" tops out ~0.9, "lose weight" ~0.3),
# so an emoji is picked when it is an outlier for THIS prompt: p >= mean + k*sd (and >= min_p).
SELECTION = {"k": 2.5, "min_p": 0.08, "max": 12, "warmup": 24}
SUGGESTIONS = ["things you can wear", "things you can wear in winter", "i need to lose weight",
               "starting a band", "things a magnet could attract"]

client = None
model_lock = threading.Lock()   # one forward pass at a time (CPU-bound anyway)
cache_lock = threading.Lock()
creative_cache = {}             # "prompt\x1fid" -> P(related)


# ------------------------------------------------------------------ trolley problem
VEHICLES = [("runaway trolley", "trolley"), ("runaway tram", "tram"),
            ("train whose brakes have failed", "train"), ("runaway mine cart", "cart")]
WHO = [("person", "people"), ("worker", "workers"), ("hiker", "hikers"), ("track inspector", "track inspectors")]
TEMPLATES = [
    "A {vehicle} is heading down the main track toward {main} who cannot get away. You stand "
    "next to a lever. If you pull it, the {short} switches to a side track where {side} {side_be} tied up.",
    "A {vehicle} is speeding toward {main} on the main track. On the side track {side_be} {side}. "
    "You can pull a lever to divert the {short}.",
    "You are at a railway switch. A {vehicle} will hit {main} on the main track unless you pull "
    "the lever, which sends the {short} onto a side track with {side}.",
    "{Main} {main_be} stuck on the main track as a {vehicle} approaches. A lever would divert the "
    "{short} to a side track, where {side} {side_be} standing.",
]


def count(n, who):
    singular, plural = who
    return f"{n} {singular if n == 1 else plural}"


def die(n):
    return "dies" if n == 1 else "die"


def trolley_scenario(mode, trial, seed):
    rng = random.Random(seed * 1000 + trial)
    if mode == "swapped":
        main_n, side_n = 1, 5
    elif mode == "random":
        main_n, side_n = rng.randint(1, 6), rng.randint(1, 6)
    else:
        main_n, side_n = 5, 1
    vehicle, short = rng.choice(VEHICLES)
    who = rng.choice(WHO)
    main, side = count(main_n, who), count(side_n, who)
    text = rng.choice(TEMPLATES).format(
        vehicle=vehicle, short=short, main=main, Main=main[0].upper() + main[1:], side=side,
        main_be="is" if main_n == 1 else "are", side_be="is" if side_n == 1 else "are")
    question = {"decision": {
        "type": "choice",
        "instructions": "You control the lever. What do you do?",
        "criteria": {
            "pull_the_lever": f"switch to the side track: {side} {die(side_n)}, {main} saved",
            "leave_it_alone": f"do nothing: {main} on the main track {die(main_n)}",
        },
    }}
    return main_n, side_n, text, question


def api_trolley(body):
    mode = body.get("mode", "classic")
    trial = int(body.get("trial", 1))
    seed = int(body.get("seed", 1))
    main_n, side_n, text, question = trolley_scenario(mode, trial, seed)
    started = time.perf_counter()
    with model_lock:
        answer = client.ask(text, question)["decision"]
    ms = (time.perf_counter() - started) * 1000
    return {"trial": trial, "main": main_n, "side": side_n, "text": text,
            "choice": "pull" if answer["choice"] == "pull_the_lever" else "leave",
            "p_pull": answer["probabilities"]["pull_the_lever"],
            "confidence": top_prob(answer), "ms": round(ms)}


# ------------------------------------------------------------------ score: message temperature
SCORE_QUESTIONS = {
    "frustration": {"type": "score", "instructions": "How frustrated is the customer?",
                    "criteria": ["calm", "slightly annoyed", "frustrated", "furious"]},
    "urgency": {"type": "score", "instructions": "How time-critical is this message?",
                "criteria": ["no time pressure", "should be handled soon", "needs a reply today",
                             "emergency: business is blocked or customer leaving"]},
    "churn": {"type": "score", "instructions": "How likely is this customer to cancel?",
              "criteria": ["very unlikely", "possible", "likely", "about to cancel"]},
    "sentiment": {"type": "score", "instructions": "How does the customer feel about us?",
                  "criteria": ["negative", "neutral", "positive"]},
}
SCORE_WEIGHTS = {"frustration": 0.40, "urgency": 0.35, "churn": 0.25}
score_cache = {}


def fraction(answer):
    return answer["score"] / max(len(answer["probabilities"]) - 1, 1)


def route(answers):
    """Business rules in code: weights and routing thresholds, not prompts."""
    f = {k: fraction(a) for k, a in answers.items()}
    priority = sum(w * f[k] for k, w in SCORE_WEIGHTS.items())
    if f["churn"] >= 0.85 or priority >= 0.75:
        decision = "Escalate to the retention lead"
    elif priority >= 0.6:
        decision = "Priority queue - reply within the hour"
    elif priority >= 0.45:
        decision = "Reply today"
    elif f["sentiment"] >= 0.6 and f["frustration"] < 0.3:
        decision = "Happy customer - share with marketing as a testimonial"
    else:
        decision = "Normal queue"
    return round(priority, 3), decision


def api_score(body):
    text = " ".join(str(body.get("text", "")).split())[:2000]
    if not text:
        return {"error": "empty message"}
    started = time.perf_counter()
    cached = text in score_cache
    if not cached:
        with model_lock:
            score_cache[text] = client.ask(text, SCORE_QUESTIONS)
    answers = score_cache[text]
    priority, decision = route(answers)
    slim = {k: {"score": a["score"], "probabilities": a["probabilities"], "legend": a["legend"],
                "confidence": top_prob(a)} for k, a in answers.items()}
    return {"answers": slim, "priority": priority, "route": decision, "cached": cached,
            "questions": len(SCORE_QUESTIONS), "ms": round((time.perf_counter() - started) * 1000)}


# ------------------------------------------------------------------ creative emoji pile
def creative_question(prompt):
    return {"related": {"type": "noul", "instructions": f"Is this related to: {prompt}?"}}


def normalize(prompt):
    return " ".join(prompt.lower().split())[:200]


def decide_emojis(prompt, ids):
    """P(related) for each emoji id; cached per (prompt, id)."""
    prompt = normalize(prompt)
    results, missing = {}, []
    with cache_lock:
        for i in ids:
            key = f"{prompt}\x1f{i}"
            if key in creative_cache:
                results[i] = creative_cache[key]
            else:
                missing.append(i)
    if missing:
        states = [f"{CATALOG[i][0]} {CATALOG[i][1]}" for i in missing]
        with model_lock:
            answers = client.ask_many(states, creative_question(prompt), batch_size=16)
        with cache_lock:
            for i, a in zip(missing, answers):
                results[i] = creative_cache[f"{prompt}\x1f{i}"] = round(a["related"]["noul"], 4)
            save_cache()
    return results, len(ids) - len(missing)


def api_creative(body):
    prompt = body.get("prompt", "")
    ids = [int(i) for i in body.get("ids", []) if 0 <= int(i) < len(CATALOG)][:64]
    started = time.perf_counter()
    results, cached = decide_emojis(prompt, ids)
    return {"results": [{"id": i, "p": results[i]} for i in ids], "cached": cached,
            "ms": round((time.perf_counter() - started) * 1000)}


def load_cache():
    if CACHE_FILE.exists():
        try:
            creative_cache.update(json.loads(CACHE_FILE.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass


def save_cache():
    tmp = CACHE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(creative_cache, ensure_ascii=False), encoding="utf-8")
    tmp.replace(CACHE_FILE)


def warm_up():
    """Pre-compute the suggested prompts in small chunks so live requests can interleave."""
    for prompt in SUGGESTIONS:
        ids = list(range(len(CATALOG)))
        for start in range(0, len(ids), 8):
            decide_emojis(prompt, ids[start:start + 8])
        print(f"  warm-up done: {prompt!r}")


# ------------------------------------------------------------------ HTTP plumbing
class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(UI_DIR), **kwargs)

    def log_message(self, fmt, *args):
        pass  # keep the console readable

    def send_json(self, payload, status=200):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        routes = {"/": "/index.html", "/trolley": "/trolley.html", "/creative": "/creative.html",
                  "/score": "/score.html"}
        if self.path in routes:
            self.path = routes[self.path]
        if self.path == "/api/config":
            return self.send_json({"backend": client.describe(), "selection": SELECTION,
                                   "suggestions": SUGGESTIONS})
        if self.path == "/api/creative/catalog":
            return self.send_json([{"id": i, "emoji": e, "name": n} for i, (e, n) in enumerate(CATALOG)])
        if self.path.startswith("/api/"):
            return self.send_json({"error": "not found"}, 404)
        if self.path.endswith(".py") or "/." in self.path:
            return self.send_json({"error": "not found"}, 404)
        return super().do_GET()

    def do_POST(self):
        handlers = {"/api/trolley/trial": api_trolley, "/api/creative/decide": api_creative,
                    "/api/score": api_score}
        handler = handlers.get(self.path)
        if handler is None:
            return self.send_json({"error": "not found"}, 404)
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            return self.send_json(handler(body))
        except Exception as exc:  # surface errors to the UI instead of a dropped connection
            return self.send_json({"error": f"{type(exc).__name__}: {exc}"}, 500)


def main():
    global client
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-warm", action="store_true", help="skip pre-computing the suggested prompts")
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser tab")
    args = parser.parse_args()

    print("Loading the decision model ...")
    client = DecisionClient()
    print(client.describe())
    load_cache()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://localhost:{args.port}"
    print(f"\nUI demos running at {url}   (trolley: {url}/trolley, creative: {url}/creative, "
          f"score: {url}/score)")
    print("Press Ctrl+C to stop.\n")
    if not args.no_warm:
        threading.Thread(target=warm_up, daemon=True).start()
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
