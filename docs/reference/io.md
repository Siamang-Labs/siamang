# `siamang.io` — readers and writers reference

The I/O layer round-trips survey data with all metadata (variable
labels, value labels, missing-value codes, missing-value kinds, formats)
intact between siamang's `SurveyData` and the common research file
formats.

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

Convention: every reader exposes `read(path, **kwargs) -> SurveyData`;
every writer exposes `write(data, path, **kwargs) -> Path`. Writers
return the `Path` they wrote to.

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
| `SPSSWriter.write(data, path, **kwargs)` | Writes via `pyreadstat.write_sav` with full metadata: variable labels, value labels, missing values, and column formats. `data.variables` must be set (otherwise written with bare column names). |
| `read_spss(path, **kwargs)` | Convenience function — equivalent to `SPSSReader().read(path, **kwargs)`. |

Round-trip example:

```python
data = read_spss("input.sav")              # full metadata recovered
data = data.recode_values("age", {-1: pd.NA})
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
| `StataWriter.write(data, path, version=15, **kwargs)` | `pyreadstat.write_dta` with metadata. `version` selects the Stata file-format version (Stata 12 = 117, 13/14 = 118, ≥ 15 = 119). |
| `read_stata(path, **kwargs)` | Convenience function. |

---

## R

```python
from siamang.io import RScriptWriter

RScriptWriter().write(data, path="political_trust_R/")
```

Writes a three-file bundle into the target directory:

- `data.csv` — the responses.
- `dictionary.json` — full `VariableMap` serialisation.
- `load_data.R` — an R script that reads the CSV, applies value labels
  (`factor(...)`) and missing-value codes from `dictionary.json`, and
  attaches variable labels via `Hmisc::label`.

Returns the `Path` to `load_data.R`.

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
