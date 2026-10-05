# jev-samples

Team material about **Jev**, TypeSafe AI's "System One" decision model, and how it could
be used in marketing software.

| Folder | Content |
|--------|---------|
| [`presentation/`](presentation) | `Jev_Team_Overview.pptx` (6 slides) + the script and images used to build it |
| [`samples/`](samples) | 6 runnable Python samples (Choice, Score, Noul) + 3 browser UI demos (trolley problem ×100, creative emoji pile, live Score gauges), all running locally on the open-source, Jev-compatible [Laya](https://huggingface.co/convaiinnovations/laya) model |

## Jev in one paragraph

Jev does not generate text. You send it a **state** (text or JSON) and a set of typed
**questions**; it returns typed **answers** with calibrated probabilities, all questions
in one parallel forward pass (70–500 ms). The three primitives are **Choice** (pick one
option), **Score** (rate on ordered levels) and **Noul** (probability of yes). Your code
combines the answers, applies thresholds and decides what happens next, while LLMs keep
doing the writing and open-ended reasoning.

## Getting access to Jev

Jev is **not publicly available yet**: it has been in early access since 15 Sep 2026 and is
**not in the Microsoft Foundry model catalog**.

1. **TypeSafe API** - apply for the preview at typesafe.ai, then create an API key
   ([docs](https://docs.typesafe.ai)). Our samples switch to it with `JEV_BASE_URL` + `JEV_API_KEY`.
2. **Microsoft Foundry agent** - add Jev to a Foundry agent as an OpenAPI tool that calls
   `POST https://api.typesafe.ai/v1/systemone` with your TypeSafe key
   ([Using Jev with Agents in Microsoft Foundry for Model Evaluation](https://techcommunity.microsoft.com/blog/azuredevcommunityblog/using-jev-with-agents-in-microsoft-foundry-for-model-evaluation/4559851)).
3. **Open-source [Laya](https://huggingface.co/convaiinnovations/laya)** - no sign-up, runs locally;
   this is what all samples here use.

## Quick start

```powershell
git clone https://github.com/stvonolf/jev-samples
cd jev-samples
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r samples\requirements.txt
cd samples
..\.venv\Scripts\python.exe 01_lead_scoring.py     # console samples 01-06
..\.venv\Scripts\python.exe 07_ui_demos.py         # browser demos -> http://localhost:8765
```

See [`samples/README.md`](samples/README.md) for all samples, the UI demos, measured latency,
lessons learned and how to switch to the TypeSafe Jev API.

## Sources

- [Jev explained in 7min..](https://www.youtube.com/watch?v=vj7hysh0mOI) - Caleb Writes Code
- [Jev Is WAY More Powerful Than We Thought](https://www.youtube.com/watch?v=I34qxJjyms0) - Pursuing AI
- [Building a Harness with Jev](https://www.youtube.com/watch?v=VE5dsWll06M) - LangChain ([blog post](https://www.langchain.com/blog/building-a-harness-with-jev))
- [Using Jev with Agents in Microsoft Foundry for Model Evaluation](https://techcommunity.microsoft.com/blog/azuredevcommunityblog/using-jev-with-agents-in-microsoft-foundry-for-model-evaluation/4559851) - Microsoft Tech Community
- [TypeSafe AI](https://typesafe.ai/) - homepage (positioning, speed/cost claims) and [System One](https://docs.typesafe.ai/concepts/system-one) concept page
- [TypeSafe docs](https://docs.typesafe.ai) - API reference, primitives, patterns, use-case map
- [Jev for Marketing: 8 Use Cases and the Limits](https://www.get-ryze.ai/blog/jev-for-marketing) - Ryze AI
- [Laya](https://huggingface.co/convaiinnovations/laya) / [GitHub](https://github.com/NandhaKishorM/laya) - open-source Jev-compatible model (Apache-2.0)

Slide images: thumbnails of the referenced YouTube videos (credited and linked on the slides;
the title banner of the second one is cropped off), a screenshot rendered from a real run of
`samples/06_agent_harness.py`, and screenshots of the three UI demos. Rebuild the deck with
`.venv\Scripts\python.exe presentation\build_presentation.py`.
