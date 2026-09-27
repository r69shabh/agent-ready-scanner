# TEARDOWN.md — Why another checker?

| Tool | Level | Method | Metric | Gap |
|---|---|---|---|---|
| Moonshot K2VV (594★) | vendor API | black-box toolcall F1 + schema accuracy vs official API | trigger similarity, schema acc | tells you *which* provider drifts, not *why your API* lies |
| OpenRouter Exacto | router | routes to top tool-accuracy providers (tau2/LiveMCPBench) | tool success lift | consumer-side routing; doesn't fix your schema |
| VeriSpec / Ferndesk / openapi-agent-ready | static | lint OpenAPI text | style score | no live proof; misses 200-but-silent class entirely |
| Prefactor et al. | post-deploy | observe spans, LLM-judge | 56.6% success, silent % | after the damage; judge AUROC ≤0.65 |
| **This (pre-flight)** | your API | static + live GET probes + agent-sim + 1-line fix | silent-failure rate, miss rate | proves the lie *before* deploy, with mergeable diff |

Moat sketch: behavioral evidence (curl-reproducible) + fix generation + CI gate. Static linters can't copy without live harness; observability can't move pre-deploy without schema analysis. Biggest risk: OpenRouter/Vercel ships "deploy check" — mitigate by owning the fix-PR + CI niche for startups.
