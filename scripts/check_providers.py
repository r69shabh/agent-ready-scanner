"""Smoke-test free-tier LLM providers. Exits 0 only if replies parse.

Usage:
  export NVIDIA_API_KEY=... GROQ_API_KEY=...
  python3 scripts/check_providers.py
"""
import os
import sys

sys.path.insert(0, ".")


def check(name: str, key: str, base: str, model: str) -> bool:
    if not os.environ.get(key):
        print(f"{name}: SKIP (no {key})")
        return True
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ[key], base_url=base)
        r = client.chat.completions.create(
            model=model, temperature=0, max_tokens=20,
            messages=[{"role": "user", "content": "Reply with exactly: READY"}])
        text = (r.choices[0].message.content or "").strip()
        ok = "READY" in text.upper()
        print(f"{name}: {'OK' if ok else 'BAD-REPLY'} ({model} -> {text[:60]!r})")
        return ok
    except Exception as e:
        print(f"{name}: FAIL {type(e).__name__}: {str(e)[:200]}")
        return False


if __name__ == "__main__":
    from scanner.agent_sim import PROVIDERS
    nv = PROVIDERS["nvidia"]
    gq = PROVIDERS["groq"]
    ok = check("nvidia", nv["env_key"], nv["base_url"], nv["model"])
    ok = check("groq", gq["env_key"], gq["base_url"], gq["model"]) and ok
    sys.exit(0 if ok else 1)
