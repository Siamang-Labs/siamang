"""Data snapshots: a responses file plus its codebook, readable anywhere.

A snapshot is what a platform exports so an analysis can be reproduced away
from it: one data file (Parquet, CSV, Excel, SPSS or Stata) and, next to it,
the codebook as a data dictionary (``<name>.dictionary.json``, the format of
:class:`~siamang.io.DictionaryWriter`). :func:`read_snapshot` puts the two
back together as a :class:`~siamang.data.SurveyData`::

    data = read_snapshot("data/responses.parquet", questionnaire=survey)

Formats that carry their own metadata (``.sav``, ``.dta``) need no
dictionary; one found or given next to them takes precedence. Without either,
the codebook comes from the questionnaire when one is passed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from siamang.core.questionnaire import Questionnaire
from siamang.core.variable import VariableMap
from siamang.data.survey_data import SurveyData
from siamang.io.dictionary import DictionaryReader, DictionaryWriter

#: File suffixes :func:`read_snapshot` understands.
SNAPSHOT_FORMATS = (".parquet", ".csv", ".xlsx", ".xls", ".sav", ".dta")


def read_snapshot(
    path: str | Path,
    *,
    dictionary: str | Path | None = None,
    questionnaire: Questionnaire | None = None,
    weight: str | None = None,
    **read_kwargs: Any,
) -> SurveyData:
    """Load a data file and its codebook into a :class:`SurveyData`.

    ``dictionary`` names the data-dictionary JSON; when omitted,
    ``<stem>.dictionary.json`` and ``dictionary.json`` next to the file are
    tried. ``questionnaire`` is attached to the result and supplies the
    codebook when no dictionary or embedded metadata is available.
    ``weight`` names the weight column to apply. Extra keyword arguments go
    to the pandas / pyreadstat reader.

    With a codebook, categorical columns whose codes are integers are
    restored to nullable ``Int64`` when a text format (CSV, Excel) turned
    them into floats.
    """

    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"No such snapshot file: {source}")
    suffix = source.suffix.lower()
    if suffix not in SNAPSHOT_FORMATS:
        raise ValueError(
            f"Unsupported snapshot format {suffix!r}; expected one of {', '.join(SNAPSHOT_FORMATS)}."
        )

    embedded: VariableMap | None = None
    if suffix == ".parquet":
        frame = pd.read_parquet(source, **read_kwargs)
    elif suffix == ".csv":
        frame = pd.read_csv(source, **read_kwargs)
    elif suffix in {".xlsx", ".xls"}:
        frame = pd.read_excel(source, **read_kwargs)
    elif suffix == ".sav":
        from siamang.io.spss import SPSSReader

        loaded = SPSSReader().read(source, **read_kwargs)
        frame, embedded = loaded.frame, loaded.variables
    else:
        from siamang.io.stata import StataReader

        loaded = StataReader().read(source, **read_kwargs)
        frame, embedded = loaded.frame, loaded.variables

    dictionary_path = _find_dictionary(source, dictionary)
    if dictionary_path is not None:
        variables: VariableMap | None = DictionaryReader().read(dictionary_path)
    elif embedded is not None:
        variables = embedded
    elif questionnaire is not None:
        variables = _questionnaire_variables(questionnaire)
    else:
        variables = None

    if variables is not None:
        frame = _restore_integer_codes(frame, variables)

    data = SurveyData(frame=frame, variables=variables, questionnaire=questionnaire)
    if weight is not None:
        data = data.with_weight(weight)
    return data


def write_snapshot(
    data: SurveyData,
    path: str | Path,
    *,
    dictionary: bool = True,
    **write_kwargs: Any,
) -> Path:
    """Write ``data`` as a snapshot: the data file plus ``<stem>.dictionary.json``.

    The format follows the suffix of ``path`` (see :data:`SNAPSHOT_FORMATS`).
    The dictionary is written when ``data`` has variable metadata and
    ``dictionary`` is true; for ``.sav`` / ``.dta`` the metadata is also
    embedded in the file itself. Returns the data file path.
    """

    target = Path(path)
    suffix = target.suffix.lower()
    if suffix not in SNAPSHOT_FORMATS:
        raise ValueError(
            f"Unsupported snapshot format {suffix!r}; expected one of {', '.join(SNAPSHOT_FORMATS)}."
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    if suffix == ".parquet":
        data.frame.to_parquet(target, index=False, **write_kwargs)
    elif suffix == ".csv":
        data.frame.to_csv(target, index=False, **write_kwargs)
    elif suffix in {".xlsx", ".xls"}:
        data.frame.to_excel(target, index=False, **write_kwargs)
    elif suffix == ".sav":
        from siamang.io.spss import SPSSWriter

        SPSSWriter().write(data, target, **write_kwargs)
    else:
        from siamang.io.stata import StataWriter

        StataWriter().write(data, target, **write_kwargs)
    if dictionary and data.variables:
        DictionaryWriter().write(data.variables, dictionary_path_for(target))
    return target


def dictionary_path_for(data_path: str | Path) -> Path:
    """Where the codebook of a snapshot file lives: ``<stem>.dictionary.json``."""

    source = Path(data_path)
    return source.with_name(f"{source.stem}.dictionary.json")


def _find_dictionary(source: Path, explicit: str | Path | None) -> Path | None:
    if explicit is not None:
        path = Path(explicit)
        if not path.is_file():
            raise FileNotFoundError(f"No such dictionary file: {path}")
        return path
    for candidate in (dictionary_path_for(source), source.with_name("dictionary.json")):
        if candidate.is_file():
            return candidate
    return None


def _questionnaire_variables(questionnaire: Questionnaire) -> VariableMap:
    if questionnaire.variables:
        return questionnaire.variables
    variables = VariableMap()
    for question in questionnaire.all_questions():
        bound = question.var if isinstance(question.var, list) else [question.var]
        for variable in bound:
            if variable.name not in variables:
                variables.add(variable)
    return variables


def _restore_integer_codes(frame: pd.DataFrame, variables: VariableMap) -> pd.DataFrame:
    """Turn float columns back into ``Int64`` where the codebook says codes are integers."""

    restored = frame
    for name, variable in variables.items():
        if name not in frame.columns:
            continue
        codes = list(variable.labels) + list(variable.missing_values)
        if not codes or not all(
            isinstance(code, int) and not isinstance(code, bool) for code in codes
        ):
            continue
        series = frame[name]
        if not pd.api.types.is_float_dtype(series):
            continue
        values = series.dropna()
        if not values.empty and not bool((values % 1 == 0).all()):
            continue
        if restored is frame:
            restored = frame.copy()
        restored[name] = series.round().astype("Int64")
    return restored


__all__ = ["SNAPSHOT_FORMATS", "dictionary_path_for", "read_snapshot", "write_snapshot"]
