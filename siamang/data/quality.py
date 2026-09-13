"""Response-quality checks: straightlining, contradictions, duplicates.

The companion to :mod:`siamang.data.respondents`, which answers "how long did
this take and did they finish". These answer "does the pattern of answers look
like someone reading the questions".

Same shape as that module on purpose — a frame goes in, a boolean mask or a
Series comes out, and nothing is dropped here. Deciding what to do about a
flagged respondent belongs to the caller (the ``prepare.quality`` node defaults
to marking, not dropping), because "we removed the suspicious ones, trust us" is
not a claim a methods section can make.

Every check returns ``False`` for a respondent it cannot judge — too few items,
a column the frame does not have — so a misconfigured check flags nobody rather
than everybody. A check that was not configured at all is spelled ``None`` or an
empty sequence, and both mean the same thing: the flow codegen renders an unset
``mapping`` parameter as the literal ``None`` (see ``flow/template.py``), so the
generated script hands us one whenever the author left a check blank.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd

__all__ = [
    "attention_failed",
    "duplicate_pattern",
    "inconsistency",
    "quality_flags",
    "quality_score",
    "straightlining",
]

#: Reasons a response can be flagged, in the order they appear in
#: ``quality_flags``. The strings are stable: they end up in a variable's value
#: labels, in exports and in the report a methods section quotes.
REASONS = ("straightlining", "inconsistency", "duplicate", "attention")


def _present(frame: pd.DataFrame, columns: Sequence[str] | None) -> list[str]:
    return [c for c in (columns or []) if c in frame.columns]


def _differs(left: pd.Series, right: pd.Series) -> pd.Series:
    """Element-wise "these two answers disagree", comparing numbers as numbers.

    A column with a single missing answer is float in pandas, so the code ``3``
    arrives as ``3.0``. Comparing the two as text ("3.0" != "3") would report a
    contradiction — or a failed attention check — for every honest respondent in
    a battery that anyone skipped. Rows that are not both numeric fall back to
    text, which is what open answers and category strings need.
    """

    left_num = pd.to_numeric(left, errors="coerce")
    right_num = pd.to_numeric(right, errors="coerce")
    numeric = left_num.notna() & right_num.notna()
    return (numeric & (left_num != right_num)) | (
        ~numeric & (left.astype(str) != right.astype(str))
    )


def straightlining(
    frame: pd.DataFrame,
    items: Sequence[str] | None,
    *,
    max_sd: float = 0.0,
    min_items: int = 3,
) -> pd.Series:
    """``True`` where a respondent gave (near-)identical answers across ``items``.

    The classic flatliner: every row of a matrix answered "4". Measured as the
    standard deviation **across** the battery for one respondent, so it needs a
    battery worth measuring — fewer than ``min_items`` present columns flags
    nobody. ``max_sd=0.0`` is the strict reading (literally identical);
    raise it to catch "4,4,4,5".

    Rows with any missing answer in the battery are not flagged: an incomplete
    battery is a partial, which is a different finding.
    """

    present = _present(frame, items)
    if len(present) < max(2, min_items):
        return pd.Series(False, index=frame.index)
    numeric = frame[present].apply(pd.to_numeric, errors="coerce")
    spread = numeric.std(axis=1, ddof=0)
    complete = numeric.notna().all(axis=1)
    return complete & spread.notna() & (spread <= float(max_sd))


def inconsistency(
    frame: pd.DataFrame,
    pairs: Mapping[str, str] | Sequence[tuple[str, str]] | None,
) -> pd.Series:
    """``True`` where a respondent contradicted themselves.

    ``pairs`` names columns that should agree — a question and its reversed
    twin after recoding, or the same fact asked twice. A pair whose columns are
    not both present is skipped rather than counted as a contradiction.
    """

    if isinstance(pairs, Mapping):
        items: list[tuple[str, str]] = list(pairs.items())
    else:
        items = list(pairs or [])
    flagged = pd.Series(False, index=frame.index)
    for left, right in items:
        if left not in frame.columns or right not in frame.columns:
            continue
        a = frame[left]
        b = frame[right]
        both = a.notna() & b.notna()
        flagged = flagged | (both & _differs(a, b))
    return flagged


def duplicate_pattern(
    frame: pd.DataFrame,
    items: Sequence[str] | None,
    *,
    min_items: int = 5,
) -> pd.Series:
    """``True`` for every row sharing its exact answer pattern with another row.

    Two respondents answering a long battery identically is the signature of one
    person submitting twice, or of a script. Short batteries collide honestly —
    fewer than ``min_items`` present columns flags nobody — and **all** members
    of a colliding group are flagged, not just the later ones: which of them is
    the original is not ours to decide.
    """

    present = _present(frame, items)
    if len(present) < max(2, min_items):
        return pd.Series(False, index=frame.index)
    subset = frame[present]
    complete = subset.notna().all(axis=1)
    duplicated = subset.duplicated(keep=False)
    return complete & duplicated


def attention_failed(
    frame: pd.DataFrame,
    expected: Mapping[str, object] | None,
) -> pd.Series:
    """``True`` where an attention check was answered with anything but its
    expected value.

    ``expected`` maps a column to the answer a reading respondent gives. An
    unanswered check is not a failure — that is a partial.
    """

    flagged = pd.Series(False, index=frame.index)
    for column, want in (expected or {}).items():
        if column not in frame.columns:
            continue
        answered = frame[column].notna()
        wanted = pd.Series([want] * len(frame), index=frame.index)
        flagged = flagged | (answered & _differs(frame[column], wanted))
    return flagged


def quality_flags(
    frame: pd.DataFrame,
    *,
    items: Sequence[str] | None = (),
    pairs: Mapping[str, str] | Sequence[tuple[str, str]] | None = (),
    expected: Mapping[str, object] | None = None,
    max_sd: float = 0.0,
) -> pd.Series:
    """One string per respondent naming every check they failed, ``""`` if none.

    The reasons are joined with ``"; "`` in :data:`REASONS` order, so the column
    reads as an explanation rather than a verdict: ``"straightlining; duplicate"``.
    """

    checks = {
        "straightlining": straightlining(frame, items, max_sd=max_sd) if items else None,
        "inconsistency": inconsistency(frame, pairs) if pairs else None,
        "duplicate": duplicate_pattern(frame, items) if items else None,
        "attention": attention_failed(frame, expected) if expected else None,
    }
    reasons = [(r, checks[r]) for r in REASONS if checks.get(r) is not None]
    if not reasons:
        return pd.Series("", index=frame.index, dtype="object")
    return pd.Series(
        ["; ".join(r for r, mask in reasons if bool(mask.iloc[i])) for i in range(len(frame))],
        index=frame.index,
        dtype="object",
    )


def quality_score(flags: pd.Series) -> pd.Series:
    """How many checks each respondent failed — 0 for a clean response.

    Deliberately a count and not a 0–100 index: a made-up scale invites a
    made-up cutoff, while "failed two of the four checks we ran" is something a
    methods section can state exactly.
    """

    return flags.fillna("").apply(lambda v: 0 if not v else len(str(v).split("; ")))
