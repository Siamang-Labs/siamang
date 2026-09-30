# Data Import and Export

The `siamang.io` layer round-trips survey datasets between siamang's `SurveyData`
and the common research file formats — CSV, Excel, SPSS, Stata, and R — preserving
variable labels, value labels, missing-value codes and kinds, and column formats
wherever the format allows.

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

**Convention:** every reader exposes `read(path, **kwargs) -> SurveyData`; every
writer exposes `write(data, path, **kwargs) -> Path` and returns the `Path` it
wrote. `SurveyData` itself also has high-level `data.export("spss", path=...)` and
`data.export_dictionary(...)` helpers — see [[Working with Data|Working-with-Data]].

---

## `SurveyDataReader` — auto-detect by extension

```python
from siamang.io import SurveyDataReader

data = SurveyDataReader().read("responses.sav")   # picks the reader by suffix
```

A format router that dispatches on the file extension:

| Extension | Backed by |
| :--- | :--- |
| `.csv` | `CSVReader` |
| `.xlsx`, `.xls` | `ExcelReader` |
| `.sav` | `SPSSReader` |
| `.dta` | `StataReader` |

Unknown suffixes raise `ValueError`. Use it when you do not know (or do not care)
which concrete reader applies.

---

## Reading a data file from anywhere: `read_snapshot`

A file a client sent, a national survey, a Qualtrics export: `read_snapshot`
reads it as it comes and brings its columns with it — the flow's **Data file**
node is this call.

```python
from siamang.io import inspect_snapshot, read_snapshot

data = read_snapshot("national_survey.xlsx", questionnaire=survey)
schema = inspect_snapshot("national_survey.xlsx", questionnaire=survey)
schema["read"]        # {'sheet': 'Sheet1', 'skip_rows': 0, 'header_rows': 1, ...}
schema["codebook"]    # 'file': not this survey's data
[c["name"] for c in schema["columns"] if c["suspected_missing"]]   # -7, -9 ...
```

**How the file is written is found out**, and each choice can be given:

