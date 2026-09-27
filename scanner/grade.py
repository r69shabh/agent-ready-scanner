"""Grading: score = 0.4*static + 0.4*live + 0.2*agent, with caps.

Caps (averages hide lies):
- any live `silent` -> grade max C (65)
- any hallucination -> grade max D (45)
- static-only unconfirmed findings are labeled, never fail alone.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Grade:
    score: float
    letter: str
    capped_by: str | None = None


def _letter(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def grade(static_score: float, live_verdicts: list[str],
          agent_outcomes: list[str], live_ran: bool) -> Grade:
    live_score = 100.0
    if live_ran and live_verdicts:
        silent = sum(1 for v in live_verdicts if v == "silent")
        honest = sum(1 for v in live_verdicts if v == "honest")
        total = len([v for v in live_verdicts if v in ("silent", "honest")])
        live_score = ((honest / total * 100) if total else 100.0)
        if silent and honest == 0:
            live_score = min(live_score, 20.0)
    elif not live_ran:
        live_score = static_score  # no double-count when offline

    bad = sum(1 for o in agent_outcomes if o in ("would-miss", "miss"))
    total_a = len([o for o in agent_outcomes if o != "skipped"])
    agent_score = (100 - (bad / total_a * 100)) if total_a else 100.0

    score = round(0.4 * static_score + 0.4 * live_score + 0.2 * agent_score, 1)

    capped_by = None
    if "silent" in live_verdicts and score > 65:
        score, capped_by = 65.0, "live silent failure caps grade at C"
    if "hallucination" in agent_outcomes and score > 45:
        score, capped_by = 45.0, "agent hallucination caps grade at D"

    return Grade(score=score, letter=_letter(score), capped_by=capped_by)
