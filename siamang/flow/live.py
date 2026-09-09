"""Live tiles: a flow publishes values a dashboard shows.

``publish(node, kind, label, value)`` is the one call node templates make. Outside
a platform it is a no-op that only records what was published, so a generated
script runs unchanged from the command line; a platform, a test or
:class:`~siamang.flow.runner.FlowRunner` installs a *sink* to receive tiles::

    with live.capture() as tiles:
        run_the_flow()
    tiles  # -> [Tile(node="tile_n", kind="number", label="Clean respondents", value=1198)]
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
    tile = Tile(node=node, kind=kind, label=label, value=value)
    for sink in list(_sinks):
        sink(tile)
    return tile


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
