"""A tiny Jev-compatible client shared by all samples.

Two interchangeable backends return the *same* answer shape:

* ``local`` (default) - runs the open-source Laya model in-process
  (https://huggingface.co/convaiinnovations/laya, Apache-2.0, ~421M params, CPU is fine).
* ``http`` - any server that speaks Jev's ``POST /v1/systemone`` API:
  TypeSafe Jev itself, or a self-hosted ``laya-serve``.

Switch backends with environment variables only - no code changes:

    # TypeSafe Jev (needs an API key / subscription)
    $env:JEV_BASE_URL = "https://api.typesafe.ai"; $env:JEV_API_KEY = "..."
    # Self-hosted Laya over HTTP (pip install "laya[serve]"; laya-serve)
    $env:JEV_BASE_URL = "http://localhost:8000"

Optional: ``LAYA_CHECKPOINT`` = english | multilingual | typed-decisions forces one local
checkpoint; by default Laya's Router picks one per request (English vs. multilingual).
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
import warnings
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Sequence, Union

# transformers probes for TensorFlow at import, which can deadlock model construction.
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
warnings.filterwarnings("ignore", message=".*ships invalid temperatures.*")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

State = Any  # str | dict | list - exactly what Jev accepts as `state`
Questions = Dict[str, Dict[str, Any]]
Answers = Dict[str, Dict[str, Any]]


class DecisionClient:
    """Ask typed questions (choice / score / noul) about a state."""

    def __init__(self, checkpoint: Optional[str] = None,
                 preload: Union[bool, Sequence[str]] = True) -> None:
        self.base_url = (os.getenv("JEV_BASE_URL") or "").rstrip("/")
        self.api_key = os.getenv("JEV_API_KEY")
        self.model = os.getenv("JEV_MODEL", "jev-latest")
        self.checkpoint = os.getenv("LAYA_CHECKPOINT") or checkpoint or None
        self.load_seconds = 0.0

        if self.base_url:
            self.backend = "http"
            return

        self.backend = "local"
        from laya import Router  # imported lazily so the HTTP backend needs no torch

        started = time.perf_counter()
        self._router = Router()
        if preload:
            # True -> the default checkpoint; a list (e.g. ["english", "multilingual"]) loads
            # several up front so the first non-English request does not pay the load time.
            names = [self.checkpoint or "english"] if preload is True else list(preload)
            self._router.preload(names)
        self.load_seconds = time.perf_counter() - started

    # ------------------------------------------------------------------ public API
    def ask(self, state: State, questions: Questions) -> Answers:
        """Evaluate one state; returns ``{question_id: answer}``."""
        if self.backend == "http":
            return self._post(state, questions)["answers"]
        return self._router.predict(state, questions, model=self.checkpoint)["answers"]

    def ask_many(self, states: Sequence[State], questions: Questions,
                 batch_size: int = 16) -> List[Answers]:
        """Evaluate many states against the same questions (batched / parallel)."""
        if self.backend == "http":
            with ThreadPoolExecutor(max_workers=8) as pool:
                return list(pool.map(lambda s: self.ask(s, questions), states))
        requests = []
        for state in states:
            request = {"state": state, "questions": questions}
            if self.checkpoint:
                request["model"] = self.checkpoint
            requests.append(request)
        results = self._router.predict_batch(requests, batch_size=batch_size)
        return [r["answers"] for r in results]

    def describe(self) -> str:
        if self.backend == "http":
            return f"HTTP backend -> {self.base_url}/v1/systemone (model={self.model})"
        ckpt = self.checkpoint or "auto-routed"
        return (f"Local Laya backend (checkpoint={ckpt}, "
                f"model loaded in {self.load_seconds:.1f}s)")

    # ------------------------------------------------------------------ HTTP backend
    def _post(self, state: State, questions: Questions, retries: int = 4) -> Dict[str, Any]:
        body = json.dumps({"state": state, "model": self.model, "questions": questions})
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(f"{self.base_url}/v1/systemone",
                                         data=body.encode("utf-8"), headers=headers)
        for attempt in range(retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    return json.loads(response.read())
            except urllib.error.HTTPError as err:
                # 429 = rate limited, 529 = overloaded: back off and retry (per Jev docs).
                if err.code in (429, 529) and attempt < retries:
                    time.sleep(0.5 * 2 ** attempt)
                    continue
                raise RuntimeError(f"{err.code} from {self.base_url}: {err.read()[:300]!r}")
        raise RuntimeError("unreachable")


# ---------------------------------------------------------------------- helpers
def top_prob(answer: Dict[str, Any]) -> float:
    """Probability mass on the reported answer - the number to gate on.

    Laya returns it as ``answer_confidence``; for Jev responses it is derived from the
    probabilities so the same gating code works on both backends.
    """
    if "answer_confidence" in answer:
        return float(answer["answer_confidence"])
    if answer["type"] == "noul":
        p = float(answer["noul"])
        return max(p, 1.0 - p)
    return float(max(answer["probabilities"].values()))


def score_fraction(answer: Dict[str, Any]) -> float:
    """Map a Score answer onto 0..1 (0 = lowest level, 1 = highest level)."""
    levels = len(answer["probabilities"])
    return float(answer["score"]) / max(levels - 1, 1)


def bar(value: float, width: int = 20) -> str:
    filled = int(round(max(0.0, min(1.0, value)) * width))
    return "█" * filled + "░" * (width - filled)


def header(title: str, client: Optional[DecisionClient] = None) -> None:
    print("=" * 78)
    print(title)
    if client is not None:
        print(client.describe())
    print("=" * 78)


class Stopwatch:
    """``with Stopwatch() as sw: ...`` then ``sw.ms``."""

    def __enter__(self) -> "Stopwatch":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.ms = (time.perf_counter() - self._start) * 1000.0
