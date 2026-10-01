# Node Reference

Every node in the Flows palette: what it does, what it takes and gives, and
every parameter with its exact label, default and allowed values. Use it
alongside [[Analysis Flows|Studio-Flows]], which explains the canvas, and
[[Cleaning and Weighting Data|Studio-Cleaning-and-Weighting]], which puts the
preparation nodes in order.

The palette is served by the engine, so this list is the engine's own: 61
nodes in five groups — **Sources** (4), **Prepare** (16), **Analyze** (26),
**Visualize** (7) and **Output** (8). Within each group the nodes appear here in
the palette's order. Each palette item shows the node's title and a short
name (the part after the dot below, e.g. `crosstab`); nodes that need the
project database also say `· platform`.

---

## Reading this page

**Ports.** Every node lists what it takes in and what it gives out, with the
port's name and type:

| Type | What flows through |
|---|---|
| **SurveyData** | the dataset *plus* its codebook and questionnaire — which is why tables come out labeled |
| **Table** | a frequency table, crosstab, group-means table, banner, coefficient table, t-test, correlation matrix, factor loadings, key drivers, a perceptual map's dimensions, rows and columns, price points and curves, a Trend's points… |
| **Chart** | a bar chart (a histogram and a donut too), box plot, heatmap, Likert chart, scatter plot or trend, or the Result chart of an analysis |
| **Stat** | a test result or a set of statistics (χ², Fisher's p, t, Kruskal-Wallis, Wilcoxon, Cochran's Q, a correlation, CIs, model fit), or what a Tab book wrote |
| **Report** | a report section or a whole report |
| **Any** | anything — only the **Live tile** input accepts every type |

The **Result chart**'s input takes a **Table** or a **Stat**, several of them:
an analysis's table and its statistics.

Weights, recodes, flags and derived variables are *columns inside*
SurveyData, not separate wires.

**Parameters.** "required" in the Default column means the node reports an
error until you fill it in. The inspector marks every other parameter
*optional*. Types:

| Type | How you set it in the inspector |
|---|---|
| variable | a dropdown of the variables available at this node (`name — label`), filtered to the scales the node accepts. A stored variable of another scale stays shown as what the node reads, with its scale: "q_md_score_1 (interval — Rows takes nominal / ordinal)" — an error of the check for a codebook variable, a warning for one a node of the flow makes. A made variable has the scale the nearest node upstream that makes it gives it (a Recode of a derived variable is ratio, like its source), and the dropdown offers it with that scale; a name the codebook has keeps the codebook's. An arm an **Assign to a condition** script writes is offered as a nominal variable ("assigned by a script") when the codebook does not list it. A field that can read columns the codebook does not describe lists them last, under **Beside the answers**: a **Trend**'s **Time** offers the timestamps the survey's responses carry — `created_at — Response date (created_at)`, `updated_at — Last change (updated_at)`, `started_at — Start time (started_at)`. A field leaves out what its node refuses as soon as it is picked: a **Trend**'s **Time** and **Split by** and a **Bar chart**'s **Split by** do not offer multiple-choice questions, rankings or open answers, and a **Trend**'s **Measure variable** for a mean no nominal or multiple-choice question; a stored one stays shown with the reason (`aware (several answers: not one wave or date)`) |
| variables (several) | a checklist of the same variables, filtered the same way; a checked variable the list would not offer stays in it, with its scale or "(not in codebook)", and can be unchecked |
| choice | a list of the allowed values, as wide as the field. The field shows the code chosen; in the list, where the code is a statistician's shorthand, its name is on the line under it — "Welch's ANOVA" under `welch_anova`, "Benjamini-Hochberg" under `fdr_bh`. An optional field's list starts with **— default —**, which leaves the default, with "the node's default: …" under it. The stored value and the generated script keep the code. A list of more than ten opens with a filter box. How the lists work: [Lists in the inspector](Studio-Flows#lists-in-the-inspector) |
| answer code | an answer of the variable another parameter names, picked from that variable's value labels (`1 — Male`): a dropdown (**— pick an answer —** when the field is required, **— none —** otherwise), or a checklist where several answers may be checked. A t-test's **Group A** and **Group B** and a **Trend**'s **Answer codes** leave the codebook's missing codes out — its missing answers and its `missing_values` alike (both nodes refuse a missing code there). A stored code that is not among them reads "5 (not an answer of gender)" in a dropdown and "5 is not an answer of gender" under a checklist. A code stored as text is read as the node reads it: a t-test and a Trend find their answers by their text, so a **Group A** of `"1"` shows as `1 — Male`; **Proportion CI**'s answer, the **Counts as yes** of McNemar and Cochran's Q, a **Perceptual map**'s **Counts as yes (attributes)** and **Price sensitivity**'s **Counts as would buy** compare codes by type, so there text "1" is not the answer 1 and shows as given, `"1" (not an answer of gender)`. Where the field reads a list of variables, the answers are those of the first one checked. When that variable has no value labels, the field is a JSON box instead |
| whole number, number | a number box; the placeholder shows the default |
| checkbox | checked = on |
| text | a text box; where the text names a new variable or column, the hint says "names a new variable". A few text boxes suggest values as you type — a **Bar chart**'s **Bins** (`auto`, `10`, `0, 18, 25, 35, 50, 65`) and a **Heatmap**'s **Color map** (`theme`, `YlOrRd`, `Blues`, `viridis`, `RdBu_r`) — and take any other value the node reads |
| JSON object, JSON | a text box that must contain valid JSON; it is read when you leave the box, and a parse error is shown under it. Where the help gives an example, the empty box shows it (`[18, 30, 45, 65, 100]`) |
| condition | the Builder's condition editor, over the variables available at this node |
| formula | a monospaced box, with the variables available at this node listed under it |
| file name | a file the node writes: a field labeled **File name**, the name typed between a fixed `outputs/` and the file's ending (`outputs/` `client_q3` `.xlsx`); a **Format** list under it where the node writes several. A `/` in the name makes folders. The lines under it say where a run leaves the file and what is wrong with a name (see [Where files go](#where-files-go)) |
| codeframe | a dropdown of the project's codeframes by path (`analysis/<name>.codeframe.json`; **— choose a codeframe —** when none is chosen), with **Edit codeframe…**, or **New codeframe…** when none is chosen (see [Code open answers](#code-open-answers)) |
| upload | a file the node reads: a list, by name, of the uploads under **Files** the field can read, with the chosen file's size and date under it and **Upload…** and **Type a name…** (**Type another name…** once a file is chosen) under that (see [Where files go](#where-files-go)) |

**Choices on this page** are written as their code, followed by the name the
list shows on the line under it: `welch_anova` ("Welch's ANOVA"). Look for
the code in the list, with the name under it; the field shows the code
alone.

