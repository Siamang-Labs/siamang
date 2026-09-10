"""Frames the metadata-carrying writers can store.

SPSS and Stata cells are scalars. A multiple-choice answer arrives as a list
of codes (``[1, 3]``) and a ranking as an ordered list; a respondent who never
saw the question has ``None`` in the same column. ``scalar_frame`` turns a
list into the codes joined with ``;`` (``"1;3"``) and a mapping into JSON,
leaving missing values missing, so a column mixes only strings and NaN.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
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
