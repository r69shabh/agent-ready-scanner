"""One-line fix generation: promote prose constraints into schema enums."""
from __future__ import annotations


def enum_fix_snippet(param_name: str, values: list[str]) -> str:
    vals = "\n".join(f"              - {v}" for v in values)
    return (
        f"# Fix for query param `{param_name}` — paste into its `schema:`\n"
        f"          schema:\n"
        f"            type: string\n"
        f"            enum:\n{vals}\n"
        f"# Expected effect (SilentProbe): prose-only miss class 88/88 -> ~0/89"
    )


def generic_fix(kind: str, param: str) -> str:
    if kind == "missing-description":
        return (f"# Add a description + example to `{param}` so agents don't guess:\n"
                f"# description: \"...\" \n# example: \"...\"")
    return "# No automatic fix — needs human review."
