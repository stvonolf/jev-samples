# Jev samples (running locally on Laya)

Seven runnable Python samples showing how a **System One decision model** like
[TypeSafe Jev](https://docs.typesafe.ai) fits into marketing software. Samples 01–06 are
console scripts; sample 07 is a pair of browser UIs rebuilt from the demos in the video.

We don't have a Jev subscription (Jev is in early access and not available in the Microsoft
Foundry model catalog), so the samples run the open-source, Jev-compatible
[**Laya**](https://huggingface.co/convaiinnovations/laya) model locally (Apache-2.0,
421M parameters, CPU is fine). Laya uses the same `state` + typed `questions` →
typed `answers` contract as Jev's `POST /v1/systemone`, so the samples can switch to Jev
by changing environment variables (see [Switching to TypeSafe Jev](#switching-to-typesafe-jev)).

| # | Sample | Use case | Primitives | Pattern | Inspired by |
|---|--------|----------|------------|---------|-------------|
| 01 | [`01_lead_scoring.py`](01_lead_scoring.py) | Rank and route inbound leads | Choice + Score + Noul | Composite scoring, confidence-gated disqualification | Marketing research |
| 02 | [`02_campaign_reply_triage.py`](02_campaign_reply_triage.py) | Triage replies to an email campaign (EN/DE/CZ) | Choice + Noul | Confidence-gated routing (auto / review / escalate), compliance override | Marketing research |
| 03 | [`03_seo_internal_linking.py`](03_seo_internal_linking.py) | Build an internal-link map for a website | Noul + Choice | Pairwise decisions at scale, rules in code, anchor text from a closed set | Video 2: 586-page SEO demo |
| 04 | [`04_social_feed_monitor.py`](04_social_feed_monitor.py) | Live social listening: hide slop, route complaints | Noul + Score + Choice | Observe → decide → act loop | Video 2: real-time slop detector |
| 05 | [`05_marketing_command_bar.py`](05_marketing_command_bar.py) | "pause the black friday emails" → function call | Choice | Function calling, speculative fan-out, pre-parsed values | Video 2: voice-controlled drawing app |
| 06 | [`06_agent_harness.py`](06_agent_harness.py) | AI assistant harness | Choice + Noul | Model routing, auto mode (tool-call risk gate), Jev-as-a-judge | Video 3: LangChain harness |
| 07 | [`07_ui_demos.py`](07_ui_demos.py) + [`ui/`](ui) | Browser demos: trolley problem ×100, creative emoji pile, live message-temperature gauges | Choice + Score + Noul | Real-time decision loop, streaming decisions, relative thresholds, composite scoring | Video 2: trolley + designer demos; Score demo added |

## Setup

Python 3.10+ (tested with 3.14 on Windows, CPU only).

```powershell
git clone https://github.com/stvonolf/jev-samples
cd jev-samples
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r samples\requirements.txt
cd samples
..\.venv\Scripts\python.exe 01_lead_scoring.py        # any of 01-06
..\.venv\Scripts\python.exe 07_ui_demos.py            # UI demos -> http://localhost:8765
```

The first run downloads the checkpoint from Hugging Face (~0.8 GB English; sample 02 also
downloads the ~0.6 GB multilingual checkpoint). Later runs load it from the local cache in ~10 s.

## UI demos (sample 07)

`07_ui_demos.py` starts a small, dependency-free web server and opens
<http://localhost:8765> (`--port`, `--no-browser`, `--no-warm` are available).

- **`/trolley` - "The trolley problem, 100 times."** One Choice per trial (pull the lever /
  leave it alone) with freshly randomised wording, an animated track scene, a 100-cell result
  grid, and 1× playback for the first 5 trials, then 10×. Modes: *classic* (5 on main, 1 on side,
  as in the video), *sanity check* (1 on main, 5 on side) and *random counts*.
  Our run: 100/100 pulls in classic mode (P 0.75–0.98) - but Laya also pulls in the sanity
  check (0/13 chose fewer deaths): the model reacts to the story pattern, it does not count.
- **`/creative` - the designer's emoji pile.** Type a request; each of ~235 emoji gets one Noul
  ("Is this related to: <request>?") and the ones that stand out fly up under the prompt while
  decisions stream in. P(related) levels differ a lot between prompts, so the UI picks outliers
  (≥ mean + 2.5 sd, max 12) instead of a fixed threshold. On a laptop CPU a new prompt takes
  ~40–75 s; the suggested prompts are pre-computed at start-up and cached in
  `ui/.decision_cache.json`, so they replay instantly during a live demo.
- **`/score` - "How hot is this message?"** Four Score questions about one customer message
  (frustration, urgency, churn risk, sentiment), re-evaluated 0.7 s after you stop typing
  (~1.3–1.5 s per evaluation on a laptop CPU). Each gauge shades its levels by probability and
  puts a needle at the probability-weighted score, so you can watch it land *between* levels.
  **Play escalation** types an invoice complaint sentence by sentence: frustration climbs
  0.96 → 1.42 → 1.84 → 2.11 → 2.44 and churn jumps to 2.84 at "we will cancel". Code turns the
  scores into a priority (0.40 frustration + 0.35 urgency + 0.25 churn) and a route
  (normal queue … escalate to retention; happy customers → testimonial for marketing).

## Switching to TypeSafe Jev

[`jev_client.py`](jev_client.py) has two interchangeable backends that return the same answer shape:

```powershell
# Default: local Laya, in-process
..\.venv\Scripts\python.exe 02_campaign_reply_triage.py

# TypeSafe Jev (needs an API key)
$env:JEV_BASE_URL = "https://api.typesafe.ai"; $env:JEV_API_KEY = "<key>"
..\.venv\Scripts\python.exe 02_campaign_reply_triage.py

# Laya as a Jev-compatible HTTP server (pip install "laya[serve]"; laya-serve)
$env:JEV_BASE_URL = "http://localhost:8000"
```

`LAYA_CHECKPOINT` = `english` | `multilingual` | `typed-decisions` forces a local checkpoint;
by default Laya's `Router` picks English or multilingual per request.

Gate on `top_prob(answer)` (the probability on the reported answer). Laya calls it
`answer_confidence`; for Jev the helper derives it from `probabilities` / `noul`.

## What we measured (laptop CPU: Intel Core Ultra 7 268V, no CUDA)

| | Laptop CPU (ours) | Reported elsewhere |
|---|---|---|
| One short question | ~250–350 ms | Laya on a T4 GPU: ~33 ms; Jev API: 70–500 ms end-to-end |
| 4–5 questions about one item (one forward pass) | ~1–2 s | Laya T4: ~40–85 ms for 5 questions |
| Model load from cache | ~8–15 s | |

CPU is fine for demos and batch jobs; use a GPU (or the Jev API) for real-time use.

## Lessons learned while building the samples

Laya is used **zero-shot** here (no fine-tuning). Getting good results took the same
care any classifier needs:

1. **Ask atomic questions.** "Is the sender a competitor, student, job seeker or vendor?"
   as one Noul was unreliable; a single *persona* Choice with one option per case worked.
2. **Keep structured data and business rules in code.** Employee count, routing tables,
   risk policies and thresholds are code; the model only judges language.
3. **Give the model only the text it needs.** Passing every CRM field made persona
   confidence drop; title + company + message worked better.
4. **Wording matters - measure it.** We compared 3–5 phrasings per question on a small
   hand-labelled set. Short option labels beat long descriptions for the command bar;
   "Do both pages cover the same marketing topic?" beat "Are they closely related?" for SEO.
5. **Gate on confidence and fail safe.** Uncertain answers go to a human, the powerful
   LLM, or a clarification question - never to an irreversible action.
6. **Compliance rules override everything.** An opt-out Noul suppresses a contact even
   when the main intent is uncertain.
7. **Don't trust the model to count.** In the trolley demo Laya pulls the lever whether
   5 or 1 people are on the main track; arithmetic and hard rules belong in code.
8. **Probability levels differ between questions.** For the emoji pile, the best "related"
   probability is ~0.9 for "things you can wear" but ~0.3 for "i need to lose weight" -
   rank and pick outliers, or calibrate a threshold per question.
9. **Score needs enough text.** On short email subject lines only urgency separated well;
   on full customer messages frustration, urgency and churn risk track the text closely.
10. **For real use, label 200–500 examples** of your own data, pick thresholds on them, and
   consider fine-tuning (Laya's fine-tuned `typed-decisions` checkpoint goes from 0.36 to
   0.77 accuracy on its benchmark).
