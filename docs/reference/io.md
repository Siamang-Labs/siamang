# `siamang.io` — readers and writers reference

The I/O layer moves survey data between siamang's `SurveyData` and the
common research file formats. SPSS and Stata round-trip metadata
(variable labels, value labels, missing-value codes); CSV and Excel
carry data only (pair them with a JSON dictionary for metadata); the R
export writes a CSV plus dictionary plus loader script.
[`read_snapshot`](#snapshots) reads a data file from anywhere — a CSV in any
encoding and delimiter, a sheet of a workbook, a Qualtrics export — with the
codebook it brings, and `inspect_snapshot` describes it.

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
| `SPSSReader.read(path, **kwargs)` | Reads via `pyreadstat.read_sav(path, user_missing=True)` by default. Reconstructs a `VariableMap` from `meta.variable_value_labels`, `meta.variable_labels`, `meta.missing_ranges`, and the column dtypes; returns `SurveyData(frame=df, variables=...)`. Whole-number codes are integers (SPSS stores `1.0`), so `read_snapshot` gives the column back as `Int64`. |
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
| `StataReader.read(path, **kwargs)` | `pyreadstat.read_dta(path, user_missing=True)` → `SurveyData` with `VariableMap`. Stata keeps no measurement level: a variable with value labels is nominal, any other interval. |
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
- `import_survey.dictionary.json` — full `VariableMap` serialization (the name
  a snapshot's dictionary has, so `read_snapshot` finds it beside the CSV).
- `import_survey.R` — an R script (using `jsonlite`) that reads the CSV as
  UTF-8 (`na.strings = ""`, so a text answer "NA" stays an answer), replaces
  missing-value codes with `NA`, applies value labels (`factor(...)`; a code
  without a label keeps a level of its own, and missing codes are no level),
  sets each column's `label` attribute to the variable's label, and leaves a
  `survey_data` data frame. Multiple-choice columns (codes joined by `;`) stay
  text. The script finds its files beside itself when run with `Rscript` or
  `source()`d from any directory.

Returns the `Path` to `import_survey.R`. If `path` ends in `.R`, that
name is used instead (e.g. `trust.R` → `trust.csv`,
`trust.dictionary.json`, `trust.R`).

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

```python
read_snapshot(path, *, dictionary=None, questionnaire=None, weight=None,
              codebook="auto", encoding="auto", delimiter="auto", decimal="auto",
              sheet="auto", header_rows="auto", skip_rows=None, missing=None,
              **read_kwargs) -> SurveyData
```

reads any data file a researcher brings, not only a snapshot: `READ_FORMATS`
are the snapshot formats plus `.tsv`, `.txt` (delimited text, Excel's
"Unicode text") and `.xlsm`. `weight` names the weight column to apply.

**Reading** (`siamang.io.tabular`). Each option is detected when `"auto"`
(or None) and can be given instead; what was used is in
`inspect_snapshot(...)["read"]`.

| Option | Files | Detected as |
|--------|-------|-------------|
| `encoding` | text | a byte-order mark (UTF-8, UTF-16, UTF-32); else UTF-8 when the whole file decodes so; else UTF-16 without a mark; else the code page among Windows-1251, 1252, 1250, KOI8-R and CP866 in which the file's non-ASCII lines (wherever in the file they are) read as words (`tabular.legacy_encoding`): Cyrillic letters in a word with no Latin one, accented letters inside Latin words ("très", "Łódź"); not words that mix scripts, turn case mid-word or are all accented letters ("îòâåò", Cyrillic read as Western). Windows-1251 is kept unless KOI8-R or CP866 reads clearly better or with letters Russian uses clearly more; it wins a tie with Windows-1252 (a lone "м" is read as Cyrillic), and Windows-1252 a tie with 1250. A guessed code page is named in `notes` (`read.encoding_guessed`) |
| `delimiter` | text | of `,` `;` tab `\|` (`"tab"` names the tab), the one that splits the first rows into the same number of fields most consistently, the names row included, quotes respected. When `,` and `;` split every row alike (`Рост, см;Вес, кг` over `175,5;70,2`), `;` unless its fields hold commas of text more often than `,`'s fields hold a `;`. A one-column table of decimal commas (`score` over `4,5`, or `Доход, руб.` over `1000,50`) is read as one column |
| `decimal` | both | text: `,` when the first rows' numbers are written `4,5` (never with `,` between fields), else `.`; with `;` or tab between fields, a column whose decimals come later (`1` for three hundred rows, then `0,85`) is read with the other mark too. Excel: the mark the sheet's numbers kept as text show (`0,5`, `12,25`, `1 234,5`, or `0.5`); `.` in a Qualtrics export; a column of nothing but `1,500`-like values stays text with a note when nothing tells |
| `sheet` | Excel | the first sheet that holds a table (two columns, two rows at its top) and does not document another — a README, a sheet named like a codebook (Codebook, Variables, Dictionary, Описание …) or one that lists another sheet's names is passed over when another table is there; a name, or a number counting from 1 |
| `skip_rows` | both | the rows above the names: the names are the first row that fills half the table's width, so a title or a note above them is left out — in a sheet, also a row of three or more texts side by side over answers that span them, when columns beyond have no name (None: detected) |
| `header_rows` | both | 1 (the names); a Qualtrics export — an `{"ImportId": …}` row, or `StartDate` and `ResponseId` among the names with a text under `StartDate` and a date under that (Status, Progress or Finished alone are no export) — 2 (names, then question texts, which become the variables' labels) or 3 (and the ImportId row, dropped); given, `"1"`, `"2"` or `"3"` (a flow's `2` is `"2"`) |

The frame is then tidied: text columns whose every value reads as numbers
(`1 234,5`, `12,5%`, `100.0` stored as text), dates (ISO, `31.12.2025`,
`12/31/2025`) or true/false become so — a cell of spaces, `-`, `NA`, `#N/A` …
in such a column is a blank; in a text column only an empty cell is missing,
so an answer `NA` (Namibia) or `None` stays an answer. Digits with a leading
zero (`00123`) or of sixteen and more stay text. Names lose surrounding
spaces, unnamed empty columns (a trailing delimiter) are dropped, a text file
never puts leading fields into an index (`index_col=False`). What is worth
knowing is in the schema's `notes`: columns renamed for a duplicate name, a
last row that reads like a total (`Итого`). Keyword arguments for pandas /
pyreadstat still win: `sep=`, `header=`, `skiprows=`, `names=` (a text file
then takes them as they are, with no header detection), `sheet_name=`.

A file that cannot be read raises `SnapshotReadError` (a `ValueError`), in
words: `The file is not UTF-8: byte b'\xd5' at position 40 cannot be read in
it. It looks like Windows-1251 (Cyrillic): set Encoding to cp1251, or leave it
on auto.`; `Line 7 has 6 fields where the table has 5 (read with delimiter ';'
and UTF-8) …`; an `.xls` that is a web page, or an XML spreadsheet; an `.xls`
without `xlrd` (a dependency since this release; an `.xlsx` saved as `.xls`
is read by what it is); a sheet that is not there (naming those that are);
an empty file.

**The codebook** is resolved in this order: an explicit `dictionary` path;
`<stem>.dictionary.json` or `dictionary.json` next to the file; metadata
embedded in a `.sav` / `.dta`; then, by `codebook`:

- `"auto"` (default) — the questionnaire's variables (its declared codebook,
  or its questions' variables, with a nominal variable for the arm of every
  `Script.assign_condition` it does not declare, labeled with the arms, as
  Simulated data have it) **when the file is the questionnaire's data**
  (`siamang.io.file_codebook.questionnaire_match`): at least half of the
  file's columns — response metadata left out (`file_codebook.is_metadata`:
  ids and timestamps; Studio's export columns `duration_s`, `started_at`,
  `captcha`, `tab_switches`, `hidden_seconds`, `pastes`, `url_…`, and `_id`-like
  copies; Qualtrics' fixed columns, `Q_…` metadata and `…_DO` display orders),
  and so are a shared variable's "Other" texts (`q5_other`, `Q5_4_TEXT`) —
  are its variables, by name or with case
  and punctuation aside when that names one variable (`Q1` for `q1`, as the
  Qualtrics importer names an export tag), and they are at least half of the
  questionnaire's variables (a small file whose `gender`, `age` and `comment`
  share names with a survey's is not its data) — or the file's own codebook
  (a dictionary beside it, SPSS/Stata metadata) labels the variables it shares
  with the questionnaire as the questionnaire does (a table a flow of the
  project wrote); and in both cases no more than a quarter of the shared
  columns hold values that are neither the variable's codes, missing codes or
  value labels (nor numbers, for a numeric variable). Otherwise the **file's own
  codebook** (`file_variables`): a variable per column, labeled by the file's
  label row, with a scale guessed from its values (`infer_scale`: true/false
  and text nominal; dates interval; whole numbers with two values nominal,
  three to ten consecutive between 0 and 10 ordinal, up to twelve repeating
  codes below 100 nominal; other numbers ratio, interval with negatives —
  missing codes, declared or suspected, left out first). Categorical
  whole-number columns come back `Int64`;
- `"file"` — always the file's own codebook;
- `"questionnaire"` — always the questionnaire's.

The questionnaire is attached to the `SurveyData` **only when it describes
the file**: a national survey or a client's file whose `region` or
`gender` shares a name with a survey variable keeps its own names and
labels. `1;3` cells of the questionnaire's multiple-choice questions — and
`1,3`, as Qualtrics writes several answers (in its export, or wherever every
comma-joined part is the question's code) — are split into lists when it
describes the file, and in any other file only in a column whose answers are
that question's codes; a text column named like one (`yes; really`) is not
split. When it describes the file, a choice-text export's several answers
(`Acme,Initech`; a label holding a comma, `Globex, Inc.`, is matched whole)
become the lists of their codes. Such columns stay text while the file is
read, so `1,3` is never taken for 1.3. Columns named differently from
the questionnaire's variables (`Q1`) are renamed to them. With a
questionnaire's (or a dictionary's) codebook, a column of text whose every
answer is one of its variable's value labels — a choice-text export,
"Moderately" for 3 — becomes the codes; one with answers that are not labels
keeps its text and says so in `notes`. Without any codebook (no dictionary, no
metadata, no questionnaire) the result has the file's own codebook too (it had
none before).

