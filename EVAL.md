# EVAL.md — Eval plan

## 1. What we measure (and why)
| Metric | Definition | Target | Source |
|---|---|---|---|
| Silent-failure rate | live probes returning 200+plausible when they should error / filter | report raw # + % | SilentProbe live-perturb method |
| Prose-only constraint % | params with prose constraint but no schema encoding | <10% for A | SilentProbe 40.1% baseline |
| Enum coverage | enum-typed params / value-constrained params | >80% for A | SilentProbe 7.5% baseline |
| Agent miss rate | tasks where simulated agent uses invalid/unlisted value | 0 for A | 88/88 miss class |
| False-negative / hallucination | agent says "nothing found" when data exists / invents figure | 0; caps grade D | 41% / 12% baselines |
| Fix acceptance | 1-line diffs merged or accepted | ≥1 per scan (v0 qualitative) | 88/88→0/89 story |
| Cost / safety | requests sent, $ spent, mutating calls | ≤30 reqs, $0 static, 0 mutations default | guardrail |

## 2. Method
- **Static:** parse OpenAPI; for each param with description matching constraint patterns (`one of`, `allowed values`, `must be`, `e.g.`) but without `enum`/`pattern`/`minimum`/`maximum` → `prose-only`. Confidence: high if pattern + example list extractable; medium otherwise. Mediums never fail the grade alone.
- **Live (GET-only):** for each candidate: (a) invalid-enum probe (`?status=__invalid__`), (b) ignored-param probe (nonsense param), (c) empty-filter probe. Verdict `silent` iff 2xx + body parses + no error field and (for a) no 400/422 and response not provably filtered. All else → `honest` or `inconclusive` (labeled).
- **Agent-sim offline:** "could an agent know allowed values from schema alone?" If allowed values only in prose → `would-miss`. This deterministically reproduces the exemplified-vocab class without credits.
- **Agent-sim LLM (optional):** 5 tasks, temp 0, tool schema = OpenAPI-derived JSON schema. Score miss/false-negative/hallucination by deterministic post-checks (not LLM-judge; judges cap at 0.65 AUROC per Prefactor).

## 3. Pass/fail & grading
Score = 0.4*static + 0.4*live + 0.2*agent → A≥90 B≥75 C≥60 D≥40 F<40. Caps: any live `silent` → ≤C (65); any hallucination → ≤D (45); any medium-only evidence → append `unconfirmed`.

## 4. Baselines & regression
- `samples/vulnerable_api.json` must score ≤C with ≥2 live-silent (or static-high if offline) — guards against grade inflation.
- `samples/healthy_api.json` must score ≥B with 0 silent — guards against false alarms.
- Store `reports/*.json` + rerun diff in v1 CI.

## 5. Risks
LLM nondeterminism (mitigate: temp 0, 5 tasks, deterministic post-checks); target rate limits (mitigate: max-requests, backoff, read-only); auth walls (label skipped, don't penalize); PII in bodies (truncate to 500 chars, redact tokens).
