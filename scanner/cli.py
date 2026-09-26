"""CLI: scan --spec <file|url> [--base-url ...] [--no-live] [--agent-model ...] --report out.html"""
from __future__ import annotations

import json
from pathlib import Path

import click
from jinja2 import Template
from rich.console import Console
from rich.table import Table

import httpx

from . import __version__
from .agent_sim import llm_sim, offline_sim
from .fixes import enum_fix_snippet, generic_fix
from .grade import grade
from .live import PROBE_HEADERS, run_probes
from .spec import get_operations, load_spec
from .static import analyze

console = Console()


@click.group()
@click.version_option(__version__)
def cli() -> None:
    """Agent-Ready Scanner — will your API survive AI agents?"""


@cli.command()
@click.option("--spec", "spec_src", required=True, help="OpenAPI file path or URL")
@click.option("--base-url", default=None, help="Live server base URL for GET probes")
@click.option("--no-live", is_flag=True, help="Static + offline sim only ($0)")
@click.option("--agent-model", default="offline",
              type=click.Choice(["offline", "claude", "gpt"]),
              help="Agent sim mode (llm modes need API keys)")
@click.option("--max-requests", default=30, show_default=True)
@click.option("--report", default="reports/report.html", show_default=True)
@click.option("--json-out", default=None, help="Also write machine-readable JSON")
def scan(spec_src: str, base_url: str | None, no_live: bool,
         agent_model: str, max_requests: int, report: str,
         json_out: str | None) -> None:
    spec = load_spec(spec_src)
    ops = get_operations(spec)
    static = analyze(spec, ops)

    live_ran = bool(base_url) and not no_live
    live = run_probes(base_url, ops, max_requests=max_requests) if live_ran else []

    prose_params = {f.param for f in static.prose_only}
    if agent_model == "offline":
        agent = offline_sim(ops, prose_params)
    else:
        try:
            agent = llm_sim(ops, model=agent_model)
        except Exception as e:
            console.print(f"[yellow]LLM sim failed ({e}); falling back to offline.[/yellow]")
            agent = offline_sim(ops, prose_params)

    g = grade(static.static_score,
              [f.verdict for f in live],
              [t.outcome for t in agent], live_ran)

    # Console summary
    table = Table(title=f"Agent-Ready: {g.letter} ({g.score})")
    table.add_column("Layer"); table.add_column("Result")
    table.add_row("Static", f"{static.enum_coverage}% enum, {static.machine_pct}% machine, "
                            f"{static.prose_only_pct}% prose-only ({len(static.prose_only)} findings)")
    table.add_row("Live", f"{len(live)} probes: "
                          f"{sum(1 for f in live if f.verdict=='silent')} silent, "
                          f"{sum(1 for f in live if f.verdict=='honest')} honest, "
                          f"{sum(1 for f in live if f.verdict=='inconclusive')} inconclusive"
                  if live_ran else "skipped (static-only)")
    table.add_row("Agent", ", ".join(f"{t.outcome}" for t in agent[:5]))
    if g.capped_by:
        table.add_row("Cap", g.capped_by)
    console.print(table)

    # Top fixes
    top_fixes: list[str] = []
    for f in static.prose_only[:3]:
        top_fixes.append(enum_fix_snippet(f.param, f.suggested_enum)
                         if f.suggested_enum else generic_fix(f.kind, f.param))
    while len(top_fixes) < 3:
        top_fixes.append(generic_fix("review", "remaining findings in report"))

    # HTML report
    live_rows = [dict(operation=f.operation, probe=f.probe, url=f.url,
                      status=f.status, verdict=f.verdict, evidence=f.evidence,
                      evidence_body=f.evidence, curl=f.curl) for f in live]
    # attach truncated bodies already in evidence; keep template happy
    tmpl = Template(Path(__file__).with_name("report.html").read_text())
    html = tmpl.render(grade=g, static=static, ops=ops, live=live_rows,
                       live_ran=live_ran, agent=agent, top_fixes=top_fixes,
                       spec_source=spec_src, max_requests=max_requests, fixes=__import__("scanner.fixes", fromlist=["x"]))
    Path(report).parent.mkdir(parents=True, exist_ok=True)
    Path(report).write_text(html)
    console.print(f"[green]Report -> {report}[/green]")

    if json_out:
        payload = {"grade": {"letter": g.letter, "score": g.score, "cap": g.capped_by},
                   "static": {"enum_coverage": static.enum_coverage, "machine_pct": static.machine_pct,
                              "prose_only_pct": static.prose_only_pct,
                              "prose_only": [vars(f) for f in static.prose_only]},
                   "live": [vars(f) for f in live],
                   "agent": [vars(t) for t in agent]}
        Path(json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(json_out).write_text(json.dumps(payload, indent=2))
        console.print(f"[green]JSON -> {json_out}[/green]")


if __name__ == "__main__":
    cli()