`missing` are codes that mean no answer — per column, `{column: codes}` or
the text `"q5: -9; q6_1: -7, -8"` (`file_codebook.missing_text`
writes it; a name holding `;` or `:` in double quotes), or for every column,
`"-7, -8, -9"` or a list — added to the missing codes of each variable whose
column holds one (the questionnaire's variables are copied, not changed). A
code for every column is not a negative one in a column of other negative
values (a balance of `-7.0` among `-2300` and `-120.75`), so
`apply_missing_values` (the Missing values node) blanks them and tables leave
them out. With a codebook, integer-coded columns that a text format turned
into floats come back as nullable `Int64`.

```python
inspect_snapshot(path, *, <read_snapshot's options>, rows=None) -> dict
```

reads the file as `read_snapshot` does (`rows` limits it to the first rows;
`"sampled"` says the file goes on past them — a file of exactly `rows` rows is
not sampled) and returns, JSON-ready and without a single answer in it:

| Key | |
|-----|-|
| `format`, `rows`, `sampled` | the suffix, the rows read |
| `read` | how it was read: `encoding`, `delimiter`, `decimal`, `sheet`, `sheets`, `skip_rows`, `header_rows`, `qualtrics`, and `*_detected` for each detected |
| `codebook` | `"questionnaire"`, `"file"`, `"dictionary"` or `"embedded"` |
| `questionnaire` | `{matches, columns, variables, shared, renamed, conflicts, agrees}` — how the file's answer columns met the questionnaire's variables; None without one |
| `columns` | per column, in order: `name`, `label`, `type` (`integer`, `number`, `text`, `date`, `boolean`, `list`, or `empty` when no cell holds a value — its `scale` is then None), `scale`, `inferred`, `labels` (`[{code, label}]`), `missing`, `suspected_missing`, `personal`, `n_missing`, `n_unique`, `in_codebook` |
| `variables` | the codebook the data carries, in the questionnaire document's form (`{name: {scale, label, labels, missing}}`, a guessed scale with `"inferred": true`) |
| `converted`, `kept_text`, `notes` | choice texts turned into codes, columns kept as text (`{column: values not labels}`), what a reader should know |

`suspected_missing` (`file_codebook.suspected_missing`) are codes that look
like missing codes, to confirm with `missing=`: -1 … -9, -97 … -99, -997 …
-999 in a column whose other values are not negative (of amounts only -7 and
below), including a column of nothing but -7; 97, 98, 99, 997 … in a column of
at most twenty whole numbers all below half of them. A column of changes (-3 …
3) or of genuine negative amounts is not suspected. `personal`
(`file_codebook.personal_data`) points out a column that holds personal data
by its name — e-mail, IP address, location (latitude, longitude), name,
phone, participant ID (Prolific, MTurk, Qualtrics' ExternalReference),
address, in English and Russian — or by its values (e-mail and IP addresses),
for a host to suggest dropping it early; nothing is dropped.

`snapshot_options(params)` gives the `read_snapshot` keywords of a Data file
node's parameters as its template writes them (`DATA_FILE_OPTIONS`, those set
and not `auto`), so a host inspects the file the node reads with the node's
own options: `inspect_snapshot(path, questionnaire=survey,
**snapshot_options(params))` is what `check_flow(files=...)` takes.

`write_snapshot(data, path, *, dictionary=True, **write_kwargs)` writes the
data file in the format of the suffix and the dictionary when `data` has
variable metadata. Parquet needs `pip install "siamang[parquet]"`.
`SurveyDataReader` also accepts `.parquet`, and gives multiple-choice answers back as lists, as `read_snapshot` does.

---

## `export_file`

`export_file(data, path) -> Path` (`siamang.io.export`) writes whatever the
extension names — `EXPORT_FORMATS`: the snapshot formats as `write_snapshot`
writes them (data plus `<stem>.dictionary.json`), `.R` for the
[R bundle](#r), `.json` for the codebook alone (`DictionaryWriter`; a
`ValueError` when the data has no codebook). Any other extension is a
`ValueError` naming the ones that work. Every file lands beside `path`. The
flow's `output.export_file` node is this call.

