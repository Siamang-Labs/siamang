"""Live tiles: a flow publishes values a dashboard shows.

``publish(node, kind, label, value)`` is the one call node templates make. Outside
a platform it is a no-op that only records what was published, so a generated
script runs unchanged from the command line; a platform, a test or
:class:`~siamang.flow.runner.FlowRunner` installs a *sink* to receive tiles::

    with live.capture() as tiles:
        run_the_flow()
    tiles  # -> [Tile(node="tile_n", kind="number", label="Clean respondents", value=1198)]

A chart tile carries the chart (``value``, whose picture a platform saves) and,
when the chart has an interactive form, its Vega-Lite spec (``spec``:
``SurveyChart.vega_lite()``, see :mod:`siamang.reporting.vega`), which a
dashboard draws with a tooltip on every mark — the picture when it cannot.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

TILE_KINDS = ("number", "table", "chart", "stat", "text")


@dataclass(frozen=True, slots=True)
class Tile:
    node: str
    kind: str
    label: str
    value: Any
    #: A chart tile's Vega-Lite spec, or None (another kind, or a chart
    #: without an interactive form).
    spec: dict[str, Any] | None = None


Sink = Callable[[Tile], None]

_sinks: list[Sink] = []


def publish(
    node: str,
    *,
    kind: str,
    label: str,
    value: Any,
    metric: str = "value",
) -> Tile:
    """Publish ``value`` for the tile of ``node``.

    ``metric`` says what to show of the value: ``"value"`` publishes it as is,
    ``"rows"`` publishes the number of rows of a ``SurveyData`` or frame.
    """

    if kind not in TILE_KINDS:
        raise ValueError(f"Unknown tile kind {kind!r}; expected one of {', '.join(TILE_KINDS)}.")
    if metric == "rows":
        frame = getattr(value, "frame", value)
        value = int(len(frame))
    elif metric != "value":
        raise ValueError(f"Unknown tile metric {metric!r}; expected 'value' or 'rows'.")
    tile = Tile(node=node, kind=kind, label=label, value=value, spec=_spec(kind, value))
    for sink in list(_sinks):
        sink(tile)
    return tile


def _spec(kind: str, value: Any) -> dict[str, Any] | None:
    """A chart tile's Vega-Lite spec — None for another kind, a chart without
    one, and a spec that could not be made: a tile never fails the run, and
    its picture is still there."""

    make = getattr(value, "vega_lite", None) if kind == "chart" else None
    if not callable(make):
        return None
    try:
        spec = make()
    except Exception as exc:  # noqa: BLE001 - the picture is kept, and the warning says why
        import warnings

        warnings.warn(
            f"Live tile chart: no interactive chart ({type(exc).__name__}: {exc}); "
            "its picture is kept.",
            RuntimeWarning,
            stacklevel=3,
        )
        return None
    return spec if isinstance(spec, dict) else None


def add_sink(sink: Sink) -> None:
    """Receive every tile published from now on."""

    _sinks.append(sink)


def remove_sink(sink: Sink) -> None:
    with contextlib.suppress(ValueError):
        _sinks.remove(sink)


@contextlib.contextmanager
def capture() -> Iterator[list[Tile]]:
    """Collect the tiles published inside the block."""

    tiles: list[Tile] = []
    add_sink(tiles.append)
    try:
        yield tiles
    finally:
        remove_sink(tiles.append)


__all__ = ["TILE_KINDS", "Tile", "add_sink", "capture", "publish", "remove_sink"]
