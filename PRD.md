# PRD — Agent-Ready Scanner v0

## 1. Problem
Agents fail silently in production. The API returns HTTP 200 + plausible JSON, the agent reports success, downstream state is wrong. Prefactor (4.5M runs): 56.6% true success; 45–75% of failures silent. SilentProbe (2,501 OpenAPI docs, 27 live vendors, 12 models): prose-only constraints fail silently 44/61 (p=2e-13); exemplified vocab missed 88/88; agents detect 12%, repair 0%, hallucinate 12%, false-negative 41%.

## 2. User
Startup API owner / founding engineer shipping an agent on their own API in the next 2–4 weeks. No eval team. Budget ~$10–100 for pre-flight. Success = "show me where my API will lie to the agent, with a fix I can merge today."

Non-user (v0): platform observability buyers (Prefactor covers post-deploy), engine contributors (vLLM crowd).

## 3. One thing it must get right
Every finding must include a **live repro** (request → 200 response proving silence) or be labeled `static-only, unconfirmed`. Never cry wolf on static heuristics alone. (This is the trust decision — same class as HelloPM's feedback-tool rule "never invent a theme.")

## 4. Scope v0 (M2, ~$10 credits)
- IN: OpenAPI 3.x (JSON/YAML, URL or file); static analysis; read-only GET live probes (default max 30 reqs); offline heuristic agent-sim; 1-line `enum` fix diffs; HTML report; A–F grade.
- OUT: mutations (POST/PUT/DELETE need explicit flag, off in v0); auth'd endpoints (report as skipped); LLM-judge as primary verdict (only as supplement; deterministic checks decide); hosted SaaS/billing; CI action (v1).

## 5. Decisions & tradeoffs
1. **Behavioral over static.** Static linters (VeriSpec, openapi-agent-ready) flag style; we prove silence live. Costs requests + time, but it's the only claim users believe.
2. **GET-only default.** Loses coverage on write paths (where money moves). Keeps v0 safe to run against prod. Write-path support = guided replay with sandbox flag in v1.
3. **Offline heuristic agent-sim first, LLM sim optional.** LLM sim costs credits + nondeterminism. Heuristic (would an agent know the allowed values from schema alone?) reproduces the 88/88 miss class deterministically. LLM run is `--agent-model claude|gpt|both`.
4. **Grade caps, not averages.** One live silent failure → max C; one hallucination → max D. Averages hide lies; caps surface them.
5. **Redact + label.** Auth headers redacted; every live finding shows curl + status + body excerpt so the owner can rerun in 30s.

## 6. Metrics (see EVAL.md)
- North star: silent-failure rate per API (live-proven / probes run).
- Leading: prose-only constraint %, enum coverage, agent miss rate.
- Product: fix-merge rate (did the 1-line enum get merged?), rerun delta (88/88 → 0/89 story).
- Guardrail: max requests respected, $/scan, zero mutating calls in default mode.

## 7. Demo story (2 min)
"Here's Petstore `status` — description says `available, pending, sold`, schema says `string`. Watch: `?status=banana` → 200 + list. Agent asked for `available`, got mixed list, told user 'all available'. One-line fix: add `enum: [available, pending, sold]`. Rerun → honest 400."
