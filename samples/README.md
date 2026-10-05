# Jev samples (running locally on Laya)

Six runnable Python samples showing how a **System One decision model** like
[TypeSafe Jev](https://docs.typesafe.ai) fits into marketing software.

We don't have a Jev subscription, so the samples run the open-source, Jev-compatible
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

## Setup

Python 3.10+ (tested with 3.14 on Windows, CPU only).

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r samples\requirements.txt
cd samples
..\.venv\Scripts\python.exe 01_lead_scoring.py
```

The first run downloads the checkpoint from Hugging Face (~0.8 GB English; sample 02 also
downloads the ~0.6 GB multilingual checkpoint). Later runs load it from the local cache in ~10 s.

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
7. **For real use, label 200–500 examples** of your own data, pick thresholds on them, and
   consider fine-tuning (Laya's fine-tuned `typed-decisions` checkpoint goes from 0.36 to
   0.77 accuracy on its benchmark).
