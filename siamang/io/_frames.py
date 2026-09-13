"""Frames the metadata-carrying writers can store.

SPSS and Stata cells are scalars. A multiple-choice answer arrives as a list
of codes (``[1, 3]``) and a ranking as an ordered list; a respondent who never
saw the question has ``None`` in the same column. ``scalar_frame`` turns a
list into the codes joined with ``;`` (``"1;3"``) and a mapping into JSON,
leaving missing values missing, so a column mixes only strings and NaN.

Every text format writes that same ``1;3`` — CSV, Excel, SPSS and Stata — so
the answers do not depend on which download button was pressed, and
``list_frame`` reads them back where the questionnaire says the column holds
several answers. Parquet is the exception and keeps the real list, because the
format can.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd


def _scalar(value: Any) -> Any:
    if isinstance(value, list | tuple):
        return ";".join("" if item is None else str(item) for item in value)
    if isinstance(value, Mapping):
        return json.dumps(dict(value), ensure_ascii=False)
    return value


def scalar_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """A copy of ``frame`` whose object columns hold scalars only."""

    out = frame.copy()
    for column in out.columns:
        series = out[column]
        if (
            series.dtype == object
            and series.map(lambda v: isinstance(v, list | tuple | Mapping)).any()
        ):
            out[column] = series.map(_scalar)
    return out


def _code(token: str) -> Any:
    token = token.strip()
    if not token:
        return None
    try:
        return int(token)
    except ValueError:
        pass
    try:
        return float(token)
    except ValueError:
        return token


def list_frame(frame: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    """The inverse of :func:`scalar_frame` for columns known to hold lists.

    Only the named columns are touched, and only where a text format left a
    string: a frame read from Parquet already holds lists and passes through.

    An empty cell comes back as missing rather than as an empty list. The two
    are the same answer — "did not answer" — and no text format keeps them
    apart, so inventing a distinction on the way back in would be a fiction.
    """

    out = frame
    for column in columns:
        if column not in frame.columns:
            continue
        series = frame[column]
        if series.dtype != object or not series.map(lambda v: isinstance(v, str)).any():
            continue
        if out is frame:
            out = frame.copy()
        out[column] = series.map(
            lambda v: (
                [code for code in (_code(t) for t in v.split(";")) if code is not None] or None
            )
            if isinstance(v, str)
            else v
        )
    return out
