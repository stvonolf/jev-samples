"""Speaker notes for Jev_Team_Overview.pptx (kept out of build_presentation.py for readability)."""

NOTES = {
    "what": """
WHAT: Jev (TypeSafe AI, early access since Sept 2026) is the first "System One" model. You send a state and typed questions (choice / score / noul) to POST /v1/systemone and get typed answers with probabilities back. No text generation.

TYPESAFE'S OWN POSITIONING (typesafe.ai): "an AI lab building machine-native intelligence infrastructure for automation". "We took the opposite research direction - not chat": RLHF optimises for human preference and produces superhuman instruction followers, but also mode dropping, overconfidence and a lack of reliability, so LLMs need humans in the loop. System One models are built to be used natively by machines, with a new architecture, a new sampler and a new training algorithm (RLCD). Taglines: "Decisions, not strings", "calibrated confidence", "more like code: reliable, fast, type-safe". Headline claim: 193.6x faster and 444.6x cheaper on workflows for System One tasks (their demo: $0.000081 in 0.114 s vs an LLM at $0.013880 in 8.566 s); $42 per billion input tokens (= $0.042 per million), "238x lower input price than Claude Fable 5.1". They also claim "zero hallucinations" - read that as "always a valid typed answer", not "always right". All vendor-reported.

SYSTEM ONE (docs.typesafe.ai/concepts/system-one): text input only (strings, JSON objects, arrays of text) - images, audio and video are not supported yet. Calibration is measured across groups of predictions; it does not guarantee that a single answer is correct. No replies, no code, no explanations of reasoning.

WHY (Caleb Writes Code, "Jev explained in 7min"): the AI stack's application layer pushed models toward chat (RLHF) and coding agents (RLVR). Workflow automation never crossed the cost/speed threshold, even with very capable models. TypeSafe argues that forcing chat/agent-optimised models into automation is the wrong approach and trains for calibrated decisions instead (RLCD). Most community demos show off speed (sorting email, RAG, games, model routing) rather than depth - LLMs can do these functionally, but not at 70-500 ms, because they generate tokens one after another.

HOW FAST/CHEAP: video 1 quotes 40-200x faster at 70-500 ms end-to-end; LangChain quotes 20-200x faster and 40-400x cheaper on classification-style tasks; TypeSafe's homepage says 193.6x faster / 444.6x cheaper on System One workflows. Price $0.042 per 1M input tokens, output free (~$0.0004 per decision).

NAME: System 1 / System 2 from Kahneman, "Thinking, Fast and Slow".

LANGCHAIN DEMO: "Is there PII in this text?" - LLM writes an answer + structured output in ~5 s; Jev returns 0.98 almost instantly.

Takeaway from video 1: this is less about Jev's novelty and more about the use-case space growing horizontally - narrow, specialised models next to general LLMs.
""",

    "how": """
EXAMPLE CALL (support ticket from the docs / LangChain video): POST /v1/systemone with state "Hi, I've been trying to connect my Stripe account for 3 days and it keeps failing. I'm losing sales. Please help ASAP." and three questions in one request: team (choice: billing / technical / ...), mood (score: calm / frustrated / very angry) and urgent (noul). Answers: team = billing (p 0.84, confidence 0.60), mood = 1.04 (frustrated, not very angry), urgent = 0.999.

""" + """
PRIMITIVES (all three videos + docs.typesafe.ai/api):
- Choice: map of option -> rubric (or null). Returns choice, probabilities per option, confidence. Max 255 options.
- Score: ordered array of level descriptions (2-10). Returns a probability-weighted score that can land between levels (1.04 = frustrated, not very angry), plus legend/probabilities/confidence.
- Noul: yes/no; returns P(yes). Optional criteria for what true/false mean.
- Many questions about one state are answered in ONE parallel pass - adding questions barely changes latency (unlike LLMs, which reason sequentially).
- Instructions and criteria can be structured JSON; refer to state fields in backticks.

Caleb's framing: "It almost feels like we're back to logic gates and registers" - you build abstractions on top. On the Pareto frontier Jev competes with Flash/Nano-class models, but only on workflow-specific tasks.

DOCS PATTERNS: confidence-gated routing (the answer tells you WHAT, confidence tells you WHETHER to act), composite scoring (atomic scores, weights in code), speculative fan-out (ask everything in one call, code decides what is relevant), intent routing.

SYSTEM ONE WORKFLOW (docs.typesafe.ai/concepts/system-one) - refund request: 1) build a state with the customer's message, the relevant transactions and the refund policy; 2) ask independent questions together (refund requested? evidence of a duplicate charge? does the policy support a refund?); 3) combine the answers with deterministic checks in code and route the case for action or review. Confidence decides when to act and when to escalate to a person or a reasoning model. Inputs are text only (strings, JSON objects, arrays of text); calibration holds across groups of predictions, not for every single answer.

LANGCHAIN ("Building a Harness with Jev"): langchain-typesafe exposes TypeSafeClassifier plus experimental middleware: ModelRouterMiddleware (fast vs powerful model per request) and AutoModeMiddleware (tool-risk gating). Jev-as-a-judge for LangSmith online evals: rubric criteria scored by Jev - reported as cheaper, faster and more consistent than LLM judges. Sample 06 in our repo implements all three ideas.
""",

    "marketing": """
MARKETING USE CASES (TypeSafe use-case map: lead generation, advertising, customer support, moderation; Ryze AI "Jev for Marketing: 8 use cases and the limits"):
- Lead scoring and routing: score each lead against the ICP and pick the owner - two questions, one call. Sales gets the top band, the rest goes to nurture. (A 700-lead demo on X did exactly this.)
- Search terms & negatives (paid search): buyer / researcher / job seeker / competitor / junk -> auto-negative, queue or drop by confidence.
- Ad creative tagging: Matthew Berman ran Jev on 724 live ads from 37 brands in 40 s (~9 cents) - hook, format, offer, CTA, awareness stage, landing-page mismatch.
- SEO internal links: the 586-page Distribb demo from video 2.
- AI citation / GEO checks: "Is our brand recommended in this AI answer?" (Noul).
- Review & survey themes: classify every response instead of sampling 200.
- Content QA gate: 20 Nouls per draft; only passing drafts reach an editor.
- Model routing: frontier vs small vs no model.
Cost at list price is cents per job -> jobs that ran monthly on a frontier LLM can run nightly.

DECIDE-THEN-ACT LOOP (Ryze): collect with code -> shortlist to 10-15 candidates -> one bounded question per row -> threshold (high confidence auto, middle band to approval queue, low dropped) -> LLM writes only where text is needed -> verify the LLM output with Jev before it ships.

VIDEO 2 (Pursuing AI): AI that watches, decides and acts. Driving simulator (real-time control), trolley problem 100 trials (99% pull, consistent), designer visual exploration (hundreds of tiny decisions what to show), voice + gesture control of a drawing app, live slop detector on X, SEO 586 pages, Laya (local, M3 Max) playing Snake at ~60 decisions/s with 10-18 ms latency and ~1 GB memory.

LIMITS: no explanation; bounded answers only; vendor-reported benchmarks measure agreement with frontier models (Jev 67.8% vs Claude Opus 5 73.1%, GPT-5.6 Sol 74.1% on TypeSafe's 4-workflow benchmark); "cannot hallucinate" means it cannot break the schema - it can still pick the wrong option. Label 500 rows of your own data before trusting a threshold. Waitlist access, price may move.
""",

    "access": """
AVAILABILITY: Jev (TypeSafe AI) has been in early access since 15 Sep 2026. You apply for the preview, then create an API key under "API keys" (free starter credit is typical). It is NOT in the Microsoft Foundry model catalog - there is no one-click deployment.

MICROSOFT FOUNDRY (Microsoft Tech Community, "Using Jev with Agents in Microsoft Foundry for Model Evaluation", 30 Sep 2026):
- Create a Foundry agent, add an OpenAPI tool with an OpenAPI 3.0 schema for POST https://api.typesafe.ai/v1/systemone (operationId evaluate_with_jev; Noul / Choice / Score question schemas) and a new connection holding the key as "Bearer <key>".
- Agent instructions: for every support message MUST call evaluate_with_jev, use exactly 'instructions' and 'criteria' properties, model "jev-latest", pass the original message as state, do not classify yourself, show the Jev output.
- Example from the article: "The room had no water in and one of the towels was dirty" -> billing noul 0.02, tone choice frustrated (0.74, confidence 0.6), urgency score 1.81 (handle today 0.85). The application then routes / escalates / requires human review deterministically.
- Pattern: User/Application -> Foundry model or agent -> Jev judgement -> deterministic logic -> action/response.
- Why Jev: consistent evaluation against explicit criteria, structured outputs, classification/routing, guardrails before tool calls, model routing; every decision has a probability for thresholds.
- Explainability: SHAP-style attribution is hard when the model is only reachable through a hosted API. Jev does not replace SHAP but adds a separate, measurable judgement layer around opaque MaaS models.
- Pricing (Sept 2026): jev-1.13.0 $0.042 per 1M input tokens, output free; limits 250,000 tokens/s and 1,200 requests/min (subject to change). Typical latency ~70-500 ms.

OPEN SOURCE: Laya (huggingface.co/convaiinnovations/laya) - Apache-2.0, Jev-compatible request/response shape, runs locally; laya-serve exposes POST /v1/systemone so Jev clients only change the base URL. All our samples run on it.

RUN THE SAMPLES: git clone https://github.com/stvonolf/jev-samples; python -m venv .venv; .venv\\Scripts\\python -m pip install -r samples\\requirements.txt; cd samples; ..\\.venv\\Scripts\\python 01_lead_scoring.py (01-06), ..\\.venv\\Scripts\\python 07_ui_demos.py for the browser demos (http://localhost:8765). First run downloads ~0.8 GB of model weights.
""",

    "handson": """
RESULTS PER SAMPLE (laptop CPU, zero-shot Laya):
- 01 Lead scoring (Choice + Score + Noul): VP with approved budget -> 86/100 -> enterprise AE; student and SEO agency disqualified; a possible competitor (p 0.49) goes to a human check instead of being dropped.
- 02 Campaign reply triage, EN/DE/CZ (Choice + Noul): 10/10 correct labels; 7 automated, 1 review, 2 escalated; opt-out requests always suppressed (compliance rule in code).
- 03 SEO internal linking (Noul + Choice): 36 page pairs -> 18 links with anchor texts, 54 rejected; the summer-party page gets no links.
- 04 Social feed monitor (Noul + Score + Choice): 3/3 slop posts hidden; complaint -> support, cancellation -> retention, question -> sales, feature request -> product.
- 05 Command bar (Choice): "cut spend on meta prospecting in half" -> change_budget(meta_prospecting, decrease, 50%); vague commands get "did you mean ...?".
- 06 Agent harness (Choice + Noul): routing saves 48% of LLM cost; 6/6 tool calls classified correctly (allow / ask human / block); Jev-as-a-judge catches hype and two invented claims.
- 07 UI demos: trolley x100 (Choice), creative emoji pile (Noul), "How hot is this message?" (Score) - next slide.

NEXT STEPS: 1) pick one pilot (reply triage or lead scoring); 2) label 300-500 real examples and set thresholds on them; 3) compare Laya (fine-tuned) vs the Jev API on that set; 4) ship behind a confidence gate with human review for the middle band.

LEARNINGS IN DETAIL: atomic questions win (one persona Choice beat four disqualifier Nouls); numbers, business rules and routing stay in code; give the model only the text it needs; wording matters - we compared 3-5 phrasings per question on small labelled sets; gate on confidence and fail safe (human, powerful LLM or a clarification question); compliance rules override the model; CPU ~0.3 s per question vs ~33 ms on a T4 GPU.

""" + """
REPO: https://github.com/stvonolf/jev-samples - samples/ has seven runnable Python samples + jev_client.py (local Laya backend or any Jev-compatible HTTP endpoint via JEV_BASE_URL / JEV_API_KEY). Run: git clone https://github.com/stvonolf/jev-samples; cd jev-samples; python -m venv .venv; .venv\\Scripts\\python -m pip install -r samples\\requirements.txt; cd samples; ..\\.venv\\Scripts\\python 01_lead_scoring.py (01-06 are console samples); ..\\.venv\\Scripts\\python 07_ui_demos.py starts the browser demos on http://localhost:8765.

LAYA (huggingface.co/convaiinnovations/laya): ModernBERT-large backbone (395M) + a decision head trained from scratch, 421M total; multilingual checkpoint on mmBERT-base for 100+ languages; trained with RLCD-style proper scoring rules. laya-serve exposes the same POST /v1/systemone request/response shape as TypeSafe Jev. Author-reported vs Jev (third-party numbers, different setups): 7.8x faster on a T4 GPU (32.8 ms vs 236-276 ms p50), better calibration after temperature fitting, but Jev is better with >20 options (Banking77: 0.87 vs 0.43). The base checkpoint scores 0.36 on the typed-decisions benchmark; the fine-tuned typed-decisions checkpoint 0.77 - fine-tuning matters.

OUR MEASUREMENTS (Intel Core Ultra 7 268V, CPU only): ~250-350 ms for one short question, ~1-2 s for 4-5 questions about one item, model load ~10 s from cache. Fine for batch/demo; use a GPU or the Jev API for real-time.

LESSONS: we tested 3-5 phrasings per question on small labelled sets. Examples: "Do both pages cover the same marketing topic?" (AUC 1.0) beat "Are the pages closely related?"; short option labels beat long descriptions for the command bar; plain-text tool-call descriptions + a "kind of action" Choice beat risk Nouls on JSON. Giving the model fewer CRM fields improved persona detection.

NEXT STEPS: one pilot use case, label data, measure Laya vs Jev, ship behind confidence gating with human review for the middle band.
""",

    "demos": """
SAMPLE 07 (samples/07_ui_demos.py): a stdlib-only web server on top of jev_client.DecisionClient - so it runs on local Laya by default and on TypeSafe Jev when JEV_BASE_URL / JEV_API_KEY are set. Open http://localhost:8765. One demo per primitive.

TROLLEY (/trolley, Choice), modelled on the "The trolley problem, 100 times" demo from video 2 (X post by @FinanceYF5): one Choice per trial ("pull_the_lever" vs "leave_it_alone", criteria spell out who dies). Each trial uses freshly randomised wording (vehicle, people, sentence template), so the 100 decisions are not identical calls. First 5 trials at 1x, then 10x, like the original. Classic mode reproduces the video (100/100 pull). Sanity-check mode swaps the counts (1 on main, 5 on side) - Laya still pulls the lever (0 of 13 trials chose fewer deaths in our run), and a random-counts mode shows the same. Lesson: fast decision models pattern-match; put arithmetic and hard rules in code.

CREATIVE (/creative, Noul), modelled on the designer demo (@heystefan_): type a request, every emoji in a pile of ~235 gets a Noul. Emoji that stand out for the request animate up under the prompt as decisions stream in, 8 per request. Because P(related) levels vary by prompt (wear ~0.9 max, lose weight ~0.3 max), the UI selects relative outliers (mean + 2.5 sd, at most 12). Speed on our laptop CPU: ~0.15-0.3 s per emoji decision, so a brand-new prompt takes ~40-75 s; the suggested prompts are pre-computed and cached at server start so they replay instantly. On a GPU or the Jev API this is real time.

SCORE (/score): "How hot is this message?" - four Score questions about one customer message (frustration: calm/slightly annoyed/frustrated/furious; urgency: no time pressure ... emergency; churn risk: very unlikely ... about to cancel; sentiment: negative/neutral/positive), re-evaluated 0.7 s after you stop typing (~1.3-1.5 s per evaluation on the laptop CPU). Each gauge shades the levels by probability and puts a needle at the probability-weighted score, so you can see it land between levels. "Play escalation" types an invoice complaint sentence by sentence: frustration 0.96 -> 1.42 -> 1.84 -> 2.11 -> 2.44, churn jumps to 2.84 at "we will cancel". Priority = 0.40 frustration + 0.35 urgency + 0.25 churn (normalised) is computed in code and mapped to a route (normal queue / reply today / priority / escalate to retention; happy customers -> testimonial for marketing). We first tried scoring short email subject lines - only urgency separated well, so Score works best on richer text.

WHAT WE TRIED (creative): grouped Choice (10 emoji + "none" per question) was faster but less precise; mean-pooled encoder embeddings as a shortlist were no better than random; the emoji + name state with "Is this related to: X?" had the best ranking (AUC ~0.9 on labelled sets, except physics questions like magnets).
""",

}
