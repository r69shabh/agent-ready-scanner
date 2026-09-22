"""Load OpenAPI 3.x specs from file (JSON/YAML) or URL."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import yaml


def load_spec(source: str, timeout: float = 20.0) -> dict[str, Any]:
    if source.startswith("http://") or source.startswith("https://"):
        r = httpx.get(source, timeout=timeout, follow_redirects=True)
        r.raise_for_status()
        text = r.text
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return yaml.safe_load(text)
    p = Path(source)
    text = p.read_text()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return yaml.safe_load(text)


def get_operations(spec: dict[str, Any]) -> list[dict[str, Any]]:
    ops: list[dict[str, Any]] = []
    for path, methods in (spec.get("paths") or {}).items():
        if not isinstance(methods, dict):
            continue
        for method, op in methods.items():
            if method.startswith("x-") or not isinstance(op, dict):
                continue
            ops.append({
                "path": path,
                "method": method.upper(),
                "operationId": op.get("operationId", f"{method}_{path}"),
                "summary": op.get("summary", ""),
                "parameters": op.get("parameters", []) or [],
            })
    return ops
