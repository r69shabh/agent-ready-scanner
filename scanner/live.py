"""Live read-only probes (GET-only by default).

SilentProbe §3 method: send schema-derived perturbations and classify:
- honest: 4xx/5xx with error field, or provably filtered response
- silent: 2xx + parsable body + no error field + invalid input accepted
- inconclusive: network/auth/empty-spec cases (labeled, never fail grade alone)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx

PROBE_HEADERS = {"X-Agent-Ready-Probe": "1", "User-Agent": "agent-ready-scanner/0.1"}
INVALID_TOKEN = "__invalid__"
ERROR_KEYS = ("error", "errors", "message", "detail", "fault", "code")


@dataclass
class LiveFinding:
    operation: str
    probe: str  # invalid-enum | ignored-param | empty-filter
    url: str
    status: int | str
    verdict: str  # silent | honest | inconclusive
    evidence: str
    curl: str


def _classify(status: int, body_text: str, probe_value: str) -> tuple[str, str]:
    lowered = body_text.lower()
    has_error_field = any(f'"{k}"' in lowered for k in ERROR_KEYS)
    if 400 <= status < 600:
        return ("honest", f"HTTP {status} with {'error field' if has_error_field else 'no body'}")
    if 200 <= status < 300:
        if has_error_field and ("invalid" in lowered or "not valid" in lowered or "bad request" in lowered):
            return ("honest", f"HTTP {status} but body reports the error")
        if probe_value in body_text:
            return ("silent", f"HTTP {status}; echo/accept of invalid value, no error field")
        return ("silent", f"HTTP {status} with parsable body, invalid input accepted, no error field")
    return ("inconclusive", f"HTTP {status}")


def run_probes(base_url: str | None, operations: list[dict[str, Any]],
               static_prose_params: set[str] | None = None,
               max_requests: int = 30, timeout: float = 15.0) -> list[LiveFinding]:
    findings: list[LiveFinding] = []
    if not base_url:
        return findings
    base = base_url.rstrip("/")
    budget = max_requests

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        for op in operations:
            if budget <= 0:
                break
            if op["method"] != "GET":
                continue  # read-only default
            query_params = [p for p in op["parameters"]
                            if isinstance(p, dict) and p.get("in") == "query"]
            if not query_params:
                continue
            first = query_params[0]
            pname = first.get("name", "q")
            path = op["path"].replace("{", "").replace("}", "")
            op_label = f"{op['method']} {op['path']}"

            probes = [
                ("invalid-enum", {pname: INVALID_TOKEN}),
                ("ignored-param", {pname: "test", "___probe_nonsense": "1"}),
            ]
            for probe_name, params in probes:
                if budget <= 0:
                    break
                budget -= 1
                url = f"{base}{path}?{urlencode(params)}"
                curl = f"curl -H 'X-Agent-Ready-Probe: 1' '{url}'"
                try:
                    r = client.get(url, params=None, headers=PROBE_HEADERS)
                    body = r.text[:500]
                    verdict, evidence = _classify(r.status_code, r.text, INVALID_TOKEN)
                except Exception as e:  # network/auth issues -> inconclusive
                    verdict, evidence = "inconclusive", f"request failed: {type(e).__name__}: {e}"
                    findings.append(LiveFinding(op_label, probe_name, url, "ERR", verdict, evidence, curl))
                    continue
                findings.append(LiveFinding(op_label, probe_name, url, r.status_code, verdict, evidence, curl))
    return findings
