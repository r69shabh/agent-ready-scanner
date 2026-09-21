# Agent-Ready Scanner

**Will your API survive AI agents?**

Silent failures kill agents in production: the API returns `HTTP 200` with a plausible body, the agent thinks it succeeded, the user gets a wrong answer. Research shows:

- Production agents succeed only **56.6%** of the time (Prefactor, 4.5M runs); **45–75% of failures are silent**.
- Only **7.5%** of OpenAPI params declare `enum`, **15.2%** declare any machine-checkable constraint; **40.1%** state a constraint in prose the schema doesn't encode (SilentProbe, arXiv:2609.00035).
- Prose-only vocabularies: missed by every model **88/88**. Written in full: correct **88–91%**. Promoting vocab into schema: **88/88 → 0/89 failures**.
- LLM-judge catches false-success at max AUROC **0.65** — deterministic state checks win.

This scanner is a **pre-flight check** (not post-deploy observability): paste an OpenAPI URL → get an A–F grade, 3 live silent-failure repros, and a 1-line fix diff.

Built for Apple Silicon (M2, no GPU). Uses only public APIs + optional Claude/OpenAI credits.

## Quickstart

```bash
cd /Users/rishabh/agent-ready-scanner
pip install -r requirements.txt

# 1. Static-only scan (no network calls to target, $0)
python -m scanner.cli scan --spec samples/vulnerable_api.json --no-live --report reports/demo.html

# 2. Full scan with live read-only probes against a demo server
python -m scanner.cli scan --spec samples/vulnerable_api.json --base-url https://petstore3.swagger.io/api/v3 --report reports/full.html

# 3. Scan any public OpenAPI
python -m scanner.cli scan --spec https://petstore3.swagger.io/api/v3/openapi.json --no-live --report reports/petstore.html
```

## What it checks

| Layer | Checks | Source |
|---|---|---|
| Static | enum coverage, machine-checkable %, prose-only constraints, missing descriptions/examples, error-schema honesty | SilentProbe §2 |
| Live (read-only GET) | invalid-enum accepted as 200, ignored-param still 200, empty-filter 200-with-empty vs honest 400, prose-only value silently ignored | SilentProbe §3 (219 perturbations) |
| Agent sim | 5 tasks via Claude/OpenAI (or offline heuristic if no key); measures miss / false-negative / hallucination | SilentProbe §4 + Prefactor taxonomy |
| Fix | prose → `enum:` diff, one line per finding | SilentProbe fix result |

## Grading

- Score = 0.4*static + 0.4*live + 0.2*agent (0–100) → A ≥90, B ≥75, C ≥60, D ≥40, F <40
- Any live silent failure caps grade at C. Any hallucinated figure caps at D.

## Safety

- Live probes default to **GET-only, read-only**. `--allow-mutations` is required for POST/PUT/DELETE (never enabled in v0).
- Sends `X-Agent-Ready-Probe: 1` header. Respects `--max-requests` (default 30).
- Redacts `Authorization` values from reports.

## Portfolio mapping (for startup AI PM roles)

- `PRD.md` — problem, user, metric, tradeoff decisions
- `EVAL.md` — eval plan: silent-failure rate, fix acceptance, guardrails
- `TEARDOWN.md` — KVV vs Exacto vs static linters vs this
- `reports/` — shareable HTML evidence

See `PRD.md` for the full product story.
