"""Excel cells that hold text as text.

openpyxl stores any string that begins with ``=`` as a formula, and pandas'
``to_excel`` hands it the strings as they are. A respondent's open answer
``=HYPERLINK("http://…","Click me")`` — or a label, a caption, a variable name
— then becomes a live formula in the workbook a report or an export ships,
and reading the file back gives no value for it at all (a formula has no
cached result until Excel computes one). Respondent text and names are data,
as Studio's own exports treat them: every cell :func:`to_excel` writes and
:func:`as_text` passes over keeps its text as a string. A link from one sheet
to another names the sheet as :func:`sheet_link` quotes it.

A cell holds no time zone either, and pandas refuses to write a time that has
one: the response times a platform's data carries (timezone-aware) stopped the
whole file. :func:`to_excel` writes such a time in UTC, without the zone.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pandas as pd


def as_text(sheets: Iterable[Any]) -> None:
    """Turn every formula cell of ``sheets`` (openpyxl worksheets) back into
    the text it was written as."""

    for sheet in sheets:
        for row in sheet.iter_rows():
            for cell in row:
                if cell.data_type == "f" and isinstance(cell.value, str):
                    cell.data_type = "s"


def _in_utc(value: Any) -> Any:
    """A time with a zone as the same moment in UTC, without the zone; any
    other value as it is."""
    if isinstance(value, dt.datetime) and value.tzinfo is not None:
        return pd.Timestamp(value).tz_convert("UTC").tz_localize(None)
    if isinstance(value, dt.time) and value.tzinfo is not None:
        return value.replace(tzinfo=None)
    return value


def without_zones(frame: pd.DataFrame) -> pd.DataFrame:
    """``frame`` with every time that has a time zone in UTC and without it —
    a column of them, one inside a column of objects, the index — which is
    what a workbook can hold. The frame given is left as it is; one with no
    such time comes back unchanged."""

    out = frame
    for position in range(frame.shape[1]):
        series = frame.iloc[:, position]
        if isinstance(series.dtype, pd.DatetimeTZDtype):
            fixed = series.dt.tz_convert("UTC").dt.tz_localize(None)
        elif (
            series.dtype == object
            and series.map(lambda v: getattr(v, "tzinfo", None) is not None).any()
        ):
            fixed = series.map(_in_utc)
        else:
            continue
        if out is frame:
            out = frame.copy()
        out.isetitem(position, fixed)
    if isinstance(out.index, pd.DatetimeIndex) and out.index.tz is not None:
        out = out.copy() if out is frame else out
        out.index = out.index.tz_convert("UTC").tz_localize(None)
    return out


def to_excel(
    frames: pd.DataFrame | Iterable[tuple[str, pd.DataFrame]], path: str | Path, **kwargs: Any
) -> Path:
    """Write ``frames`` — one frame, or ``(sheet name, frame)`` pairs — to the
    workbook ``path`` as ``DataFrame.to_excel`` does, text kept as text and a
    time with a zone in UTC (:func:`without_zones`). ``kwargs`` go to
    ``to_excel`` (``index=False``, ``sheet_name`` for one frame)."""

    path = Path(path)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        if isinstance(frames, pd.DataFrame):
            without_zones(frames).to_excel(writer, **kwargs)
        else:
            for name, frame in frames:
                without_zones(frame).to_excel(writer, sheet_name=name, **kwargs)
        as_text(writer.book.worksheets)
    return path


def sheet_link(name: str) -> str:
    """The place a link inside a workbook points to: the top of sheet
    ``name``, quoted and with an apostrophe in the name doubled, as Excel
    writes a sheet in a formula — ``'Brand''s image'!A1``. Unquoted, or with
    the apostrophe single, the link leads nowhere."""

    return "'" + name.replace("'", "''") + "'!A1"


__all__ = ["as_text", "sheet_link", "to_excel", "without_zones"]
