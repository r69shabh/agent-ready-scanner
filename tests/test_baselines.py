"""Eval baselines: vulnerable must score low w/ prose-only; healthy must score high."""
from scanner.grade import grade
from scanner.spec import get_operations
from scanner.static import analyze
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    return json.loads((ROOT / "samples" / name).read_text())


def test_vulnerable_has_prose_only():
    spec = _load("vulnerable_api.json")
    ops = get_operations(spec)
    st = analyze(spec, ops)
    assert len(st.prose_only) >= 1, "vulnerable fixture must have >=1 prose-only finding"
    assert st.prose_only_pct > 0
    g = grade(st.static_score, [], ["would-miss"], live_ran=False)
    assert g.score < 75, f"vulnerable should not grade B+: {g}"


def test_healthy_scores_high():
    spec = _load("healthy_api.json")
    ops = get_operations(spec)
    st = analyze(spec, ops)
    assert len(st.prose_only) == 0
    assert st.enum_coverage >= 50
    g = grade(st.static_score, [], ["ok"], live_ran=False)
    assert g.score >= 75, f"healthy should grade B+: {g}"


def test_caps():
    g = grade(95.0, ["silent", "honest"], ["ok"], live_ran=True)
    assert g.letter == "C" and g.score == 65.0
    g2 = grade(95.0, ["honest"], ["hallucination"], live_ran=True)
    assert g2.letter == "D" and g2.score == 45.0