- **Encoding** (`encoding=`): UTF-8 with or without a byte-order mark, UTF-16
  (Excel's "Unicode text"), or a Windows code page — Windows-1251 is what
  Russian Excel saves "CSV (comma delimited)" in. The code page is told by
  how the file's letters read as words, wherever in the file they are, so a
  file of codes with a few "м" and "ж" is read as Cyrillic, not as "ì" and
  "æ"; the schema's notes say the code page was a guess. `encoding="cp1251"`
  says it.
- **Delimiter** (`delimiter=`): `,` `;` tab or `|`. Excel saves CSV with `;`
  wherever the comma is the decimal mark (Russian and most European settings),
  and names such as `Рост, см;Вес, кг` are read as the two columns they are.
- **Decimal mark** (`decimal=`): `4,5` is read as 4.5 in such a file, also in
  a column whose first decimals come after hundreds of whole numbers; `1 234,5`
  and `12,5%` are numbers too. In an Excel sheet the numbers it keeps as text
  tell the mark; a column of nothing but `1,500`-like values (one and a half,
  or fifteen hundred?) stays text with a note until you set it.
- **Sheet** (`sheet=`): the first sheet that holds a table, so a README or a
  codebook sheet in front ("Variables", a list of the data's names) is passed
  over; `sheet="Data"` or `sheet=2` (counting from 1).
- **Rows above the names** (`skip_rows=`): a title or a note above the table
  is left out.
- **Header rows** (`header_rows=`): a Qualtrics export has the question texts
  under the names (and, as CSV, an `{"ImportId": ...}` row): they become the
  variables' labels instead of a respondent, and the metadata columns get
  their types (dates, numbers, `Finished` true/false). It is known by the
  ImportId row, or by `StartDate` and `ResponseId` with the texts under them.

Numbers stored as text, dates and true/false become what they are; a code
with a leading zero (`00123`) stays a code; an answer "NA" in a text column
stays an answer. A file that cannot be read says why and what to set:
`The file is not UTF-8: … It looks like Windows-1251 (Cyrillic): set Encoding
to cp1251, or leave it on auto.`

**Whose codebook.** The questionnaire describes the file only when the file is
its data: at least half of its columns are the questionnaire's variables
(response metadata aside — ids, timestamps, Siamang Studio's `captcha`,
`tab_switches`, `url_…` columns, Qualtrics' fixed, `Q_…` and display-order
columns, and a question's "Other" text) and they are at least half of the
questionnaire's
variables — or the file's dictionary labels them as the questionnaire does (a
table a flow wrote) — and their answers fit them. Then the questionnaire's
labels, scales and value labels apply, multiple answers (`1;3`, or `1,3` as
Qualtrics writes them) become lists, `Q1` is read as the questionnaire's `q1`,
and a "choice text" export's answers ("Moderately", "Acme,Initech") become
their codes. Any other file keeps **its own codebook**:
its names, the labels of its label row, and a scale guessed from its values
(`codebook="questionnaire"` or `codebook="file"` decides instead of the
guess). A file whose `region` happens to share a name with your survey's
`region` is not labeled "Capital / North / South".

**Missing codes.** `inspect_snapshot` lists the codes that look like missing
codes in each column (`-7`, `-8`, `-9`, `99` …) — suspected, not applied.
Say which are, per column — `read_snapshot(path, missing="sought_advice: -9;
source_1: -7")` — or for every column that holds them, `missing="-7, -8, -9"`
(a negative code is then left alone in a column of other negative amounts, a
balance). `apply_missing_values()` (the **Missing values** node) blanks them
and tables leave them out. Per column is safer: a `99` that is "refused" in
one column is an age of 99 in another.

**Personal data.** Each column of the schema says whether it looks like it
holds personal data (`"e-mail"`, `"IP address"`, `"location"`, `"name"`,
`"phone"`, `"participant ID"`, `"address"`) — a Qualtrics export's
`IPAddress`, `LocationLatitude`, `RecipientEmail`, a `prolific_id`. Drop such
columns first (a **Select columns** node) unless the analysis needs them.

**Qualtrics, the recommended route.** Import the survey's `.qsf`
(`siamang.model.import_qsf_file`, or Siamang Studio's Builder), export the data
from Qualtrics as CSV with *Use numeric values*, and read it with the
questionnaire: the answers are the questionnaire's codes with its labels, and
a multiple-choice question's `1,3` is the list of its codes. A *choice text*
export works too when every answer is one of the labels.

**A platform's own data.** A research bundle's `--data` snapshot and
`FlowRunner(...).run(sources=...)` read the responses with the questionnaire's
codebook, as the platform does, whatever part of the survey they hold (a
pilot's data has the columns of the questions reached).

---

## CSV

```python
from siamang.io import CSVReader, CSVWriter

data = CSVReader().read("responses.csv")
CSVWriter().write(data, "out.csv")
```

| Class | Behaviour |
| :--- | :--- |
| `CSVReader.read(path, **kwargs)` | `pd.read_csv(path, **kwargs)` → `SurveyData(frame=...)`. **Metadata is not reconstructed.** |
| `CSVWriter.write(data, path, **kwargs)` | `data.frame.to_csv(path, index=False, **kwargs)`; returns `Path`. |

CSV carries data only. To recover labels and missing-value codes, pair the CSV with
a JSON dictionary (see [Data dictionary](#data-dictionary-codebooks)):

```python
from siamang.io import CSVReader, DictionaryReader

data = CSVReader().read("responses.csv")
data = data.__class__(frame=data.frame, variables=DictionaryReader().read("dict.json"))
```

---

## Excel

```python
from siamang.io import ExcelReader, ExcelWriter

data = ExcelReader().read("responses.xlsx")
ExcelWriter().write(data, "out.xlsx")
```

| Class | Behaviour |
| :--- | :--- |
| `ExcelReader.read(path, **kwargs)` | `pd.read_excel(path, **kwargs)`. |
| `ExcelWriter.write(data, path, **kwargs)` | `data.frame.to_excel(path, index=False, **kwargs)`. |

Like CSV, Excel I/O carries data only. Requires `openpyxl` (bundled by default);
`.xls` (Excel 97–2003) needs `xlrd`, bundled too. To read a workbook as it
comes — the sheet with the table, a title above it, numbers stored as text —
use [`read_snapshot`](#reading-a-data-file-from-anywhere-read_snapshot).

---

## SPSS `.sav`

```python
from siamang.io import SPSSReader, SPSSWriter, read_spss

data = read_spss("trust.sav")              # SPSSReader().read(...)
SPSSWriter().write(data, "trust_out.sav")
```

| Class | Behaviour |
| :--- | :--- |
| `SPSSReader.read(path, **kwargs)` | Reads via `pyreadstat.read_sav(path, user_missing=True)`. Rebuilds a `VariableMap` from `meta.column_names_to_labels`, `meta.variable_value_labels`, `meta.missing_ranges`, and `meta.variable_measure`. |
| `SPSSWriter.write(data, path, **kwargs)` | Writes via `pyreadstat.write_sav` with variable labels, value labels, missing values, and measurement levels (nominal/ordinal/scale). `data.variables` must be set, or columns are written bare. |
| `read_spss(path, **kwargs)` | Convenience for `SPSSReader().read(...)`. |

SPSS round-trips full metadata, so a file edited through siamang opens in SPSS as if
untouched:

```python
import pandas as pd
data = read_spss("input.sav")                       # metadata recovered
# Treat -1 as missing (recode_values would write to a new column instead):
data = data.with_frame(data.frame.replace({"age": {-1: pd.NA}}))
SPSSWriter().write(data, "output.sav")
```

`pyreadstat` is bundled by default (it powers both SPSS and Stata I/O).

---

## Stata `.dta`

```python
from siamang.io import StataReader, StataWriter, read_stata

data = read_stata("trust.dta")
StataWriter().write(data, "trust_out.dta", version=15)
```

| Class | Behaviour |
| :--- | :--- |
| `StataReader.read(path, **kwargs)` | `pyreadstat.read_dta(path, user_missing=True)` → `SurveyData` with a `VariableMap`. |
| `StataWriter.write(data, path, version=15, **kwargs)` | `pyreadstat.write_dta` with metadata. `version` (default `15`) is forwarded to `pyreadstat.write_dta` as the target Stata version. |
| `read_stata(path, **kwargs)` | Convenience function. |

Labels and value labels round-trip as with SPSS, with two Stata-specific
limits: Stata accepts only single-letter user missing codes (`.a`–`.z`), so
numeric missing codes (e.g. `99`) are dropped on write, and measurement levels
are not stored in `.dta` files. Pair a `.dta` export with a JSON dictionary to
preserve the full codebook.

---

## R

```python
from siamang.io import RScriptWriter

RScriptWriter().write(data, path="political_trust_R/")
```

Writes a three-file bundle into the target directory and returns the `Path` to
the R script:

- `import_survey.csv` — the responses;
- `import_survey.dictionary.json` — full `VariableMap` serialization, named
  like a snapshot's dictionary so `read_snapshot("import_survey.csv")` finds it;
- `import_survey.R` — an R script that reads the CSV (as UTF-8) and the
  dictionary (via `jsonlite`), replaces missing-value codes with `NA`, applies
  value labels with `factor(...)` and puts each variable's codebook label (not
  the question's text) in the column's `label` attribute, leaving the result in an object named `survey_data`. A code
  the codebook has no label for keeps a level of its own; a multiple-choice
  column (codes joined by `;`) stays text, because a factor holds one value per
  respondent; a text answer that reads `NA` stays an answer.

If `path` ends in `.R` (e.g. `trust.R`), the files are named after its stem
instead (`trust.csv`, `trust.dictionary.json`, `trust.R`). The script finds
its files beside itself whether it is run with `Rscript` or `source()`d from
another directory.

```r
# In R:
source("political_trust_R/import_survey.R")   # builds the labelled `survey_data`
```

### One call for any format: `export_file`

```python
from siamang.io import export_file

export_file(data, "outputs/clean.sav")      # data + clean.dictionary.json
export_file(data, "outputs/clean.R")        # the R bundle above
export_file(data, "outputs/codebook.json")  # the codebook alone
```

The format follows the extension: `.parquet`, `.csv`, `.xlsx`, `.sav` and
`.dta` as `write_snapshot` writes them, `.R` the R bundle, `.json` the data
dictionary alone (an error when the data has no codebook). Every file lands
beside the path given. It is what the flow's **Export file** node runs.

---

## Data dictionary (codebooks)

```python
from siamang.io import DictionaryReader, DictionaryWriter

DictionaryWriter().write(survey.variables, "dict.json")
restored = DictionaryReader().read("dict.json")     # -> VariableMap
```

| Class | Behaviour |
| :--- | :--- |
| `DictionaryWriter.write(variables: VariableMap, path)` | `json.dump(variables.to_dict(), ...)`. |
| `DictionaryReader.read(path)` | `VariableMap.from_dict(json.load(...))`. Raises `ValueError` if the JSON root is not a dict. |

Use a dictionary to store a survey's codebook alongside a CSV export (CSV/Excel
carry no metadata), or to distribute a variable schema independently of the
questionnaire.

---

## Round-tripping labels and missing values

SPSS and Stata are the formats that preserve the most metadata (see the
Stata-specific limits above). A typical recode-and-export cycle:

```python
import pandas as pd
from siamang.io import read_spss, SPSSWriter

data = read_spss("input.sav")
data = data.with_frame(data.frame.replace({"age": {-1: pd.NA}})).apply_missing_values()
SPSSWriter().write(data, "output.sav")
```

For CSV-based pipelines, export both the data and a dictionary, and reattach the
dictionary on read:

```python
from siamang.io import CSVWriter, DictionaryWriter, CSVReader, DictionaryReader

CSVWriter().write(data, "out.csv")
DictionaryWriter().write(data.variables, "out_dict.json")

# later …
again = CSVReader().read("out.csv")
again = again.__class__(frame=again.frame, variables=DictionaryReader().read("out_dict.json"))
```

---

See also: [[Working with Data|Working-with-Data]] · [[Analysis]] ·
[[Variables and Measurement|Variables-and-Measurement]] · [[Cookbook]] ·
[[API Reference Index|API-Reference-Index]]
