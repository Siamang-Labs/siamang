"""Respondent-level cleaning: one row per respondent, completion time, partials.

Plain pandas functions over a responses frame, so they work on data from any
source — a platform table, a snapshot file, a simulated frame — and slot into
``SurveyData.with_frame(...)``::

    clean = data.with_frame(respondents.dedup_responses(data.frame))

A response frame carries, besides the answer columns, whatever the collector
added: ``respondent_id`` (set by the runtime so a resumed survey updates the
same row), ``started_at`` / ``submitted_at`` timestamps and, often, a
``duration_s`` column. The defaults below follow those names.
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd


def dedup_responses(
    df: pd.DataFrame,
    *,
    id_col: str = "respondent_id",
    order_by: str | None = "submitted_at",
    keep: str = "last",
) -> pd.DataFrame:
    """Collapse repeated submissions per respondent into one row.

    Rows are ordered by ``order_by`` (when the column exists) so that
    ``keep="last"`` retains the most recent submission and ``keep="first"``
    the earliest. Rows whose ``id_col`` is null or blank are anonymous: they
    are always kept, as distinct respondents. A frame without ``id_col`` is
    returned as a copy. The original row order is restored in the result.
    """

    if keep not in {"first", "last"}:
        raise ValueError("keep must be 'first' or 'last'.")
    if id_col not in df.columns:
        return df.copy()
    if order_by is not None and order_by not in df.columns:
        # A frame that names its timestamps differently — a platform responses
        # table has started_at/created_at, not submitted_at — would otherwise be
        # left unordered, and "keep the latest" would quietly keep an arbitrary
        # row. Fall back rather than pretend.
        order_by = next(
            (
                c
                for c in ("submitted_at", "started_at", "updated_at", "created_at")
                if c in df.columns
            ),
            None,
        )
    out = df
    if order_by and order_by in df.columns:
        out = out.sort_values(order_by, kind="stable")
    has_id = out[id_col].notna() & (out[id_col].astype(str).str.len() > 0)
    identified = out[has_id].drop_duplicates(subset=[id_col], keep=keep)
    anonymous = out[~has_id]
    combined = pd.concat([identified, anonymous])
    return combined.sort_index().reset_index(drop=True)


def completion_time(
    df: pd.DataFrame,
    *,
    start_col: str = "started_at",
    end_col: str = "submitted_at",
    duration_col: str | None = "duration_s",
) -> pd.Series:
    """Per-response completion time in seconds.

    Uses a numeric ``duration_col`` when the frame has one; otherwise the
    difference between the parsed ``end_col`` and ``start_col`` timestamps.
    Rows where neither is available get ``NaN``.
    """

    if duration_col and duration_col in df.columns:
        return pd.to_numeric(df[duration_col], errors="coerce")
    if start_col in df.columns and end_col in df.columns:
        start = pd.to_datetime(df[start_col], errors="coerce")
        end = pd.to_datetime(df[end_col], errors="coerce")
        return (end - start).dt.total_seconds()
    return pd.Series([float("nan")] * len(df), index=df.index, dtype=float)


def partial_flag(df: pd.DataFrame, required: Sequence[str]) -> pd.Series:
    """``True`` where any ``required`` column is null or blank — a partial response.

    A required column the frame does not have at all counts as missing for
    every row, so a misspelled name shows up immediately instead of passing
    everyone as complete.
    """

    missing = pd.Series(False, index=df.index)
    for col in required:
        if col not in df.columns:
            return pd.Series(True, index=df.index)
        null = df[col].isna() | (df[col].astype(str).str.len() == 0)
        missing = missing | null
    return missing


def speeders(
    df: pd.DataFrame,
    *,
    min_seconds: float,
    duration: pd.Series | None = None,
) -> pd.Series:
    """``True`` where the response was completed faster than ``min_seconds``.

    ``duration`` defaults to :func:`completion_time`; responses without a
    known duration are never flagged.
    """

    seconds = completion_time(df) if duration is None else duration
    return seconds.notna() & (seconds < float(min_seconds))


__all__ = ["completion_time", "dedup_responses", "partial_flag", "speeders"]
