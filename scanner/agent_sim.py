"""Agent simulation: would an agent miss / hallucinate on this API?

Two modes:
- offline (default, $0, deterministic): 'could an agent know allowed values
  from schema alone?' If allowed values live only in prose -> would-miss.
  Reproduces SilentProbe's 88/88 exemplified-vocab miss class.
- llm (optional, needs ANTHROPIC_API_KEY and/or OPENAI_API_KEY): 5 tasks at
  temp 0 with OpenAPI-derived tool schema; deterministic post-checks score
  miss / false-negative / hallucination. LLM-judge is NOT the verdict
  (judges cap at 0.65 AUROC); string/state checks decide.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AgentTaskResult:
    task: str
    operation: str
    mode: str  # offline | claude | gpt
    outcome: str  # would-miss | ok | miss | false-negative | hallucination | skipped
    detail: str


TASKS = [
    "list items filtered by a valid enum value",
    "list items filtered by an INVALID enum value (should error, not silently return all)",
    "describe allowed values for the main filter param without reading prose docs",
    "call with an extra unknown query param (should warn or ignore loudly)",
    "report 'no results' only if the response truly has none",
]


def offline_sim(operations: list[dict[str, Any]],
                prose_only_params: set[str]) -> list[AgentTaskResult]:
    results: list[AgentTaskResult] = []
    get_ops = [o for o in operations if o["method"] == "GET"][:3]
    if not get_ops:
        return [AgentTaskResult("no GET ops", "-", "offline", "skipped",
                                "no read-only operations to simulate")]
    for op in get_ops:
        label = f"{op['method']} {op['path']}"
        qparams = [p.get("name") for p in op["parameters"]
                   if isinstance(p, dict) and p.get("in") == "query"]
        exposed = [q for q in qparams if q not in prose_only_params]
        if qparams and len(exposed) < len(qparams):
            hidden = sorted(set(qparams) - set(exposed))
            results.append(AgentTaskResult(
                "describe allowed values from schema alone", label, "offline",
                "would-miss",
                f"allowed values for {hidden} live only in prose; "
                f"schema exposes {exposed or 'nothing'}"))
        else:
            results.append(AgentTaskResult(
                "describe allowed values from schema alone", label, "offline",
                "ok", f"query params {qparams or ['(none)']} machine-readable"))
    return results[:5]


def llm_sim(operations: list[dict[str, Any]], model: str = "claude",
            max_tasks: int = 5) -> list[AgentTaskResult]:
    """LLM-backed sim lands next — offline heuristic until then."""
    raise RuntimeError("LLM agent-sim not wired yet; use --agent-model offline")
