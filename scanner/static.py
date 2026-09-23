"""Static analysis: enum coverage, machine-checkable %, prose-only constraints.

Implements the SilentProbe §2 layer: only ~7.5% of params declare enum,
~15.2% declare any machine-checkable constraint, while ~40.1% state a
constraint in prose the schema doesn't encode. Prose-only is the top
silent-failure predictor (44/61 silent, p=2e-13).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

CONSTRAINT_PATTERNS = [
    r"one of",
    r"allowed values?",
    r"must be",
    r"should be",
    r"can be",
    r"either",
    r"valid values?",
    r"possible values?",
    r"e\.g\.",
    r"such as",
    r"options?:",
]

EXAMPLE_LIST_RE = re.compile(
    r"(?:one of|allowed values?|valid values?|possible values?|either|options?)\s*:?\s*"
    r"[`\"']?([\w\-,\s|`\"']+)",
    re.IGNORECASE,
)


def _extract_example_values(description: str) -> list[str]:
    m = EXAMPLE_LIST_RE.search(description or "")
    if not m:
        return []
    chunk = m.group(1)
    parts = re.split(r"[,|/]", chunk)
    vals = []
    for p in parts:
        p = p.strip().strip("`\"'").strip()
        if p and len(p) <= 40 and " " not in p:
            vals.append(p)
        if len(vals) >= 12:
            break
    return vals


def _mentions_constraint(description: str) -> bool:
    d = (description or "").lower()
    return any(re.search(p, d) for p in CONSTRAINT_PATTERNS)


def _is_machine_checkable(param: dict[str, Any]) -> bool:
    schema = param.get("schema") or {}
    # direct or content-encoded schema
    if "content" in param:
        try:
            media = next(iter(param["content"].values()))
            schema = media.get("schema", {}) or schema
        except StopIteration:
            pass
    for key in ("enum", "pattern", "minimum", "maximum", "minLength",
                "maxLength", "format", "exclusiveMinimum", "exclusiveMaximum"):
        if key in schema and schema[key] not in (None, "", []):
            return True
    return False


@dataclass
class StaticFinding:
    param: str
    location: str  # query/path/header/cookie
    operation: str
    kind: str  # prose-only | missing-description | missing-example | ok-enum
    confidence: str  # high | medium
    description: str
    suggested_enum: list[str] = field(default_factory=list)


@dataclass
class StaticResult:
    total_params: int
    enum_params: int
    machine_checkable: int
    prose_only: list[StaticFinding]
    missing_docs: list[StaticFinding]
    enum_coverage: float
    machine_pct: float
    prose_only_pct: float
    static_score: float


def analyze(spec: dict[str, Any], operations: list[dict[str, Any]]) -> StaticResult:
    total = 0
    enum_c = 0
    machine_c = 0
    prose_only: list[StaticFinding] = []
    missing: list[StaticFinding] = []

    for op in operations:
        for p in op["parameters"]:
            if not isinstance(p, dict):
                continue
            name = p.get("name", "?")
            loc = p.get("in", "?")
            desc = p.get("description", "") or ""
            total += 1
            schema = p.get("schema") or {}
            if schema.get("enum"):
                enum_c += 1
            if _is_machine_checkable(p):
                machine_c += 1
            elif _mentions_constraint(desc):
                vals = _extract_example_values(desc)
                prose_only.append(StaticFinding(
                    param=name, location=loc,
                    operation=f"{op['method']} {op['path']}",
                    kind="prose-only",
                    confidence="high" if vals else "medium",
                    description=desc[:300],
                    suggested_enum=vals,
                ))
            if not desc:
                missing.append(StaticFinding(
                    param=name, location=loc,
                    operation=f"{op['method']} {op['path']}",
                    kind="missing-description", confidence="medium",
                    description="(no description)",
                ))

    enum_cov = (enum_c / total * 100) if total else 100.0
    machine_pct = (machine_c / total * 100) if total else 100.0
    prose_pct = (len(prose_only) / total * 100) if total else 0.0

    # Static score: reward enum/machine coverage, penalize prose-only.
    static_score = max(0.0, min(100.0,
        0.5 * enum_cov + 0.5 * machine_pct - 1.5 * prose_pct))

    return StaticResult(
        total_params=total, enum_params=enum_c,
        machine_checkable=machine_c, prose_only=prose_only,
        missing_docs=missing, enum_coverage=round(enum_cov, 1),
        machine_pct=round(machine_pct, 1),
        prose_only_pct=round(prose_pct, 1),
        static_score=round(static_score, 1),
    )
