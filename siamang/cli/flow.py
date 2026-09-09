"""`siamang flow` — check, run and describe analysis flows."""

from __future__ import annotations

import sys
from pathlib import Path

from siamang.flow import FlowError, FlowRunner, check_flow, default_registry
from siamang.flow.document import loads as load_flow
from siamang.model import DocumentError, from_document, loads


def _questionnaire(path: str | None):
    if path is None:
        return None, None
    document = loads(Path(path).read_text(encoding="utf-8"))
    return document, from_document(document).survey


def run_check(path: str, questionnaire: str | None = None) -> int:
    """``siamang flow check flow.json [--questionnaire questionnaire.json]``."""

    try:
        flow = load_flow(Path(path).read_text(encoding="utf-8"))
        qdoc, _survey = _questionnaire(questionnaire)
        issues = check_flow(flow, questionnaire=qdoc)
    except (OSError, ValueError, FlowError, DocumentError) as exc:
        print(f"validation error: {exc}")
        return 2
    if not issues:
        print("OK — no issues.")
        return 0
    exit_code = 0
    for issue in issues:
        suffix = f" ({issue.node})" if issue.node else ""
        print(f"[{issue.severity}] [{issue.code}] {issue.message}{suffix}")
        if issue.severity == "error":
            exit_code = 1
    return exit_code


def run_flow(
    path: str,
    *,
    data: list[str] | None,
    questionnaire: str | None,
    cwd: str | None = None,
    upto: str | None = None,
) -> int:
    """``siamang flow run flow.json --data snapshot [--questionnaire q.json] [--cwd dir]``."""

    try:
        flow = load_flow(Path(path).read_text(encoding="utf-8"))
        qdoc, survey = _questionnaire(questionnaire)
        runner = FlowRunner(flow, questionnaire=survey, questionnaire_document=qdoc)
        sources = _sources(runner, data or [])
        result = runner.run(sources=sources, cwd=cwd, upto=upto, raise_on_error=False)
    except (OSError, ValueError, FlowError, DocumentError) as exc:
        print(f"flow error: {exc}", file=sys.stderr)
        return 2
    for run in result.runs:
        line = f"{run.state:8} {run.node} ({run.ms} ms)"
        if run.error:
            line += f": {run.error}"
        print(line)
    for tile in result.tiles:
        value = (
            tile.value if isinstance(tile.value, int | float | str) else type(tile.value).__name__
        )
        print(f"tile     {tile.node} [{tile.kind}] {tile.label}: {value}")
    return 0 if result.ok else 1


def _sources(runner: FlowRunner, data: list[str]) -> dict[str, str]:
    """``--data path`` feeds the only snapshot source; ``--data node=path`` names one."""

    snapshot_nodes = [n for n in runner.graph.order if runner.graph.specs[n].snapshot]
    sources: dict[str, str] = {}
    for item in data:
        if "=" in item:
            node, path = item.split("=", 1)
            sources[node] = path
        elif len(snapshot_nodes) == 1:
            sources[snapshot_nodes[0]] = item
        elif not snapshot_nodes:
            raise FlowError("This flow has no data source that a snapshot can stand in for.")
        else:
            raise FlowError(
                "Several data sources; pass --data <node>=<path> for each of: "
                + ", ".join(snapshot_nodes)
            )
    return sources


def run_nodes(as_json: bool = False) -> int:
    """``siamang flow nodes [--json]`` — list the node registry."""

    registry = default_registry()
    if as_json:
        sys.stdout.write(registry.dumps())
        return 0
    for category, specs in registry.by_category().items():
        if not specs:
            continue
        print(f"{category}:")
        for spec in specs:
            params = ", ".join(
                f"{name}{'*' if param.required else ''}" for name, param in spec.params.items()
            )
            ports = " -> ".join(
                part
                for part in (
                    ", ".join(f"{n}: {'|'.join(p.types)}" for n, p in spec.inputs.items()),
                    ", ".join(f"{n}: {t}" for n, t in spec.outputs.items()),
                )
                if part
            )
            print(f"  {spec.type:26} {spec.title}  [{ports}]  {params}")
    return 0
