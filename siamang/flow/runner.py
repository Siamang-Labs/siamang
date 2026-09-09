"""Execute a flow in-process, node by node.

:class:`FlowRunner` walks the graph in :func:`~siamang.flow.document.node_order`
and executes every node's rendered template in one shared namespace — the
same text :func:`~siamang.flow.codegen.generate_flow` writes into a script.
Platform-only nodes (``source.responses``, ``source.table``,
``output.write_table``) are the exception: a source is fed from ``sources``
(a ``SurveyData`` or a snapshot path per node id) and a write is skipped
unless a ``db`` object is supplied.

    runner = FlowRunner(flow, questionnaire=survey)
    result = runner.run(sources={"src": "data/responses.parquet"}, cwd="work")
    result.outputs["xtab"]["table"].to_frame()
    result.tiles
"""

from __future__ import annotations

import contextlib
import os
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from siamang.core.questionnaire import Questionnaire
from siamang.data.survey_data import SurveyData
from siamang.flow import live
from siamang.flow.document import FlowError, FlowGraph, resolve_flow
from siamang.flow.registry import Registry
from siamang.flow.template import output_names, render_node
from siamang.io.snapshot import read_snapshot


@dataclass(frozen=True, slots=True)
class NodeRun:
    node: str
    state: str  # ok | skipped | error
    ms: int
    code: str
    error: str | None = None


@dataclass(slots=True)
class FlowResult:
    order: list[str]
    outputs: dict[str, dict[str, Any]]
    runs: list[NodeRun]
    tiles: list[live.Tile]
    namespace: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def ok(self) -> bool:
        return all(run.state != "error" for run in self.runs)

    def output(self, node_id: str, port: str | None = None) -> Any:
        ports = self.outputs[node_id]
        if port is None:
            if len(ports) != 1:
                raise KeyError(f"Node {node_id} has outputs {', '.join(ports)}; name one.")
            return next(iter(ports.values()))
        return ports[port]


class FlowRunner:
    def __init__(
        self,
        document: dict[str, Any],
        *,
        questionnaire: Questionnaire | None = None,
        registry: Registry | None = None,
        questionnaire_document: dict[str, Any] | None = None,
    ) -> None:
        self.graph: FlowGraph = resolve_flow(
            document, registry=registry, questionnaire=questionnaire_document
        )
        self.questionnaire = questionnaire

    def run(
        self,
        *,
        sources: Mapping[str, SurveyData | str | Path] | None = None,
        db: Any = None,
        cwd: str | Path | None = None,
        upto: str | None = None,
        raise_on_error: bool = True,
    ) -> FlowResult:
        """Execute the flow (or every node up to and including ``upto``).

        ``sources`` feeds platform sources by node id; ``db`` stands in for the
        platform database module (``as_survey_data`` / ``write_table``);
        ``cwd`` is where relative output paths land.
        """

        graph = self.graph
        order = list(graph.order)
        if upto is not None:
            if upto not in graph.nodes:
                raise FlowError(f"Unknown node {upto!r}.")
            needed = _ancestors(graph, upto) | {upto}
            order = [node_id for node_id in order if node_id in needed]

        namespace: dict[str, Any] = {"__name__": "__siamang_flow__"}
        if self.questionnaire is not None:
            namespace["survey"] = self.questionnaire
        if db is not None:
            namespace["db"] = db
        self._import(namespace, graph)

        outputs: dict[str, dict[str, Any]] = {}
        runs: list[NodeRun] = []
        with live.capture() as tiles, _chdir(cwd):
            for node_id in order:
                spec = graph.specs[node_id]
                names = output_names(node_id, spec)
                started = time.perf_counter()
                code = render_node(graph, node_id)
                try:
                    if spec.snapshot and (sources is None or node_id not in sources):
                        if db is None:
                            raise FlowError(
                                f"Source {node_id} ({spec.type}) needs data: pass sources={{{node_id!r}: …}}."
                            )
                        exec(code, namespace)  # noqa: S102 - the registry's own template
                    elif spec.snapshot:
                        data = self._source(sources[node_id])
                        namespace[names["data"]] = data
                        code = f"{names['data']} = <{type(data).__name__} from sources>"
                    elif spec.platform and db is None:
                        runs.append(
                            NodeRun(node_id, "skipped", 0, code, "platform-only node; pass db=…")
                        )
                        continue
                    else:
                        exec(code, namespace)  # noqa: S102 - the registry's own template
                except Exception as exc:  # noqa: BLE001 - reported per node
                    ms = int((time.perf_counter() - started) * 1000)
                    runs.append(NodeRun(node_id, "error", ms, code, f"{type(exc).__name__}: {exc}"))
                    if raise_on_error:
                        raise FlowError(f"Node {node_id} ({spec.type}) failed: {exc}") from exc
                    break
                ms = int((time.perf_counter() - started) * 1000)
                outputs[node_id] = {port: namespace.get(name) for port, name in names.items()}
                runs.append(NodeRun(node_id, "ok", ms, code))
        return FlowResult(
            order=order, outputs=outputs, runs=runs, tiles=list(tiles), namespace=namespace
        )

    def _source(self, value: SurveyData | str | Path) -> SurveyData:
        if isinstance(value, SurveyData):
            return value
        return read_snapshot(value, questionnaire=self.questionnaire)

    @staticmethod
    def _import(namespace: dict[str, Any], graph: FlowGraph) -> None:
        statements: set[str] = set()
        for node_id in graph.order:
            spec = graph.specs[node_id]
            if spec.platform:
                continue  # its module is the platform SDK; `db` is injected instead
            statements.update(spec.imports)
        for statement in sorted(statements):
            exec(statement, namespace)  # noqa: S102 - import statements from the registry


def _ancestors(graph: FlowGraph, node_id: str) -> set[str]:
    seen: set[str] = set()
    stack = list(graph.upstream(node_id))
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        stack.extend(graph.upstream(current))
    return seen


@contextlib.contextmanager
def _chdir(path: str | Path | None):
    if path is None:
        yield
        return
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    previous = os.getcwd()
    os.chdir(target)
    try:
        yield
    finally:
        os.chdir(previous)


__all__ = ["FlowResult", "FlowRunner", "NodeRun"]
