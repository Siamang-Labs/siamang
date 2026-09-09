# `siamang.io` — readers and writers reference

The I/O layer moves survey data between siamang's `SurveyData` and the
common research file formats. SPSS and Stata round-trip metadata
(variable labels, value labels, missing-value codes); CSV and Excel
carry data only (pair them with a JSON dictionary for metadata); the R
export writes a CSV plus dictionary plus loader script.

```python
from siamang.io import (
    SurveyDataReader,
    CSVReader, CSVWriter,
    ExcelReader, ExcelWriter,
    SPSSReader, SPSSWriter, read_spss,
    StataReader, StataWriter, read_stata,
    RScriptWriter,
    DictionaryReader, DictionaryWriter,
)
```

Convention: every tabular reader (CSV, Excel, SPSS, Stata) exposes
`read(path, **kwargs) -> SurveyData`; every tabular writer exposes
`write(data, path, **kwargs) -> Path`. Writers return the `Path` they
wrote to. `DictionaryReader`/`DictionaryWriter` work with a
`VariableMap` instead of `SurveyData`, and `RScriptWriter.write(data,
path)` takes no extra kwargs.

---

## `SurveyDataReader`

```python
class SurveyDataReader:
    def read(self, path: str | Path, **kwargs) -> SurveyData: ...
```

Format router. Dispatches based on the file extension:

| Extension | Backed by |
|-----------|-----------|
| `.csv` | `CSVReader` |
| `.xlsx`, `.xls` | `ExcelReader` |
| `.sav` | `SPSSReader` |
| `.dta` | `StataReader` |

Unknown suffixes raise `ValueError`.

---

## CSV

```python
CSVReader().read("responses.csv")
CSVWriter().write(data, "responses.csv")
```

| Class | Behaviour |
|-------|-----------|
| `CSVReader.read(path, **kwargs)` | `pd.read_csv(path, **kwargs)` → `SurveyData(frame=...)`. **Variable metadata is not reconstructed** — pair with a JSON dictionary if you need it. |
| `CSVWriter.write(data, path, **kwargs)` | `data.frame.to_csv(path, index=False, **kwargs)`. Returns `Path`. |

---

## Excel

```python
ExcelReader().read("responses.xlsx")
ExcelWriter().write(data, "responses.xlsx")
```

| Class | Behaviour |
|-------|-----------|
| `ExcelReader.read(path, **kwargs)` | `pd.read_excel(path, **kwargs)`. |
| `ExcelWriter.write(data, path, **kwargs)` | `data.frame.to_excel(path, index=False, **kwargs)`. |

Like CSV, the Excel I/O carries data only.

---

## SPSS `.sav`

```python
from siamang.io import SPSSReader, SPSSWriter, read_spss

data = read_spss("trust.sav")              # SPSSReader().read(...)
SPSSWriter().write(data, "trust_out.sav")
```

| Class | Behaviour |
|-------|-----------|
| `SPSSReader.read(path, **kwargs)` | Reads via `pyreadstat.read_sav(path, user_missing=True)` by default. Reconstructs a `VariableMap` from `meta.variable_value_labels`, `meta.variable_labels`, `meta.missing_ranges`, and the column dtypes; returns `SurveyData(frame=df, variables=...)`. |
| `SPSSWriter.write(data, path, **kwargs)` | Writes via `pyreadstat.write_sav` with full metadata: variable labels, value labels, missing values, and measurement levels (nominal/ordinal/scale). `data.variables` must be set (otherwise written with bare column names). |
| `read_spss(path, **kwargs)` | Convenience function — equivalent to `SPSSReader().read(path, **kwargs)`. |

Round-trip example:

```python
data = read_spss("input.sav")              # full metadata recovered
# Treat -1 as missing (recode_values would write to a new column instead):
data = data.with_frame(data.frame.replace({"age": {-1: pd.NA}}))
SPSSWriter().write(data, "output.sav")     # SPSS opens it as if untouched
```

---

## Stata `.dta`

```python
from siamang.io import StataReader, StataWriter, read_stata

data = read_stata("trust.dta")
StataWriter().write(data, "trust_out.dta", version=15)
```

Same shape as SPSS:

| Class | Behaviour |
|-------|-----------|
| `StataReader.read(path, **kwargs)` | `pyreadstat.read_dta(path, user_missing=True)` → `SurveyData` with `VariableMap`. |
| `StataWriter.write(data, path, version=15, **kwargs)` | `pyreadstat.write_dta` with metadata. `version` is the target Stata version (8–15 supported, default 15), forwarded to `pyreadstat.write_dta`. |
| `read_stata(path, **kwargs)` | Convenience function. |

Note: Stata only supports single-letter user missing codes (`.a`–`.z`),
so numeric missing codes (e.g. `99`) are dropped on write, and
measurement levels are not stored in `.dta` files. Pair a `.dta` export
with a JSON dictionary to preserve the full codebook.

---

## R

```python
from siamang.io import RScriptWriter

RScriptWriter().write(data, path="political_trust_R/")
```

Writes a three-file bundle into the target directory:

- `import_survey.csv` — the responses.
- `import_survey_dictionary.json` — full `VariableMap` serialisation.
- `import_survey.R` — an R script (using `jsonlite`) that reads the CSV,
  replaces missing-value codes with `NA`, applies value labels
  (`factor(...)`), and leaves a `survey_data` data frame.

Returns the `Path` to `import_survey.R`. If `path` ends in `.R`, that
name is used instead (e.g. `trust.R` → `trust.csv`,
`trust_dictionary.json`, `trust.R`).

---

## Data dictionary

```python
from siamang.io import DictionaryReader, DictionaryWriter

DictionaryWriter().write(variable_map, "dict.json")
restored = DictionaryReader().read("dict.json")
```

| Class | Behaviour |
|-------|-----------|
| `DictionaryWriter.write(variables: VariableMap, path)` | `json.dump(variables.to_dict(), path)`. |
| `DictionaryReader.read(path)` | `VariableMap.from_dict(json.load(path))`. Raises `ValueError` if the JSON root isn't a dict. |

Useful for storing a survey's codebook alongside a CSV export, or for
distributing a variable schema independently of the questionnaire.

---

## Snapshots

A snapshot is a data file plus its codebook, the unit a platform exports so an
analysis can be reproduced elsewhere: `responses.parquet` (or `.csv`, `.xlsx`,
`.sav`, `.dta`) and, next to it, `responses.dictionary.json` in the
[data dictionary](#data-dictionary) format.

```python
from siamang.io import read_snapshot, write_snapshot

path = write_snapshot(data, "data/responses.parquet")     # + data/responses.dictionary.json
data = read_snapshot("data/responses.parquet", questionnaire=survey)
```

`read_snapshot(path, *, dictionary=None, questionnaire=None, weight=None, **read_kwargs)`
resolves the codebook in this order: an explicit `dictionary` path;
`<stem>.dictionary.json` or `dictionary.json` next to the file; metadata
embedded in a `.sav` / `.dta`; the variables of `questionnaire`. The
questionnaire, when given, is attached to the `SurveyData`; `weight` names
the weight column to apply. With a codebook, integer-coded columns that a
text format turned into floats come back as nullable `Int64`.

`write_snapshot(data, path, *, dictionary=True, **write_kwargs)` writes the
data file in the format of the suffix and the dictionary when `data` has
variable metadata. Parquet needs `pip install "siamang[parquet]"`.
`SurveyDataReader` also accepts `.parquet`.

