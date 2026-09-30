"""Data snapshots: a responses file plus its codebook, readable anywhere.

A snapshot is what a platform exports so an analysis can be reproduced away
from it: one data file (Parquet, CSV, Excel, SPSS or Stata) and, next to it,
the codebook as a data dictionary (``<name>.dictionary.json``, the format of
:class:`~siamang.io.DictionaryWriter`). :func:`read_snapshot` puts the two
back together as a :class:`~siamang.data.SurveyData`::

    data = read_snapshot("data/responses.parquet", questionnaire=survey)

It reads any data file a researcher brings the same way: a CSV in whatever
encoding, delimiter and decimal mark Excel saved it with, a sheet of a
workbook, a Qualtrics export with its rows of question texts
(:mod:`siamang.io.tabular`). Formats that carry their own metadata (``.sav``,
``.dta``) need no dictionary; one found or given next to them takes
precedence. Without either, the codebook is the questionnaire's when the file
is the questionnaire's data, and the file's own otherwise
(:mod:`siamang.io.file_codebook`): a file that is not this survey's keeps its
own names and labels. :func:`inspect_snapshot` says all of it — how the file
was read, each column's label, type and scale, the codes that look like
missing codes, the columns that hold personal data — as the codebook a flow
check takes for the file (:func:`~siamang.flow.check_flow`'s ``files``).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from siamang.core.question import MultiChoice, Ranking
from siamang.core.questionnaire import Questionnaire
from siamang.core.variable import Variable, VariableMap
from siamang.data.survey_data import SurveyData
from siamang.io._frames import list_frame
from siamang.io.dictionary import DictionaryReader, DictionaryWriter
from siamang.io.file_codebook import (
    QuestionnaireMatch,
    codes_from_labels,
    column_type,
    comma_answers,
    file_variables,
    lists_from_labels,
    parse_missing,
    personal_data,
    questionnaire_match,
    suspected_missing,
    with_missing,
)
from siamang.io.tabular import SnapshotReadError, TableRead, read_text_table, read_workbook

#: File suffixes :func:`write_snapshot` writes and :func:`read_snapshot` reads.
SNAPSHOT_FORMATS = (".parquet", ".csv", ".xlsx", ".xls", ".sav", ".dta")
#: Every suffix :func:`read_snapshot` reads: the snapshot formats, delimited
#: text saved as ``.tsv`` or ``.txt`` (Excel's "Unicode text"), and ``.xlsm``.
READ_FORMATS = (*SNAPSHOT_FORMATS, ".tsv", ".txt", ".xlsm")
#: Where :func:`read_snapshot` takes a file's codebook from (``codebook=``).
CODEBOOKS = ("auto", "file", "questionnaire")

#: The Data file node's parameters that are :func:`read_snapshot`'s options.
DATA_FILE_OPTIONS = (
    "dictionary",
    "codebook",
    "sheet",
    "header_rows",
    "skip_rows",
    "delimiter",
    "encoding",
    "decimal",
    "missing",
)

_TEXT_FORMATS = {".csv", ".tsv", ".txt"}
_EXCEL_FORMATS = {".xlsx", ".xlsm", ".xls"}


def read_snapshot(
    path: str | Path,
    *,
    dictionary: str | Path | None = None,
    questionnaire: Questionnaire | None = None,
    weight: str | None = None,
    codebook: str = "auto",
    encoding: str | None = "auto",
    delimiter: str | None = "auto",
    decimal: str | None = "auto",
    sheet: str | int | None = "auto",
    header_rows: int | str | None = "auto",
    skip_rows: int | None = None,
    missing: Any = None,
    **read_kwargs: Any,
) -> SurveyData:
    """Load a data file and its codebook into a :class:`SurveyData`.

    ``dictionary`` names the data-dictionary JSON; when omitted,
    ``<stem>.dictionary.json`` and ``dictionary.json`` next to the file are
    tried. ``questionnaire`` is the survey the file may hold the data of.
    ``weight`` names the weight column to apply.

    ``codebook`` says where the variables' labels, scales and value labels
    come from when no dictionary and no embedded metadata (``.sav``, ``.dta``)
    give them: ``"auto"`` the questionnaire's when the file is its data (at
    least half of the file's columns, response metadata aside, are its
    variables and at least half of its variables, or the file's dictionary
    labels them as it does; and they hold values that fit them —
    :func:`~siamang.io.file_codebook.questionnaire_match`),
    the file's own otherwise; ``"file"`` always the file's own (its names, a
    label row's texts, scales guessed from the values); ``"questionnaire"``
    always the questionnaire's. The questionnaire is attached to the result
    only when it describes the file; its variables are then named as the
    questionnaire names them (``Q1`` becomes ``q1``) and a choice-text
    export's answers become their codes. Multiple answers (``1;3``) are split
    into lists where the questionnaire says a column holds them — in a file it
    does not describe, only where they are the question's codes.

    Reading a text file (``.csv``, ``.tsv``, ``.txt``): ``encoding``,
    ``delimiter`` (``,`` ``;`` ``tab`` ``|``) and ``decimal`` (``.`` ``,``)
    are detected when ``"auto"``. A workbook: ``sheet`` is a sheet's name or
    number (from 1), ``"auto"`` the first sheet that holds a table. Both:
    ``skip_rows`` rows above the names (None: detected), ``header_rows`` the
    rows from the names down that are not answers (1, 2 with a label row
    under the names, 3 with a row dropped after it; ``"auto"`` finds a
    Qualtrics export). ``missing`` are codes that mean no answer (``"-7, -8"``,
    a list, or ``{column: codes}``), added to the missing codes of every
    variable whose column holds one. Extra keyword arguments go to the pandas
    / pyreadstat reader and win over what is detected (``sep=``, ``header=``,
    ``sheet_name=`` …).

    With a codebook, categorical columns whose codes are integers are
    restored to nullable ``Int64`` when a text format (CSV, Excel) turned
    them into floats. A file that cannot be read raises
    :class:`~siamang.io.tabular.SnapshotReadError` (a ``ValueError``) saying
    what was found and which option reads it.
    """

    loaded = _load(
        path,
        dictionary=dictionary,
        questionnaire=questionnaire,
        codebook=codebook,
        encoding=encoding,
        delimiter=delimiter,
        decimal=decimal,
        sheet=sheet,
        header_rows=header_rows,
        skip_rows=skip_rows,
        missing=missing,
        read_kwargs=read_kwargs,
    )
    data = SurveyData(
        frame=loaded.frame, variables=loaded.variables, questionnaire=loaded.questionnaire
    )
    if weight is not None:
        data = data.with_weight(weight)
    return data


def inspect_snapshot(
    path: str | Path,
    *,
    dictionary: str | Path | None = None,
    questionnaire: Questionnaire | None = None,
    codebook: str = "auto",
    encoding: str | None = "auto",
    delimiter: str | None = "auto",
    decimal: str | None = "auto",
    sheet: str | int | None = "auto",
    header_rows: int | str | None = "auto",
    skip_rows: int | None = None,
    missing: Any = None,
    rows: int | None = None,
    **read_kwargs: Any,
) -> dict[str, Any]:
    """What a data file holds, as a host shows it and a flow check reads it.

    Takes :func:`read_snapshot`'s options and reads the file exactly as it
    does (``rows`` limits the reading to the first rows, for a large file; the
    schema then says ``"sampled"``). Returns a JSON-ready mapping:

    - ``format``, ``rows``, ``sampled``, and ``read``: how the file was read
      (``encoding``, ``delimiter``, ``decimal``, ``sheet`` and ``sheets``,
      ``skip_rows``, ``header_rows``, ``qualtrics``), each as detected or given;
    - ``codebook``: ``"questionnaire"``, ``"file"``, ``"dictionary"`` or
      ``"embedded"`` — where the variables are described from — and
      ``questionnaire``: how the file's columns met the questionnaire's
      (``matches``, ``columns``, ``variables``, ``shared``, ``renamed``,
      ``conflicts``, ``agrees``), None without one;
    - ``columns``: one entry per column in the file's order — ``name``,
      ``label``, ``type`` (integer, number, text, date, boolean, list),
      ``scale`` and ``inferred`` (a guess from the values), ``labels`` (value
      labels as ``{code, label}``), ``missing`` (declared missing codes),
      ``suspected_missing`` (codes that look like them, to confirm),
      ``personal`` (``"e-mail"``, ``"IP address"``, ``"location"``, ``"name"``,
      ``"phone"``, ``"participant ID"``, ``"address"`` or None), ``n_missing``,
      ``n_unique`` and ``in_codebook``;
    - ``variables``: the codebook the data carries, in the questionnaire
      document's form (``{name: {scale, label, labels, missing}}``, an
      inferred scale marked ``"inferred": true``) — what
      :func:`~siamang.flow.check_flow` takes for the file;
    - ``converted`` (columns whose choice texts became codes), ``kept_text``
      (``{column: values that are not labels}``) and ``notes``.

    No answer is copied into it: only names, labels, codes and counts.
    """

    loaded = _load(
        path,
        dictionary=dictionary,
        questionnaire=questionnaire,
        codebook=codebook,
        encoding=encoding,
        delimiter=delimiter,
        decimal=decimal,
        sheet=sheet,
        header_rows=header_rows,
        skip_rows=skip_rows,
        missing=missing,
        read_kwargs=read_kwargs,
        # One row more than asked says whether the file goes on past them.
        nrows=None if rows is None else rows + 1,
    )
    sampled = False
    if rows is not None and len(loaded.frame) > rows:
        sampled = True
        loaded.frame = loaded.frame.head(rows)
    return loaded.schema(sampled)


def snapshot_options(params: Mapping[str, Any]) -> dict[str, Any]:
    """The :func:`read_snapshot` keywords a Data file node's parameters give,
    as its template writes them: those set and not ``"auto"``. A host reads
    the file the node reads with them —
    ``inspect_snapshot(path, questionnaire=survey, **snapshot_options(params))``
    — so the schema it shows is what the run reads."""

    options: dict[str, Any] = {}
    for name in DATA_FILE_OPTIONS:
        value = params.get(name)
        if value is None or value in ("", "auto") or value == [] or value == {}:
            continue
        options[name] = value
    return options


@dataclass(slots=True)
class _Loaded:
    source: Path
    frame: pd.DataFrame
    variables: VariableMap | None
    questionnaire: Questionnaire | None
    kind: str
    labels: dict[str, str] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    match: QuestionnaireMatch | None = None
    converted: list[str] = field(default_factory=list)
    kept_text: dict[str, int] = field(default_factory=dict)
    inferred: bool = False

    def schema(self, sampled: bool = False) -> dict[str, Any]:
        from siamang.model.document import _variable_to_doc

        variables = self.variables or VariableMap()
        payloads: dict[str, Any] = {}
        for name, variable in variables.items():
            try:
                payload = _variable_to_doc(variable)
            except Exception:  # noqa: BLE001 - a code JSON cannot hold
                payload = {"scale": variable.scale, "label": variable.label or name}
            if self.inferred:
                payload["inferred"] = True
            payloads[name] = payload
        columns = []
        for column in self.frame.columns:
            name = str(column)
            series = self.frame[column]
            known = variables.get(name)
            payload = payloads.get(name, {})
            declared = list(known.missing_values) if known is not None else []
            try:
                unique: int | None = int(series.nunique(dropna=True))
            except TypeError:  # lists
                unique = None
            kind = column_type(series)
            columns.append(
                {
                    "name": name,
                    "label": (known.label if known is not None else None) or self.labels.get(name),
                    "type": kind,
                    # A column with no value has no scale to guess.
                    "scale": known.scale
                    if known is not None and not (kind == "empty" and self.inferred)
                    else None,
                    "inferred": bool(self.inferred and known is not None and kind != "empty"),
                    "labels": payload.get("labels", []),
                    "missing": [_plain(code) for code in declared],
                    "suspected_missing": suspected_missing(series, declared),
                    "personal": personal_data(name, series),
                    "n_missing": int(series.isna().sum()),
                    "n_unique": unique,
                    "in_codebook": known is not None,
                }
            )
        rows = int(len(self.frame))
        return {
            "path": str(self.source),
            "format": self.source.suffix.lower().lstrip("."),
            "rows": rows,
            "sampled": bool(sampled),
            "read": {key: value for key, value in self.options.items() if key != "format"},
            "codebook": self.kind,
            "questionnaire": self.match.to_json() if self.match is not None else None,
            "columns": columns,
            "variables": payloads,
            "converted": list(self.converted),
            "kept_text": dict(self.kept_text),
            "notes": list(self.notes),
        }


def _plain(code: Any) -> Any:
    if isinstance(code, np.integer):
        return int(code)
    if isinstance(code, np.floating):
        return int(code) if float(code).is_integer() else float(code)
    return code


def _load(
    path: str | Path,
    *,
    dictionary: str | Path | None,
    questionnaire: Questionnaire | None,
    codebook: str,
    encoding: str | None,
    delimiter: str | None,
    decimal: str | None,
    sheet: str | int | None,
    header_rows: int | str | None,
    skip_rows: int | None,
    missing: Any,
    read_kwargs: dict[str, Any],
    nrows: int | None = None,
) -> _Loaded:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"No such snapshot file: {source}")
    suffix = source.suffix.lower()
    if suffix not in READ_FORMATS:
        raise SnapshotReadError(
            f"Unsupported snapshot format {suffix!r}; expected one of {', '.join(READ_FORMATS)}. "
            "Save the table as CSV UTF-8 or Excel (.xlsx)."
        )
    choice = str(codebook or "auto").strip().lower()
    if choice not in CODEBOOKS:
        raise ValueError(f"codebook must be one of {', '.join(CODEBOOKS)}, not {codebook!r}.")
    declared = parse_missing(missing)
    survey_variables = (
        _questionnaire_variables(questionnaire) if questionnaire is not None else None
    )
    several = _list_columns(questionnaire) if questionnaire is not None else []

    table: TableRead | None = None
    embedded: VariableMap | None = None
    if suffix == ".parquet":
        frame = _lists_back(pd.read_parquet(source, **read_kwargs))
        _release_arrow_memory()
        if nrows is not None:
            frame = frame.head(nrows)
    elif suffix in _TEXT_FORMATS:
        table = read_text_table(
            source,
            encoding=encoding,
            delimiter=delimiter,
            decimal=decimal,
            header_rows=header_rows,
            skip_rows=skip_rows,
            nrows=nrows,
            keep_text=several,
            **read_kwargs,
        )
        frame = table.frame
    elif suffix in _EXCEL_FORMATS:
        table = read_workbook(
            source,
            sheet=sheet,
            header_rows=header_rows,
            skip_rows=skip_rows,
            nrows=nrows,
            decimal=decimal,
            keep_text=several,
            **read_kwargs,
        )
        frame = table.frame
    elif suffix == ".sav":
        from siamang.io.spss import SPSSReader

        if nrows is not None:
            read_kwargs = {"row_limit": nrows, **read_kwargs}
        loaded = SPSSReader().read(source, **read_kwargs)
        frame, embedded = loaded.frame, loaded.variables
    else:
        from siamang.io.stata import StataReader

        if nrows is not None:
            read_kwargs = {"row_limit": nrows, **read_kwargs}
        loaded = StataReader().read(source, **read_kwargs)
        frame, embedded = loaded.frame, loaded.variables
    labels = dict(table.labels) if table is not None else {}
    notes = list(table.notes) if table is not None else []

    dictionary_path = _find_dictionary(source, dictionary)
    own: VariableMap | None = None
    kind = "file"
    if dictionary_path is not None:
        own, kind = DictionaryReader().read(dictionary_path), "dictionary"
    elif embedded is not None:
        own, kind = embedded, "embedded"

    match: QuestionnaireMatch | None = None
    describes = False
    if survey_variables is not None:
        match = questionnaire_match(frame, survey_variables, several, own=own)
        describes = choice == "questionnaire" or (choice == "auto" and match.matches)
    if describes and own is None and match is not None and match.renamed:
        frame = frame.rename(columns=match.renamed)
        for old, new in match.renamed.items():
            if old in labels:
                labels[new] = labels.pop(old)
        notes.append(
            "Columns named as the questionnaire names its variables: "
            + ", ".join(f"{old} → {new}" for old, new in match.renamed.items())
            + "."
        )

    listed: list[str] = []
    if suffix != ".parquet" and several and survey_variables is not None:
        # A column the questionnaire says holds several answers is split where
        # its answers are that question's (1;3 of its codes) even in a file
        # that is not the survey's data — never a text that only shares its
        # name ("yes; really").
        fitting = several if describes or match is None else [n for n in several if match.fits(n)]
        if describes:
            # A choice-text export: "Acme,Initech" becomes the codes [1, 3].
            listed = lists_from_labels(frame, survey_variables, fitting)
        qualtrics = bool(table is not None and table.options.get("qualtrics"))
        commas = [
            name
            for name in fitting
            if name in frame.columns
            and name in survey_variables
            and (qualtrics or comma_answers(frame[name], survey_variables[name]))
        ]
        frame = list_frame(frame, fitting, commas=commas)
    inferred = False
    if own is not None:
        variables: VariableMap | None = own
    elif describes and survey_variables is not None:
        variables, kind = survey_variables, "questionnaire"
    else:
        variables = file_variables(frame, labels, declared)
        inferred = True
    converted: list[str] = []
    kept: dict[str, int] = {}
    if not inferred and variables is not None:
        converted, kept = codes_from_labels(frame, variables, skip=several)
        converted = [name for name in listed if name not in converted] + converted
        if declared:
            variables = with_missing(variables, frame, declared)
        # The frame is this function's own (just read): restored in place.
        _restore_integer_codes(frame, variables)
    for name, count in kept.items():
        notes.append(
            f"{name}: {count} of its answers are not among its value labels, so its text is "
            "kept as it is."
        )
    if match is not None and choice == "auto" and not describes and match.shared:
        why = (
            f"{len(match.conflicts)} of them hold answers that do not fit the variable "
            f"({', '.join(sorted(match.conflicts)[:5])})"
            if len(match.conflicts) * 4 > len(match.shared)
            else "too few for the file to be its data"
        )
        notes.append(
            f"{len(match.shared)} of the file's {match.columns} columns share names with the "
            f"questionnaire's variables — {why} — so they keep the file's own labels "
            "(Codebook: questionnaire gives them the questionnaire's)."
        )
    options = dict(table.options) if table is not None else {}
    return _Loaded(
        source=source,
        frame=frame,
        variables=variables,
        questionnaire=questionnaire if describes else None,
        kind=kind,
        labels=labels,
        options=options,
        notes=notes,
        match=match,
        converted=converted,
        kept_text=kept,
        inferred=inferred,
    )


def _lists_back(frame: pd.DataFrame) -> pd.DataFrame:
    """Parquet keeps a multiple-choice answer as a list, but pandas reads it
    back as a numpy array — which no multiple-choice helper takes for a list
    (``multi.is_multi`` is false, Explode fails on "the truth value of an array
    is ambiguous"). Every array cell becomes the list it was written as."""

    out = frame
    for column in frame.columns:
        series = frame[column]
        if series.dtype != object:
            continue
        arrays = series.map(lambda value: isinstance(value, np.ndarray))
        if not arrays.any():
            continue
        if out is frame:
            out = frame.copy()
        out[column] = series.map(
            lambda value: value.tolist() if isinstance(value, np.ndarray) else value
        )
    return out


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
        from siamang.io.csv import CSVWriter

        CSVWriter().write(data, target, **write_kwargs)
    elif suffix in {".xlsx", ".xls"}:
        from siamang.io.excel import ExcelWriter

        ExcelWriter().write(data, target, **write_kwargs)
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
    """The codebook a questionnaire gives its data: its declared variables, or
    the questions' when it declares none, and the arm every
    ``Script.assign_condition`` draws, labeled with the arms — as Simulated
    data describe it. Without the arm a flow read ``1`` and ``2`` where the
    respondents were shown "Control" and "Treatment", and a data check called
    the column one the codebook does not know."""

    from siamang.local_simulator import with_arm_variables

    if questionnaire.variables:
        variables = questionnaire.variables
    else:
        variables = VariableMap()
        for question in questionnaire.all_questions():
            bound = question.var if isinstance(question.var, list) else [question.var]
            for variable in bound:
                if variable.name not in variables:
                    variables.add(variable)
    return with_arm_variables(variables, questionnaire.scripts)


def _list_columns(questionnaire: Questionnaire) -> list[str]:
    """Columns the questionnaire says hold several answers in one cell.

    Taken from the questionnaire rather than guessed from the data: ``"1;3"``
    and a free-text answer that happens to contain a semicolon look the same in
    a CSV, and only the questionnaire knows which is which.
    """

    columns = []
    for question in questionnaire.all_questions():
        multiple = isinstance(question, MultiChoice) and question.mode == "array"
        if (multiple or isinstance(question, Ranking)) and isinstance(question.var, Variable):
            columns.append(question.var.name)
    return columns


def _release_arrow_memory() -> None:
    """Hand back to the system what reading Parquet left in Arrow's pool.

    The pool keeps the buffers of the table pandas was built from once they
    are freed, for the next read: 30 MB for a 20,000 x 177 file, a sixth of
    what a 512 MB sandbox leaves a flow once its imports are loaded."""

    try:
        import pyarrow
    except ImportError:  # read by another engine
        return
    pyarrow.default_memory_pool().release_unused()


def _restore_integer_codes(frame: pd.DataFrame, variables: VariableMap) -> pd.DataFrame:
    """Turn float columns back into ``Int64`` where the codebook says codes are
    integers — in ``frame`` itself, a column at a time, which is returned.

    Copying the frame first held two of it at once (and the copy was not
    returned to the system): only a frame the caller owns is passed here."""

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
        restored[name] = series.round().astype("Int64")
    return restored


__all__ = [
    "CODEBOOKS",
    "DATA_FILE_OPTIONS",
    "READ_FORMATS",
    "SNAPSHOT_FORMATS",
    "SnapshotReadError",
    "dictionary_path_for",
    "inspect_snapshot",
    "read_snapshot",
    "snapshot_options",
    "write_snapshot",
]
