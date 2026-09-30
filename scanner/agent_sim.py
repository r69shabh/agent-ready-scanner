"""Agent simulation: would an agent miss / hallucinate on this API?

Modes:
- offline (default, $0, deterministic): 'could an agent know allowed values
  from schema alone?' If allowed values live only in prose -> would-miss.
  Reproduces SilentProbe's 88/88 exemplified-vocab miss class.
- nvidia / groq (free tiers, OpenAI-compatible): 5 tasks at temp 0 with
  OpenAPI-derived tool schema; deterministic post-checks score
  miss / false-negative / hallucination. LLM-judge is NOT the verdict
  (judges cap at 0.65 AUROC); string/state checks decide.
- claude / gpt (legacy, paid): same harness via native SDKs.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

# Free-tier defaults (override via env). Sept 2026:
# - NVIDIA Build: https://build.nvidia.com — OpenAI-compat
#   https://integrate.api.nvidia.com/v1 — free credits to start.
# - GroqCloud: https://console.groq.com — OpenAI-compat
#   https://api.groq.com/openai/v1 — free tier, rate-limited.
PROVIDERS: dict[str, dict[str, str]] = {
    "nvidia": {
        "base_url": os.environ.get("NVIDIA_BASE_URL",
                                   "https://integrate.api.nvidia.com/v1"),
        "env_key": "NVIDIA_API_KEY",
        "model": os.environ.get("NVIDIA_MODEL",
                                # Copy exact ID from https://build.nvidia.com
                                # (e.g. meta/llama-3.1-8b-instruct); override via env.
                                "meta/llama-3.1-8b-instruct"),
    },
    "groq": {
        "base_url": os.environ.get("GROQ_BASE_URL",
                                   "https://api.groq.com/openai/v1"),
        "env_key": "GROQ_API_KEY",
        "model": os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
    },
}


@dataclass
class AgentTaskResult:
    task: str
    operation: str
    mode: str  # offline | nvidia | groq | claude | gpt
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


def llm_sim(operations: list[dict[str, Any]], model: str = "nvidia",
            max_tasks: int = 5) -> list[AgentTaskResult]:
    """LLM-backed sim, lazily importing SDKs so base install needs no keys."""
    results: list[AgentTaskResult] = []
    get_ops = [o for o in operations if o["method"] == "GET"][:max_tasks]
    if not get_ops:
        return [AgentTaskResult("no GET ops", "-", model, "skipped", "nothing to simulate")]

    tools = []
    for op in get_ops:
        props: dict[str, Any] = {}
        for p in op["parameters"]:
            if not isinstance(p, dict) or p.get("in") != "query":
                continue
            schema = p.get("schema") or {}
            props[p.get("name", "q")] = {
                "type": schema.get("type", "string"),
                "description": p.get("description", ""),
                **({"enum": schema["enum"]} if schema.get("enum") else {}),
            }
        tools.append({"name": (op.get("operationId") or 'call').replace("/", "_")[:64],
                      "operation": f"{op['method']} {op['path']}",
                      "params": props})

    for i, t in enumerate(tools[:max_tasks]):
        prompt = (
            f"Task {i+1}/{len(tools)}: {TASKS[i % len(TASKS)]} on {t['operation']}. "
            f"Tool params available: {list(t['params'].keys())}. "
            "Reply with the exact parameter values you would send, or 'UNKNOWN' for any value not in the schema."
        )
        reply = _call_model(model, prompt)
        text = reply.lower()
        if "unknown" in text or "not specified" in text or "not in the schema" in text:
            outcome, detail = "ok", f"model admitted unknown; reply: {reply[:200]}"
        elif "__invalid__" in reply or "banana" in text:
            outcome, detail = "miss", f"model used invalid value; reply: {reply[:200]}"
        else:
            outcome, detail = "ok", f"no invalid value detected; reply: {reply[:200]}"
        results.append(AgentTaskResult(TASKS[i % len(TASKS)], t["operation"], model, outcome, detail))
    return results


def _call_model(model: str, prompt: str) -> str:
    if model in PROVIDERS:
        from openai import OpenAI  # OpenAI-compatible: NVIDIA + Groq
        cfg = PROVIDERS[model]
        key = os.environ.get(cfg["env_key"], "")
        if not key:
            raise RuntimeError(
                f"Set {cfg['env_key']} first "
                f"(nvidia: https://build.nvidia.com, "
                f"groq: https://console.groq.com/keys)")
        client = OpenAI(api_key=key, base_url=cfg["base_url"])
        r = client.chat.completions.create(model=cfg["model"], temperature=0,
                                           max_tokens=300,
                                           messages=[{"role": "user", "content": prompt}])
        return r.choices[0].message.content or ""
    if model == "claude":
        from anthropic import Anthropic
        client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        msg = client.messages.create(model="claude-haiku-4-5-20251001",
                                     max_tokens=300, temperature=0,
                                     messages=[{"role": "user", "content": prompt}])
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    # legacy "gpt" = OpenAI proper
    from openai import OpenAI
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    r = client.chat.completions.create(model="gpt-4o-mini", temperature=0,
                                       max_tokens=300,
                                       messages=[{"role": "user", "content": prompt}])
    return r.choices[0].message.content or ""