**The variables available at a node** are the questionnaire's codebook
variables, then those that nodes upstream of it make — a **Recode**,
**Derive**, **Index / scale**, **Bands**, **Explode multiple choice**,
**MaxDiff scores**, **Cluster (k-means)**, **Factor analysis** with **Add
factor scores** checked, **Response quality**, **Speeders & partials**, a
weighting node, or a **Code open answers** (its **Theme variable**, or the
name its codeframe carries) — labeled "*label* · made by *node*" (or "made
by *node*"), then those a table the flow reads brings, labeled "from table
*table* · made by *flow*". Below a **Data file**, the file's own columns come
first, grouped under "From *name*" (the file's name), and the questionnaire's
variables only when the file is this survey's data (see
[The file's columns in the flow](#the-files-columns-in-the-flow)). A
variable made further down the flow is not offered: it does not exist yet
when this node runs. See
[Parameters and variable pickers](Studio-Flows#parameters-and-variable-pickers).

**Fields that depend on a choice.** Some parameters are read only with some
choices of the node — a **t-test**'s **Groups** only with **Design**
`independent`, its **Second measurement** only with `paired`. The inspector
shows the fields the current choices read and hides the others; each node
below says which. A hidden field that still holds a value you gave it is
named under the others — "Not used with these choices, and kept for when they
apply: **Groups** (with Design = independent)." — with **Clear it** (**Clear
them** for several); a condition of several parts is bracketed when there is
another ("(Show = count and Sort = code and Layout ≠ histogram and Layout ≠
donut) or Layout = grouped"). Its value comes back into use when you switch back; until
then it is not checked — a Group A kept after **Design** went `paired`, or a
**Groups** naming a variable since removed, is no error, on the canvas or at
Save. A
field that one of the node's rules makes necessary (below) is marked
required rather than *optional*.

**Rules between parameters.** A few nodes have rules about how their choices
go together, written in the node's own words — for example "Tukey's HSD
follows a one-way ANOVA — set Test to anova, or Post-hoc to none." They are
checked as you edit, and by the engine at **Check** and at Save, with the
code `PARAM_CONFLICT`. An **error** is a combination the node cannot run: the
flow cannot run until you change it. A **warning** names a setting the node
would ignore with the other choices, such as a post-hoc test while
**Significance test** is off. Each node's rules are listed with it below.

**One-line texts.** The texts a node's card summarizes — a **Report
section**'s **Heading**, a **Derive** formula, a **Live tile**'s **Label**, a
path, a table or variable name — are written into a comment line of the
generated script, so they must be one line. A line break (or another control
character; a tab is fine) fails the engine check at **Check** and at Save,
on that node, with the error `PARAM_LINE_BREAK`: "“heading” holds a line
break or another control character: it must be one line of text." The flow
then has no script until you fix it. A flow saved before this check with
such a text is left out of a research bundle (see
[What is inside](Studio-Reproducibility#what-is-inside)).

### Where files go

No file is typed as a path. The flow still stores the whole path —
`outputs/client_q3.xlsx`, `assets/panel_wave2.csv` — so flows saved earlier,
the engine's check and the generated script read what they always read.

**A file a node writes** goes in `outputs/`, the only folder a run keeps: it
appears in **Files** as `outputs/<flow>/<file>` and on the run's card. The
**File name** field keeps `outputs/` and the file's ending fixed, so you type
only the name:

- **The ending comes from the format.** A name typed with an ending the node
  writes, such as `tabs.xlsx`, loses it and keeps the format (no
  `tabs.xlsx.xlsx`); a pasted `outputs/` is dropped, and a space becomes `_`
  as you type. An ending the node cannot write is answered under the field —
  for a **Save report**, "Reports are saved as Markdown and HTML — for a PDF,
  open the HTML and print it." — with a fix such as **Use satisfaction**.
- **A name uses Latin letters (A–Z, a–z), digits, `-`, `_` and `.`**, with `/`
  between folders, at most 100 characters. Other characters are named — "A
  file name here can use letters a–z, digits, -, _ and . — not “(” or “)”."
  for `Q3 (final)` — with **Use Q3_final**. While the name has a problem, the
  field does not say where the file will be.
- **Two nodes writing one file** are pointed out: "Another node (tabbook)
  already writes outputs/tabbook.xlsx — this one would replace it.", with
  **Use tabbook_2**. Names that differ only in the case of their letters count
  as one file, as they do on a Mac or on Windows. When another flow of the
  project saves a file of the same name, the field says so too: Studio keeps
  each flow's copy apart, but in a downloaded research bundle one would
  replace the other.
- **Where it ends up.** "After a run: Files → outputs/*flow*/*name*" (**Files**
  becomes a link once a run has made the file), "Beside it: …" for what the
  node writes next to it, and what **Run all** leaves out, such as "Run all
  doesn't keep this file: run this flow on its own to get it." (see
  [What Run all keeps](Studio-Flows#what-run-all-keeps)).
- **A node added from the palette is named after the flow** —
  `outputs/<flow>.md`, `<flow>_tabbook.xlsx`, `<flow>_data.csv`,
  `<flow>_maxdiff_choices.csv`, `<flow>_conjoint_choices.csv` — numbered when
  the flow already names that file. An empty field stores nothing and shows,
  as its placeholder, the name the engine then writes, where the node has one
  (`report` for a **Save report**, `tabbook` for a **Tab book (Excel)**).
- **A path saved earlier** that the field cannot show as a name — outside
  `outputs/`, with no ending, or with an ending the node cannot write — is
  shown as it was written, under "Other location, kept as it was written",
  with the reason ("This file isn't in outputs/, so a run doesn't keep it
  under Files.") and a button such as **Save it as outputs/tabs.xlsx
  instead**.
- A required name left empty is an error on the node: "No file name yet: type
  the name to save it under."

**A file a node reads** is an upload under [[Files|Studio-Files]]. The field
lists, by name, only the uploads it can read — a **Data file**'s **File** the
data files, its **Dictionary (JSON)** the `.json` files — and the note under
it gives the chosen file's size and upload date (a data file's rows × columns
first), then "Each run reads the file as it is in Files at that moment." Under
the list:

- **Upload…** opens **Upload a data file** (or **Upload a dictionary**), which
  says what it takes, refuses a file of another kind, even one dragged in, and
  selects the new upload once it is stored.
- **Type a name…** (**Type another name…** once a file is chosen) names a file
  that is not uploaded yet, such as one a connector will deliver. You type the
  name only (`assets/` is added), and the field says "*name* isn't in this
  project's Files: upload it before the run, or choose another file." A name
  with characters Files would change is answered with the name Files stores,
  such as **Use Wave_3_final_.csv**. **Choose from Files** goes back to the
  list.
- With no uploads the field reads "No files uploaded yet. Upload a CSV, Excel,
  SPSS, Stata or Parquet file (up to 50 MB)."; while the project's files load,
  "Loading this project's files…"; when they cannot be loaded, it says so,
  with **Try again**.
- An upload deleted since stays chosen as "*name* — not in Files", with the
  same sentence. A chosen upload the field would not offer stays too, marked
  "can't be read as data" or "not a dictionary (.json)".
- A value saved earlier that a run cannot bring in — a path that is not an
  upload's name, such as `./assets/panel_wave2.csv` — is shown under "Other
  location, kept as it was written": "A run only brings in files uploaded
  under Files, so it won't find this one.", with **Use the uploaded
  panel_wave2.csv** when Files has it. A **Data file**'s
  [Columns panel](#the-columns-panel) then says **not read**.
- A required file left empty is an error on the node: "No file chosen yet:
  pick one of the project's Files, or upload one."

Only the uploads a flow names are copied into its run (see
[Data file](#data-file)).

---

## Sources

Nodes with no input that produce **SurveyData**. A flow needs at least one.

### Data file

`source.file` — reads a data file uploaded under [[Files|Studio-Files]] as it
comes, and brings **its own columns** into the flow. The palette describes it
as "A data file from Files: CSV (in any encoding, with , ; tab or | between
fields), Excel, SPSS, Stata or Parquet. Its columns come into the flow with
it: their names, the labels of a label row (a Qualtrics export's question
texts), value labels and missing codes where the format keeps them."

It reads `.csv`, `.tsv` and `.txt` (text tables in any encoding, separated by
commas, semicolons, tabs or vertical bars), `.xlsx`, `.xlsm` and `.xls`,
`.sav` (SPSS), `.dta` (Stata) and `.parquet`, the ending in any case. The
nodes below it offer the file's columns, and the checks know them (see
[The file's columns in the flow](#the-files-columns-in-the-flow)); the
questionnaire's variables come with the file only when the file is this
survey's data.

**In:** none → **Out:** `data` (SurveyData)

The inspector shows the parameters in this order: **File**, **Codebook**, the
**Reading options**, **Missing codes**, **Dictionary (JSON)** — then the
[Columns panel](#the-columns-panel).

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **File** | upload | required | the uploads ending in `.csv`, `.tsv`, `.txt`, `.xlsx`, `.xlsm`, `.xls`, `.sav`, `.dta`, `.parquet` | The data file, chosen by name from the uploads under **Files**, or uploaded from here with **Upload…** (stored as `assets/<name>`). The note under the list gives its rows × columns as the node read it (as **Files** read it, with the default options, until then; "reading its columns…" while **Files** reads it), its size and upload date. |
| **Codebook** | choice | `auto` | `auto`, `file`, `questionnaire` | Where the columns' labels, scales and value labels come from. `auto`: the questionnaire's when the file is this survey's data, else the file's own. `file` — "the file's own: its names, label row and values": for data from elsewhere whose columns happen to share names with the questionnaire. `questionnaire` — "the questionnaire's, for the columns it knows". Once the file is read, **auto** shows what it decided: "auto — the file's own" or "auto — the questionnaire's". |
| **Header rows** | choice | `auto` | `auto`, `1`, `2`, `3` | Rows at the top that are not answers, the names first: `1` "names only"; `2` "names, then labels (question texts)", whose second row labels the columns; `3` "names, labels, and a row left out (Qualtrics CSV)". `auto` finds a Qualtrics export (its ImportId row, or `StartDate` and `ResponseId` with a row of texts under them), else reads one row. |
| **Skip rows** | whole number | — | 0 or more | Rows above the names to leave out (a title, a note). Empty finds the names row: the first that fills at least half of the table's width. |
| **Sheet** | text | — | — | Excel: the sheet to read, by its name or its number (1 is the first). Empty reads the first sheet that holds a table. |
| **Delimiter** | choice | `auto` | `auto`, `,`, `;`, `tab`, `\|` | Text files: what separates the fields — comma, "semicolon (Excel with Russian or European settings)", "tab (Excel's Unicode text)", vertical bar. `auto` tries each on the first rows. |
| **Encoding** | choice | `auto` | `auto`, `utf-8`, `utf-16`, `cp1251`, `koi8-r`, `cp866`, `cp1252`, `cp1250`, `iso-8859-1` | Text files: how the letters are written. `cp1251` is "Windows-1251, Cyrillic (Russian Excel's CSV)", `utf-16` "Excel's Unicode text". `auto` reads a byte-order mark, then UTF-8, then the most likely Windows code page. |
| **Decimal mark** | choice | `auto` | `auto`, `.`, `,` | How numbers write their fraction, 4.5 or 4,5, in a text file and for numbers an Excel sheet keeps as text. `auto` reads a comma where the numbers are written so, and leaves values as ambiguous as `1,500` as text when nothing tells. |
| **Missing codes** | text | — | — | Codes that mean no answer in this file, per column — `q5: -9` and `q6_1: -7, -8`, one column a line (or `;` between them) — or for every column that holds them: `-7, -8, -9` (a negative code is then left alone in a column of other negative amounts). **Missing values** turns them into blanks, and tables leave them out. A box of a few lines; the empty box shows "e.g. q5: -9 (a line per column)". |
| **Dictionary (JSON)** | upload | — | the `.json` uploads | Optional: the file's codebook as a data dictionary (`<name>.dictionary.json`, as a Siamang export writes it); its labels, scales and missing codes describe the file's columns. `<name>.dictionary.json` files are listed first, and when the one named after **File** is in **Files** the field offers **Use *name*.dictionary.json**. |

**Reading options.** **Header rows**, **Skip rows**, **Sheet**,
**Delimiter**, **Encoding** and **Decimal mark** sit under one line,
**Reading options**, which says what auto found — "Reading options · all
auto (found: XLSX, sheet Sheet1, 1 header row)" — or names the options set
("Reading options · Header rows 2, Delimiter ;"). Click it to open it; it
opens by itself on a node where one of them is set. Only the options of the
chosen kind of file show: for a text file **Header rows**, **Skip rows**,
**Delimiter**, **Encoding** and **Decimal mark**; for a workbook **Header
rows**, **Skip rows**, **Sheet** and **Decimal mark**; none for SPSS, Stata
and Parquet, which say all of it themselves (an option set for another kind
of file still shows, so it can be cleared). An option left on auto says in
its field what was found: "auto — found ;" in **Delimiter**, "found: Sheet1"
in an empty **Sheet**. In each option's list a value has its meaning on the
line under it, such as "Windows-1251, Cyrillic (Russian Excel's CSV)" under
`cp1251`; these lists have no **— default —**, since `auto` is the default.

**Missing codes per file.** When **Missing codes** names columns the file
does not have — codes left from a file the node read before, which a run
would skip without a word — the field says "Missing codes name columns this
file doesn't have: …" with **Remove them** (**Remove it** for one).

#### The Columns panel

Under the parameters, once a **File** is chosen, the **Columns** panel shows
what the node read from the file with these options — its head says **read**,
**reading…**, **not in Files**, **not read** (a **File** under "Other
location") or **cannot read**:

- "*rows* rows × *columns* columns" and how the file was read: the format,
  the delimiter, the encoding (or "with a byte-order mark"), a decimal comma,
  the sheet ("sheet Sheet1 of 3"), rows above the names skipped, or "a
  Qualtrics export: its question texts label the columns, its ImportId row is
  left out". A `+` after the rows means only the first 50,000 rows were read.
- Where the labels and scales come from: "Labels and scales: the
  questionnaire's — the file is this survey's data.", "… from the file's
  dictionary.", "… from the file's own SPSS / Stata labels." or "Labels and
  scales: from the file (column names; scales guessed from the values)." (with
  "the second header row as labels" when there is one). Notes on how the
  file's names met the questionnaire's follow, such as "2 of the file's 16
  columns share names with questionnaire variables (gender, satisfaction), but
  satisfaction holds answers that don't fit its variable, so they keep the
  file's own labels. Set Codebook to questionnaire to use the
  questionnaire's."
- **Codes that look like missing codes** in *n* columns — "-9, -8, -7 (e.g.
  q5: -9; q6_1: -7). They count as answers until you mark them." — with
  **Mark them as missing in these columns**, which writes each code into
  **Missing codes** for the columns it was found in only ("Each code only in
  the columns where it was found: a -7 among a column's amounts, or an age of
  99, stays a value."). Once they are, the panel says "Marked as missing in *n*
  columns — see Missing codes above." with **Undo**. When some are marked and
  others not, the button reads **Add this file's missing codes (*n*
  columns)**.
- **Looks like personal data**, a short warning mark, when some columns'
  names or values look like an email, an IP address, a location, a name, a
  phone number, an address or a participant ID. Its **ⓘ** names those
  columns, each with its kind ("email (e-mail)"), and says "An analysis
  rarely needs these; leave them out early so no table, report or export
  carries them." Beside it, **Add a Select columns node without them** puts a
  **Select columns** node labeled "Without personal data", keeping every
  other column, after the Data file; it takes over what the Data file fed,
  and is selected. Nothing is dropped until you press it.
- **Show the *n* columns** lists each column on two lines: its name, a
  personal-data mark and its missing codes — declared, and suspected ones with
  a `?` — then its label, its value labels count, its type where it says
  something (text, date) and its scale, `*` marking a scale guessed from the
  values ("* a scale guessed from the values · ? a code that looks like a
  missing code").
- The last line names the options set ("Read with: Header rows 2, Missing
  codes.") and says "The nodes below this one can pick these columns. The file
  is read apart from the flow, and only its column list comes back here,
  never an answer."

While the file is read the panel says "Reading the file's columns… Nodes
below it aren't checked for names until it is read."; a file not read yet
with the node's options says "This file has not been read with these options
yet; someone who can run previews opens this node to read it." **Read again**
("Read the file again with these options") reads it once more. A file that cannot be
read says why in words: the encoding it looks like and what to set, a line
with a different number of fields than the table ("Line 4 has 3 fields where
the table has 2 …"), the sheets a workbook has, an empty file, or a format
the node does not read. When the chosen file is not in **Files**, the panel
says only **not in Files**; the note under **File** says the rest. A **File**
under "Other location" is never read: the panel says **not read** and "Only
a file uploaded under Files is read for its columns. Choose the upload under
File above (upload it first if it isn't there), and its columns show here.",
with no **Read again**. The field's **Use the uploaded …** (for an older
path) or **Use *name*** (for a typed name), where it offers one, or its list
chooses the upload.

#### The file's columns in the flow

The nodes below a Data file offer the file's columns in their pickers,
grouped under "From *name*" (the file's name as **File** lists it), then the
variables the nodes between make ("Made in this flow", or "From the
questionnaire and this flow" when the file is this survey's data). The check
on the canvas, at **Check**, at Save and before a preview knows them:

- A name the file does not have is an error: "*param*: "*name*" is not a
  column of assets/*name*, nor made by this flow."
- A scale the file's values only suggest is a warning where it does not fit
  the node, not an error: "*param*: "*name*" looks ratio (as guessed from its
  file's values); this node expects nominal/ordinal." Set **Codebook**, or
  recode the column, when the guess is wrong.
- The questionnaire's variables are known below the file only when the file
  is its data, so a file from elsewhere keeps its own names, labels and
  scales even where a column shares a name with a survey variable. The
  survey's response timestamps (`created_at` and the others) are known only
  if the file has those columns.
- While the file is not read yet, or cannot be read, the names below it are
  not checked, and their fields take a typed name ("a column of the file",
  or "columns of the file, separated by commas").
- A table a [Write table](#write-table) node writes from the file brings the
  file's columns to the flows that read it.

**Where the labels come from.** With **Codebook** `auto`, the node takes the
labels, value labels and scales from the dictionary you choose, else the
labels inside an SPSS or Stata file, else the questionnaire's codebook when
the file is this survey's data — at least half of the file's answer columns
are the questionnaire's variables and they are at least half of its variables
(or the file's dictionary labels them as the questionnaire does), and their
answers fit — else the file's own: its names, the labels of its label row,
and scales guessed from its values. Once the file has been read, the flow is
checked and run with what auto decided then, so a later edit of the
questionnaire does not change it until the flow is checked again.

**On the platform:**

- The node reads a file you uploaded under [[Files|Studio-Files]], chosen by
  its name in **File** — for example `household_survey.xlsx` — or uploaded
  from the node with **Upload…** (see [Where files go](#where-files-go)).
  **Files** reads each data file once it is uploaded, so the node usually
  knows its columns before you open it. Runs, **Run all** and **Run to here**
  all get it.
- Only the uploads a flow names are copied into its run. An uploaded
  dictionary is therefore not found "next to the file" on the platform:
  choose it in **Dictionary (JSON)** as well — the field offers **Use
  panel_wave2.dictionary.json** when the file is `panel_wave2.csv`.
- An upload that is missing shows in the run's log before the node fails:
  "note: assets/panel_wave2.csv is not among this project's Files" (or "… is
  listed under Files but its content is gone"). Each run reads the file as it
  is in **Files** at that moment, and its log says which version it read:
  "read assets/panel_wave2.csv (sha256 …)", the start of the content's hash,
  so two runs over a replaced upload can be told apart.
- In a research bundle made **with the responses so far**, the uploads the
  flows name are included at the same path; in a bundle without data, put
  the file there yourself (see [[Reproducibility|Studio-Reproducibility]]).

### Responses

`source.responses` · platform — the answers collected by your survey,
from the project's `responses` table, as SurveyData labeled by the
questionnaire's codebook. New flows start with one of these already placed
(id `src`).

**In:** none → **Out:** `data` (SurveyData)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Table** | text | `responses` | — | Which project table to read. `responses` is the table your survey writes. A table name has lowercase letters, digits and `_`, starts with a letter or `_`, and has at most 63 characters. |
| **Environment** | text | `main` | — | Keep the responses collected by this environment's deployments (plus rows no deployment collected, such as imported or sample data). Typed as text, e.g. `main` or `pilot`: lowercase letters, digits and `-`, starting with a letter, at most 63 characters. |
| **Only completed responses** | checkbox | off | — | Drop interviews that were started but not submitted. |

What comes in besides the answers: `duration_s` (interview length in
seconds), `started_at`, `captcha`, `tab_switches`, `hidden_seconds`, `pastes`
and every URL parameter of the survey link (`url_…`).

**How the answers arrive.** One column per variable, whichever survey runtime
collected the response — responses stored before the current runtime are read
into the same layout:

- A question that writes several variables — a matrix, a MaxDiff, a conjoint,
  a Multiple choice with **Data layout** `wide` — arrives as one column per
  variable. A wide choice is 1 when chosen and 0 when offered and not chosen;
  with the current survey runtime, an option the respondent never saw
  (hidden by its own condition) is left empty rather than 0.
- A matrix answer is the column's codebook code: a 0–10 scale is 0–10.
  Responses collected by an earlier runtime, which stored the column's
  position (1–11 for a 0–10 scale), are read as the code too — so a matrix
  whose codes are not 1, 2, 3, … gives different numbers than it did before
  this was fixed. Check **Recode** mappings, **Filter rows** values and
  weighting targets written against the old values.
- "Other (please specify)" arrives as the question's Other code (`-66` unless
  the question sets another) in the question's variable, and the typed text
  in its own column, `<variable>_other`. "None of the above" is the
  question's None code (`-77` unless set), and "Not applicable" the
  variable's declared not-applicable code — or the text `na` when the
  codebook declares none. See
  [[Codebook and Variables|Studio-Codebook-and-Variables]].
- A variable a custom script writes arrives as its own column; flags an
  earlier runtime stored together (`__flags__`) arrive one column each (for
  example `speeder`).

Notes:

- **Environment** keeps the responses of that environment's deployments plus
  the rows no deployment collected (imported data, a template's sample data).
- **Only completed responses** has no effect on a table without a `partial`
  column. Partial interviews reach the `responses` table only from surveys
  published with the current survey runtime: a survey published before
  partial saves were fixed sends only submitted interviews until you publish
  it again, and from then on a flow that does not check this box sees its
  partial interviews too.
- A **Table** or **Environment** that no project can have (see the rules
  above), including a name that ends in a line break, fails the engine check
  at Save: "“x y” is not a table name: …" or "“Main” is not an environment
  name: …".
- In a research bundle this node reads a data file instead of the database.
  A bundle made with data carries one already filtered the way this node
  filters (`data/responses.main.csv`, `data/responses.main.completed.csv`, or
  `data/responses.csv` when the filter keeps every row); with a file you
  supply yourself, the file is read as is. See
  [[Reproducibility|Studio-Reproducibility]].

### Simulated data

`source.simulated` — "Synthetic responses generated from the questionnaire's
logic — conditions, routing, assigned arms — for building a flow before
fieldwork." The same seed gives the same data, including in a research
bundle.

**In:** none → **Out:** `data` (SurveyData)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Respondents** | whole number | `200` | at least 1 | How many synthetic respondents to generate. |
| **Seed** | whole number | `42` | — | Random seed: the same seed gives the same data every time. |

Each simulated respondent walks the questionnaire as the survey would move
them, its scripts included:

- a Scripts → **Assign to a condition** arm is drawn by the arms' weights and
  arrives as a column (a nominal variable labeled with the arms), and the
  pages shown only to one arm are filled for that arm;
- a page shuffle is dealt to each respondent;
- questions hidden by their own, their block's or their page's condition stay
  empty, and so do answer options hidden by their own condition.

Quotas belong to publishing, not to the questionnaire, so no quota closes
here (Test → Simulate in the Builder does apply them). The generated line is
`n_<id> = simulate_survey(survey, n=…, seed=…)`. In a research bundle whose
engine pin lags behind Studio (the README says so), this node stops with an
error — see [[Reproducibility|Studio-Reproducibility]].

### Project table

`source.table` · platform — a table in the project database, typically one
another flow wrote with **Write table** (for example a cleaned copy of the
responses), as SurveyData labeled by the questionnaire's codebook.

**In:** none → **Out:** `data` (SurveyData)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Table** | text | required | — | Name of a project table written by a **Write table** node (or another table in **Data**): lowercase letters, digits and `_`, starting with a letter or `_`, at most 63 characters. |

- **Run all** runs this flow after the flow whose **Write table** writes the
  table named here, whatever the flows are called, and skips it (marked
  failed) when that flow fails. Running this flow on its own does not run the
  writer first: it reads the table as it is. See
  [Run all](Studio-Flows#run-all).
- A table no run has written yet stops the node, in a preview and in a run:
  "The table clean_responses does not exist yet: it is written by 1. Clean
  raw responses. Run that flow (or Run all) first, then this one." — naming
  the flow whose **Write table** writes it, or "…: a flow's Write table node
  makes it." when none does.
- A multiple-choice question kept as one variable, and a ranking, come back
  as lists, as from **Responses**, so **Explode multiple choice** and a tab
  book read them.
- The table brings the variables its writer stored with it — labels, scales
  and value labels of a recode, a derived variable, an index, a cluster, the
  quality flags — merged with the questionnaire's codebook (the
  questionnaire's entry wins a name both have). They can be picked in this
  flow's nodes ("from table *table* · made by *flow*"), and naming one passes
  the engine check. A table last written before tables kept their variables
  arrives without those labels until its writer runs again. See
  [Cleaning and Weighting Data](Studio-Cleaning-and-Weighting#writing-the-cleaned-data-to-a-table).
- In a research bundle made with data this node reads `data/tables/<table>.csv`
  — the table as it was in the project database when the bundle was made,
  with its variables in `data/tables/<table>.dictionary.json` — not a table
  the writing flow produces there.

---

## Prepare

SurveyData in, SurveyData out: the steps a methods section calls "data
preparation". The recommended order is described in
[[Cleaning and Weighting Data|Studio-Cleaning-and-Weighting]].

### Apply weight

`prepare.apply_weight` — "Weight the results downstream by a column. Weighted
results say so, and a result with no weighted form says it is unweighted."
Use it after **Cell weights** or **Rake weights** created the column (or when
the data already carries one).

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Weight column** | text | `weight` | — | The column holding the weights. The hint under it lists which results are weighted and which are not (the two tables below). |

These nodes use the applied weight, and their output names it (`Weight` or
`weight` among the statistics). In the weighted tables and charts a weight
that is missing or not a number counts as 0.

| Node | Weighted |
|---|---|
| **Frequencies** | N is the sum of the weights and the percentages follow it, with an **Unweighted N** column beside it (see [Frequencies](#frequencies)) |
| **Crosstab** | cells and totals are sums of weights and the percentages are taken from them; the chi-square test uses Kish's effective base. Fisher's exact test counts respondents (see [Crosstab](#crosstab)) |
| **Group means** | means, SDs and medians; N, the significance test and the post-hoc pairs stay unweighted (see [Group means](#group-means)) |
| **Descriptive statistics** | mean, SD, median and quartiles, beside a **Weighted N** column; N, Missing, skewness and kurtosis are not weighted (see [Descriptive statistics](#descriptive-statistics)) |
| **Correlation**, **Correlation matrix** with **Method** `pearson` | the coefficient, with its p-value and CI on Kish's effective base (see [Correlation](#correlation)) |
| **Banner table** | percentages and counts; tests on Kish's effective base |
| **Net Promoter Score** | the shares and the score (its standard error on Kish's effective base); N counts respondents |
| **Regression** | linear models become weighted least squares; logistic and ordinal logistic models are weighted too |
| **TURF** | the base, each portfolio's reach and its frequency |
| **MaxDiff** | every column: **Shown**, **Best**, **Worst**, **Score**, **Utility** and **Share %** (see [MaxDiff](#maxdiff)) |
| **Conjoint** | the part-worths and **Importance %** (see [Conjoint](#conjoint)) |
| **Share of preference** | the shares, from weighted part-worths |
| **Principal components** | loadings, eigenvalues and explained variance, from the weighted covariance (or correlation) matrix |
| **Scale reliability** | alpha, item means, item–total correlations and alpha-if-deleted |
| **Key drivers** | the correlations, betas, R² and every driver's share, from the weighted correlation matrix; the tests on Kish's effective N (see [Key drivers](#key-drivers)) |
| **Perceptual map** | every cell of the table it maps is a sum of weights; the chi-square test of a crosstab counts respondents (see [Perceptual map](#perceptual-map)) |
| **Price sensitivity** | every curve and share; **N** stays the respondents (see [Price sensitivity](#price-sensitivity)) |
| **Bar chart** | bars are sums of weights or weighted percentages — split into groups too, in a histogram and a donut too — or weighted means with **By**; its confidence intervals and significance letters are on Kish's effective base (see [Bar chart](#bar-chart)) |
| **Heatmap** with **By**, or without it with **Method** `pearson` | weighted means by group; weighted Pearson coefficients |
| **Likert chart** | the shares are sums of weights; each item's `n` counts respondents (see [Likert chart](#likert-chart)) |
| **Trend** | each point's percent, mean or count (the sum of weights), its band on Kish's effective base; the bases count respondents (see [Trend](#trend)) |
| **Result chart** | as the result it draws is, and its title's second line says which (see [Result chart](#result-chart)) |
| **Proportion CI** | only when its **Weighted** box is checked (see [Proportion CI](#proportion-ci)) |
| **Tab book (Excel)** | counts and bases are sums of weights (shown to one decimal) beside the unweighted base, percentages are of those sums, and the letters test on Kish's effective base (see [Tab book (Excel)](#tab-book-excel)) |

These have no weighted form. After Apply weight they run on the respondents
as they are and **say so**: "unweighted (the weight 'weight' is not applied)"
— as a `weight` statistic, a `Weight` line under the table, or a second line
of the chart's title (also under a title you set):

| Node | Where it says so |
|---|---|
| **Compare groups** | statistic `weight` |
| **Correlation** with **Method** `spearman` or `kendall` | statistic `weight` |
| **Correlation matrix** with **Method** `spearman` or `kendall` | `Weight` under the table |
| **t-test** | `Weight` under the table |
| **Paired tests** (Cochran's Q too) | `Weight` under the table (and under the pairs of Friedman and Cochran's Q) |
| **Factor analysis** | `Weight` under each of its three tables |
| **Group means** | the post-hoc table's `Weight` line (the means above it are weighted) |
| **Crosstab** with **Test** `fisher` | its `Base` line: "the test counts respondents (an exact test needs whole counts); weighted counts shown" |
| **Perceptual map**'s chi-square test | `Chi-square counts` = "respondents (unweighted), as a test of a table must" (the map itself is weighted) |
| **Cluster (k-means)** | statistic `weight` |
| **Proportion CI** with **Weighted** unchecked | statistic `weight` |
| **Box plot**, **Scatter plot**, **Heatmap** without **By** with **Method** `spearman` or `kendall` | second title line |
| **Response quality**, **Code open answers**, **Data check** | `Weight` under their table: they count responses, answers and rows |
| **Bands**, **MaxDiff scores** | `Weight` in their statistics: they count respondents, or score each one |

**Describe** counts rows and, on weighted data, adds a `weighted_n_valid`
column: the weighted base a table of each variable would report. The data
files of **Choice data for HB** and **Conjoint data for HB** have no weight
column. The Methods draft describes the step as "estimates that support
weights were weighted by `weight` (rank tests, k-means clustering, box and
scatter plots and Spearman and Kendall correlation heatmaps stay unweighted,
as do t-tests, the tests of group means (ANOVA, Welch's ANOVA) and their
post-hoc comparisons, paired tests (Cochran's Q among them), Fisher's exact
test, a perceptual map's chi-square test, rank correlations and factor
analysis)".

> **Note.** The MaxDiff **Utility** and **Share %**, Conjoint, Share of
> preference, Principal components, Scale reliability, the Bar chart and the
> Heatmap of means were computed unweighted after Apply weight before this was
> fixed, and a weighted **Proportion CI** counted non-respondents in its base.
> A TURF portfolio's frequency was unweighted too. Run a weighted flow again
> and these numbers change; reports and tiles from earlier runs keep the old
> ones.

### Bands

`prepare.bands` — "Cut a number into bands — age into age groups, income into
brackets — as a labeled ordinal variable; what falls outside every band is
counted."

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Variable** | variable | required | ordinal / interval / ratio variables | Its missing codes (a 999 "Refused") are left out before cutting, so they never land in a band. |
| **Boundaries** | JSON | required | — | Increasing numbers, e.g. `[18, 30, 45, 65, 100]`. A band includes its lower boundary and runs up to, not including, the next; values outside every band stay blank. |
| **Band labels** | JSON | — | — | One fewer than the boundaries, e.g. `["18–29", "30–44", "45–64", "65+"]`. Defaults to "18 to under 30" and so on. |
| **New variable** | text | required | — | Name of the band variable. |
| **Label** | text | — | — | Defaults to the variable's label and "(bands)". |
| **Bands include their upper boundary** | checkbox | off | — | Then a band runs from above its lower boundary up to and including the upper one (the first band takes its lower boundary too). |

- The new variable is ordinal, coded 1, 2, 3, … in the order of the bands,
  with the band labels as its value labels — so a **Crosstab** or **Group
  means** by it prints "18 to under 30", not `1`. Later nodes offer it in
  their variable lists ("made by *node*"), and a **t-test**'s **Group A** and
  **Group B** offer its bands.
- With **Bands include their upper boundary** checked, the default labels read
  "18 to 30", "over 30 to 45", ….
- The `stat` output names the step (`Variable` = `age → age_band`), counts
  each band (`Bands` = `16 to under 30: 12; 30 to under 45: 15; …`) and what
  fell outside (`Outside the bands`), and adds `Missing codes`, `Blank` and
  `Not numbers` when there are any. A value outside every band (below the
  first boundary, or at or above the last) is blank in the new variable,
  never forced into the nearest band.
- Boundaries that do not increase, or labels whose number does not match,
  stop the run with the reason: "Band boundaries must increase, got [18, 18,
  30].", "5 boundaries make 4 bands, but 3 labels were given."
- The counts are of respondents; on weighted data the statistics add `Weight`
  = "unweighted (the weight 'weight' is not applied)". Tables of the band
  variable after **Apply weight** are weighted as usual.

### Cell weights

`prepare.cell_weights` — post-stratification on one variable: after
weighting, that variable's distribution matches your targets. It adds the
weight column but does not apply it — follow it with **Apply weight**.

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Variable** | variable | required | nominal / ordinal variables | The single-answer variable to weight on. |
| **Targets (code → share)** | JSON object | required | — | Target share per code, e.g. `{"1": 0.45, "2": 0.55}`. Shares or counts both work; they are normalized. |
| **Weight column** | text | `weight` | — | Name of the new weight column. |
| **Cap** | number | — | at least 1 | Upper bound for weights of mean 1 (must be greater than 1). Capping makes the match to the targets approximate. |

- Targets may be shares or counts; they are normalized, so
  `{"1": 45, "2": 55}` and `{"1": 0.45, "2": 0.55}` mean the same.
- A category you leave out of the targets keeps its current share.
- Weights are scaled to a mean of 1, so the weighted N equals the number of
  rows. **Cap** must be greater than 1.
- A multiple-answer variable is refused: a respondent in two categories has no
  single cell. Weight on a single-answer variable, or on the 0/1 columns
  **Explode multiple choice** creates.

### Dedup respondents

`prepare.dedup` — one row per respondent. A respondent who resumed the survey
or submitted twice is kept once: the latest submission by default.

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Respondent id column** | text | `respondent_id` | — | Column that identifies a respondent. |
| **Order by** | text | `submitted_at` | — | Column that orders a respondent's submissions. If it is missing, Studio falls back to `submitted_at`, `started_at`, `updated_at` or `created_at`, whichever exists. |
| **Keep** | choice | `last` | `first`, `last` | `last` keeps the most recent submission, `first` the earliest. |

Rows with a blank respondent id are always kept, each as its own respondent.
Data without the id column passes through unchanged.

### Derive

`prepare.derive` — a new variable computed from others with a small formula
language: arithmetic, functions and `if … then … else`. The formula is stored
as text and parsed, never executed as code, so what you write is exactly what
a reviewer reads in the generated script.

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **New variable** | text | required | — | Name of the new variable. |
| **Formula** | formula | required | — | e.g. round(spend_year / 12, 2), or: if age < 30 then 1 else 2. Functions: mean, sum, min, max, abs, round, log, coalesce. A missing answer stays missing; dividing by zero gives missing, not infinity. |
| **Label** | text | — | — | Defaults to the formula itself — the most honest description of the number. |
| **Scale** | choice | `ratio` | `ratio`, `interval`, `ordinal`, `nominal` | Measurement scale of the new variable. Choose `nominal` or `ordinal` when the result is a code rather than an amount. |
| **Value labels** | JSON object | — | — | For a formula that yields codes: code → label, e.g. {"1": "Under 30", "2": "30 or over"}. Set the scale to ordinal or nominal with them. |

**Value labels** are typed as JSON, codes as keys:
`{"1": "Under 30", "2": "30 or over"}` for `if age < 30 then 1 else 2` — the
example the empty box shows. Tables of the new variable then print the labels,
not `1` and `2`, and a **t-test**'s **Group A** and **Group B** downstream offer
`1 — Under 30` and `2 — 30 or over`. To cut a number into ranges, **Bands**
writes the labels for you.

**The formula language.**

| Element | Syntax |
|---|---|
| Numbers | `12`, `0.5`, `.5` |
| Variables | codebook names, e.g. `spend_year`, `q1` |
| Arithmetic | `+`, `-`, `*`, `/`, unary `-`, parentheses |
| Comparisons | `=`, `!=`, `>`, `>=`, `<`, `<=` |
| Logic | `and`, `or`, `not` |
| Conditional | `if <condition> then <value> else <value>` |
| Functions | `mean(…)`, `sum(…)`, `min(…)`, `max(…)` — across their arguments, row by row; `abs(x)`, `round(x, digits)`, `log(x)`, `coalesce(x, y, …)` |

Examples: `round(spend_year / 12, 2)` · `(q1 + q2 + q3) / 3` ·
`mean(q1, q2, q3)` · `if age < 30 then 1 else 2` ·
`if income > 0 then round(income / 12, 2) else 0` · `coalesce(children, 0)`.

Precedence, loosest first: `if … then … else`, `or`, `and`, `not`,
comparisons, `+ -`, `* /`, unary minus. The comparison and logic words mean
exactly what they mean in a skip-logic condition. `contains` (chose) is not
available: a formula works on numbers — run **Explode multiple choice** first
and use the 0/1 column.

Two behaviors to know before you read a result:

- **A blank stays blank.** A respondent who skipped a question has no value,
  and arithmetic on it has none either. Dividing by zero also gives a blank
  rather than infinity — an infinity looks like a number all the way into the
  report. Write `coalesce(x, 0)` where you mean "treat a blank as zero".
- **A text variable is refused by name**, rather than turning into a column of
  blanks. Recode it first.

A formula is checked when you press **Check** and when you Save: an unreadable
one says where reading stopped ("… (at character 14)"), and a variable that is
neither in the codebook nor made earlier in the flow is named. Write it on one
line: the box wraps long formulas, but a line break in it fails the check (see
[One-line texts](#reading-this-page)).

### Explode multiple choice

`prepare.explode` — one 0/1 column per option of a multiple-answer question
(`brand_1`, `brand_2`, …), so that weights, regression, clustering and TURF can
read it.

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Multiple-choice variable** | variable | required | nominal variables | A question whose answers are lists of codes. |
| **Column prefix** | text | — | — | Defaults to the variable's own name and an underscore, so option 1 becomes brand_1. |

Each column is named with the option's code as the engine writes it: a code
the codebook's `{code: label}` form writes as `1.0` makes `brand_1.0`, and the
variable pickers downstream offer that name.
| **Drop the original column** | checkbox | off | — | Off by default — the list column still answers questions the indicators cannot, such as how many options each respondent picked. |

Someone who did not answer the question gets a **blank** in every indicator,
not a row of zeroes — "chose nothing" and "was never asked" are different
facts, and only the first belongs in a base. The indicator names follow the
codebook's codes (`<prefix><code>`), and later nodes offer them in their
variable lists ("made by *node*") — for example as a **TURF**'s **Options**.
A Multiple choice question with **Data layout** `wide` already has one 0/1
variable per choice and needs no Explode.

### Filter rows

`prepare.filter` — keeps only the respondents who satisfy a condition, built
with the same visual editor as the questionnaire's logic.

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Condition** | condition | required | — | Rows that satisfy the condition are kept; the others are removed. |

A condition edited by hand in the flow's JSON is checked as the engine will
write it: a part of an *and* / *or*, or what a *not* negates, that is not a
comparison or a variable, and a variable reference without a name, are errors
on the node before a Save.

The editor offers **ALL of the following** / **ANY of the following**, the
operators = ≠ > ≥ < ≤ **in**, **not in**, **chose**, **did not choose**, and
value pickers that show value labels (`Capital region (1)`). Its variables
are those available at this node — the codebook's, and those made upstream,
such as `quality_score` or a recode — so you can, for example, keep only
`quality_score` = `0`. A condition that nests groups opens as JSON.
Conditions typed as raw text are refused ("raw string conditions cannot be
evaluated on data").

### Index / scale

`prepare.index` — combines several items into one index variable, the mean
or the sum of the items. Check the items' internal consistency with **Scale
reliability** first.

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Index name** | text | required | — | Name of the new index variable. |
| **Items** | variables (several) | required | — | The component variables. |
| **Method** | choice | `mean` | `mean`, `sum` | `mean` or `sum` of the items. |
| **Label** | text | — | — | Codebook label of the index. |

### MaxDiff scores

`prepare.maxdiff_scores` — "One counting-score variable per MaxDiff item, per
respondent — best minus worst over the times it was shown — so the
preferences can go into a crosstab, a cluster or a regression."

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **MaxDiff question** | text | required | — | The question's id or name. Its design is read from the questionnaire. |
| **Variable prefix** | text | — | — | Each item's score is <prefix><item code>. Defaults to the question and _score_, so item 3 of q_md becomes q_md_score_3. |

- **MaxDiff question** is a dropdown of the questionnaire's MaxDiff questions
  (**— pick a MaxDiff question —**), each as `name — question text`. A stored
  name the questionnaire does not have is kept and marked "(not in the
  questionnaire)", and the engine check names it at **Check** and at Save:
  "Parameter 'question' of md_scores: no MaxDiff question named 'q_mdx'; this
  questionnaire has: q_md." With no MaxDiff question in the questionnaire the
  field is a text box.
- One variable per item, `q_md_score_1`, `q_md_score_2`, …, labeled
  "MaxDiff score: *item*", interval, from −1 (picked worst every time it was
  shown) to 1 (picked best every time). A respondent who was never shown an
  item has a **blank** for it, not a 0: "never picked" and "never offered" are
  different answers. Later nodes offer the variables ("MaxDiff score: Price ·
  made by *node*").
- The `stat` output gives the **Question**, **Respondents scored**, **Not
  scored**, **Items**, the **Variables** (`q_md_score_1 … q_md_score_5`), the
  **Score** ("best minus worst over times shown, −1 to 1; blank where never
  shown") and, when some answers could not be read against the design,
  **Unreadable answers** with the reasons.
- The scores are per respondent, so no weight enters them; on weighted data
  the statistics say "unweighted (the weight 'weight' is not applied)". A
  **Group means** of a score after **Apply weight** is weighted as usual.
- These are counting scores from a few tasks per person: coarse but real. The
  **MaxDiff** node gives the aggregate utilities; for individual utilities,
  export with **Choice data for HB**.

### Missing values

`prepare.missing` — applies the codebook's declared missing codes ("Don't
know", "Refused" with their codes): they become blanks, so they stop counting
as real values in means and tests. Optionally drops the rows that are blank in
chosen variables.

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Action** | choice | `to_nan` | `to_nan`, `drop_rows` | `to_nan` turns the codebook's declared missing codes into blanks; `drop_rows` does that and then drops rows blank in the variables listed below. |
| **Drop rows missing in** | variables (several) | empty | — | For drop_rows: rows with a blank in any of these variables are dropped. |

The inspector shows **Drop rows missing in** only while **Action** is
`drop_rows` (see [Fields that depend on a choice](#reading-this-page)).

Put this node before any analysis whose defaults count a missing code as an
answer — **Correlation** with `spearman`, **Compare groups** without Dunn's
test, **Group means** with **Test** `auto`, the **Crosstab** chi-square; each
of them says when it did. A test you choose by hand (**Correlation**
`pearson` or `kendall`, **Compare groups** with Dunn's test, **Group means**
with another **Test**, **Crosstab** with `fisher`), and the **t-test**,
**Correlation matrix**, **Paired tests**, **Factor analysis**, **Descriptive
statistics** and **Bands**, leave the codes out on their own (see
[Analyze](#analyze)).

### Response quality

`prepare.quality` — flags straightlining, contradictions, duplicate answer
patterns and failed attention checks. By default it **marks** responses rather
than dropping them, so you decide what to exclude and say so in your
write-up.

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData), `table` (Table)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Battery to check** | variables (several) | empty | — | A matrix or a battery of same-scale items. Straightlining and duplicate patterns are measured across these; a flat pattern (the same answer throughout) is straightlining, never a duplicate, since two straightliners of one column match whoever they are. |
| **Duplicates also match on** | variables (several) | empty | — | Other answers a duplicate must repeat as well as the battery, such as age, gender and a few questions of their own. Two honest respondents can answer a battery alike, and both are dropped as one person submitting twice; the more answers two responses must share, the surer the match. Empty, the battery alone decides. |
| **Answers that must agree** | JSON object | empty | — | left variable: right variable. A respondent answering them differently is flagged as contradictory. |
| **Attention checks** | JSON object | empty | — | variable: the answer a reading respondent gives. |
| **Straightlining tolerance** | number | `0.0` | at least 0.0 | Standard deviation across the battery at or below which a response counts as flat. 0 means literally identical answers. |
| **Mode** | choice | `flag` | `flag`, `drop` | Flag adds the columns and keeps everyone; drop also removes the flagged responses. |
| **Flags column** | text | `quality_flags` | — | New variable holding the names of the failed checks (empty when clean). |
| **Score column** | text | `quality_score` | — | New variable counting the failed checks (0 when clean). |

The four checks:

| Check (name in the flags) | Flagged when |
|---|---|
| `straightlining` | the standard deviation of a response across **Battery to check** is at or below **Straightlining tolerance** |
| `inconsistency` | a pair in **Answers that must agree** was answered differently |
| `duplicate` | the response's complete answer pattern across a battery of at least 5 items — not a flat one — is identical to another response's, and so are its answers to **Duplicates also match on** (two unanswered ones match) — every member of such a group is flagged |
| `attention` | an attention-check variable was answered with anything but the expected answer |

- **Flags column** (`quality_flags`) holds the failed checks joined with
  `; `, e.g. `straightlining; duplicate`, and is empty for a clean response;
  **Score column** (`quality_score`) counts them. Both enter the codebook
  (labels "Quality flags" and "Checks failed") and travel into exports and the
  generated script.
- **Second output — `table`:** one row per check with N and %, then **Any
  check** and **Clean**, as shares of everyone screened, counted *before*
  anything is dropped. Wire it into a **Report section** to put your exclusion
  numbers in the report. The counts are of responses whatever the weight; on
  weighted data the table says "Weight: unweighted (the weight 'weight' is not
  applied)".
- Later nodes offer `quality_flags` and `quality_score` in their variable
  lists, so a **Filter rows** can keep the clean responses (`quality_score` =
  `0`) instead of **Mode** `drop`.
- For **Attention checks**, the inspector offers **Fill from the questionnaire
  (N marked)** when questions are marked as attention checks in the Builder;
  otherwise it says "Mark a question as an attention check in Builder to fill
  this in."

### Rake weights

`prepare.rake_weights` — iterative proportional fitting: adjusts weights until
several margins (region, gender, age group…) match their targets at once. It
adds the weight column but does not apply it — follow it with **Apply
weight**.

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Targets (variable → code → share)** | JSON object | required | — | One block per margin, e.g. `{"region": {"1": 0.45, "2": 0.30, "3": 0.25}, "gender": {"1": 0.48, "2": 0.52}}`. |
| **Weight column** | text | `weight` | — | Name of the new weight column. |
| **Max iterations** | whole number | `50` | at least 1 | Maximum raking passes. |
| **Tolerance** | number | `1e-06` | — | Stop when no margin changes by more than this in a pass. |
| **Cap** | number | — | at least 1 | Upper bound for weights of mean 1 (must be greater than 1). |

Targets are normalized per margin (shares or counts). A category missing from
a margin's targets is left unadjusted on that margin. Weights are scaled to a
mean of 1. Multiple-answer variables are refused, as for **Cell weights**.

### Recode

`prepare.recode` — maps the codes of a variable onto new codes, into a new
variable with its own codebook entry: collapsing a 5-point scale to 3 points,
merging small categories, harmonizing codes between waves.

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Variable** | variable | required | — | The variable to recode. |
| **Old code → new code** | JSON object | required | — | Old code → new code, e.g. `{"1": 1, "2": 1, "3": 2}`. Codes not listed are left blank in the new variable. |
| **New variable** | text | — | — | Defaults to `<variable>_recoded`. |
| **Label** | text | — | — | Codebook label of the new variable. |
| **Scale** | choice | — | `nominal`, `ordinal`, `interval`, `ratio` | Measurement scale of the new variable. |

- Codes you do not list in the mapping become blank in the new variable, so
  list every code you want to keep (`{"1": 1, "2": 2, "3": 3, "4": 3, "5": 3}`).
- The new variable's value labels are its codes themselves (`1`, `2`, …):
  there is no field for value labels, so tables of a recoded variable show
  codes. Say what the codes mean in the **Label** or in a caption.
- **Scale** defaults to the source variable's scale; **Label** defaults to the
  new variable's name.
- Later nodes offer the new variable in their variable lists, as
  "*label* · made by *node*".

### Select columns

`prepare.select` — keeps only the listed variables.

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Variables** | variables (several) | required | — | The variables to keep. |

Everything else is dropped, including columns later nodes may need — the
weight, `respondent_id`, timestamps. Select late, or include them.

### Speeders & partials

`prepare.speeders` — quality screening on interview length and completeness.
It adds two columns, `duration_s` and `partial`, and drops speeders. With
**Drop partials** on, it also drops the interviews that miss any of the
**Required answers**; with no required answers listed, it drops no partials.
Later nodes offer both in their variable
lists ("completion time · made by *node*", "partial response · made by
*node*").

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Minimum seconds** | whole number | `60` | at least 0 | Interviews completed faster than this are dropped; `0` drops none. |
| **Required answers** | variables (several) | empty | — | An interview is *partial* when any of these is blank. With none listed, no interview is. |
| **Drop partials** | checkbox | on | — | Also drop the interviews that **Required answers** marks as partial. Off, they stay, marked in `partial`. |

The rules, precisely:

- A **speeder** is a response whose duration is known and shorter than
  **Minimum seconds**. Duration is the platform's interview length, or
  `submitted_at` − `started_at` when that is all the data has. A response
  whose duration is unknown is never treated as a speeder.
- A response is **partial** when *any* variable in **Required answers** is
  blank. With no required answers listed, nobody is partial, so **Drop
  partials** removes nothing. A required name that does not exist in the data
  marks *every* response partial — check the names.
- The node's `partial` replaces the table's own `partial` column, so an
  interview broken off after answering every required question stays in,
  marked `false`. To leave unfinished interviews out, check **Only completed
  responses** on the [Responses](#responses) node.

### Code open answers

`prepare.text_code` — applies a **codeframe** to an open-text variable: each
answer gets the themes a coder gave it by hand, else the ones the codeframe's
word rules find, else it stays uncoded. The same way at every run, with no
model and no network — and the rules code the answers collected after they
were written too. You build the codeframe in the codeframe editor. See
[[Coding Open Answers|Studio-Open-Answer-Coding]].

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData), `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Codeframe** | codeframe | required | — | The codeframe file (`analysis/<name>.codeframe.json`) — its themes, the answers coded by hand (kept as fingerprints, never as texts) and the rules that code the rest, including answers collected later. |
| **Theme variable** | text | — | — | Defaults to the name the codeframe carries. A codeframe that gives an answer several themes makes a multiple-choice variable (a list of codes per answer). |
| **Also add sentiment** | checkbox | off | — | A sentiment variable beside the theme, and each theme's negative / neutral / positive split in the table. Only when the codeframe was built with it — the stat says when it was not. |

- **Codeframe** is a dropdown of the project's codeframes (**— choose a
  codeframe —**), with a line under it: "Choose a codeframe document of this
  project." or "No codeframe document exists in this project." The button
  under it opens the codeframe editor: **New codeframe…** when none is
  chosen — it asks for the open-text variable and a name, sets the new file on
  the node at once and shows the answers this flow's **Responses** node
  reads — and **Edit codeframe…** for the chosen one. A new codeframe is a
  document only once saved in its editor; until then the dropdown lists it as
  "*path* (not saved)" and the line reads "*path* is not saved yet: it is kept
  in this tab until you save it in its editor." (in another tab: "*path* is
  not saved in this project: it was started and never saved. Start it again,
  or choose another codeframe."). There is no button to code with the AI
  assistant: AI coding of open answers is switched off on this platform.
- **Theme variable** left empty takes the name the codeframe carries (set in
  the editor's **Codeframe settings → Theme variable**, `<variable>_theme`
  by default).
- **Output `data`:** adds the theme variable (label `Theme: <variable>`, value
  labels = your theme labels): the code, or with several themes an answer the
  list of codes (a **multiple-choice** variable). An answer coded as no theme
  and an uncoded one are empty there. With **Also add sentiment**, also a
  `<theme variable>_sentiment` variable coded −1 / 0 / 1 (Negative / Neutral /
  Positive).
- **Output `table`:** one row per theme and per net ("*net* (net)", its themes
  under it; a net counts a respondent once), ordered by their counts, with N
  and %; then **No theme** (answers a coder decided have none, when there are
  any), **Coded**, **Coded by hand**, **Coded by rules** and **Uncoded**. Every
  % is of the **respondents who answered**; with several themes an answer the
  themes add up to more than 100 %. With **Also add sentiment** and a
  codeframe built with it, each row adds **Negative %**, **Neutral %** and
  **Positive %** of its answers.
- **Output `stat`** — the table's statistics, which it also prints under it:
  **Variable**, **Answered**, **Themes**, **Coverage** ("87.5 % of the answers
  are coded"), **Coded by hand**, **Coded by rules**, **Distinct uncoded
  answers** (how many different answers are left to read), **Percentages**
  ("of the respondents who answered", and with several themes an answer "; a
  respondent can have several themes, so the themes add up to more than 100
  %"), **Nets** when there are nets, and **Codeframe** (the model and when)
  for a codeframe the assistant built earlier. With sentiment: **Sentiment**
  ("negative 66.7 %, neutral 0.0 %, positive 33.3 % of 3 answers") and **Net
  sentiment** (positive minus negative, in points); asked of a codeframe
  built without it, **Sentiment** reads "not in this codeframe". Wire it into
  a **Live tile** to watch the coverage as new answers arrive.
- **An older codeframe (version 1)** — one the assistant built, or the example
  study's — gives the table it always did: theme rows as shares of the
  **coded** answers, **Coded** and **Uncoded** as shares of everyone who
  answered, **Coverage** "… % of the answers have a theme" and **Percentages**
  "a theme: of the coded answers; Coded and Uncoded: of all answers".
- The table counts answers, not weights; on weighted data it says "Weight:
  unweighted (the weight 'weight' is not applied)".
- Answers are matched by their text with case, spacing and Unicode form set
  aside, so a coder's decision holds wherever the same answer appears. The
  rules read the words: English negations, clauses, word forms (`delay*`),
  alternatives (`slow|late`), negated mentions (`not_late`) and words near
  each other (`staff ~3 rude`); no regular expressions.
- Later nodes offer the theme variable in their variable lists ("made by
  *node*"), whether its name is typed in **Theme variable** or left to a
  codeframe saved in the project. A multiple-choice theme variable is treated
  as a multiple-choice question: a donut, a **Split by**, a banner column or a
  Likert chart of it is refused. The sentiment variable is not offered.
- The flow's check reads the project's codeframes: a codeframe the run could
  not apply is an error of the flow ("Parameter 'codeframe' of *node*: *path*
  cannot be applied: …"), and so is one that codes a variable the
  questionnaire does not have ("… codes '*variable*', which is not a variable
  of this questionnaire.").

---

## Analyze

SurveyData in; a **Table**, a **Stat**, or both (**Cluster (k-means)** and
**Factor analysis** also pass the data on). Frequencies and Crosstab wired
straight to a **Responses** node also show instant counts in the inspector —
see [Instant counts](Studio-Flows#instant-counts). How each node treats an
applied weight is summed up under [Apply weight](#apply-weight).

**Which test.** You can let a node choose, or name the test yourself:

| Question | Node and choice |
|---|---|
| Does a mean differ between two groups? | **t-test** (Welch's by default, or Student's), or **Group means** with **Test** `welch` / `student` |
| … between three or more groups? | **Group means** with **Test** `anova` or `welch_anova`, and **Post-hoc** `tukey` / `games_howell` for every pair |
| Do ratings (ranks) differ between groups? | **Compare groups** (Mann-Whitney U, Kruskal-Wallis H, with Dunn's test for the pairs), or **Group means** with **Test** `mannwhitney` / `kruskal` |
| Do the same respondents answer two questions differently? | **t-test** with **Design** `paired`; **Paired tests** (Wilcoxon signed-rank, or McNemar for yes/no) |
| … three or more questions? | **Paired tests** (Friedman, with pairwise Wilcoxon tests) |
| … three or more yes/no questions (brands they know, channels they saw)? | **Paired tests** with **Test** `cochran` (Cochran's Q, with pairwise McNemar tests) |
| Is a mean different from a fixed value? | **t-test** with **Design** `one_sample` |
| Are two answers related? | **Crosstab** (chi-square, or Fisher's exact test for small counts); **Correlation** (Pearson, Spearman or Kendall) |
| How do several variables correlate? | **Correlation matrix** |
| What does an ordered answer (dissatisfied … satisfied) depend on? | **Regression** with **Model** `ordinal` |
| Which attributes drive an overall rating? | **Key drivers** |
| Which brands go with which attributes, or which regions with which answers? | **Perceptual map** |
| What would respondents pay? | **Price sensitivity** (Van Westendorp or Gabor-Granger) |
| Which items belong together? | **Factor analysis**, **Principal components**, **Scale reliability** |

To draw a result — means with their intervals, a scree plot, a reach curve,
odds ratios, a map, price curves — connect the node's table to a
[Result chart](#result-chart).

Three rules hold for all of these tests:

- **Missing codes are not answers.** A test you choose by hand — and the
  **t-test**, **Correlation matrix**, **Paired tests**, **Factor analysis**,
  **Key drivers**, **Perceptual map**, **Price sensitivity** and the ordinal
  **Regression** — leaves the codebook's missing codes (a "Refused" coded 9)
  out and says how many: "Missing codes left out = Trust: Acme: 44 (9 =
  Refused)" (in **Paired tests**, **Factor analysis**, **Key drivers**, a
  **Perceptual map** and **Price sensitivity**: "Missing codes = 44 answers
  with a missing code (9 = Refused) left out"; in the ordinal **Regression**:
  `missing_codes` = "Trust: Acme: 74 (9 = Refused)"). **Descriptive statistics** leaves them out
  too, counts them in its **Missing** column with the blanks and names the
  codes ("Missing codes = trust_acme: 9"). The defaults — **Correlation** `spearman`, **Compare
  groups** without Dunn's test, **Group means** with **Test** `auto`, the
  **Crosstab** chi-square — read the data as they always have, so a flow
  keeps its numbers, and say when they counted a missing code as an answer:
  "Missing codes counted as answers = Trust: Acme: 44 (9 = Refused); run
  Missing values first to leave them out" (`missing_codes_counted` among the
  statistics of **Correlation** and **Compare groups**). That is why **Group means** can give a
  Kruskal-Wallis H with **Test** `auto` and a different one with `kruskal`.
  Put **Missing values** first to have every node leave them out.
- **What the data cannot carry is said in words.** A two-group test asked of
  three groups, one respondent in a group, or no spread at all gives a line
  such as "Test = not run: Welch's t-test (unequal variances) compares two
  groups and Region has 3 — choose anova or welch_anova", not a number or a
  crash. A request that cannot work at all (a **t-test** of a grouping with
  three groups and none named) stops the run with the reason; the check warns
  about it before the run ("Gender has 3 answers (1 = Male, 2 = Female, 3 =
  Other); a t-test compares two — name them in Group A and Group B, unless the
  data this node reads holds only two of them."), and a **Paired tests** node
  given a number of variables its test cannot compare is an error of the
  check, in the run's own words ("McNemar compares exactly two variables; 3
  were given. For three or more yes/no variables, use Cochran's Q.").
- **The weight is used where there is a standard weighted form** (Pearson's
  correlation) and otherwise the result says "unweighted (the weight 'weight'
  is not applied)" — see [Apply weight](#apply-weight).

### Banner table

`analyze.banner` — the cross-break: several questions down the page, several
breakdowns across it, each cell a column percentage with its count, and
letters marking significant differences.

**In:** `data` (SurveyData) → **Out:** `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Questions (down)** | variables (several) | required | nominal / ordinal variables | One block of rows per question. |
| **Breakdowns (across)** | variables (several) | required | nominal / ordinal variables | Each becomes a block of columns. Letters run across the whole table, but columns are only compared inside their own block. |
| **Significance letters** | checkbox | on | — | Mark significant differences with column letters. |
| **Level** | number | `0.05` | 0.001–0.2 | Significance level for the letters. |
| **Multiple comparisons** | choice | `none` | `none`, `bonferroni` | `bonferroni` corrects for the number of comparisons; `none` is the industry default. |

A letter says this column is significantly higher than the column that letter
names — and three rules keep that claim honest, all restated under the table:

- Columns are compared **only inside their own block**. The values of one
  breakdown are mutually exclusive, which is what the test assumes; columns
  from two different breakdowns overlap (a northerner is also under 35), so
  they are never compared.
- On weighted data the test uses the **effective base** (Kish), because
  weights make a sample behave like a smaller one. The banner uses the
  applied weight.
- A column with **fewer than 30 respondents is not tested**, and the table
  says which ones those were.

The same test puts letters on a **Bar chart** split into groups
(**Significance letters**) and into every sheet of a
[Tab book (Excel)](#tab-book-excel), which writes each question of the study
by the banner to a workbook. Those two leave the codebook's missing codes out
and test each column on its respondents who answered; the Banner table
counts a missing code as an answer and tests on everyone in the column —
the same numbers when everyone answered and no missing code was given.

### Cluster (k-means)

`analyze.cluster` — segments respondents on a set of items with k-means
(the best of ten k-means++ starts, deterministic for a given seed). It adds a labeled nominal
cluster variable to the data and returns the centroids. Wire its `data` output
on to use the segments: later nodes offer the cluster variable in their
variable lists (a **Crosstab** by segment, say), and **Export file** or
**Write table** take it further.

The segmentation is drawn on the respondents as they are, never on the
weight: on weighted data its statistics carry `weight` = "unweighted (the
weight 'weight' is not applied)". To give the segments their weighted sizes,
run a **Frequencies** of the cluster variable on the weighted data.

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData), `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Items** | variables (several) | required | ordinal / interval / ratio variables | Variables to segment on. |
| **Clusters** | whole number | `3` | 2–12 | Number of clusters. |
| **Cluster variable** | text | `cluster` | — | Name of the new cluster variable. |
| **Seed** | whole number | `42` | — | The random draws of ten k-means++ starts; the start with the smallest within-cluster sum of squares is kept, so the clusters do not depend on the order of the rows. |
| **Standardize items** | checkbox | on | — | Put the items on a common scale before clustering. |
| **Number clusters by** | variable | — | one of the **Items** | Optional. Empty, the clusters are numbered by size, largest first; set, by this item's mean, lowest first. Two segments of close sizes swap numbers when a few respondents come or go, and a name given to a number (with **Derive**) then lands on the other segment; numbered by the item that tells them apart, each keeps its number. |

### Compare groups

`analyze.compare_groups` — a nonparametric test of whether a variable differs
between groups: "Mann-Whitney U for two groups, Kruskal-Wallis H for more —
with Dunn's test on every pair of groups after Kruskal-Wallis when asked."

**In:** `data` (SurveyData) → **Out:** `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Variable** | variable | required | ordinal / interval / ratio variables | The variable to compare. |
| **Group** | variable | required | nominal / ordinal variables | The grouping variable. |
| **Test** | choice | `auto` | `auto`, `kruskal`, `mannwhitney` | `auto` uses Mann-Whitney U for two groups and Kruskal-Wallis H for more. |
| **Post-hoc** | choice | `none` | `none`, `dunn` | Dunn's test compares every pair of groups after Kruskal-Wallis — one line per pair with z and the adjusted p. With it the codebook's missing codes are left out of the test too, and the result says how many; without it they are counted as answers, as they always were, and the result says so (missing_codes_counted) — so the Kruskal-Wallis result can change. Run Missing values first to have both leave them out. |
| **Dunn p adjustment** | choice | `holm` | `holm`, `bonferroni` | Shown only with **Post-hoc** `dunn`. |

- Without Dunn's test the statistics are `statistic` and `p_value`, with
  `groups` (Kruskal-Wallis) or `group_a` and `group_b` (Mann-Whitney), and
  `missing_codes_counted` when a missing code was counted as an answer. With
  it they name the `test` ("Kruskal-Wallis H"), `statistic`, `p_value`,
  `groups`, `n` and `posthoc` ("Dunn's test (Holm)"), then one entry per pair
  of groups, by their value labels — `Capital vs North` = "z = 0.193, p =
  1.0" (the adjusted p) — and `missing_codes` for the codes left out.
- Rule: "Dunn's test follows Kruskal-Wallis — set Test to kruskal or auto, or
  Post-hoc to none." (an error with **Test** `mannwhitney`).
- For the same test with the means table, the effect size and a table of the
  pairs, use **Group means** with **Test** `kruskal` and **Post-hoc** `dunn`.

Rank tests have no standard weighted form: on weighted data the test runs on
the respondents as they are, and the statistics add `weight` = "unweighted
(the weight 'weight' is not applied)".

### Conjoint

`analyze.conjoint` — part-worths and attribute importance from a
choice-based conjoint question: what people gave up to get what.

**In:** `data` (SurveyData) → **Out:** `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Conjoint question** | text | required | — | The question's id or name. Its attributes and design are read from the questionnaire. |

Every level is measured against the first level of its own attribute, which
sits at zero. Importance is an attribute's range of part-worths over the sum of
all ranges — **of the levels you tested**: price from £10 to £12 will look
unimportant beside price from £10 to £100, and that is a fact about your
design. Estimates are aggregate; for individual-level part-worths, export with
**Conjoint data for HB**. The statistics give the **Question**, the **Base**
("812 respondents"), **Tasks read**, the **Method** ("conditional logit
(aggregate)"), the **Reference**, **Pseudo R²** and a **Note** that importance
is of the levels tested. After **Apply weight** the part-worths — and so the
importances — are fitted on the weighted choices, the **Base** gives the
weighted total beside the people ("812 respondents (798 weighted)") and
**Weight** names the column. See
[[MaxDiff and Conjoint|Studio-MaxDiff-and-Conjoint]].

### Share of preference

`analyze.conjoint_shares` — a market simulator: what the part-worths predict a
market of specific products would do.

**In:** `data` (SurveyData) → **Out:** `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Conjoint question** | text | required | — | The conjoint question's id or name. |
| **Products** | JSON | required | — | Name → one level code per attribute, e.g. {"Ours": {"brand": 1, "price": 15}}. A half-specified product has no utility. |
| **Include "none of these"** | checkbox | off | — | Only when the question offered it. Leaving it out rescales everyone who would have walked away into buyers. |

A half-specified product has no utility, so give every attribute a level.
Leaving "none of these" out when the question offered it rescales the people
who would have walked away into buyers.

The table has one row per product (its utility and share) and a footer; the
`stat` output carries the same footer: **Question**, **Base** ("812
respondents"), **Method** ("logit rule on aggregate conditional-logit
part-worths") and **Note** — "shares of the products listed, not market
shares", or with **Include "none of these"** "shares of the products listed
and of choosing none, not market shares". After **Apply weight** the shares
come from part-worths fitted on the weighted choices, as in **Conjoint**; the
**Base** adds the weighted total ("812 respondents (798 weighted)") and
**Weight** names the column.

### Correlation

`analyze.correlation` — "Pearson, Spearman or Kendall correlation between two
variables, with its p-value and N — Pearson with a 95 % CI, and weighted when
a weight is applied."

**In:** `data` (SurveyData) → **Out:** `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **X** | variable | required | ordinal / interval / ratio variables | First variable. |
| **Y** | variable | required | ordinal / interval / ratio variables | Second variable. |
| **Method** | choice | `spearman` | `pearson`, `spearman`, `kendall` | Spearman and Kendall (tau-b) correlate ranks and suit rating scales; Pearson measures a straight-line relationship and gives a 95 % CI. Pearson is weighted when a weight is applied, the rank methods are not and say so. Pearson and Kendall leave the codebook's missing codes (a 9 = Refused) out and say how many. Spearman, the default, counts them as answers — as this node always has, so flows made before keep their numbers — and says so in missing_codes_counted; run Missing values first to leave them out. |

The list names each code under it: `pearson` ("Pearson r"), `spearman`
("Spearman rho"), `kendall` ("Kendall tau-b"). What each gives:

| Method | Statistics |
|---|---|
| `spearman` | `rho`, `p_value`, `n`; `missing_codes_counted` when a missing code was counted as an answer |
| `pearson` | `method` ("Pearson"), `r`, `p_value`, `n`, the confidence interval `lower` – `upper` and `confidence` (0.95); `missing_codes` for the codes left out |
| `kendall` | `method` ("Kendall tau-b"), `tau`, `p_value`, `n`; `missing_codes` |

p is two-sided. Kendall's tau-b corrects for ties, which a rating scale is
full of. A flow saved before **Method** existed has no value there and runs
Spearman, exactly as before.

**On weighted data** Pearson's r is the weighted coefficient; its p and
interval are computed on Kish's effective base (`n_effective`), so a weight
never makes a correlation look more certain than the respondents behind it,
and `weight` names the column. Equal weights give the unweighted result.
Spearman and Kendall run on the respondents as they are and add `weight` =
"unweighted (the weight 'weight' is not applied)".

### Correlation matrix

`analyze.correlation_matrix` — "Pearson, Spearman or Kendall correlations
between every pair of several variables — coefficients with significance
marks, or one row per pair with p and N."

**In:** `data` (SurveyData) → **Out:** `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Variables** | variables (several) | required | ordinal / interval / ratio variables | The variables to correlate, every pair of them. |
| **Method** | choice | `spearman` | `pearson`, `spearman`, `kendall` | Spearman and Kendall (tau-b) correlate ranks and suit rating scales; Pearson measures straight-line relationships and is weighted when a weight is applied. |
| **Missing answers** | choice | `pairwise` | `pairwise`, `listwise` | Pairwise uses, for each pair, everyone who answered both, so N can differ between pairs; listwise keeps only the respondents who answered every variable. |
| **p adjustment** | choice | `none` | `none`, `holm`, `bonferroni`, `fdr_bh` | Allows for the number of pairs tested — Holm and Bonferroni hold the chance of any false finding at 5 %, fdr_bh (Benjamini-Hochberg) the share of false findings among the significant ones. The marks then follow the adjusted p. |
| **Layout** | choice | `matrix` | `matrix`, `pairs` | Matrix prints the lower triangle with \* p < .05, \*\* p < .01, \*\*\* p < .001; pairs gives one row per pair with the coefficient, p and N. |

`matrix` — the lower triangle, variables by their labels, `—` on the
diagonal:

```
| Variable             | Age    | Trust: Acme | Trust: Globex | Overall satisfaction |
| Age                  | —      |             |               |                      |
| Trust: Acme          | -0.031 | —           |               |                      |
| Trust: Globex        | -0.010 | 0.072       | —             |                      |
| Overall satisfaction | -0.042 | 0.045       | -0.067        | —                    |
```

`pairs` — one row per pair: **Variable 1**, **Variable 2**, the coefficient
(**r**, **rho** or **tau**), **p**, the adjusted p when there is one (**p
(Holm)**) and **N**. Read this one when N differs from pair to pair.

Under the table, and in the `stat` output: **Method** ("Spearman rank
correlation", "Pearson correlation", "Kendall rank correlation (tau-b)"),
**Missing** ("pairwise: each pair uses everyone who answered both", or
"listwise: only respondents who answered every variable"), **N** (a range
such as `112–194` when pairs differ), **p adjustment** ("none", "Holm,
over 3 pairs", or "Holm, over the 2 pairs computed (of 3)" when a pair could not
be computed — it reads `n/a` in the matrix), **Marks** (matrix layout; "(adjusted p)" when adjusted) and
**Missing codes left out** — the matrix leaves the codebook's missing codes
out with every method. On weighted data a Pearson matrix is weighted and adds
**Weight** and **Base** ("weighted coefficients; p on Kish's effective
base"); Spearman and Kendall say "Weight = unweighted (the weight 'weight' is
not applied)".

To draw the matrix, connect its `table` to a **Result chart** (Kind
`heatmap`): the lower triangle with the table's significance marks.

### Perceptual map

`analyze.correspondence` — "Correspondence analysis of a crosstab, or of the
attributes checked for each brand — the dimensions and their share of the
inertia, and where each row and column lies on the map, with contributions and
quality." A table of counts says cell by cell which brands are seen as modern
and which as good value; the map shows it at a glance: a brand lies toward
the attributes it gets more of than the average brand does. Connect any of its
tables to a **Result chart** to draw the map.

**In:** `data` (SurveyData) → **Out:** `table` (Table), `rows` (Table), `columns` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Table** | choice | `crosstab` | `crosstab`, `attributes` | crosstab counts the respondents in each pair of answers of Rows and Columns (a multiple-choice variable counts each answer chosen). attributes counts, for each answer of Rows — the brand, in data with a row per respondent and brand — the respondents who checked each of the Attributes. |
| **Rows** | variable | required | nominal / ordinal variables | The points of one kind on the map — brands, regions, segments. A respondent whose answer is blank or one of the codebook's missing codes is left out. |
| **Columns** | variable | — | nominal / ordinal variables | Crosstab: the points of the other kind — the answers crossed with Rows. Shown only with **Table** `crosstab`. |
| **Attributes** | variables (several) | — | — | Attributes: two or more 0/1 variables, one per attribute ("is modern", "good value"), such as the ones Explode multiple choice makes; a blank or a missing code counts as unchecked. Shown only with **Table** `attributes`. |
| **Counts as yes (attributes)** | answer code | — | — | The code, or a list of codes, that counts as checking an attribute. Empty works for 0/1 variables. Shown only with **Table** `attributes`. |
| **Dimensions in the tables** | whole number | `2` | 1–10 | How many dimensions the rows and columns tables give coordinates, contributions and cos² for; the map shows the first two, and the inertia table lists them all. |

The **Table** list has `crosstab` ("Rows by Columns") and `attributes`
("Attributes checked for each answer of Rows"); the node's card reads `region ×
satisfaction`, or `brand × modern, good_value, friendly` for attributes.

- **Two layouts.** `crosstab` crosses two questions: **Rows** `region`,
  **Columns** `brand_used`. `attributes` needs data with one row per
  respondent and brand, the brand in a column of its own (**Rows**) and one 0/1
  column per attribute. No node reshapes a brand grid into that layout: bring
  such a file in with a **Data file** node. **Rows** can also be a question
  about the respondent — a region, a segment — with the 0/1 columns of an
  exploded multiple-choice question as **Attributes**: the map then shows which
  regions check which options.
- **Rules:** "A crosstab map crosses Rows with Columns — choose the Columns
  variable.", "An attribute map counts the Attributes checked for each answer
  of Rows — choose two or more attribute variables." and "A perceptual map of
  attributes needs two or more attribute variables; 1 was given." (errors);
  "Counts as yes is read only with Table = attributes — set it, or clear
  Counts as yes." (a warning).

**The outputs.** The preview shows the three tables one under another, the
`rows` and `columns` tables each under its output's name.

| Output | What it holds |
|---|---|
| `table` | one row per dimension — **Dimension**, **Singular value**, **Principal inertia**, **% of inertia**, **Cumulative %** — with the statistics under it |
| `rows` | one row per answer of **Rows**, by its label — **Mass**, **Quality**, **Inertia %**, then per dimension **Dim 1**, **Contribution 1 %**, **cos² 1**, **Dim 2**, …; under it **Coordinates** "principal (symmetric map)", **Contribution** "% of the dimension's inertia", **Quality** "cos² of the 2 dimensions shown" |
| `columns` | the same for the answers of **Columns**, or for the **Attributes** by their labels |
| `stat` | **Map** ("Region × Overall satisfaction", or "Region × Attributes"), **Rows**, **Columns**, **N**, **Counts as yes** (attributes: "1 = Yes"), **Total inertia**, **Dimensions**, **Dimension 1 %**, **Dimension 2 %**, …, **Map %** (the share of the inertia the map shows); for a crosstab of two single-answer questions **Chi-square**, **df** and **p**; **Note**, **Not in the map**, **Excluded**, **Excluded because** ("no answer (or a missing code) to Rows or Columns") and **Missing codes** when there is something to say |

- **Reading the map.** Rows and columns are both in principal coordinates —
  the symmetric map R's `ca` and FactoMineR draw by default. Each axis is a
  dimension, with its share of the table's inertia (its departure from
  independence). A point's **Quality** says how well the dimensions shown
  represent it; its **Contribution** how much it shapes a dimension.
- **Signs are arbitrary** in any correspondence analysis: here each dimension
  points toward the row that contributes most to it, so a map can be the
  mirror image of another package's.
- **The chi-square test** of independence is given for a crosstab of two
  single-answer questions. Where a respondent can be counted in several cells
  — a multiple-choice variable, an attribute map — there is no test.
- An answer nobody gave is named, not drawn: "Not in the map = South (nobody
  counted in them)". A table with two rows or two columns has one dimension:
  "Note = the table has one dimension (two rows or two columns), so the map is
  a line".
- **Refusals**, with the reason: a table smaller than two rows by two columns
  ("Region × Gender: A perceptual map needs at least two rows and two columns
  with counts; this table has 3 × 1."), rows that all have the same profile
  ("… so there is nothing to map: the table is independent."), attributes
  that are not 0/1
  without **Counts as yes** ("The attributes hold 1, 2, 3, 4, 5, 9: name the
  code (or codes) that counts as checking an attribute in Counts as yes — `yes`
  outside a flow."), and a multiple-choice attribute (run **Explode multiple
  choice** first, or use the crosstab layout with it as **Columns**).
- **On weighted data** every cell is a sum of weights, so the map is weighted,
  and the statistics add **Weight** and **Weighted N**. The chi-square test
  counts respondents and says so: "Chi-square counts = respondents
  (unweighted), as a test of a table must".

### Crosstab

`analyze.crosstab` — "Cross-tabulation with a chi-square test and Cramér's V,
or Fisher's exact test for small tables."

**In:** `data` (SurveyData) → **Out:** `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Rows** | variable | required | nominal / ordinal variables | Row variable. |
| **Columns** | variable | required | nominal / ordinal variables | Column variable. |
| **Percentages** | choice | `col` | `none`, `row`, `col`, `total` | Which percentages to show: `none`, `row`, `col` (column %) or `total`. |
| **Significance test** | checkbox | on | — | Add the test chosen under **Test**. (It was labeled **Chi-square test** before Fisher's test was added; stored flows keep their setting.) |
| **Test** | choice | `chi2` | `chi2`, `fisher` | Chi-square with Cramér's V, on Kish's effective base when weighted. Fisher's exact test suits small counts; for 2 × 2 it gives the odds ratio and its 95 % CI, larger tables use the Fisher-Freeman-Halton test (exact, or from 20,000 random tables with a fixed seed when there are too many to sum). Fisher counts respondents, unweighted, and leaves the codebook's missing codes out of the table and the test; chi-square keeps them as rows and columns of their own, as it always has, and says so. |

For a multiple-answer row variable the table counts respondents, not answers,
and does not offer a chi-square test (its independence assumption does not
hold).

**Chi-square** (`chi2`, the default) gives χ², df, p, Cramér's V and N. A
declared missing code (a "Refused") stays a row or column of its own, as it
always has, and the statistics then say "Missing codes counted as answers =
Trust: Acme: 12 (9 = Refused); run Missing values first to leave them out".

**Fisher's exact test** (`fisher`) is the test to use when cells are small —
the chi-square's approximation is poor when expected counts fall below 5. The
codebook's missing codes are left out of the table and the test
("Missing codes left out = …").

- A **2 × 2** table gets **Test** "Fisher's exact test", the two-sided **p**,
  the **Odds ratio** (conditional maximum likelihood) with its exact **OR 95%
  CI**, and **Odds ratio of**, which says which way round it is read:
  "Under 50 (vs 50 or over) for Male over Female". **Estimate** reads
  "conditional maximum likelihood with its exact interval, as R's fisher.test
  defines them (R stops its root search sooner, so its printed values can
  differ slightly on sparse tables)" — the p-values agree with R's.
- A **larger** table gets **Test** "Fisher-Freeman-Halton exact test" and
  **p**, summed exactly over every table with the observed margins when there
  are at most 200,000 of them (**p method** "exact, over every table with
  these margins"), and otherwise estimated from 20,000 random tables drawn
  from a fixed seed, so a rerun gives the same p: **p method** "Monte Carlo,
  20,000 random tables with these margins from a fixed seed (± 0.0021); too
  many tables to sum exactly", the ± being the Monte Carlo error.
- A table the test cannot use reads "Test = Fisher's exact test: not run —
  the table has fewer than two rows or columns with answers in them".
- **Rule:** "Fisher's exact test is not run while Significance test is off."
  (a warning).

After **Apply weight**, the cells and totals are sums of weights (to one
decimal) and the percentages are taken from them the same way. The
chi-square test is run on the counts scaled down to the effective (Kish)
sample size, as the **Banner table** does: weights make a sample behave like a
smaller one. With **Significance test** on, the statistics keep **N** (the
respondents counted) and add **Weighted N**, **Weight** and **Base**: for
chi-square also **Effective N**, with **Base** "effective (Kish) for the test;
weighted counts shown"; for Fisher's test, which needs whole counts, **Base**
"the test counts respondents (an exact test needs whole counts); weighted
counts shown". With the test off they are **Weighted N** and **Weight**. For
a multiple-answer row variable the percentages are of each column's weighted
base, and an **Unweighted base** row follows the "Base (respondents
answering)" row.

### Data check

`analyze.data_check` — "The data against its codebook before any analysis —
values outside the valid range, codes without a label, duplicate IDs, columns
nobody declared — with how many rows each and examples."

**In:** `data` (SurveyData) → **Out:** `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Variables** | variables (several) | empty | — | Check only these. Empty checks every column and every codebook variable. |

One row per problem, errors first, with the columns **Severity**
(`error` or `warning`), **Variable**, **Problem**, **Rows** (how many rows
have it), **Examples** (up to five offending values with their counts —
`17 (1), 999 (1)` — and "… (3 more)" beyond five) and **Code**:

| Problem | Code |
|---|---|
| outside the valid range 18–75 | `OUT_OF_RANGE` |
| codes the codebook has no label for | `INVALID_LABEL_VALUE` |
| the same ID on more than one row | `DUPLICATE_ID` |
| weight values that are not numbers | `INVALID_WEIGHT` |
| missing codes without a label | `MISSING_VALUE_WITHOUT_LABEL` |
| the weight column is not in the data | `MISSING_WEIGHT_COLUMN` |
| in the codebook but not in the data | `MISSING_COLUMN` |
| in the data but not in the codebook | `EXTRA_COLUMN` |

- A declared missing code is not "outside the valid range": a 999 "Refused"
  is not flagged for an age of 18–75.
- Columns the codebook does not know, and codebook variables the data lacks
  (common after a **Select columns**), are gathered into one row each.
- The weight column and the response metadata beside the answers —
  `respondent_id`, `duration_s`, `partial`, `started_at`, the `url_*`
  parameters and the like — are expected there, so they are not problems;
  the statistics name them under **Not in the codebook, as expected** (for
  example "weight (the weight)").
- The statistics: **Checked** ("9 variables, 240 rows"), **Errors**,
  **Warnings**, and with nothing wrong **Result** "no problems found" (the
  table is then empty).
- It counts rows, so on weighted data it adds "Weight: unweighted (the weight
  'weight' is not applied)".

Put it right after the source and wire its table into a **Report section**
or a **Live tile**: it is the check a methods section's "data were screened
for out-of-range values" rests on.

### Describe

`analyze.describe` — a summary table of the data: one row per codebook
variable with its label, scale, N, missing and unique values — or the codebook
itself.

**In:** `data` (SurveyData) → **Out:** `table` (Table)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Show** | choice | `variables` | `variables`, `codebook` | `variables`: one row per variable with N, missing and unique values; `codebook`: the codebook table. |

The rows include the variables earlier nodes made. The counts are of rows
(records), which is what a completeness check is about; after **Apply
weight** a `weighted_n_valid` column stands beside them — the sum of the
weights of the rows that have a value, the weighted base a table of that
variable would report.

### Descriptive statistics

`analyze.descriptives` — "N, missing, mean, SD, median, minimum and maximum of
several numeric variables — by group if you like, with quartiles, skewness
and kurtosis on request."

**In:** `data` (SurveyData) → **Out:** `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Variables** | variables (several) | required | ordinal / interval / ratio variables | The codebook's missing codes (a 99 "Don't know") are not answers and count as missing. |
| **By group** | variable | — | nominal / ordinal variables | Optional. One row per variable and group; a blank or a missing code of the group variable is no group. A multiple-choice question gives one group per option, and they overlap. |
| **Quartiles, skewness and kurtosis** | checkbox | off | — | Only with **Layout** `long`. |
| **Layout** | choice | `long` | `long`, `means` | With **By group**. `long`: a row per variable and group with N, mean, SD, median, minimum and maximum. `means`: a row per variable and a column per group with its mean, a compact profile of the groups; their sizes are under the table. |

One row per variable — or per variable and group — with **Variable**,
**Label**, the group, **N**, **Missing**, **Mean**, **SD**, **Min**,
**Median** and **Max**; the checkbox adds **Q1** and **Q3** (linear
interpolation, R's default) and **Skewness** and **Kurtosis** (the
bias-corrected G1 and excess G2 that SPSS and Excel report).

- **A missing code is not an answer.** A declared missing code, and a value
  that is not a number, count in **Missing**; the statistics name them
  (`Missing codes` = `trust_acme: 9`, `Not numbers`). This is the difference
  from **Describe**, which counts what is in the cells.
- **Undefined is blank.** The SD of one answer, skewness below three answers
  and kurtosis below four are empty cells, never `nan`.
- **By group:** a respondent whose group is blank or a missing code is in no
  group (**Not in a group**). A multiple-choice **By group** gives one group
  per option, of everyone who chose it; a respondent who chose two is in both,
  and **Groups** says the groups overlap.
- **On weighted data** the mean, SD, median and quartiles are weighted — the
  same formulas as **Group means**, so the two never disagree — beside a
  **Weighted N** column, while **N** and **Missing** stay counts of
  respondents and **Min** and **Max** those of every answer. A respondent
  weighted 0 (or with no weight) is set aside from the weighted statistics,
  the SD's n included, so one weighted answer has no SD. The statistics add
  **Weight**, **Weighted N**, **Effective N** (Kish), the **Design effect** and
  the **Note** "mean, SD and median are weighted; N and Missing count
  respondents" (with **Quartiles, skewness and kurtosis** checked: "mean, SD,
  median and quartiles are weighted; N and Missing count respondents; skewness
  and kurtosis are unweighted") — with "; rows weighted 0 are left out of the
  weighted statistics" after "count respondents" when any row weighs 0.

To chart the means, connect its `table` to a **Result chart**: `means` (each
mean with its 95 % interval) or `means_sd` (± 1 SD), a row per variable with
its base; with **By group**, a color per group, the legend giving each
group's base (`Capital (n = 170–197)` when it differs between variables).

### Key drivers

`analyze.drivers` — "Which of several predictors matter most for an outcome —
each one's share of R² by Johnson's relative weights or the Shapley value
(LMG), beside the correlations and standardized betas." A regression's
coefficients answer another question — what changes when one rating moves and
the others stay put — and when the ratings correlate, as ratings of one brand
do, a coefficient can shrink or even flip sign because a neighbor took its
share. Key drivers splits the model's R² between the drivers instead, so the
shares add up to R² (100 %).

**In:** `data` (SurveyData) → **Out:** `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Outcome** | variable | required | — | What the drivers explain — a rating, a score, a likelihood to recommend. A respondent missing it or any driver is left out; the codebook's missing codes count as missing. |
| **Drivers** | variables (several) | required | — | Two or more numeric predictors — ratings of attributes, scores, 0/1 variables. A nominal variable with more than two answers has no amounts to weigh; make a 0/1 variable per answer with Explode multiple choice or Derive. |
| **Importance** | choice | `relative_weights` | `relative_weights`, `shapley` | relative_weights is Johnson's method, which splits R² through the orthogonal variables closest to the drivers (as R's rwa). shapley averages each driver's gain in R² over every order in which the drivers could enter the model (LMG, as R's relaimpo) — exact, for at most 15 drivers. Both add up to R², shown as 100 %; they agree closely. |

The **Importance** list has `relative_weights` ("Johnson's relative
weights") and `shapley` ("Shapley value (LMG)"); the card reads `satisfaction ~
price, service, range, staff`.

**The table** has one row per driver, the largest share first — **Rank**,
**Driver** (by its label), **r** (its correlation with the outcome), **Beta**
(the standardized coefficient), **Beta p** (its t-test in the regression),
**VIF**, **Relative weight** (or **Shapley value**) and **% of R²**:

```
| Rank | Driver        | r      | Beta   | Beta p  | VIF  | Relative weight | % of R² |
| 1    | Trust: Acme   | -0.177 | -0.175 | 0.02088 | 1.01 | 0.0308          | 88.1    |
| 2    | Trust: Globex | -0.068 | -0.06  | 0.4218  | 1.0  | 0.0041          | 11.7    |
| 3    | Age           | -0.011 | 0.006  | 0.9381  | 1.01 | 0.0001          | 0.2     |
```

Under it, and in `stat`: **Method** ("Johnson's relative weights", or
"Shapley value decomposition of R² (LMG)"), **Outcome**, **Drivers**, **N**,
**R²**, **Adjusted R²**, the model's **F**, **df** ("3, 173") and **p**,
**Excluded**, **Excluded because** ("a missing value in the outcome or any
predictor (listwise)") and **Missing codes** ("138 answers with a missing code
(9 = Refused) left out").

- **Warnings** (in **Warning**): a VIF of 10 or more ("strong collinearity —
  VIF …: their betas are unstable, and the importance splits the variance they
  share between them"), and a suppressor, a driver whose beta has the other
  sign than its correlation ("… the beta has the opposite sign of the
  correlation (a suppressor), so the share says little about it on its own").
  Drivers that explain the outcome exactly (R² of 1) get no test: "Note = the
  drivers explain the outcome exactly, so there is no residual to test
  against".
- **Rules** (errors of the check, before the run): "Key drivers splits R²
  between two or more predictors; 1 was given. For one predictor, its
  correlation with the outcome is the whole story." and, for `shapley`, "The
  Shapley value decomposition averages over every order of the predictors:
  with 16 that is 65,536 subset regressions, and it is computed for at most
  15 predictors. Use Johnson's relative weights, which come close to it, or
  fewer predictors."
- **Refusals** — the run stops on this node with the reason: a nominal driver
  with more than two answers ("Gender is nominal with 3 answers (1 = Male, 2 =
  Female, 3 = Other): its codes are not amounts to weigh. Make a 0/1 variable
  per answer (Explode multiple choice, or Derive) and use those."), a driver
  or outcome that is the same for everyone, drivers that are a combination of
  each other ("… are collinear: one is a combination of the others, so their
  shares cannot be told apart. Leave one of them out."), and fewer respondents
  than the regression needs.
- **On weighted data** the correlations, betas, R² and shares come from the
  weighted correlation matrix, and the tests are taken on Kish's effective N:
  the statistics add **Weight**, **Effective N** and **Tests on** ("Kish's
  effective N"), and **df** has decimals ("3, 167.33").

Connect its `table` to a **Result chart** for the bars: each driver's share
of R², largest first, a driver with a negative beta in a second color
(legend "positive beta", "negative beta"), titled "Key drivers of Overall
satisfaction" with the method, R² and N on the line under it.

### Factor analysis

`analyze.factor` — "Exploratory factor analysis of a set of items —
loadings, communalities, variance explained, KMO and Bartlett's test, factor
correlations, and factor scores if wanted." It is the check before a set of
items is averaged into a scale: which items move together, how strongly each
belongs to each factor, and whether the items share enough to be factored at
all.

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData), `loadings` (Table), `variance` (Table), `correlations` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Items** | variables (several) | required | ordinal / interval / ratio variables | Three or more, analyzed as standardized scores (their correlations). A respondent missing any item is left out; the codebook's missing codes count as missing. |
| **Factors** | whole number | — | at least 1 | Empty chooses the number by the rule below. |
| **Number of factors by** | choice | `kaiser` | `kaiser`, `parallel` | When Factors is empty. kaiser keeps the eigenvalues above 1; parallel keeps the factors whose eigenvalue beats the 95th percentile of 100 random data sets of the same size, drawn from Seed. |
| **Extraction** | choice | `minres` | `minres`, `principal`, `ml` | minres (minimum residual) as psych and factor_analyzer; principal is iterated principal axis factoring; ml is maximum likelihood, as R's factanal, and adds a test of fit; it is started from 14 fixed points and keeps the best, and warns when they disagree (often a sign of too many factors). |
| **Rotation** | choice | `varimax` | `varimax`, `promax`, `oblimin`, `none` | varimax keeps the factors uncorrelated. promax and oblimin let them correlate and report how much (the correlations output); their loadings are the pattern matrix. |
| **Sort items by factor** | checkbox | off | — | — |
| **Hide loadings below** | number | `0` | 0–1 | Blank out the loadings smaller than this in the table (0 shows every loading), so the structure reads at a glance. |
| **Add factor scores** | checkbox | off | — | Regression-method scores, one variable per factor, missing for the respondents left out. |
| **Score variable prefix** | text | `factor_` | — | The scores are named <prefix>1, <prefix>2, … — with Add factor scores on. The prefix itself is not a variable. Shown only with **Add factor scores** checked. |
| **Seed (parallel analysis)** | whole number | `42` | — | Shown only with **Number of factors by** `parallel`. |

The lists name each code under it: `minres` ("minimum residual"),
`principal` ("principal axis"), `ml` ("maximum likelihood"); `varimax`
("orthogonal"), `promax` ("oblique"), `oblimin` ("oblique, quartimin");
`kaiser` ("eigenvalues above 1"), `parallel` ("parallel analysis").

**The outputs.** The preview shows the three tables one under another, each
under its output's name.

| Output | What it holds |
|---|---|
| `loadings` | one row per item — **Variable**, **Label**, **Factor 1**, **Factor 2**, …, **Communality**, **Uniqueness** and **MSA** (the item's measure of sampling adequacy) |
| `variance` | one row per possible factor — **Eigenvalue**, **% of variance**, **Cumulative %**, then for the factors kept **Extracted SS**, **Extracted %**, **Extracted cumulative %** and, after a rotation, **Rotated SS**; with parallel analysis also **Random 95th percentile** |
| `correlations` | the correlations between the factors — after `promax` or `oblimin`; an orthogonal solution notes "an orthogonal solution: the factors are uncorrelated by construction" |
| `stat` | **Extraction**, **Rotation** ("promax (power 4), Kaiser-normalized"), **Factors**, **Factors chosen by** ("fixed", "Kaiser criterion (eigenvalues above 1)", "parallel analysis (95th percentile of 100 random data sets, seed 42)"), **Items**, **N**, **Variance explained %**, **KMO**, **Bartlett chi-square**, **Bartlett df**, **Bartlett p**, **RMSR**; with `ml` the test of fit, **Fit chi-square**, **Fit df** and **Fit p**; **Warning** when there is something to warn about; **Scores** with **Add factor scores**; **Excluded** and **Excluded because**; **Missing codes** |
| `data` | the data passed on — with **Add factor scores**, plus `factor_1`, `factor_2`, … |

- Each factor is signed so its loadings sum positive, and the factors are
  ordered by the variance they carry. The numbers reproduce R's `psych::fa`
  and the `factor_analyzer` package (and `factanal` for maximum likelihood).
- **Refusals**, with the reason: fewer than three items ("A factor analysis
  needs at least three items; 2 were given."), no more respondents than
  items, an item everyone answered the same, an item that copies or totals
  others, as many factors as items, and with `ml` more factors than maximum
  likelihood can fit ("Maximum likelihood cannot fit 3 factors to 5 items: …
  Use at most 2.").
- **Warnings** (in **Warning**): a KMO below 0.5, an item with (almost) no
  uniqueness left, a rule that suggests more factors than can be fitted (the
  most that fit is used), with `minres` or `principal` more factors than the
  items' correlations can identify, and with `ml`, starts that disagree — a
  reason to compare a solution with fewer factors.
- **Factor scores.** With **Add factor scores** checked the `data` output
  carries `factor_1`, `factor_2`, … (interval), blank for the respondents
  left out, and later nodes offer them ("factor 1 score · made by *node*") —
  a **Group means** of `factor_1` by region, a **Regression** on them. With
  **Factors** empty the pickers list every score the analysis could make (one
  fewer than the items), the ones after the first as "factor 2 score (empty
  unless the rule keeps it) · made by *node*". The run makes the scores of the
  factors it kept, and of the others the ones a node downstream reads, empty and
  labeled "Factor 2 score (not made: the Kaiser criterion kept 1 factor)";
  **Scores** names them ("factor_1 (regression method); factor_2 empty: the
  Kaiser criterion kept 1 factor"). A score nothing reads is not added, so the
  data, its exports and its tables carry only the scores made and the ones in
  use.
- It is unweighted: on weighted data each table says "Weight: unweighted (the
  weight 'weight' is not applied)". The scores of a later **Group means** are
  weighted as usual.

### Frequencies

`analyze.freq` — the distribution of one variable with value labels, %, and
cumulative %.

**In:** `data` (SurveyData) → **Out:** `table` (Table)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Variable** | variable | required | — | The variable to tabulate. |
| **Exclude missing** | checkbox | on | — | Leave blank answers out of the table. |
| **Sort** | choice | `value` | `value`, `freq`, `label` | `value` (by code), `freq` (largest count first) or `label` (alphabetical). |

**Cumulative %** is the running share of the counts (after **Apply weight**,
of the weights), rounded once, so the last answer always reads 100.0, even
when the **%** column, each row rounded on its own, adds up to 99.9 or 100.1.

For a multiple-answer question, each option's share is of the respondents who
answered, so the **%** column sums above 100 %; the base is a row of its own
and there is no cumulative column.

After **Apply weight**, **N** is the sum of the weights (shown to one
decimal) and the percentages are taken from the sums as they are, not from
the rounded N — so, over the same respondents, they agree with the **Bar
chart**'s and the **Likert chart**'s to the last digit. An **Unweighted N** column beside **N** gives
the respondents actually counted — the number a reader judges a percentage
by — and the
statistics add **Weighted N** and **Weight**. For a multiple-answer question
the weighted counts are rounded to whole numbers, the base row carries the
unweighted base under **Unweighted N**, and the statistics read, for example,
"812 respondents (798 weighted)".

### MaxDiff

`analyze.maxdiff` — what a best–worst question found: one row per item, best
first, with the counting score, the conditional-logit utility and the share it
implies.

**In:** `data` (SurveyData) → **Out:** `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **MaxDiff question** | text | required | — | The question's id or name. Its design is read from the questionnaire, so nothing has to be re-entered here. |
| **Estimate** | choice | `both` | `both`, `counts`, `utilities` | Counting is best minus worst over shown and anyone can recount it. Utilities are a conditional logit on the choices the design actually showed. |

The design is read from the questionnaire, so the only thing to name is the
question. Utilities come from an **aggregate** conditional logit; individual
ones need hierarchical Bayes, which **Choice data for HB** exports for. Each
respondent's own counting scores, as variables a crosstab or a cluster can
use, come from **MaxDiff scores** (Prepare). The footer gives the
**Question**, the **Base** ("812 respondents"), **Tasks read**, the
**Method**, the **Reference** item and **Pseudo R²**.

After **Apply weight** every column is weighted: **Shown**, **Best** and
**Worst** are sums of weights (rounded to whole numbers), the **Score**
follows them, and the **Utility** and **Share %** are fitted on the weighted
choices. The footer adds **Weight** and gives the weighted total beside the
people: "812 respondents (798 weighted)". Before this was fixed the
**Utility** and **Share %** columns stayed unweighted; a weighted flow run
again gives different numbers there.

### Group means

`analyze.means` — "Mean, SD, median and N of a variable by group, with a
significance test — chosen for you, or by hand with post-hoc comparisons of
every pair of groups."

**In:** `data` (SurveyData) → **Out:** `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Variable** | variable | required | ordinal / interval / ratio variables | The variable whose mean is compared. |
| **By** | variable | required | nominal / ordinal variables | The grouping variable. |
| **Significance test** | checkbox | on | — | Add the significance test. |
| **Test** | choice | `auto` | `auto`, `student`, `welch`, `anova`, `welch_anova`, `mannwhitney`, `kruskal` | Auto chooses by scale and groups (t-test or ANOVA for interval data, Mann-Whitney or Kruskal-Wallis for ordinal). Student and Welch compare two groups (Welch does not assume equal variances), ANOVA and Welch's ANOVA two or more, Mann-Whitney and Kruskal-Wallis compare ranks. A test chosen here reports df and an effect size and leaves the codebook's missing codes out. Auto counts them as answers, as it always has, and says so (Missing codes counted as answers); run Missing values first to leave them out. |
| **Post-hoc** | choice | `none` | `none`, `tukey`, `games_howell`, `dunn` | Every pair of groups compared after the test — Tukey's HSD after ANOVA, Games-Howell after Welch's ANOVA, Dunn after Kruskal-Wallis. The pairs appear under the table. |
| **Dunn p adjustment** | choice | `holm` | `holm`, `bonferroni` | How Dunn's p-values allow for the number of pairs. Tukey and Games-Howell allow for it themselves. Shown only with **Post-hoc** `dunn` (and a **Test** other than `auto`). |

The **Test** list names each code under it: `student` ("Student's t"),
`welch` ("Welch's t"), `anova` ("one-way ANOVA"), `welch_anova` ("Welch's
ANOVA"), `mannwhitney` ("Mann-Whitney U"), `kruskal` ("Kruskal-Wallis H");
**Post-hoc** has `tukey` ("Tukey HSD"), `games_howell` ("Games-Howell"),
`dunn` ("Dunn's test").

**`auto`** (the default, and what every flow saved before **Test** existed
runs) picks by the variable's scale and the number of groups: Student's
t-test or a one-way ANOVA for interval and ratio data, Mann-Whitney U or
Kruskal-Wallis H for ordinal data. Its footer is a single line such as
"Kruskal-Wallis H = 2.417; p = 0.2986; N = 120; Variable = Satisfaction".

**A test chosen by hand** is named in the footer with its statistic, df, p
and an effect size, and leaves the codebook's missing codes out of the table
and the test ("Missing codes left out = …"):

| Test | Footer |
|---|---|
| `student`, `welch` | **Test** ("Welch's t-test (unequal variances)"), **t**, **df**, **p**, **Mean difference**, **Difference** ("Male − Female"), **95% CI**, **Cohen's d** |
| `anova`, `welch_anova` | **Test** ("One-way ANOVA", "Welch's ANOVA"), **F**, **df** ("2, 237"; Welch's has decimal df), **p**, **η²** |
| `mannwhitney` | **Test**, **U**, **p**, **rank-biserial r** |
| `kruskal` | **Test** ("Kruskal-Wallis H"), **H**, **df**, **p**, **ε²** |

A two-group test asked of more groups is not run and says what to choose
instead: "Test = not run: Welch's t-test (unequal variances) compares two
groups and Region has 3 — choose anova or welch_anova".

**Post-hoc comparisons.** With **Post-hoc** set, the footer adds a summary
("Post-hoc = Tukey HSD: 0 of 3 pairs differ at p < 0.05") and a second table
prints under the means table — in the preview and in the report —
headed **Post-hoc: Tukey HSD**, one row per pair of groups by their value
labels:

| Post-hoc | Columns |
|---|---|
| `tukey` (Tukey-Kramer for unequal groups) | **Pair**, **Difference**, **95% CI low**, **95% CI high**, **q**, **p** |
| `games_howell` | the same, with **df** before **p** |
| `dunn` | **Pair**, **Mean rank difference**, **z**, **p (unadjusted)**, **p (Holm)** (or **p (Bonferroni)**) |

Tukey and Games-Howell give the difference of the means with its
simultaneous interval, the studentized range q and a p that already allows for
the number of pairs; Dunn gives the difference of the mean ranks, z, and p
before and after the adjustment. A p below 0.0001 keeps four significant
digits (`3.363e-07`); a Tukey or Games-Howell p below 1e-07 reads `< 1e-07`,
because the studentized range is not computed finely enough to give a
smaller one — past that point it came out as the same tiny number for every
strong pair. Under the pairs: **Method**, **Groups**,
**Difference** ("mean of the first group minus the second", or for Dunn "mean
rank of the first group minus the second") and, for Tukey and Games-Howell,
**p** "adjusted for the number of pairs by the method itself" — with "; < 1e-07
where it is smaller than SciPy computes the studentized range to" when a pair
reads `< 1e-07`.

**Rules** (errors, then warnings):

- "Tukey's HSD follows a one-way ANOVA — set Test to anova, or Post-hoc to
  none."
- "Games-Howell follows Welch's ANOVA — set Test to welch_anova, or Post-hoc
  to none."
- "Dunn's test follows Kruskal-Wallis — set Test to kruskal, or Post-hoc to
  none."
- "Test is not run while Significance test is off." (warning)
- "Post-hoc is not run while Significance test is off." (warning)

After **Apply weight**, each group's mean, SD and median are weighted (the SD
is scaled so that equal weights give exactly the ordinary sample SD, counting
only the answers that carry weight — a respondent weighted 0 is set aside, and
a group with one weighted answer has no SD, a blank cell; the median is the
value at which the cumulative weight reaches half). **N** stays
the number of respondents, and the significance test and the post-hoc pairs
stay unweighted; the statistics add **Weight** and the note "means, SD and
medians are weighted; N and the test are not", and the post-hoc table says
"Weight: unweighted (the weight 'weight' is not applied)".

Connect its `table` to a **Result chart** to draw each group's mean with its
95 % interval (`means`) or ± 1 SD (`means_sd`), each group with its base
(`North (n = 97)`). After a post-hoc test each mean carries letters: "Means
sharing a letter do not differ (Tukey HSD, p < .05)."

### Net Promoter Score

`analyze.nps` — detractors (0–6), passives (7–8) and promoters (9–10) of a
0–10 item, and the score with its standard error and 95 % confidence interval.
Uses the applied weight.

**In:** `data` (SurveyData) → **Out:** `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **0–10 item** | variable | required | ordinal / interval / ratio variables | A 0–10 likelihood-to-recommend item. |

After **Apply weight** the group shares and the score are weighted and the
standard error uses Kish's effective base; the **N** column still counts
respondents, and the statistics add **Weight**. A **Result chart** of its
`table` draws the detractors, passives and promoters as one stacked bar,
with the score and its interval (Kind `stacked`).

### Paired tests

`analyze.paired` — "The same respondents answering two or more questions —
Wilcoxon signed-rank or McNemar for two, Friedman or Cochran's Q for three or
more, with pairwise comparisons." Use it where **Compare groups** would be
wrong because the answers are not from different people: one scale asked
about two brands, a rating before and after a message, three concepts each
rated by everyone, three brands each respondent has heard of or not.

**In:** `data` (SurveyData) → **Out:** `table` (Table), `pairs` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Variables** | variables (several) | required | — | Two for Wilcoxon or McNemar, three or more for Friedman or Cochran's Q — asked of the same respondents, on the same answer scale. Differences are the first minus the second (for Friedman's pairs, A − B), as in the paired t-test. A respondent missing any of them is left out of all of them; the codebook's missing codes count as missing. |
| **Test** | choice | `auto` | `auto`, `wilcoxon`, `mcnemar`, `friedman`, `cochran` | Auto runs Wilcoxon signed-rank for two variables and Friedman for more. McNemar is for two yes/no questions, Cochran's Q for three or more. Wilcoxon and Friedman rank the answers, so they refuse a nominal variable. |
| **Counts as yes (McNemar, Cochran's Q)** | answer code | — | — | The answer code, or a list of codes, that counts as yes; every other answer counts as no. Empty works for 0/1 variables such as the ones Explode multiple choice makes. Shown only with **Test** `mcnemar` or `cochran`. |
| **Same answer twice (Wilcoxon)** | choice | `wilcox` | `wilcox`, `pratt` | wilcox drops the respondents who gave both the same answer before ranking, as R and SPSS do; pratt ranks them with the others and leaves them out of the sums. Shown with every **Test** but `mcnemar` and `cochran` (Friedman's pairwise tests use it too). |
| **p-value** | choice | `auto` | `auto`, `exact`, `approximate` | Auto is exact for small samples — Wilcoxon: up to 50 pairs with no ties or zeros, or up to 13 with them; McNemar (and the pairs of Cochran's Q): fewer than 25 respondents who answered the two differently — and the normal (Wilcoxon) or chi-square (McNemar) approximation otherwise. |
| **Pairwise comparisons (Friedman, Cochran's Q)** | choice | `holm` | `holm`, `bonferroni`, `none` | A Wilcoxon signed-rank test (after Friedman) or a McNemar test (after Cochran's Q) for every pair of variables, its p-value adjusted for the number of pairs by Holm's step-down method or by Bonferroni. The pairs output holds them. Shown with **Test** `friedman`, `cochran` or `auto` (auto is Friedman for three or more). |

The **Test** list names each code under it: `wilcoxon` ("Wilcoxon
signed-rank"), `mcnemar` ("McNemar, yes/no"), `friedman` ("Friedman, three
or more"), `cochran` ("Cochran's Q, three or more yes/no"). `auto` never
picks Cochran's Q: choose it by hand.

**Counts as yes (McNemar, Cochran's Q)** is a checklist of the first
variable's answers (`4 High`, `5 Full`) — check 4 and 5 for a top-two box.
McNemar or Cochran's Q on variables that are not 0/1 without it stops with
the answers to choose from: "McNemar needs to know which answer counts as
yes: the variables hold 1 = No trust, 2 = Low, 3 = Medium, 4 = High, 5 =
Full. Name that code (or a list of codes) in Counts as yes …" ("Cochran's Q
needs to know …" the same way). Rule (a warning): "Counts as yes is read only
by McNemar and Cochran's Q — set Test to mcnemar or cochran, or clear it." A
number of variables the test cannot compare is an error of the check, before
the run, in the run's own words: "McNemar compares exactly two variables; 3
were given. For three or more yes/no variables, use Cochran's Q.",
"Friedman's test compares three or more variables; 2 were given. For two, use
Wilcoxon signed-rank (or McNemar for yes/no).", "Cochran's Q compares three
or more yes/no variables; 2 were given. For two, use McNemar."

**Who is compared.** Each respondent is compared with themselves, so a
respondent who did not answer every variable is left out of all of them
(listwise), and the codebook's missing codes count as missing. The footer
says how many: **Excluded** (91), **Excluded because** ("a missing value in
either variable (listwise)") and **Missing codes** ("95 answers with a
missing code (9 = Refused) left out").

**Direction.** Every difference is the first variable minus the second — as
in the **t-test** with **Design** `paired`, so the two agree in sign. **W+**
sums the ranks of the respondents whose first answer is higher.

What each test gives (the `table` output, with its statistics under it and in
`stat`):

| Test | Table | Statistics |
|---|---|---|
| **Wilcoxon signed-rank** | per variable and for the difference: **N**, **Mean**, **SD**, **Median** | **Difference** ("Trust: Acme − Trust: Globex"), **N**, **Positive differences**, **Negative differences**, **Zero differences**, **W+**, **W-**, **Z**, **p**, **p-value** ("exact" or "normal approximation, tie-corrected"), **r** (Z/√n), **Rank-biserial r**, **Zeros** ("dropped before ranking (Wilcoxon)") |
| **McNemar** | the 2 × 2 table of yes and no on the two variables | **Counts as yes** ("4 = High, 5 = Full"), **N**, **% yes** of each, **Difference (points)**, **Yes only** for each variable (the two discordant counts), **Chi-square** and **df**, or the exact binomial p, **p**, **p-value** ("chi-square with continuity correction", or "exact binomial (12 discordant pairs)"), **Cohen's g**, **Odds ratio** |
| **Friedman** | per variable: **N**, **Mean**, **SD**, **Median**, **Mean rank** | **Variables**, **N**, **Chi-square**, **df**, **p**, **Kendall's W**, **Pairwise** ("Wilcoxon signed-rank, Holm-adjusted p") |
| **Cochran's Q** | per variable: **N**, **Yes**, **% yes** | **Test** ("Cochran's Q"), **Counts as yes** ("1 = Yes"), **Variables**, **N**, **Q**, **df**, **p**, **Pairwise** ("McNemar, Holm-adjusted p") |

The **`pairs`** output holds the pairwise comparisons, one row per pair:

- after **Friedman** — **Variable A**, **Variable B**, **N**, **Zero
  differences**, **W+**, **W-**, **Z**, **p**, **p adjusted**, **r**,
  **Rank-biserial r** — with "Difference = A − B" and "Adjustment = Holm (3
  comparisons)" under it;
- after **Cochran's Q** — a McNemar test of every pair: **Variable A**,
  **Variable B**, **N**, **% yes A**, **% yes B**, **Difference (points)**,
  **Yes only A**, **Yes only B**, **Chi-square** (or the exact p), **p**, **p
  adjusted** — with "Test = McNemar for each pair", "Difference = A − B",
  "Adjustment = Holm (3 comparisons)" and the **p-value** method under it.

The preview shows the pairs under the main table. With two variables the
output is empty and says "no pairwise comparisons: two variables are one
comparison; see the table's statistics".

Cochran's Q asks McNemar's question of three or more yes/no variables: is the
share saying yes the same for all of them? Q = (k − 1)(k ΣCⱼ² − N²) / (k N −
ΣRᵢ²) on k − 1 df, as R's `DescTools::CochranQTest` and statsmodels'
`cochrans_q` compute it.

- Everyone giving the same answer twice is a result, not an error: **p** is
  left out and a **Note** says why.
- A nominal variable is refused by Wilcoxon and Friedman, which rank answers;
  use McNemar or Cochran's Q for yes/no questions.
- None of these tests has a weighted form: on weighted data the statistics
  say "Weight: unweighted (the weight 'weight' is not applied)".
- Connect the `table` to a **Result chart** for a picture of it: after
  Wilcoxon or Friedman the means of the measurements with their 95 %
  intervals (`means`, or `means_sd`), noting "The same 393 respondents
  answered each; the test compares their ranks — Wilcoxon signed-rank, p =
  0.9402."; after McNemar or Cochran's Q the share saying yes to each, with
  Wilson's interval (`shares`).

### Principal components

`analyze.pca` — loadings and explained variance of a set of items. Three
outputs: `loadings` (Table), `variance` (Table: eigenvalues and explained
variance) and `stat`; the node's preview shows the loadings, with the
variance table under them (headed **variance**). For latent factors rather
than components — communalities, rotations that let factors correlate, KMO
and Bartlett's test, factor scores — use **Factor analysis**.

**In:** `data` (SurveyData) → **Out:** `loadings` (Table), `variance` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Items** | variables (several) | required | ordinal / interval / ratio variables | The items to analyze. |
| **Components** | whole number | — | at least 1 | Empty keeps the components with an eigenvalue above 1. |
| **Standardize items** | checkbox | on | — | Analyze the correlation rather than the covariance matrix. |

After **Apply weight** the components are those of the weighted covariance
(or, standardized, correlation) matrix, so the loadings, eigenvalues and
explained variance are weighted; equal weights give the unweighted result.
The `n` statistic stays the rows analyzed, and `weight` names the column.

A **Result chart** draws the scree plot from the `variance` output (with the
Kaiser line at an eigenvalue of 1) and a heatmap of the loadings from the
`loadings` output — the same two charts as for **Factor analysis**, whose
scree plot fills the factors kept and adds the parallel analysis's line when
it ran.

### Price sensitivity

`analyze.price` — "What respondents would pay — Van Westendorp's price
sensitivity meter from four price questions (the optimal and indifference
price points and the range of acceptable prices, with Newton-Miller-Smith
trial and revenue if asked), or a Gabor-Granger demand and revenue curve from
purchase intent at set prices."

**In:** `data` (SurveyData) → **Out:** `table` (Table), `curves` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Method** | choice | `van_westendorp` | `van_westendorp`, `gabor_granger` | van_westendorp reads four prices each respondent named and finds where their cumulative curves cross. gabor_granger reads a yes or no to buying at each of a set of prices and finds the demand and the revenue-maximizing price among them. |
| **Too cheap** | variable | — | interval / ratio variables | Van Westendorp: "At what price would it be so cheap that you would doubt its quality?" A respondent missing any of the four prices, or whose prices are not in the order too cheap ≤ cheap ≤ expensive ≤ too expensive, is left out and counted. |
| **Cheap (a bargain)** | variable | — | interval / ratio variables | "At what price would it be a bargain — a great buy for the money?" |
| **Expensive (getting expensive)** | variable | — | interval / ratio variables | "At what price would it start to seem expensive, though still worth considering?" |
| **Too expensive** | variable | — | interval / ratio variables | "At what price would it be so expensive that you would not consider buying it?" |
| **Likelihood at the cheap price (NMS)** | variable | — | — | Optional, for the Newton-Miller-Smith extension: how likely the respondent would be to buy at the price they called cheap, on a scale Calibration turns into a probability. |
| **Likelihood at the expensive price (NMS)** | variable | — | — | How likely the respondent would be to buy at the price they called expensive. |
| **Likelihood as probability (NMS)** | JSON | — | — | Each likelihood code with its purchase probability, e.g. `{"5": 0.7, "4": 0.5, "3": 0.3, "2": 0.1, "1": 0}` — what empty means (definitely would buy … definitely would not). |
| **Would buy at each price** | variables (several) | — | — | Gabor-Granger: one question per price — "Would you buy it at 9.99?" — asked of every respondent. A respondent missing any of them is left out; a sequential design that skips prices should fill in the implied answers first. |
| **Prices** | JSON | — | — | The price of each question, as a list in the same order, e.g. `[4.99, 6.99, 8.99]`. |
| **Counts as would buy** | answer code | — | — | The answer code, or a list of codes, that means would buy — a top-two box such as [4, 5] on a likelihood scale. Empty works for 0/1 questions. |

**The fields follow Method.** Its list has `van_westendorp` ("four price
questions") and `gabor_granger` ("buy or not at set prices"):

| Method | Fields shown | Marked required |
|---|---|---|
| `van_westendorp` | **Too cheap**, **Cheap (a bargain)**, **Expensive (getting expensive)**, **Too expensive**, the two likelihood questions and **Likelihood as probability (NMS)** | the four price questions; the other likelihood question once one is chosen |
| `gabor_granger` | **Would buy at each price**, **Prices**, **Counts as would buy** | **Would buy at each price**, **Prices** |

The card reads "Van Westendorp: p_too_cheap, p_bargain, p_expensive,
p_too_expensive" or "Gabor-Granger: buy_499, buy_699, buy_899". The empty
**Likelihood as probability (NMS)** and **Prices** boxes show the examples of
their help; **Counts as would buy** is a checklist of the first purchase
question's answers when it has value labels.

**Rules** (errors, then a warning):

- "Van Westendorp needs the too-cheap price — choose it in Too cheap.", and
  the same for the other three ("… needs the cheap (bargain) price — choose it
  in Cheap.", "… the getting-expensive price — choose it in Expensive.", "…
  the too-expensive price — choose it in Too expensive.").
- One variable named for two of the four prices: "p_price answers more than
  one of the four price questions; each is its own variable."
- "Newton-Miller-Smith needs both likelihood questions — choose the one at
  the expensive price too, or clear both." (or "… the one at the cheap price
  too …").
- "Gabor-Granger needs a purchase-intent question per price — choose them in
  Would buy at each price." and "Gabor-Granger needs the price of each
  question — list them in Prices, in the same order."
- **Prices** against the questions: "Prices lists 3 prices for 4
  purchase-intent questions; give one price per question, in the same
  order.", "Prices is a list of numbers, one per purchase-intent question,
  e.g. [5, 7.5, 10].", "Prices must all be numbers, one per purchase-intent
  question.", "Each price can be asked once; Prices lists one twice.",
  "Prices cannot be negative.", "A Gabor-Granger demand curve needs two or
  more prices."
- "Calibration is read only with the two likelihood questions — choose them,
  or clear Calibration." (a warning).

**Van Westendorp.** At every price anyone named, the curves give the share
who would call it too cheap, cheap (and *not cheap*, the rest), expensive
(and *not expensive*) and too expensive, joined by straight lines. The price
points are where they cross; PMC to PME is the **range of acceptable
prices**:

| Point | Where |
|---|---|
| **Point of marginal cheapness (PMC)** | too cheap meets not cheap |
| **Optimal price point (OPP)** | too cheap meets too expensive |
| **Indifference price point (IPP)** | not cheap meets not expensive |
| **Point of marginal expensiveness (PME)** | not expensive meets too expensive |

Where two lines run together for a stretch, the point is the middle of it;
where they do not meet within the prices named, the point is left out and a
note says so. The outputs:

| Output | What it holds |
|---|---|
| `table` | one row per point — **Point**, **Price**, **Share %** (the curves' value there), **Where** ("too cheap = not cheap"); with the likelihood questions also **Highest trial (NMS)** ("the highest mean purchase probability") and **Highest revenue (NMS)** ("the highest price × trial") |
| `curves` | one row per price named — **Price**, **Too cheap %**, **Cheap %**, **Not cheap %**, **Expensive %**, **Not expensive %**, **Too expensive %**, and with NMS **Trial %** and **Revenue per respondent**; "Curves = % of the respondents at each price named" |
| `stat` | **Method** ("Van Westendorp price sensitivity meter"), **N**, **Inconsistent**, **PMC**, **OPP**, **IPP**, **PME**, **Range of acceptable prices** ("6.4 – 14.34"); with NMS **Highest trial (NMS)**, **Trial % at it**, **Highest revenue (NMS)**, **Revenue per respondent at it** and **Calibration** ("5 → 0.7, 4 → 0.5, 3 → 0.3, 2 → 0.1, 1 → 0"); **Excluded**, **Excluded because**, **Missing codes** |

- A respondent whose four prices are not in order misunderstood a question:
  they are left out and counted in **Inconsistent**. With the likelihood
  questions, the base is the respondents who answered all six ("Excluded
  because = a missing value in any of the price or likelihood questions
  (listwise)"), so the price points and the trial curve share one base.
- **Newton-Miller-Smith** turns the likelihood answers into purchase
  probabilities — 5 → 0.7, 4 → 0.5, 3 → 0.3, 2 → 0.1, 1 → 0 when
  **Likelihood as probability (NMS)** is empty — and gives the trial curve and
  the prices with the highest trial and the highest revenue. A likelihood
  answer the calibration has no probability for stops the run: "The
  likelihood answers include 6, which the calibration does not turn into a
  probability (…); give Calibration a probability for each answer code."
- Nobody answering the four in order stops the run: "No respondent answered
  all four price questions in order (too cheap ≤ cheap ≤ expensive ≤ too
  expensive): …".

**Gabor-Granger.** The `table` (and `curves`, which holds the same rows) has
one row per price, lowest first — **Price**, **Question** (by its label),
**Would buy %**, **Revenue per respondent** (price × share), **Revenue index**
(100 at the best price) and **Elasticity** (the arc elasticity from the price
before). The statistics: **Method** "Gabor-Granger", **Counts as yes**,
**Prices**, **N**, **Revenue-maximizing price**, **Would buy % at it**,
**Revenue per respondent at it**, **Not monotone** (respondents who would buy
at a higher price but not at a lower one), **Elasticity** and **Excluded**.
Every respondent should answer every price: in a sequential design that stops
asking after a no, fill in the implied answers first (**Derive**). Questions
that are not 0/1 without **Counts as would buy** stop the run: "Gabor-Granger
needs to know which answer means would buy: the questions hold 1, 2, 3, 4, 5.
Name that code (or a list of codes, such as a top-two box) in Counts as yes —
`yes` outside a flow."

**On weighted data** every curve and share is a share of the weights; **N**
stays the number of respondents, and the statistics add **Weight** and
**Weighted N**.

Connect the `table` or the `curves` to a **Result chart** (Kind `curves`):
Van Westendorp's four curves with the points named at their prices and the
acceptable range shaded — with NMS, the trial curve in a panel below, marking
the highest trial and revenue — or Gabor-Granger's demand above its revenue,
"highest revenue at 8" marked. Each measure has its own panel: no chart puts
two scales on one axis.

### Proportion CI

`analyze.proportion_ci` — the share of respondents who gave one answer, with
its confidence interval.

**In:** `data` (SurveyData) → **Out:** `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Variable** | variable | required | — | The variable. |
| **Answer code** | answer code | required | — | The answer whose share you want, picked from the **Variable**'s value labels (`1 — Yes`). For a variable without value labels it is typed as JSON: `1` or `"yes"`. |
| **Confidence** | number | `0.95` | 0–1 | Confidence level between 0 and 1. |
| **Weighted** | checkbox | off | — | Use the applied weight. |

The statistics are `p` (the share), `lower`, `upper` and `n`. The base is
the respondents who answered the variable — someone who skipped it is not
counted as "did not choose".

- **Weighted** checked: the share is weighted and `n` is Kish's effective base
  of those respondents; a missing weight counts as 0, and weights of 1 give
  the unweighted result. The statistics add `weight` with the column's name.
  Earlier, a weighted share also counted the respondents who did not answer,
  which made it too small; a flow run again reports the corrected share.
- **Weighted** unchecked on weighted data: the share is of the respondents as
  they are, and `weight` reads "unweighted (the weight 'weight' is not
  applied)".
- Its `stat` output is the one statistic a **Result chart** draws (Kind
  `interval`): the share on a 0–100 % track with its interval, titled by the
  variable and the answer ("Gender: Female") and noting the level and base
  ("95 % confidence interval 28.4 – 35.9 %, base 600 respondents").

### Regression

`analyze.regression` — "Linear (OLS, weighted when a weight is applied),
logistic or ordinal logistic regression with a coefficient table." With a
weight applied, OLS becomes weighted least squares and the logistic and
ordinal models are weighted too, and the statistics add `weight`. Nominal
predictors are dummy-coded against their first category, using the codebook's
labels.

**In:** `data` (SurveyData) → **Out:** `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Outcome** | variable | required | — | Two values → logistic (auto); otherwise linear. Ordered answers (dissatisfied … satisfied) → choose ordinal; a nominal outcome (a region) has no order, and ordinal refuses it. |
| **Predictors** | variables (several) | required | — | Nominal predictors are dummy-coded against their first category. |
| **Model** | choice | `auto` | `auto`, `ols`, `logit`, `ordinal` | auto fits a logit when Outcome has two values and a linear model otherwise. ordinal is the proportional-odds (cumulative logit) model of three or more ordered answers — thresholds between the answers, one coefficient per predictor with its odds ratio and 95 % Wald interval, McFadden's pseudo-R²; a positive coefficient makes the higher answers more likely, as R's MASS::polr. It leaves the codebook's missing codes out and says how many. All three use the weight when one is applied. |

The **Model** list names each code under it: `ols` ("linear"), `logit`
("logistic, two answers"), `ordinal` ("ordinal logit, ordered answers").
`auto` never picks the ordinal
model, so a flow saved before it existed runs as it did.

**The ordinal model** is for an outcome of ordered answers — very
dissatisfied to very satisfied — which is neither a number an ordinary
regression may average nor a yes/no for a logit. It fits one threshold
between each pair of neighboring answers and one coefficient per predictor,
the same at every cut: logit P(y ≤ j) = θⱼ − xβ, as R's `MASS::polr` and
`ordinal::clm`, Stata's `ologit` and statsmodels' `OrderedModel` define it.
A positive coefficient makes the higher answers more likely; its odds ratio
is the odds of answering above any cut rather than at or below it.

- **The table** lists the coefficients, then the thresholds: **term**,
  **type** (`coefficient` or `threshold`), **estimate**, **std_error**,
  **statistic** (z), **p_value**, **odds_ratio**, **odds_ratio_lower** and
  **odds_ratio_upper** (the 95 % Wald interval). A threshold is named by the
  two answers it cuts between — `Very dissatisfied / Dissatisfied` — and its
  odds-ratio cells are blank. A nominal predictor's terms read `region =
  North`.
- **The statistics:** `model` ("ordinal logit (proportional odds)"),
  `outcome`, `categories`, `order` ("Very dissatisfied < Dissatisfied <
  Neutral < Satisfied < Very satisfied"), `n`, `log_likelihood`,
  `pseudo_r_squared` (McFadden's), the likelihood-ratio test against the
  thresholds alone (`lr_chi_square`, `lr_df`, `lr_p`), `aic`, `converged`,
  `coefficients` ("a positive coefficient makes the higher answers more
  likely: logit P(y ≤ j) = threshold j − xβ, as R's MASS::polr"), `interval`
  ("95 % Wald interval of the odds ratio") and `missing_codes` ("Trust: Acme:
  74 (9 = Refused)"); `note` when a labeled answer nobody in the model gave
  is not a category, `warning` when there is something to warn about.
- **A nominal outcome is refused**, before the run by the check
  (`VARIABLE_SCALE`; a warning when a node upstream makes the variable
  nominal) and by the run itself: "Region is nominal: its answers (Capital,
  North, South) have no order, and the ordinal model would take one from their
  codes. Use the logit for an outcome of two answers, or recode it onto an
  ordered scale (Recode with Scale = ordinal) first."
- **Other refusals**, with the reason: fewer than three answers ("… the
  ordinal model needs three or more ordered answers — with two, use the
  logit."), more than 20 different values ("… For a scale of numbers use the
  linear model (ols), or group the values into bands first."), text that is
  not a code, a predictor that does not vary, predictors that are a
  combination of each other. **Warned** (in `warning`): a fit that did not
  converge, and a predictor that separates the answers — its estimate runs
  off toward infinity and cannot be read.
- **On weighted data** each respondent's weight multiplies their part of the
  likelihood, as the logit's does; when the weights do not average about 1,
  `weights` says what they sum to, because the standard errors count that
  sum. The proportional-odds assumption itself is not tested.

Connect the `table` to a **Result chart** (Kind `coefficients`) for a forest
plot without the intercept: each coefficient with its 95 % interval, or for a
logit and the ordinal model each odds ratio on a log scale, the thresholds
left out. Terms are named by their labels and a note says what each nominal
predictor is compared with ("compared with Region = Capital"). Connect the
`stat` too: a linear model's intervals then use its t distribution ("t with
589 df").

### Scale reliability

`analyze.reliability` — Cronbach's alpha for a set of items, with item–total
correlations and alpha-if-deleted per item.

**In:** `data` (SurveyData) → **Out:** `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Items** | variables (several) | required | ordinal / interval / ratio variables | The items of the scale. |

After **Apply weight** alpha, the item means, the item–total correlations and
alpha-if-deleted are all computed with the weight, and the statistics add
`weight`. A row is dropped for a missing item, never for a missing weight
(that weighs 0), so the respondents counted (`n`) are the same either way.

### t-test

`analyze.ttest` — "Compares means — of two groups (Welch's or Student's
t-test), of two measurements of the same respondents (paired), or of one
variable against a value — with t, df, p, the mean difference and its CI, and
Cohen's d."

**In:** `data` (SurveyData) → **Out:** `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Design** | choice | `independent` | `independent`, `paired`, `one_sample` | Independent compares two groups of respondents; paired compares two variables answered by the same respondents; one_sample compares a mean with a fixed value. |
| **Variable** | variable | required | ordinal / interval / ratio variables | — |
| **Groups** | variable | — | nominal / ordinal variables | Independent: the variable that splits the respondents into the groups compared — one answer each; for a multiple-choice question, run Explode multiple choice and use one option's 0/1 column. |
| **Group A** | answer code | — | — | Independent: the code of the first group — needed only when Groups has more than two values. |
| **Group B** | answer code | — | — | The code of the second group. |
| **Variances** | choice | `welch` | `welch`, `student` | Welch's test does not assume the two groups vary equally and is the safer default; Student's pools the variances. |
| **Second measurement** | variable | — | ordinal / interval / ratio variables | Paired: the variable compared with Variable, respondent by respondent. |
| **Test value** | number | `0` | — | One sample: the value the mean is tested against. |
| **Confidence** | number | `0.95` | 0.5–0.999 | — |

**The fields follow Design.** Its list names each code under it:
`independent` ("two groups"), `paired` ("two variables, same people"),
`one_sample` ("a mean against a value"); the inspector shows only what that
design reads:

| Design | Fields shown | Marked required |
|---|---|---|
| `independent` | **Variable**, **Groups**, **Group A**, **Group B**, **Variances**, **Confidence** | **Groups**; **Group B** once **Group A** is set (and the other way round) |
| `paired` | **Variable**, **Second measurement**, **Confidence** | **Second measurement** |
| `one_sample` | **Variable**, **Test value**, **Confidence** | — |

**Group A** and **Group B** list the answers of the **Groups** variable
(`1 — Male`, `2 — Female`, …), including the bands of a **Bands** node. Leave
both empty when **Groups** has exactly two values.

**Rules** (errors):

- "An independent-samples t-test compares two groups — choose the variable
  that splits them in Groups."
- "A paired t-test compares two measurements of the same respondents —
  choose the second in Second measurement."
- "Name both groups to compare in Group A and Group B, or neither when Groups
  has only two values."

**The table** has one row per group — or per measurement, plus a
**Difference** row for a paired test — with **N**, **Mean**, **SD** and
**SE**, the groups by their value labels:

```
| Gender | N  | Mean   | SD     | SE    |
| Male   | 89 | 54.045 | 23.356 | 2.476 |
| Female | 86 | 55.291 | 24.349 | 2.626 |

Test = Welch's t-test (unequal variances); t = -0.345; df = 172.0; p = 0.7303;
Mean difference = -1.246; Difference = Male − Female; 95% CI = -8.369 – 5.877;
Cohen's d = -0.052; Hedges' g = -0.052; N = 175; Variable = Age
```

| Design | Footer |
|---|---|
| `independent` | **Test** ("Welch's t-test (unequal variances)" or "Student's t-test (equal variances)"), **t**, **df** (Welch's df has decimals), **p**, **Mean difference**, **Difference** (Group A − Group B), the CI (**95% CI**), **Cohen's d**, **Hedges' g**, **N**, **Variable** |
| `paired` | **Test** "Paired t-test", **t**, **df**, **p**, **Mean difference**, **Difference** ("Trust: Acme − Trust: Globex"), the CI, **Cohen's d (d_z)**, **N** (the complete pairs), **Incomplete pairs left out** |
| `one_sample` | **Test** "One-sample t-test", **Test value**, **t**, **df**, **p**, **Mean difference**, **Difference** ("mean − 3"), the CI, **Cohen's d**, **N** |

The difference is always the first minus the second — Group A − Group B,
**Variable** − **Second measurement** — as in **Paired tests**, so a t-test and
a Wilcoxon test of the same two variables agree in sign. The codebook's
missing codes are left out ("Missing codes left out = …").

**Refusals** — the run stops on this node with the reason:

- a **Groups** variable with more than two groups and none named: "Gender has
  3 groups (1 = Male, 2 = Female, 3 = Other); a t-test compares two — name
  them in Group A and Group B.";
- the same group twice: "Group A and Group B are both 1 = Male; a t-test
  compares two different groups — name another in one of them.";
- a missing code named as a group ("… is a missing code of Gender, not a
  group — name two groups that are answers.");
- a multiple-choice **Groups**: "… holds several answers per respondent, so
  its groups overlap and a t-test, which compares two separate groups, cannot
  use them. Run Explode multiple choice and compare by one option's 0/1
  column (chose it or not)."

What the data cannot carry — a group of one, no spread at all — is said in
the footer ("Test = not run: …") rather than as a number.

The t-test has no standard weighted form here: on weighted data it runs on the
respondents as they are and says "Weight: unweighted (the weight 'weight' is
not applied)". For two groups, **Group means** with **Test** `welch` or
`student` runs the same test beside weighted means.

### TURF

`analyze.turf` — how many **different** people a shortlist of options reaches
together: "which three flavors should we stock?" rather than "which three are
most popular" — or, with **Search** `fixed`, what a portfolio you already
have reaches.

**In:** `data` (SurveyData) → **Out:** `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Options** | variables (several) | required | — | One 0/1 column per option. Run prepare.explode on a multiple-choice question to get them. |
| **Largest portfolio** | whole number | `3` | at least 1 | — |
| **Search** | choice | `best` | `best`, `greedy`, `fixed` | Best tries every combination. Greedy extends the previous winner and is fast, but can miss the best portfolio — the table says which ran. Fixed searches nothing and reads the Portfolio below. |
| **Always include** | variables (several) | empty | — | Options that are in the portfolio whatever they add — shelf space already committed. |
| **Portfolio** | variables (several) | empty | — | For Search = fixed: exactly these options — each one's reach, what only it reaches, and the reach and frequency of all of them together. Empty reads every option. |

The **Search** list names each code under it: `best` ("every
combination"), `greedy` ("extend the winner"), `fixed` ("the Portfolio as it
is"). The inspector shows
**Largest portfolio** and **Always include** for `best` and `greedy`, and
**Portfolio** for `fixed`; the node's card reads "up to 3, best", or for a
fixed portfolio "fixed portfolio" and its options.

- Each respondent is counted once however many options they chose — that is
  what makes it *unduplicated* reach rather than a sum of percentages. The
  base is the respondents who answered; the applied weight is used, and the
  statistics then add **Weight**.
- **`best` and `greedy`:** one row per portfolio size with its options, reach,
  reach %, what it adds to the previous size and its frequency (the mean
  number of a portfolio's options a reached respondent chose). The table and
  the statistics (**Search**) name which search ran, because an exhaustive
  answer and a greedy one are not the same claim.
- **`fixed`:** one row per option of the **Portfolio** — its reach, its
  **unique** reach (the respondents no other option of the portfolio reaches:
  what dropping it would lose) and frequency — then a `(portfolio)` row, "All
  3 together", with the reach and frequency of the whole portfolio. The
  statistics give **Base**, **Search** "none: a fixed portfolio", **Reach**
  ("31.8 %"), **Frequency** and the **Note**. The base is the same as a
  search over **Options** would use: keep all the question's options in
  **Options**.
- **Rules** (warnings): "Always include is not read with Search = fixed, which
  evaluates exactly the Portfolio — add those options to Portfolio." and
  "Portfolio is read only with Search = fixed; best and greedy search for a
  portfolio themselves."
- On weighted data the reach is a sum of weights and the frequency a
  weighted mean.
- Options must be 0/1 columns. An exhaustive search that would not finish
  says so and suggests the ways out.
- Where the columns come from: an **Explode multiple choice** node upstream
  (its indicator columns are offered in **Options**), a Multiple choice
  question with **Data layout** `wide`, or a set of yes/no questions coded
  0/1.
- **Chart it** with a **Result chart** fed by the `table`: `best` and
  `greedy` draw the reach curve (Kind `reach`) — reach by portfolio size, each
  size named by the option it adds, by its label (`+ <label>`), with its
  reach and gain ("33.6 % (+10.5)"); a best portfolio that is not the one before
  plus an option reads "a new set" and is listed in full under the chart.
  `fixed` draws each option's reach beside what only it reaches (Kind
  `items`), with the whole portfolio's reach in the legend ("All 3 together:
  39.0 %").

---

## Visualize

**Chart** out (a **Trend** gives its points as a **Table** too). Six of the
seven draw from the data (SurveyData in); the **Result chart** draws what an
analysis computed (its table and statistics in). All seven accept a
**Title**, a **Figure width (in)** and **Figure height (in)** (2–30 inches,
10 × 6 by default) and a **Palette** — **Heatmap** takes a **Color map**
instead, and the **Likert chart** offers diverging palettes. Width and height
resize the figure the engine draws, not the picture of it, so the axis labels
keep their proportion. The newer charts — the Bar chart's newer forms, the
Pearson and Kendall heatmaps, a heatmap of means in the theme's colors, the
Likert chart, the Trend and the Result chart — also fit themselves to what
they show: long labels wrap and shrink, crowded ticks are thinned, and a
figure too small for its labels grows taller rather than print them over
each other. Counts and bases separate thousands (`n = 182,128`).

**Which chart.** A quick look needs no flow (**Data → Insights**); these
nodes are for reports and Live tiles.

| You want to show | Node | Set |
|---|---|---|
| how the answers to one question are spread | **Bar chart** | **Show** `percent`; **Sort** `value` for the largest first |
| only the answers given most, of a long list | **Bar chart** | **Top N**, and **Combine the rest as Other** for one gray bar of the rest |
| each share with its margin of error | **Bar chart** | **Show** `percent`, **Confidence intervals** |
| the parts of a whole | **Bar chart** | **Layout** `donut` |
| how a number spreads — an age, an amount | **Bar chart** | **Layout** `histogram`, **Bins** |
| a question's answers within the groups of another | **Bar chart** | **Split by**; **Layout** `stacked_100` for the shares of each group |
| … and which groups differ | **Bar chart** | **Split by**, **Show** `percent`, **Significance letters** |
| a mean in each group | **Bar chart** | **By** (and **Confidence intervals**) |
| a battery of statements on one scale | **Likert chart** | — |
| a share, a mean or a count over waves or months | **Trend** | **Time**, **Period**, **Measure** |
| a number within groups; two numbers against each other | **Box plot**; **Scatter plot** | — |
| how items correlate, or their means by group | **Heatmap** | **Method**; **By** |
| the result of an analysis — means with intervals, a scree plot, key drivers… | **Result chart** | **Kind** `auto` |

A chart is drawn as its node runs: one that cannot be drawn (a Likert chart
of items without a scale) fails its own node, with the reason, in a preview
and in a run — not the **Save report** or the preview after it.

**Palette `theme`.** Every chart's **Palette** (a **Heatmap**'s **Color map**)
offers `theme` ("the report's chart colors (Save report's Look)" under it
in the list): the chart
takes its colors from the **Look** of the **Save report** it is saved in — the
**Chart colors** you set there (see
[Chart colors](Studio-Reports#chart-colors)), with its text color, grid lines
and typeface. Left empty, those are the engine's default chart colors, eight
colors any two of which readers with protanopia or deuteranopia can tell
apart. In the report — its `.md` figures and its `.html` alike — the chart is
drawn in that report's colors. In a preview, and on a **Live tile** after a
run, it is drawn in the look of the flow's own **Save report** node — in the
default chart colors when the flow has none, or when its **Save report**
nodes name different looks. Its colors never come from the house style;
only the p in a **Result chart**'s note follows the house style's
**P values** there (see [P values](Studio-Reports#p-values)). A named
palette (`muted`, `RdBu`, `YlOrRd`, …) keeps its own colors whatever the
report's **Look** says. With `theme`:

- a series takes the next color of **Series**, an answer of an ordered scale
  a step of **Magnitude** (light to dark), and a Likert chart, a correlation
  heatmap or the red, gray and blue of NPS and sentiment the two **Diverging**
  ends;
- a series past the palette's colors gets a darker, then a lighter, shade of
  them — every one still at least 2:1 on the white background;
- a Heatmap of means by group is drawn as the newer charts are: each cell the
  mean of the group's respondents who answered that item (as **Group means**
  gives it), the codebook's missing codes left out and counted under the
  chart (see [Heatmap](#heatmap)).

After **Apply weight** a chart either draws the weighted numbers or says
under its title that it does not — so a picture never disagrees in silence
with a weighted table beside it:

| Chart | On weighted data |
|---|---|
| **Bar chart** | weighted: bars are sums of weights, weighted percentages, or weighted means with **By** — matching the **Frequencies**, **Crosstab** and **Group means** tables of the same data; a histogram's heights and a donut's slices are weighted too, and its intervals and letters use Kish's effective base |
| **Heatmap** with **By** | weighted means by group; the color bar reads "Weighted mean" |
| **Heatmap** without **By**, **Method** `pearson` | weighted coefficients; the color bar reads "Weighted Pearson r" |
| **Likert chart** | weighted shares; the axis reads "% of respondents (weighted)" |
| **Trend** | weighted percents, means and counts; the axis reads "% of respondents (weighted)", "Mean (weighted)" or "Respondents (weighted)" |
| **Result chart** | as the result it draws: its title's second line reads "weighted by 'weight'" or "unweighted (the weight 'weight' is not applied)" |
| **Box plot**, **Scatter plot**, **Heatmap** without **By** with **Method** `spearman` or `kendall` | unweighted — a box, a point per respondent and a rank correlation have no standard weighted form — with a second title line "unweighted (the weight 'weight' is not applied)", under your own **Title** too |

### Bar chart

`visualize.bar` — "Distribution of a variable as counts or percentages —
split by a second variable, grouped or stacked, like the chart of a crosstab
— or its mean by group; a histogram of a number, or a donut."

**In:** `data` (SurveyData) → **Out:** `chart` (Chart)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Variable** | variable | required | — | The variable to chart. |
| **By** | variable | — | nominal / ordinal variables | The mean of Variable in each group of this one. For the answers themselves in each group, use Split by. |
| **Show** | choice | `count` | `count`, `percent` | Count, or percent of the respondents who answered — for a multiple-choice question the share who named each option, so the bars add up to more than 100 % (the chart says so). With By the bars are means. |
| **Split by** | variable | — | nominal / ordinal variables | The answers within each group of this variable — the chart of a crosstab, with percentages of each group (column percentages), weighted when a weight is applied. |
| **Layout** | choice | `grouped` | `grouped`, `stacked`, `stacked_100`, `histogram`, `donut` | With Split by: the groups' bars side by side, stacked, or stacked to 100 % of each group (percentages, whatever Show says); a multiple-choice question's options overlap and are drawn side by side only. histogram: an interval or ratio variable in Bins, as counts or percent — with Split by, a panel per group. donut: one variable's answers as the parts of a whole, their percentages on the slices and the base in the middle (not with Split by, By or a multiple-choice question). |
| **Sort** | choice | `code` | `code`, `value` | Code keeps the codebook's order; value draws the largest bar first (with Split by, the answer most given overall — or, when the answers are a scale, the groups with the largest share of its top answer first, the scale kept in order). Colors follow the answer, not its place — the same in a Top N chart and a donut of the same question. Any setting but the defaults (Show count, no Split by, Sort code, no Top N, intervals, histogram or donut) draws the newer chart, with its base and notes under the plot. |
| **Horizontal** | checkbox | off | — | Bars across, labels beside them. With Show, Split by or Sort set, vertical bars whose labels cannot be read under them (many long answers) are drawn across too. |
| **Show values** | checkbox | on | — | Print the value on each bar — in a donut, each slice's percentage. |
| **Top N** | whole number | — | 1–100 | Only the N answers given most — with Split by, given most overall; for a multiple-choice question, the options named most; for a number of many values, its N values given most (up to 30). Empty draws every answer. In a donut the rest are combined as Other. |
| **Combine the rest as Other** | checkbox | off | — | With Top N, one more bar for the answers after the top N — for a multiple-choice question, the respondents who named any of them — drawn gray and last. Off, the rest are left out; the note under the chart says how many. |
| **Confidence intervals** | checkbox | off | — | An error bar on each percentage (Wilson's interval, on Kish's effective base when weighted — each group's own base with Split by) and on each mean by group (the interval Group means draws when it leaves the missing codes out — Student's t, weighted the linearization interval; the Bar chart always leaves them out). Drawn on bars side by side (Layout grouped) only; counts have none. |
| **Confidence** | number | `0.95` | 0.5–0.999 | The intervals' confidence level. |
| **Significance letters** | checkbox | off | — | With Split by, Show percent and Layout grouped. The groups of Split by are lettered A, B, … (under their names) in the Banner table's order, and a bar carries the letters of the groups whose share of that answer is significantly lower — the Banner table's two-sided z-test of column proportions, on the group's respondents who answered (Kish's effective base when weighted); a group below 30 is not tested. The Tab book shows the same comparisons, under the letters its banner gives these columns — the same letters only when Split by is the banner's first variable. |
| **Level** | number | `0.05` | 0.001–0.2 | The letters' significance level. |
| **Multiple comparisons** | choice | `none` | `none`, `bonferroni` | `bonferroni` divides **Level** by the number of pairs of groups tested. |
| **Bins** | text | `auto` | — | auto: Freedman and Diaconis's width (whole-number answers take a whole width); a number: that many bins of equal width; two numbers or more: the bins' edges, increasing, separated by commas (0, 18, 25, 35, 50, 65). At most 100 bins. |
| **Other below (%)** | number | `3` | 0–50 | Slices smaller than this percentage are combined as Other (two or more of them); 0 keeps every slice. |
| **Title** | text | — | — | Chart title. |
| **Figure width (in)** | number | `10` | 2–30 | The figure itself, in inches — the axis labels scale with it. |
| **Figure height (in)** | number | `6` | 2–30 | — |
| **Palette** | choice | `muted` | `muted`, `deep`, `pastel`, `dark`, `colorblind`, `Set2`, `tab10`, `theme` | Theme takes the colors of the report the chart is saved in — the chart colors of its Save report's Look (by default eight colors any two of which readers with protanopia or deuteranopia can tell apart), with its text color, grid and font. The others are seaborn's palettes. |

The lists name each code under it: `count` ("respondents"), `percent` ("%
of those who answered"); `grouped` ("side by side"), `stacked` ("stacked, as
Show says"), `stacked_100` ("stacked to 100 %"), `histogram` ("histogram of
a number, in Bins"), `donut` ("donut: the parts of a whole"); `code` ("the
codebook's order"), `value` ("largest first"); `bonferroni` ("Bonferroni");
`theme` ("the report's chart colors (Save report's Look)"). **Bins** suggests
`auto`, `10` and
`0, 18, 25, 35, 50, 65`. The card reads `satisfaction by region` with
**Split by** set, and the variable alone for a donut.

**The fields each form reads.** The inspector shows only those (see
[Reading this page](#reading-this-page)): **By** with **Show** `count` and a
bar layout (`grouped`, `stacked`, `stacked_100`); **Show** and **Split by**
for every layout but `donut`; **Sort**, **Show values** and **Top N** for
every layout but `histogram`; **Horizontal** and **Combine the rest as
Other** for bars only (not a histogram or a donut); **Confidence
intervals** with `grouped` (and with a stacked layout at **Show** `count` and
**Sort** `code`, where a rule warns that it is not drawn), **Confidence** once
it is checked; **Significance letters** with **Show** `percent` and
`grouped`, its **Level** and **Multiple comparisons** once it is checked;
**Bins** for a histogram and **Other below (%)** for a donut.

**Seven charts in one node:**

| You want | Set | The chart |
|---|---|---|
| the distribution of one question | **Variable** (and **Show**) | a bar per answer: respondents, or % of those who answered |
| the answers given most, of a long list | **Top N** (and **Combine the rest as Other**) | the N answers given most; the rest left out, or one gray **Other** bar, last |
| the answers within groups — the chart of a crosstab | **Split by**, **Layout** | per group of **Split by**, its distribution: counts, or % of the group (column percentages); `stacked_100` stacks each group to 100 % |
| which groups differ on an answer | **Split by**, **Show** `percent`, **Significance letters** | the grouped bars, each carrying the letters of the groups whose share is significantly lower |
| a mean by group | **By** | the mean of **Variable** in each group of **By**, with its interval when **Confidence intervals** is checked |
| how a number spreads | **Layout** `histogram`, **Bins** | the number in bins, as counts or % — a panel per group with **Split by** |
| the parts of a whole | **Layout** `donut` | a ring of the answers' shares, the base in the middle |

**The classic chart and the newer one.** At the defaults — **Show** `count`,
no **Split by**, **Sort** `code`, no **Top N**, **Confidence intervals** off
and a bar layout — the node draws the chart it always has, picture for
picture, and a stored flow renders the same code: each new option is written
into the script only when it is set. Any other setting (**Sort** `value`
alone included) draws the newer chart, whose look differs:

- It leaves the codebook's missing codes out of the bars and says so under
  the plot ("Left out as missing: Trust: Acme: 47 (9 = Refused).").
- It writes the base under the plot — "Base: 385 respondents who answered."
  ("… who answered both. Each group's n is under its name." with **Split
  by**, each group's `n` under its name on the axis) — and, with percentages
  of groups, "Percentages are of each group of Region."; the axis reads "% of
  respondents", "% within Region" or "Count".
- A multiple-choice question counts respondents, not answers: "Several
  answers allowed: each bar is the share of respondents who named the option,
  so the bars add up to more than 100 %." It is drawn by the newer chart
  whatever the settings, and its options are never stacked.
- One series is one color; the answers of an ordered scale are one hue, light
  to dark. A color belongs to its answer, not its place, so a sorted chart,
  a **Top N** chart and a donut of the same question color the same answer
  alike; **Other** is gray.
- Sorted with **Split by** a scale (ordinal and up), the answers keep the
  scale's order and the groups go largest first, by their share of the top
  answer: "Groups in order of their share of Very satisfied; the answers keep
  the scale's order."
- Long labels wrap; every label beside horizontal bars gets a row of its own,
  and vertical bars whose labels cannot be read under them, even turned, are
  drawn across. A legend too tall or too wide to sit beside the plot goes
  under it, a percent axis puts its ticks on whole percents, and a value
  axis drops ticks rather than print their numbers into each other.
- It draws a bar (or a slice) per value given, so it refuses a number with
  more than 30 different values given: "Age is a number with 84 different
  values given, and this chart draws a bar for each: layout='histogram' draws
  its distribution (or band it first with Bands)." ("… a slice for each …"
  in a donut). With **Top N** it draws the N values given most, so N is what
  counts: up to 30 are drawn, in steps of one hue light to dark among
  themselves (among all 84, neighbors would read as one color); past 30, "Age
  is a number with 84 different values given, and top=40 draws a bar for each
  of the 40 given most: give top=30 or fewer, or layout='histogram' draws its
  distribution (or band it first with Bands)." A question nobody answered
  stops the node with "No respondent answered Trust: Acme."

**Top N and Other.** The bars keep **Sort**'s order — the codebook's, or the
largest first — and the note under the chart says what was left out: "The 3
answers given most of 5 are drawn; the other 2 are left out." With **Combine
the rest as Other**: "…; Other combines the other 2." For a multiple-choice
question: "The 2 options named most of 4 are drawn; Other is the respondents
who named any of the other 2." With **Split by** the answers are those given
most overall ("The 2 answers given most overall of 5 are drawn; …"). A donut
always combines the rest: "…; Other combines the other 3 — a donut's slices
make a whole." A **Top N** of as many answers as there are draws them all.

**Confidence intervals.** Error bars on the bars side by side, at
**Confidence**, and a note naming them: "Error bars: 95 % confidence
intervals (Wilson score)." — "(Wilson score, on Kish's effective base)" on
weighted data — or, for means by group, "Error bars: 95 % confidence
intervals of the mean (Student's t)." ("(weighted: the linearization
interval)"). A share is the one **Proportion CI** gives for the same
respondents (Proportion CI's interval is the normal approximation, so its
bounds can differ a little, most near 0 % and 100 %); a mean's interval is
the one **Group means** gives when it leaves
the missing codes out (a **Test** chosen by hand) — its `auto` test counts
them as answers, so its chart can differ from this one.

**Significance letters.** The groups of **Split by** are lettered under their
names on the axis (`Capital (A)`, `North (B)`, …), and a letter over a bar
names a group whose share of that answer is significantly lower. The note
reads "A letter over a bar names a group (its letter is under its name) whose
share of that answer is significantly lower (two-sided z-test of column
proportions, p < 0.05) — the Banner table's and the Tab book's letters.",
adding "Bonferroni-corrected" and "on Kish's effective base" where they
apply; "No group's share of any answer is significantly higher than
another's." when no bar carries a letter; and "Not tested, fewer than 30
respondents who answered: Other (C)." for a small group. The comparisons are
the Banner table's and the Tab book's for the same cells; a Tab book letters
every column of its banner in one run (A, B, C for gender, then D, E, F for
region), so its letters match the chart's only when **Split by** is the
banner's first variable.

**Histogram.** An interval or ratio variable in bins, as counts (**Show**
`count`) or % of those who answered (`percent`), with the bins' rule under
the plot:

| **Bins** | The bins | Note |
|---|---|---|
| `auto` | Freedman and Diaconis's width; whole-number answers take a whole width | "Bins: 11 of width 8 (Freedman–Diaconis), each holding 8 whole numbers." |
| a number, `10` | that many of equal width (1–100) | "Bins: 10 of equal width." |
| edges, `16, 25, 35, 50, 65, 100` | from one edge to the next, each holding its left edge, the last its right edge too; commas, semicolons or spaces between them; at most 100 bins | "Bins: the edges given; each bin holds its left edge, the last its right edge too." — and, when the bins differ in width, "The bins differ in width: a bar's height is its percentage, not its density." |

With **Split by**, each group is a panel of its own on the same bins, its `n`
over it ("Male (n = 404)"), and the base note says "Each group's n is over
its panel." After **Apply weight** the heights are sums of weights ("the
width is of the answers as they are, the heights weighted"). **Bins** it
cannot read is an error on the field as you edit: "bins: The bins' edges must
increase from one to the next, and 5 is followed by 3.", "bins: A number of
bins is a whole number from 1 to 100; got '0'.", "bins: At most 100 bins: 102
edges give 101." or "bins: Bins is auto (Freedman and Diaconis's width), a
number of bins, or the bins' edges in increasing order, separated by commas
(0, 18, 35, 65); got 'many'."

**Donut.** The answers of one question as the slices of a ring, their
percentages on the slices (beside a thin one), the base in the middle
("981 respondents"). Slices under **Other below (%)** are combined as one
gray **Other** when there are two or more of them: "Other combines 3 answers
under 20 % each: Low, Medium and High." When every answer is under it, the
node stops rather than draw one gray ring: "Each of the 40 answers to Brand
drawn is under 3 % of the respondents who answered, so Other would fill the
whole ring: draw them as bars (layout='grouped'), or lower min_slice." The
codebook's missing codes are left out, as in every newer form.

**Rules** (an error stops the flow; a warning names a setting the chart
ignores):

- Errors: "By draws the mean of Variable in each group and Split by its
  answers in each group — clear one of them."; "Top N keeps the answers given
  most, and with By the bars are means of groups — clear one of them.";
  "Split by must be another variable than Variable."
- Warnings: "By (the mean in each group) is not drawn when Show is percent;
  to show the answers in each group, use Split by." (on bars); "Stacked layouts apply
  only when Split by is set."; "Combine the rest as Other applies with Top N
  — set Top N."; "Top N keeps the answers given most; a histogram draws bins
  of a number, so it is not applied."; "By (the mean in each group) is not
  drawn in a histogram; for a histogram of each group, use Split by."; "By
  (the mean in each group) is not drawn in a donut, which shows the shares of
  Variable's answers."; "Split by is not drawn in a donut, which shows one
  variable's answers as the parts of a whole; Layout stacked_100 shows the
  answers within each group."; "Confidence intervals are drawn on bars side by
  side (Layout grouped) only."; "Confidence intervals are drawn for
  percentages and for means by group; counts have none — set Show to
  percent."; "Significance letters compare the groups of Split by — set Split
  by."; "Significance letters are drawn on bars side by side (Layout grouped),
  not on stacks."; "Significance letters compare percentages, as the Banner
  table's do — set Show to percent."
- The rules on the intervals and the letters, and on **By** with **Show**
  `percent`, speak of bars (`grouped`, `stacked`, `stacked_100`): a histogram
  or a donut draws neither intervals nor letters, and when they are left
  checked from the bars it is not warned of them — they are named under the
  fields as not used with these choices. Of a donut with **By** and **Split
  by** left over, the two warnings are that it draws neither.

The check also refuses, before the run, what the questionnaire settles: a
**Split by** that allows several answers ("Split by needs one answer per
respondent, and Brands heard of (unaided) allows several: draw it as the
Variable, or split by one of its options after Explode multiple choice."), a
stacked layout of one ("Brands heard of (unaided) allows several answers, so
its options overlap and cannot be stacked: draw them side by side (Layout =
grouped)."), a histogram of a question with answers ("A histogram draws the
distribution of a number, and Region is nominal: draw its answers as bars
(Layout = grouped).", "Brands heard of (unaided) allows several answers; a
histogram draws one number per respondent.") and a donut of a multiple-choice
question ("Brands heard of (unaided) allows several answers, so its shares add
up to more than 100 % and are not the parts of a whole: draw them as bars
(Layout = grouped)."). A number whose valid range holds more than 30 whole
numbers, drawn in a newer form, is a warning: "Age is a number of up to 84
values, and bars draw each value given: Layout histogram draws its
distribution." (a donut: "… and a donut draws a slice for each value given
…"; a **Top N** over 30: "… and Top N draws a bar for each of the 40 given
most: set Top N to 30 or fewer, or Layout histogram draws its
distribution.") — the data decides whether the newer chart refuses it. A range
of 0 to 29.5 holds 30 whole numbers, and is not warned of; nor is the classic
chart, which draws every value as it always did.

After **Apply weight**, a distribution's bars are sums of weights — the axis
reads "Weighted count", and the values on the bars have one decimal when they
are fractional (the newer chart writes a count from 100 up whole, `18,848`) —
or weighted percentages ("% of respondents
(weighted)", "% within Region (weighted)", weighted as the **Frequencies**
and **Crosstab** tables are), and with **By** the bars are weighted
means, on an axis "Weighted mean *label*". A histogram's and a donut's shares
are weighted too, and the intervals and letters use Kish's effective base.
The newer chart's base adds the weighted total ("Base: 385 respondents who
answered (weighted: 380.9).") and the note "Weighted by 'weight'; n counts
respondents." Unweighted, the axes read "Count" and "Mean *label*".

### Box plot

`visualize.boxplot` — the distribution of a variable across groups.

**In:** `data` (SurveyData) → **Out:** `chart` (Chart)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Variable** | variable | required | ordinal / interval / ratio variables | The variable whose distribution is shown. |
| **By** | variable | required | nominal / ordinal variables | The grouping variable (required). |
| **Show points** | checkbox | off | — | Overlay the individual points. |
| **Title** | text | — | — | Chart title. |
| **Figure width (in)** | number | `10` | 2–30 | The figure itself, in inches — the axis labels scale with it. |
| **Figure height (in)** | number | `6` | 2–30 | — |
| **Palette** | choice | `muted` | `muted`, `deep`, `pastel`, `dark`, `colorblind`, `Set2`, `tab10`, `theme` | Theme takes the colors of the report the chart is saved in — the chart colors of its Save report's Look (by default eight colors any two of which readers with protanopia or deuteranopia can tell apart), with its text color, grid and font. The others are seaborn's palettes. |

Quartiles and whiskers are of the respondents as they are; on weighted data
the title's second line says "unweighted (the weight 'weight' is not
applied)".

### Heatmap

`visualize.heatmap` — "Correlation matrix of several items (Spearman, Pearson
or Kendall), or their means by group."

**In:** `data` (SurveyData) → **Out:** `chart` (Chart)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Items** | variables (several) | required | — | The items to show. |
| **By** | variable | — | nominal / ordinal variables | Each item's mean in each group of this variable (weighted when a weight is applied). With a named Color map it is drawn as it always was, over the respondents who answered every item, a missing code such as 99 = Not applicable counting as an answer (run Missing values first to leave it out). With Color map theme each cell is the mean of the group's respondents who answered the item, as Group means gives it, the codebook's missing codes left out and counted, long items numbered and each group's base under its name. Without By, the heatmap is the correlation matrix of the items. |
| **Method** | choice | `spearman` | `pearson`, `spearman`, `kendall` | The correlation drawn without By, over the respondents who answered every item. Spearman, the default, reads the answers as it always has (a missing code such as 9 = Refused counts as an answer; run Missing values first to leave it out). Pearson and Kendall leave the codebook's missing codes out and say so, as Correlation matrix does; Pearson is weighted when a weight is applied, Kendall says it is not. |
| **Title** | text | — | — | Chart title. |
| **Figure width (in)** | number | `10` | 2–30 | The figure itself, in inches — the axis labels scale with it. |
| **Figure height (in)** | number | `6` | 2–30 | — |
| **Color map** | text | `YlOrRd` | a matplotlib colormap, or `theme` | A matplotlib colormap, used when means are shown by a group; a correlation matrix keeps its own diverging scale. Type theme for the colors of the report the chart is saved in — its Save report Look's sequential color for the means, its diverging pair for a correlation matrix, with its text color, grid and font. |

The **Method** list names each code under it: `pearson` ("Pearson r"),
`spearman` ("Spearman rho, answers as they are"), `kendall` ("Kendall
tau-b"). `spearman` draws the
chart the node always has; a flow saved before **Method** existed keeps it.
**Color map** suggests `theme`, `YlOrRd`, `Blues`, `viridis` and `RdBu_r` as
you type.

**Means by group in the theme's colors.** With **By** and **Color map**
`theme`, the heatmap is drawn as the newer charts are, and its numbers are
those of **Group means** for the same respondents: each cell is the mean of
the group's respondents who answered that item, not only of those who
answered every item. The notes say so — "Base: 1,159 respondents who answered
Region and an item; each group's n is under its name. Each cell is the mean
of the group's respondents who answered the item, as Group means gives it."
— and count the missing codes left out ("Left out as missing: Trust: Acme:
194 (9 = Refused); …"). Long item labels are numbered (`1. Trust: Acme`),
each group's `n` is under its name, and the means are written
at a size their cells hold. With a named color map (`YlOrRd`, the default),
the means are drawn as they always were — over the respondents who answered
every item, a missing code counting as an answer — so run **Missing values**
first there.

**Pearson and Kendall** draw the numbers of a **Correlation matrix** table
with **Missing answers** `listwise`, titled "Pearson Correlation Matrix" or
"Kendall tau-b Correlation Matrix":

- the codebook's missing codes are left out and counted under the plot, with
  N: "N = 251 respondents who answered every item (listwise)." and "Left out
  as missing: Trust: Acme: 108 (9 = Refused); Trust: Globex: 109 (9 =
  Refused).";
- a pair that cannot be computed — an item everyone answered the same, its own
  diagonal too — is a blank cell, and the note says why;
- long labels are numbered — the rows read `1. label`, the columns `1`, `2`,
  … — and the coefficients are written at a size their cells hold (at most
  10 pt); below 6 pt they are left to the table, and the note says so.

Rule (a warning): "Method applies to the correlation matrix drawn without By;
with By the heatmap shows means."

After **Apply weight**, the means by group are weighted and the color bar is
labeled "Weighted mean". A Pearson matrix is weighted too — color bar
"Weighted Pearson r", and the note "Weighted by 'weight': the coefficients
are weighted; N counts respondents." A Spearman or Kendall matrix is never
weighted: its title's second line says "unweighted (the weight 'weight' is
not applied)". For the coefficients with their p-values and N, use
**Correlation matrix** — and a **Result chart** of its table for the same
heatmap with the table's significance marks.

### Likert chart

`visualize.likert` — "A battery of items on one ordered scale as diverging
stacked bars centered on the neutral answer, with each item's top-2 and
bottom-2 shares." Each item is a bar: the answers below the middle of the
scale stack to the left of a center line, those above it to the right, so a
battery's lean reads at a glance.

**In:** `data` (SurveyData) → **Out:** `chart` (Chart)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Items** | variables (several) | required | ordinal / interval variables | Items with one answer each on the same scale — the same value labels in the codebook (a battery such as agree–disagree statements). Codes run low to high, left to right; recode a scale that runs the other way first. The codebook's missing codes (a 9 "Don't know") are left out and counted under the chart. |
| **Neutral answer** | choice | `split` | `split`, `side` | Split draws the middle answer of an odd scale half on either side of the center; side draws it apart, in a panel at the right. An even scale has no neutral answer, and its center falls between the two middle answers. |
| **Sort items** | choice | `top2` | `top2`, `listed` | top2 puts the item with the largest share in the top two answers first (the top answer alone on a scale of two or three); listed keeps the order of Items. |
| **Show values** | checkbox | on | — | Each answer's share in its segment where it fits. The top-2 and bottom-2 shares are always written at the ends. |
| **Title** | text | — | — | Empty takes the words the items' labels start with ("Trust" of "Trust: Acme" and "Trust: Globex"), the rest of each label naming its bar. |
| **Figure width (in)** | number | `10` | 2–30 | The figure itself, in inches — the axis labels scale with it. |
| **Figure height (in)** | number | `6` | 2–30 | A battery whose labels need more room makes the figure taller. |
| **Palette** | choice | `RdBu` | `RdBu`, `BrBG`, `PuOr`, `RdYlBu`, `PiYG`, `coolwarm`, `theme` | A diverging palette, the low answers in its first color; the neutral answer is gray. Theme takes the colors of the report the chart is saved in — the diverging pair of its Save report's Look (low end first), with its text color, grid and font. |

The lists name each code under it: `split` ("half on either side"), `side`
("in a panel at the right"), `top2` ("largest top-2 share first"), `listed`
("in the order of Items").

```
                                  Trust
                  Bottom-2                                    Top-2
Acme (n = 485)       42%    [ 22% | 20% |  18%  | 21% | 19% ]    40%
Globex (n = 484)     41%    [ 20% | 21% |  21%  | 20% | 18% ]    38%
                           60%   40%   20%   0%   20%   40%   60%
                                     % of respondents
               ■ No trust  ■ Low  ■ Medium  ■ High  ■ Full
```

The center line (0 %) runs through the middle of the neutral answer, here
**Medium**, half of which lies on either side.

**What counts as the scale.** Each item's labeled answers in the codebook,
its missing codes left out; without value labels, a valid range of whole
numbers (2 to 11 of them); failing that, a Likert scale question's points,
the two ends named by its end labels. Every item must have the same answers.
The check says so before the run, and a chart that cannot be drawn fails
its own node with the same words:

- "The items of a Likert chart must share one scale, and these do not: Trust:
  Acme has 1 = No trust, 2 = Low, 3 = Medium, 4 = High, 5 = Full; Overall
  satisfaction has 1 = Very dissatisfied, 2 = Dissatisfied, 3 = Neutral, 4 =
  Satisfied, 5 = Very satisfied. Draw them in separate charts, or recode them
  onto one scale first."
- "Brands heard of (unaided) allows several answers; a Likert chart draws items
  with one answer each on a scale."
- "A Likert chart draws the answers of a scale, and none of the items has
  value labels (or a valid range of whole numbers) in the codebook, or a
  Likert scale question, to say what the scale is."

**Under the chart**, notes say what it shows:

- "Base: the respondents who answered each item on the scale (n beside it).
  Items in order of their top-2 share." — each bar is labeled with its base
  (`Acme (n = 485)`);
- "Top-2: 4 = High, 5 = Full; bottom-2: 1 = No trust, 2 = Low." — the shares
  at the ends of each bar;
- "The neutral answer (3 = Medium) is split around the center." (or "… is
  drawn apart, at the right.");
- "Left out as missing: Trust: Acme: 108 (9 = Refused); Trust: Globex: 109 (9
  = Refused)." — and "Not on the scale, left out: …" for values off the
  scale, "No answer on the scale, not drawn: …" for an item nobody answered.

A single item draws one bar, titled by its label. The item labels are fitted
to the figure — smaller and wider on a narrow one — before it grows taller.
After **Apply weight** the shares are sums of weights, the axis reads "% of
respondents (weighted)" and a note says "Weighted by 'weight'; n counts
respondents."

### Result chart

`visualize.result_chart` — "The chart that suits an analysis's result, drawn
from the numbers it computed — group means with their confidence intervals, a
scree plot, TURF's reach curve, key drivers, a perceptual map, price
sensitivity curves." Because it draws the analysis's own numbers rather than
the data again, the picture never disagrees with the table beside it.

**In:** `result` (Table or Stat, several) → **Out:** `chart` (Chart)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Kind** | choice | `auto` | `auto`, `means`, `means_sd`, `interval`, `stacked`, `reach`, `items`, `utilities`, `scores`, `shares`, `importance`, `partworths`, `scree`, `loadings`, `profile`, `coefficients`, `heatmap`, `sentiment`, `map`, `curves` | Auto draws the chart the result suits; the others are listed below. |
| **Title** | text | — | — | Empty takes the result's own title ("Age by Region", "Key drivers of Overall satisfaction"). |
| **Figure width (in)** | number | `10` | 2–30 | The figure itself, in inches — the axis labels scale with it. A chart with more rows than its height holds legibly grows taller. |
| **Figure height (in)** | number | `6` | 2–30 | — |
| **Palette** | choice | `muted` | `muted`, `deep`, `pastel`, `dark`, `colorblind`, `Set2`, `tab10`, `theme` | The colors of the bars, points and series. Net Promoter Score and sentiment keep their own red–gray–blue, the heatmaps their diverging scale, and Key drivers, the Perceptual map and Price sensitivity their own color-blind-safe pairs. Theme takes every color from the report the chart is saved in — the chart colors of its Save report's Look (by default eight colors any two of which readers with protanopia or deuteranopia can tell apart), its series, its diverging pair for the red–gray–blue and the heatmaps, its text color, grid and font. |

**Connecting it.** Wire the analysis's `table` into **result** — for
**Factor analysis** and **Principal components** the `variance` output (scree)
or `loadings`, for **Proportion CI** its `stat`, for a **Perceptual map** any
of its three tables, for **Price sensitivity** its `table` or `curves`. The
input takes several wires: connect the analysis's `stat` too and the chart
learns its base and weight from it (a regression's intervals then use its t
distribution). The table alone says how the weight was used.

**The Kind field** says under it what the connected result suits and what
`auto` draws — "Group means (means.table) suits means — means with 95 %
intervals; means_sd — means ± 1 SD. Auto draws means." — and in its list
every other kind has "(not for this result)" after its name, under its code.
With nothing connected it reads "Connect an analysis's table (or Proportion
CI's stat) to see the charts it suits." A screen reader hears that line with
the field. The list names each kind under its code: `auto` ("the chart the
result suits"), `means` ("means with 95 % intervals"), `means_sd` ("means ±
1 SD"), `interval` ("a share and its interval"), `stacked` ("NPS:
detractors, passives, promoters"), `reach` ("TURF reach curve"), `items`
("TURF: each option's reach"), `utilities` ("MaxDiff utilities"), `scores`
("MaxDiff scores"), `shares` ("shares"), `importance` ("importance: Conjoint,
Key drivers"), `partworths` ("Conjoint part-worths"), `scree` ("scree
plot"), `loadings` ("loadings heatmap"), `profile` ("cluster profiles"),
`coefficients` ("coefficients or odds ratios"), `heatmap` ("correlation
heatmap"), `sentiment` ("sentiment split"), `map` ("perceptual map"),
`curves` ("price curves"). With **— default —** first, that is more than ten
entries, so the list opens with a filter box ("Filter chart kinds…"): type
"maxdiff" to keep `utilities` and `scores`.

**What it draws** — the first kind of each row is what `auto` draws:

| Analysis (output) | Kinds | The chart |
|---|---|---|
| **Group means**, **Descriptive statistics**, **t-test** (`table`) | `means`, `means_sd` | each mean with its 95 % confidence interval, or ± 1 SD, a row per group or measurement with its base (`North (n = 97)`); after a post-hoc test, letters: "Means sharing a letter do not differ (Tukey HSD, p < .05)."; a t-test notes its test ("Welch's t-test (unequal variances): difference Male − Female = 2.5 (95% CI -2.101 – 7.100), p = 0.2861") |
| **Paired tests** with Wilcoxon, Friedman or `auto` (`table`) | `means`, `means_sd` | the means of the measurements, noting that the test compares ranks |
| **Paired tests** with McNemar or Cochran's Q (`table`) | `shares` | the share saying yes to each, with Wilson's interval |
| **Proportion CI** (`stat`) | `interval` | the share and its interval on a 0–100 % track, titled "Gender: Female" |
| **Net Promoter Score** (`table`) | `stacked` | detractors, passives and promoters as one bar, with the score and its interval |
| **TURF** (`table`) | `reach`; `items` with **Search** `fixed` | reach by portfolio size, each size named by the option it adds; or each option's reach and what only it reaches |
| **MaxDiff** (`table`) | `utilities`, `scores`, `shares`; `scores` with **Estimate** `counts` | the utilities with 95 % intervals against the reference item at 0, the counting scores, or the shares |
| **Conjoint** (`table`) | `importance`, `partworths` | each attribute's importance, or the part-worths of its levels in the design's order |
| **Share of preference** (`table`) | `shares` | each product's share |
| **Principal components**, **Factor analysis** (`variance`) | `scree` | the eigenvalues with the Kaiser line at 1 — the factors kept filled, and the parallel analysis's line when it ran |
| **Principal components**, **Factor analysis** (`loadings`) | `loadings` | a heatmap of the loadings |
| **Cluster (k-means)** (`table`) | `profile` | each cluster's means down the items, the legend giving its size ("Cluster 1 (n = 141, 44.9 %)") |
| **Regression** (`table`) | `coefficients` | a forest of the coefficients with their 95 % intervals, without the intercept; odds ratios on a log scale for a logit and the ordinal logit (its thresholds left out) |
| **Correlation matrix** (`table`) | `heatmap` | the lower triangle with the table's significance marks |
| **Code open answers** (`table`) | `shares`; `sentiment` too with sentiment checked | each theme's share (of the respondents who answered; of the coded answers for an older, version 1 codeframe) — not the nets, nor the Coded and Uncoded rows; its answers' sentiment |
| **Key drivers** (`table`) | `importance` | each driver's share of R², largest first, a negative beta in a second color |
| **Perceptual map** (`table`, `rows` or `columns`) | `map` | the symmetric map of the first two dimensions, each axis with its share of the inertia |
| **Price sensitivity** (`table` or `curves`) | `curves` | Van Westendorp's curves and price points (with the NMS trial curve), or Gabor-Granger's demand above its revenue |

A **Frequencies** table is not a result it draws: use a **Bar chart**
(**Show** `percent`) for a distribution.

**Checks before the run**, as you edit and at **Check**:

- An output it cannot draw is an error, `RESULT_NOT_DRAWABLE`: "A Result
  chart cannot draw the table output of Frequencies (f); it draws the results
  of Group means, Descriptive statistics, t-test, Paired tests, Proportion CI,
  Net Promoter Score, TURF, MaxDiff, Conjoint, Share of preference, Principal
  components, Factor analysis, Cluster (k-means), Regression, Correlation
  matrix, Code open answers, Key drivers, Perceptual map, Price sensitivity."
  A statistic alone that only says the weight and base: "The stat output of
  Regression (r) only tells a chart its weight and base; connect the output
  it draws, table, too."
- A **Kind** the result does not suit is an error, `RESULT_KIND`, naming what
  it does draw — and the output of the same analysis that draws the kind you
  chose: "Kind 'scree' does not suit the loadings output of Principal
  components (p), which draws 'loadings'; its variance output draws
  'scree'."
- Results of two analyses are a warning, `RESULT_SOURCES`: "The results
  connected come from m, t; a Result chart draws one of them — the table
  output of Group means (m)."

What only the data can tell fails the node, with the reason, when it runs.

**Titles, weight and labels.** The title's second line says how the result
used the weight — "weighted by 'weight'", or "unweighted (the weight 'weight'
is not applied)" for a t-test, a paired test, a factor analysis or a cluster
— under your own **Title** too. Axis labels say what is drawn ("Mean with its
95 % confidence interval", "Weighted mean with …", "Odds ratio with its 95 %
confidence interval (Wald), log scale"). Categories are rows, first at the
top; their labels wrap and stay whole, the font shrinks as rows multiply, and
a chart that still cannot hold them grows taller rather than cut them — only
a label past four lines is cut, and never so that two read alike. The title,
axis titles and notes wrap to the plot; values never leave it. Many series
each get a color of their own. A perceptual map whose labels would overlap
is drawn taller, and one too crowded even then numbers its points and lists
the numbered names under the legend.

### Scatter plot

`visualize.scatter` — two variables against each other, optionally colored by
a third, with a trend line.

**In:** `data` (SurveyData) → **Out:** `chart` (Chart)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **X** | variable | required | interval / ratio / ordinal variables | Horizontal axis. |
| **Y** | variable | required | interval / ratio / ordinal variables | Vertical axis. |
| **Color by** | variable | — | nominal / ordinal variables | Optional variable that colors the points. |
| **Trend line** | checkbox | on | — | Draw a fitted trend line. |
| **Title** | text | — | — | Chart title. |
| **Figure width (in)** | number | `10` | 2–30 | The figure itself, in inches — the axis labels scale with it. |
| **Figure height (in)** | number | `6` | 2–30 | — |
| **Palette** | choice | `muted` | `muted`, `deep`, `pastel`, `dark`, `colorblind`, `Set2`, `tab10`, `theme` | Theme takes the colors of the report the chart is saved in — the chart colors of its Save report's Look (by default eight colors any two of which readers with protanopia or deuteranopia can tell apart), with its text color, grid and font. The others are seaborn's palettes. |

Every respondent is one point and the trend line is fitted unweighted; on
weighted data the title's second line says "unweighted (the weight 'weight'
is not applied)".

### Trend

`visualize.trend` — "A measure over waves or dates — the percent choosing an
answer, a mean, or the count of respondents — with one line per group, its
confidence band and the base of every point, as a chart and as a table." The
chart of a tracking study: satisfaction month by month, awareness wave by
wave, completes per week.

**In:** `data` (SurveyData) → **Out:** `chart` (Chart), `table` (Table)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Time** | variable | required | any variable, or a response timestamp | A wave code (one point per wave, ordered by code, its labels on the axis) or a date — a date column, or text in ISO 8601 such as the responses' created_at (2026-05-25 09:00:00+00:00). Times with a zone are read in UTC. |
| **Period** | choice | `month` | `day`, `week`, `month`, `quarter`, `year` | How dates are grouped into points. A week is an ISO week, Monday to Sunday, labeled by its ISO year and number (2026-W22). Every period between the first and the last is on the axis, an empty one as a gap. Not used for a wave code. |
| **Measure** | choice | `percent` | `percent`, `mean`, `count` | percent: the share of those who answered that gave one of the Answer codes. mean: the mean of a numeric (or ordinal) variable. count: the number of respondents — the sum of weights when weighted. |
| **Measure variable** | variable | — | — | The question the percent or the mean is of. Its missing codes are left out of every base and counted. |
| **Answer codes** | answer code (several) | — | answers of **Measure variable** | The answer counted, or a list of them counted together (a top-2 box), e.g. [4, 5]. For a multiple-choice question, choosing any of them. |
| **Split by** | variable | — | nominal / ordinal variables | One line per group. Respondents with a missing code, or no answer, are in no line. |
| **Confidence band** | checkbox | on | — | The 95% interval of each point — a percent's Wilson score interval, as the Bar chart's intervals, or the mean's t interval, on Kish's effective base when weighted. A point with fewer respondents than Minimum base is drawn without it; the table gives its interval. |
| **Minimum base** | whole number | `30` | 1 or more | A percent or a mean of fewer respondents than this is drawn hollow and noted in the table. Not used for the count, which is its own base. |
| **Title** | text | — | — | Empty takes what is tracked ("Overall satisfaction: % Satisfied or Very satisfied", "Mean Trust: Acme", "Respondents"), with "by *Split by*". |
| **Figure width (in)** | number | `10` | 2–30 | The figure itself, in inches — the axis labels scale with it. |
| **Figure height (in)** | number | `6` | 2–30 | — |
| **Palette** | choice | `muted` | `muted`, `deep`, `pastel`, `dark`, `colorblind`, `Set2`, `tab10`, `theme` | Theme takes the colors of the report the chart is saved in — the chart colors of its Save report's Look (by default eight colors any two of which readers with protanopia or deuteranopia can tell apart; past four lines each line's points also take a shape of their own), with its text color, grid and font. The others are seaborn's palettes. |

The lists name each code under it: `percent` ("% choosing the Answer
codes"), `mean` ("mean of the Measure variable"), `count` ("respondents
(weighted: sum of weights)"), and **Period**'s `week` ("ISO week, Monday to
Sunday"). **Measure variable** is shown with
`percent` and `mean`, **Answer codes** with `percent`, **Confidence band**
and **Minimum base** with `percent` and `mean` — a count has no band and is
its own base. The card reads `satisfaction = 4, 5 over created_at`, `mean
trust_acme over wave` or `respondents over created_at`.

**Time.** The picker lists the codebook's variables — **Waves and dates**
first (labeled codes, ordinal variables, date columns, a Date question's
answers), then **Other variables** — and, under **Beside the answers**, the
timestamps the survey's responses carry: `created_at — Response date
(created_at)` (when the response came in — the usual choice), `updated_at —
Last change (updated_at)` and `started_at — Start time (started_at)`. The axis
names them by those labels ("Response date (month)"). It leaves out a
multiple-choice question, a ranking and an open answer (not a Date question's),
as **Split by** does; with **Measure** `mean`, **Measure variable** leaves out
nominal and multiple-choice questions. A variable already stored stays listed,
with the reason (`aware (several answers: not one wave or date)`). A variable with value labels, or
of numbers, is read as waves: a point per code, in the order of the codes,
each named by its label ("Spring 2026", "Summer 2026"); a wave the codebook
declares between the first and the last, with no data yet, is a gap. A column
of dates, or text most of which reads as ISO 8601 dates, is grouped by
**Period**: `day` (`2026-01-05`), `week` (the ISO week, `2026-W02`), `month`
(`Jan 2026`), `quarter` (`2026 Q1`) or `year`; a value that is not a date is
left out and counted under the chart. Every period from the first to the last
is on the axis, so a week without respondents is a gap in a percent or a
mean, and a 0 in a count.

**Answer codes** is a checklist of the **Measure variable**'s answers (its
missing codes are not offered): check one answer, or several to track them
together — `4` and `5` for a top-2 box. Without value labels it is a JSON box
(`[4, 5]`).

**Under the chart**, notes say what it shows: the base ("Base: 821
respondents who answered; 114 to 150 per point."), the gaps ("Gaps: no
respondents in 6 of 18 points."), the band ("Band: 95% confidence
interval.", "Bands: 95% confidence intervals."), the hollow points ("Hollow
points: fewer than 30 respondents, drawn without a band (the table gives
their intervals)."), the weight, the missing codes left out ("Left out as
missing: Trust: Acme: 194 (9 = Refused).") and the rows no line or point
could take ("Left out: 25 without Trust: Acme."). The band is drawn for up to
four lines; with more, "No bands: the 95% intervals of 5 lines would hide one
another; the table gives each point's.", and each line's points take a shape
of their own, which the legend shows too. Every line has a color of its own,
however many there are.

**The table output** gives the same points, for a report section or a
**Live tile**: **Period**, the **Split by** group, **Percent** (or **Mean**,
or **Count**), **Lower 95%** and **Upper 95%** (not for a count), **Base**
(respondents), on weighted data **Weighted base** and **Effective base**, and
**Note** ("base below 30", "no respondents", "their weights sum to 0").
Under it: **Measure** ("% choosing 4 = Satisfied, 5 = Very satisfied —
Overall satisfaction"), **Base**, **Time** ("created_at, by week — ISO weeks,
Monday to Sunday, labeled by ISO year and week number"), **Interval** ("95%
Wilson score interval, as the Bar chart draws a share's", "95% t interval of
the mean"), **Weight**, **Low base** ("6 of 18 points have fewer than 30
respondents (drawn hollow)") and **Missing codes left out**. The node's
preview shows the table under the picture. The Methods draft describes the
node in words: "the percentage of respondents who answered Overall
satisfaction choosing 4 (Satisfied) or 5 (Very satisfied) was tracked over the
date each response came in, by month, one line per group of Region, with its
95% confidence band (Wilson score intervals, on Kish's effective base when
weighted), points of fewer than 30 respondents drawn hollow and without a
band, missing codes left out". Over a wave variable — labeled codes, or
numbers without labels, a point per code — it says "was tracked wave by wave
(Wave)".

A percent's point is the share **Proportion CI** gives for the same
respondents, and its band Wilson's interval — the one the **Bar chart** draws
for a share. A mean's band is Student's t interval. After **Apply weight**
the percents, means and counts are weighted, the intervals use Kish's
effective base, the axis adds "(weighted)" ("% of respondents (weighted)",
"Mean (weighted)", "Respondents (weighted)"), the base note adds the
weighted total ("… who answered (weighted: 822.8); …") and the note
"Weighted by 'weight'; the bases count respondents." follows.

**Rules.** Errors, before the run: "Name the Measure variable whose answers
are counted.", "Name the Answer codes whose percent is tracked — one code, or
a list such as [4, 5]." (percent) and "Name the Measure variable whose mean
is tracked." (mean). What the questionnaire settles is refused before the run
too:

- "Region is nominal: its codes are names, not amounts, so their mean says
  nothing. Track the percent choosing an answer instead (Measure = percent)."
- "Brands heard of (unaided) holds multiple-choice answers (lists of codes),
  which have no mean. Track the percent choosing an answer instead (Measure =
  percent)."
- "Brands heard of (unaided) holds multiple-choice answers (lists of codes),
  and Time is one wave or one date per respondent: choose the wave's variable
  or a date."
- "Split by needs one answer per respondent, and Brands heard of (unaided)
  allows several: split by one of its options after Explode multiple choice,
  or choose another variable."
- "9 (Refused) is a missing code of Trust: Acme, not an answer: missing codes
  are left out of the base. Name an answer."

A timestamp Studio's responses do not carry is an unknown variable
(`submitted_at`: "time: "submitted_at" is neither in the codebook nor made by
this flow or a table it reads."). One the node reads from **Simulated
data**, which has none, is a warning: "time: "created_at" is a timestamp of
the survey's responses, and this node reads Simulated data: the run stops
unless that data has a column created_at. Read the Responses source, or
choose a column the data has." Below a **Data file** whose columns have been
read, a timestamp is known only if the file has that column (see
[The file's columns in the flow](#the-files-columns-in-the-flow)); otherwise
it is an error like any name the file lacks ("time: "created_at" is not a
column of assets/panel_wave2.csv, nor made by this flow."), and the Save
also gives the warning above, naming Data file. A file whose read columns
include the timestamp gets no warning, on the canvas or at Save; one not
read yet gets the warning at Save.

What only the data can tell stops the node when it runs, with the reason: a
code that is no answer ("Trust: Acme has no answer 7; its answers are 1 = No
trust, 2 = Low, 3 = Medium, 4 = High, 5 = Full."), a Time with no dates in it
("created_at holds no dates to draw a trend over."), and more than 500
points — a date range too long for its **Period** ("created_at spans 905
days: too many points for one chart. Choose a longer Period.") or a Time of
more than 500 different values ("… has 731 different values: not wave codes.
Time is a wave code or a date; for dates, the column must hold dates (ISO
8601 text such as 2026-05-25 is read as one).").

---

## Output

Where results leave the flow.

### Choice data for HB

`output.choice_data` — writes a MaxDiff's answers in the long format that R's
hierarchical-Bayes packages read.

**In:** `data` (SurveyData) → **Out:** none (writes files, a table or a tile)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **MaxDiff question** | text | required | — | The question's id or name. Its design is read from the questionnaire. |
| **File name** | file name | required | — | The name before a fixed `.csv`, in `outputs/`; a node added from the palette gets `<flow>_maxdiff_choices`. The dictionary and R script are written beside it. |

Three files, so that estimating individual-level utilities on your own machine
needs no rewriting: the choices (`<name>.csv`), a dictionary saying what every
column means (`<name>.dictionary.json`) and a script that runs the model and
writes the per-respondent estimates back (`<name>.hb.R`). The field's **ⓘ**
adds: "It has no weight column (the HB packages take none), so an applied
weight is not in it: weight the individual utilities when you aggregate
them." A run of the flow keeps all three under **Files**; **Run all** keeps
them only when the flow lists them among its outputs (as the example study's
`segments` flow does), and the line under the field says so: "Run all
doesn't keep these files: run this flow on its own to get them."

Why export rather than estimate here: hierarchical Bayes takes minutes of
MCMC, and a flow run has one CPU and a few minutes for everything. A cut-down
chain would be a worse answer under the same name. The tables **MaxDiff** and
**Conjoint** produce are aggregate estimates, which is a different — and
honestly labeled — thing.

### Conjoint data for HB

`output.conjoint_data` — the same for a choice-based conjoint: the choices in
long format, a column dictionary and an R script.

**In:** `data` (SurveyData) → **Out:** none (writes files, a table or a tile)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Conjoint question** | text | required | — | The question's id or name. Its attributes and design are read from the questionnaire. |
| **File name** | file name | required | — | The name before a fixed `.csv`, in `outputs/`; a node added from the palette gets `<flow>_conjoint_choices`. The dictionary and R script are written beside it. |

As for MaxDiff, the file has no weight column: weight the individual
part-worths when you aggregate them. **Run all** keeps the files only when the
flow lists them among its outputs; a run of the flow keeps them always.

### Export file

`output.export_file` — "Write the data as a file (format by extension:
.parquet .csv .xlsx .sav .dta) with its dictionary, as an R bundle (.R), or
the dictionary alone (.json)."

**In:** `data` (SurveyData) → **Out:** none (writes files, a table or a tile)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **File name** | file name | required | — | The file's name, in `outputs/`; a node added from the palette gets `<flow>_data`. **Format** under it picks the kind of file — its ending. |

**Format** offers **CSV (.csv)** (a new node's), **Excel (.xlsx)**, **SPSS
(.sav)**, **Stata (.dta)**, **Parquet (.parquet)**, **R bundle (.R)** and
**Codebook only (.json)**. There is no `.xls`: an `.xls` name would hold an
`.xlsx` workbook, which Excel warns about, so a typed `clean.xls` is answered
"Choose Excel (.xlsx): an .xls name would hold an .xlsx workbook, and Excel
warns about that." with **Use clean as Excel (.xlsx)**. What each format
writes, for **File name** `clean`:

| Format | Files |
|---|---|
| **CSV**, **Excel**, **Parquet** | the data (`clean.csv`, `clean.xlsx`, `clean.parquet`) and `clean.dictionary.json` |
| **SPSS**, **Stata** | the data with its labels inside (variable labels, value labels, declared missing values) and `clean.dictionary.json` |
| **R bundle (.R)** | `clean.csv`, `clean.dictionary.json` and `clean.R` |
| **Codebook only (.json)** | the data dictionary (codebook) alone, no data — an error when the data has no codebook |

**The R bundle.** `clean.R` reads `clean.csv` (as UTF-8) and its dictionary
(with the `jsonlite` package) into a data frame named `survey_data`: the
codebook's missing codes become `NA`, labeled codes become factors, and each
column's `label` attribute is the variable's label from the codebook (not the
question's text). A code the codebook has no
label for keeps a level of its own rather than turning into `NA`; a
multiple-choice column (codes joined by `;`) stays text, because a factor
holds one value per respondent; a text answer that reads `NA` stays an
answer. The script finds its two files beside itself, whether you run it with
`Rscript clean.R` or `source("path/to/clean.R")` from R.

An `.xlsx` keeps text as text: an open answer such as `=HYPERLINK(…)` is
written as the string it is, never as a formula Excel would run.

A run of the flow keeps the files: they appear in **Files** and as download
chips on the run's card. **Run all** keeps them only when the flow lists them
among its outputs (as the example study's `cleaning` flow lists its R bundle);
for a flow built on the canvas the line under the field says "Run all doesn't
keep these files: run this flow on its own to get them." Written after the
cleaning and weighting steps, the export carries the variables the flow made
(recodes, bands, factor scores, a weight column) with their labels.

### Live tile

`output.live_tile` — publishes whatever is connected to it — a number, a
table, a chart or a statistic — as a tile on the **Live** screen. See
[[Live Monitoring|Studio-Live-Monitoring]].

**In:** `input` (Any) → **Out:** none (writes files, a table or a tile)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Kind** | choice | `number` | `number`, `table`, `chart`, `stat`, `text` | How the tile shows the value: `number`, `table`, `chart`, `stat` or `text`. |
| **Label** | text | required | — | The tile's caption on the Live screen, shown in capitals; a statistic's symbol — a Greek letter on its own, with any index written onto it (the χ² of "χ² test", ηp²) — keeps its case. |
| **Show** | choice | `value` | `value`, `rows` | rows: the number of respondents in the data connected. |

- Tiles are published by every run of the flow (a manual run, a scheduled
  run of this flow, a live recompute). **Run all** and **Run to here** do not
  publish tiles, and do not clear them either: the Live screen shows the
  tiles of the flow's latest completed run. After a rename it goes on showing
  them until the flow runs under its new name.
- **Show** = `rows` is the usual way to show "respondents after cleaning":
  connect the SurveyData output of the last cleaning step.
- A **Trend** makes a tracking tile: its `chart` with **Kind** `chart`, or
  its `table` — the points with their intervals and bases — with **Kind**
  `table`. A chart whose **Palette** is `theme` is drawn on the tile in the
  look of the flow's **Save report**, as its report draws it.
- A **chart** tile carries the chart's picture and its interactive form: the
  **Live** tab and the public page draw it with a tooltip on every mark and a
  legend that hides and shows a series, whatever the flow's **Save report**
  says about **Interactive charts in HTML**; the public page shows a
  **Scatter plot**, or a **Box plot** with outliers or **Show points**, as
  its picture only. See [Interactive chart tiles](Studio-Live-Monitoring#interactive-chart-tiles).
- A tile's size on the Live screen is not set from the canvas; tiles appear at
  the standard size; on a phone a chart tile takes the whole row at its own
  height.

### Report section

`output.report_section` — collects tables, charts and statistics into one
section of a report, with a heading, introductory text, a caption per item
and a closing note. Without a heading it is a plain block of Markdown between
the sections around it. Usually edited in the flow's **Report** view — see
[[Reports|Studio-Reports]].

**In:** `items` (Table or Chart or Stat, several, optional) → **Out:** `report` (Report)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Heading** | text | — | — | Section title, on one line. Leave empty for a plain block of text between sections. |
| **Text** | Markdown | — | — | Introductory text (Markdown). |
| **Captions** | one caption per input | — | — | A caption for each connected table, chart or statistic. |
| **Size and placement** | size per input | — | — | Per item — a width (60%, 320px), an alignment, or a page break before it. The Markdown is unaffected. |
| **Note** | Markdown | — | — | A closing note (Markdown) — methods, source, base. |

- The order you connect items in is the order they appear.
- A statistic (a **Stat** output) is printed as one line —
  `Caption: key = value; …` — where its caption is the label before the
  values. It has no size or placement: under **Size and placement** its row
  reads "one line" ("A statistic is one line of the report: size and
  placement apply to tables and charts only").
- Size and placement reach the HTML only; the Markdown is unaffected.

### Save report

`output.save_report` — combines sections, in the order you connect them, into
one report and saves it: Markdown (the content, with each chart as a PNG
beside it named by the report — `report_fig_1.png`, `report_fig_2.png` for
`outputs/report.md`), by default an HTML twin (the look, stylesheet and
images inside the file), and on request the report's tables in an Excel
workbook. Two reports in one folder therefore never share a figure. A report produced by a run on the platform ends with a provenance
footer while **Settings → Reports → End every report with the provenance
footer** is on (the default).

**In:** `sections` (Report, several) → **Out:** `report` (Report)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Title** | text | required | — | The report's title. |
| **File name** | file name | `outputs/report.md` | — | The report's name before a fixed `.md`, in `outputs/`. A node the Report view creates, or one added from the palette, gets the flow's name (`outputs/<flow>.md`). |
| **Also save HTML** | checkbox | on | — | Also write the styled `.html` twin next to the Markdown. |
| **Interactive charts in HTML** | checkbox | off | — | The HTML draws its charts in the reader's browser — a tooltip on every bar, point and cell with its value and base, a legend whose entries hide and show their series, zoom where it helps — and still opens offline, so it can be sent to a client as it is. For that it carries the chart libraries (Vega, Vega-Lite and Vega-Embed, about 0.8 MB, written in once) and each chart's numbers — what it draws, and a scatter plot's points and a box plot's outliers, the respondents' values it plots. Each chart's picture stays in the HTML for printing and for readers without scripts; the Markdown and the Excel workbook are unchanged. Applies only with Also save HTML. |
| **Table of contents** | checkbox | off | — | Add a table of contents. |
| **Also save tables to Excel** | checkbox | off | — | Every table of the report in one workbook beside it, named as the report with `.xlsx` — a sheet per table, named by its caption or its section's heading, with its statistics under it, and a Contents sheet first. Banner tables keep their significance letters and Group means its post-hoc pairs on a sheet of their own; charts are left out. |
| **Look** | report look | — | — | Typefaces, measure, table style and page size of the rendered report, and the chart colors and font of every chart in it whose Palette is theme (in the Markdown's figures too). Its p_values says how the report writes a p-value — exact, as computed (the default); 0.01, one below 0.01 as < 0.01; or 0.001, one below 0.001 as < 0.001 — in its tables' cells and statistics lines, the Markdown as the HTML, the Excel workbook (a number format, so the cell keeps its number) and the charts' notes (< .01); the results and their exports keep the exact p. Otherwise the Markdown's text is unaffected. |

- **The Excel workbook** (`<name>.xlsx` beside `<name>.md`) is
  the report's tables as a spreadsheet: numbers stay numbers, and text stays
  text — an answer, label or caption that begins with `=` is never turned into
  a formula. Its first sheet, **Contents**, carries the report's title and one
  row per table (**Sheet**, **Section**, **Table**), each a link to its
  sheet; a table without a caption is named by what it is ("Group means:
  Age", "Perceptual map: Region × Overall satisfaction — rows (Region)").
  Sheet names are cut to Excel's 31 characters, lose `[ ] : * ? / \` and are
  made unique ("Satisfaction", "Satisfaction (2)"). Charts, text and
  statistics lines (a **Stat** in a section) are not in it. The report
  composer's **Also Excel** is the same box; see
  [Tables in Excel](Studio-Reports#tables-in-excel).

- **Interactive charts in HTML** (the Report view's box of the same name)
  makes the `.html` draw its charts in the reader's browser: a tooltip with
  each value and its base, a legend that hides and shows a series, zoom on a
  **Scatter plot**, a **Trend** of more than 24 periods and a **Perceptual
  map**, and a menu that saves a chart as PNG or SVG. Beside the Markdown,
  each figure's Vega-Lite spec is written next to its picture
  (`report_fig_3.png`, `report_fig_3.vl.json`); the `.md` and the Excel
  workbook keep the pictures. Unchecked (the default), the node writes
  exactly what it wrote before the option existed. With **Also save HTML**
  unchecked it does nothing, and **Check** and the node warn: "Interactive
  charts in HTML draws the charts of the HTML — turn on Also save HTML; the
  Markdown and the Excel workbook keep their pictures." What the file then
  carries — the chart libraries and each chart's numbers, a scatter plot's
  and a box plot's points included — is under
  [Interactive charts](Studio-Reports#interactive-charts).
- The **Look** parameter is edited in the **Look** tab of the Report view
  ([Reports](Studio-Reports#the-look-tab)). A node created by the Report view
  or added from the palette starts with the project's house style as its
  look, when the project has one. A node with no look renders with the
  engine's defaults — on the platform, in previews and in a research bundle
  alike; the house style is not applied to it behind the scenes.
- The **Look** also holds the report's **Chart colors** (the theme's
  `chart_palette`, `chart_sequential`, `chart_diverging`, `chart_text_color`,
  `chart_grid_color` and `chart_font`): every chart in the report whose
  **Palette** is `theme` (a **Heatmap**'s **Color map** `theme`) is drawn in
  them, in the `.md`'s figures as in the `.html`. A chart with a named palette
  keeps its own. What the engine refuses is named on the node as you type, in
  its words: "theme: chart_palette: 'purple' is not a hex color such as
  '#2a78d6'."; "theme: chart_palette: give between 2 and 12 colors, in the
  order the series take them; got 1."; "theme: chart_palette: '#2a78d6' is
  given twice; two series would look alike."; "theme: chart_palette:
  '#ffe8b2' on the charts' white background has a contrast of 1.2:1; a bar or
  a line in it needs at least 1.3:1 to be seen."; "theme: chart_diverging: the
  two ends are the same color, so the scale would not diverge."; "theme:
  chart_text_color: '#cccccc' on the charts' white background has a contrast
  of 1.6:1; text needs at least 4.5:1."; "theme: chart_font: a list of font
  names separated by commas, without ; { } < >." See
  [Chart colors](Studio-Reports#chart-colors).
- The **Look** also holds the report's **P values** (the theme's
  `p_values`: `exact`, the default, `0.01` or `0.001`), the one choice of the
  look besides the chart colors that reaches the Markdown: a p below the
  threshold is written as the bound — `< 0.01` in a table's p column, `p <
  0.01` in a statistics line, a number format in the Excel workbook, and a
  chart's note. The results, the tables the node receives and every export
  keep the exact p, and a **Proportion CI**'s `p`, the proportion, is never
  changed. It travels with the node, so the downloaded script writes
  `theme={"p_values": "0.01"}`. Any other value is named on the node: "theme:
  p_values: '0.05' is not one of exact, 0.01, 0.001." See
  [P values](Studio-Reports#p-values).
- The line under **File name** says where a run leaves the report ("After a
  run: Files → outputs/*flow*/*name*.md") and what is written beside it
  (`<name>.html` with **Also save HTML**, `<name>.xlsx` with **Also save
  tables to Excel**, and `<name>_fig_1.png`, "a picture per chart").
- Choose this node as the flow's **Report path** (Flow settings, with no node
  selected) if you want this report kept by **Run all** and in its combined
  report; the Report view does both for you when it creates the node. A node
  added from the palette sets no **Report path**, and its field says "Run all
  keeps a report only when it is the flow's Report path (in the Flow panel,
  with no node selected): run this flow on its own to get this one." How the
  **Report path** follows the node, and the warning for one that names no
  node's file: [The combined report](Studio-Flows#the-combined-report).
- There is no PDF output. A typed `.pdf` is answered under the field —
  "Reports are saved as Markdown and HTML — for a PDF, open the HTML and print
  it." — and so are `.html` ("The report is saved as Markdown (.md); Also save
  HTML puts an .html copy beside it."), `.docx` ("Reports are saved as
  Markdown and HTML — Word opens the .html copy.") and `.xlsx`. A path ending
  in `.pdf` saved earlier fails at the run; the field shows it under "Other
  location, kept as it was written", with a fix.

### Tab book (Excel)

`output.tabbook` — "Every chosen question crossed by a banner of segments —
one sheet each, with its bases, counts, percentages and the Banner table's
significance letters — in an Excel workbook with a contents page and notes."
The tab book an agency hands a client after fieldwork: the whole study by
the segments that matter, in one file.

**In:** `data` (SurveyData) → **Out:** `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Questions** | variables (several) | — | — | Empty is every nominal, ordinal and multiple-choice variable of the codebook, except the banner variables, the weight, the response metadata, open answers (an OpenText question, or words without answer labels — they would go into the workbook word for word) and rankings (every option would read 100 %); the Notes sheet says why each is left out. Named here, any question is tabulated as asked, and an interval or ratio one shows its mean. |
| **Banner** | variables (several) | required | nominal / ordinal variables | The columns are Total, then every code of each banner variable. Letters run across the whole banner, but columns are only compared inside their own variable. |
| **Percentages** | choice | `column` | `column`, `row`, `none` | column: of the column's respondents who answered. row: of the answer's respondents across each banner variable. none: counts only. |
| **Counts** | checkbox | on | — | The count of each cell (the sum of weights on weighted data). |
| **Significance letters** | checkbox | on | — | The Banner table's test — a two-sided z-test of column proportions within each banner variable, on the base of those who answered (Kish's effective base when weighted); a column below 30 is not tested. The letters sit in their own cells beside the column percentages, and are shown only with them. |
| **Level** | number | `0.05` | 0.001–0.2 | The letters' significance level. |
| **Multiple comparisons** | choice | `none` | `none`, `bonferroni` | `bonferroni` divides **Level** by the number of pairs of columns tested. |
| **Means** | checkbox | on | — | The mean and standard deviation of an interval or ratio question per column (not tested). |
| **File name** | file name | `outputs/tabbook.xlsx` | — | The workbook's name before a fixed `.xlsx`, in `outputs/`. A node added from the palette gets `<flow>_tabbook` (`outputs/<flow>_tabbook.xlsx`), numbered when the flow already has one. |

The **Percentages** list names each code under it: `column` ("of each
column's respondents"), `row` ("of each answer's respondents"), `none`
("counts only"). **Level** and
**Multiple comparisons** are shown only while **Significance letters** is
checked. The card reads the banner and the file: `gender, region →
outputs/tabbook.xlsx`.

**The workbook.**

| Sheet | What it holds |
|---|---|
| **Contents** (first) | "Tab book", a line such as "5 questions × Total, Gender, Region", then one row per question — **#**, **Question** (its label), **Variable**, **Base**, **Sheet** — each linked to its sheet; a link to the notes; and **Not tabulated**, each question left out with **Why** |
| one per question, named after its variable | the question's label; a line with its variable, scale and base ("trust_acme · ordinal · Base: respondents who answered", "· multiple answers" for a multiple-choice question); **← Contents**; the banner — **Total**, then each banner variable over its columns, each column lettered (`Male (A)`, `Female (B)`, `Other (C)`, `Capital (D)`, …); a **Base** row; per answer its count and, under it, its percentage with the letters in the cell beside it; for an interval or ratio question **Mean** and **Standard deviation**; footnotes ("Percentages are of the column's respondents who answered.", "Several answers were allowed, so the percentages add to more than 100%.", the letters' test, "Left out, as missing codes: Trust: Acme: 194 (9 = Refused).", "Means are not tested.") |
| **Notes** | **Created** (UTC), **Respondents**, **Weight**, **Banner** ("Total, Gender (A–C), Region (D–F)"), **Percentages**, **Counts**, **Base**, **Test**, **Alpha**, **Bonferroni**, **Minimum base for a test**, **Letters**, **Means**, **Missing codes left out**, **Not tabulated** |

On each question's sheet the rows down to the bases and the column of
answers are frozen, so they stay in view as you scroll. Numbers are numbers (percentages formatted as
percentages), and text stays text: a label or an answer that begins with `=`
is never turned into a formula. A sheet name is the variable's name cut to
Excel's 31 characters, made unique.

**What the numbers are.** The counts, column percentages and letters are the
**Banner table**'s, with two differences, both said on the Notes sheet: the
codebook's missing codes are left out — of the question (not in its base) and
of a banner variable (a respondent with a missing code for region is in
Total, not in a region column) — and a column's base, for its percentages and
its test, is its respondents **who answered the question** (the Banner table
tests on everyone in the column; the two agree when everyone answered). A
letter beside a cell names a column of the same banner variable whose
percentage this one's is significantly higher than. A multiple-choice
question is one table of every option, its base those who chose at least one.

**On weighted data** each sheet has **Base (unweighted)** (respondents) and
**Base (weighted)**; counts and bases are sums of weights shown to one
decimal, the percentages are of those sums, and the test uses Kish's
effective base ("Minimum base for a test: 30 respondents (Kish's effective
base)"). A footnote says "Weighted by 'weight'; the unweighted base is the
number of respondents."

**What is left out**, and why, on the Contents and Notes sheets and in the
statistic:

- with **Questions** empty, an open answer — "an open answer: code it first
  (Code open answers)" — and a ranking — "a ranking: every respondent orders
  every option, so each would be 100 % — derive its first choice (Derive) and
  tabulate that";
- always, a question nobody answered ("nobody answered it"), and one without
  answer labels holding more than 30 different answers ("… different answers
  and no answer labels — an open answer? Code it first (Code open answers) or
  band it (Bands)") — an interval or ratio question then shows only its mean
  and standard deviation, and is left out with **Means** off ("… turn on
  Means").

Interval and ratio variables are not taken by default; name them in
**Questions** for their means.

**The statistic** says what was written — **Workbook**, **Sheets written**,
**Questions skipped**, **Skipped** (each with its reason), **Banner**,
**Percentages**, **Test** ("two-sided z-test of column proportions at 0.05,
within each banner variable") and, on weighted data, **Weight**. A preview
runs the node and shows it, with "Not kept: a preview never keeps the files
nodes write. A run writes outputs/tabbook.xlsx." (the node's file). A run
keeps the workbook as `outputs/<flow>/<name>.xlsx`, as the line under **File
name** says: on the run's card, in **Files**, and on the
**Reports** screen as **Tab book** (see
[The Reports screen](Studio-Reports#the-reports-screen)). **Run all** keeps it
too. The Methods draft says what it holds: "every nominal, ordinal and
multiple-choice question (open answers and rankings left out) was
cross-tabulated by a banner of Gender and Region into a tab book in Excel
(`outputs/tabbook.xlsx`, a sheet per question with its bases, column
percentages and counts), with significance letters beside each column
percentage …".

**Rules.** Errors: a path that is not a workbook ("path: A tab book is an
Excel workbook: its path must end in .xlsx (got 'outputs/tabs.csv')."), a
banner variable with several answers ("Brands heard of (unaided) holds
multiple-choice answers, and a banner column is a group of respondents that
no one else is in. Explode it first (prepare.explode) and use its columns, or
choose another banner variable.") and "With Percentages none and Counts off
the tables would be empty — turn one of them on." Warnings: a path
outside `outputs/` ("path: 'tabs.xlsx' is not under outputs/, where a run
keeps what it writes."), "Significance letters compare column percentages,
so the sheets show them only with Percentages column; with row percentages or
counts only they are left out.", and a ranking or an open answer named in
**Questions** ("Free comment is an open answer: its answers would go into the
workbook word for word — code it first (Code open answers)."; "… is a
ranking: every respondent orders every option, so each option would read 100
% in every column — derive its first choice (Derive) and tabulate that.").
When it runs, a banner variable of more than 30 different values stops the
node: "Postcode has 212 different values: too many columns for a banner.
Band it first (prepare.bands) or choose a variable of a few groups."

The **File name** field keeps `outputs/` and `.xlsx` fixed, so the
not-a-workbook error and the outside-`outputs/` warning come only from a path
saved earlier, which the field shows as it was written, under "Other
location, kept as it was written", with a one-click fix. A typed `tabs.csv`
is answered under the field: "A tab book is an Excel workbook: it is saved as
.xlsx."

### Write table

`output.write_table` · platform — saves the data as a project table: a source
for other flows (**Project table**) and a table on the **Data** screen.

**In:** `data` (SurveyData) → **Out:** none (writes files, a table or a tile)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Table name** | text | required | — | Table name: lowercase letters, digits and `_`, starting with a letter or `_`, at most 63 characters. |
| **If it exists** | choice | `replace` | `fail`, `replace`, `append` | `replace` (drop and recreate), `append` (add rows) or `fail` (stop the run with "table already exists"). |

- The table keeps the variables of the columns it holds — labels, scales and
  value labels, including those of variables the flow created — so a flow
  that reads it gets them back (see [Project table](#project-table)). With
  `append`, the variables are merged with those the table already carries.
  Written from a **Data file**, it brings the file's columns to the flows that
  read it.
- The columns keep their names as they are — a Qualtrics export's `StartDate`
  and `Duration (in seconds)`, a header in Cyrillic, a name with `%` in it.
  A name longer than 63 bytes (a Cyrillic letter takes two) cannot be a table
  column, and neither can an empty one or two columns of one name: the node
  stops before anything is written, in a preview as in a run — "column name
  … is longer than 63 bytes, which a table column cannot be: rename it
  (Compute or Recode into a shorter name, then Select columns) before Write
  table", or "columns named twice: …".
- A preview (**Run to here**, **Preview all**) never writes the table. The
  node's Preview pane says what a run would do: "Not written: a preview never
  writes project tables. A run writes 812 rows to table 'clean_responses' (if
  it exists: replace)."
- In a research bundle, when the script is given a data file, this node is
  skipped: there is no project database outside Studio.

---

## What is deliberately absent

- **A Python or SQL node.** Every node is a documented engine call, which is
  what keeps the generated script honest and the sandbox safe. Need custom
  code? Download the `.py` and continue in your own environment.
- **Branches and loops.** A flow is a directed acyclic graph: it reads top to
  bottom, like the script it becomes. The canvas refuses a connection that
  would close a cycle.
- **A model anywhere inside a run.** Open answers are coded by **Code open
  answers**, which applies a codeframe's decisions by hand and its word rules
  — so a flow always produces the same numbers and never calls out to
  anything.
- **A PDF writer.** Reports are Markdown and HTML (with their tables in
  Excel on request); print or convert the HTML.

## See also

- [[Analysis Flows|Studio-Flows]]
- [[Cleaning and Weighting Data|Studio-Cleaning-and-Weighting]]
- [[Coding Open Answers|Studio-Open-Answer-Coding]]
- [[Reports|Studio-Reports]]
- [[MaxDiff and Conjoint|Studio-MaxDiff-and-Conjoint]]

<!-- studio-nav -->
---

← [[Analysis Flows|Studio-Flows]] · [Studio contents](Studio-Overview#all-pages) · [[Cleaning and Weighting Data|Studio-Cleaning-and-Weighting]] →
