# Files

**Project → Files** lists everything the project keeps in storage that is not
a document: the files you upload and the output files your flow runs produce.
It also lists the project's **codeframes** — documents, but where you would
look for them — and opens them in the codeframe editor. This page covers
uploading, what Studio reads from a data file you upload, downloading and
deleting, the storage quota, reading an uploaded data file in a flow,
codeframes, and what files cannot be used for.

---

## The Files screen

```
Files   assets · run outputs                                        [ Upload ]

A Data file node in a flow reads an upload by its name. Upload here or from the node.
Each data file is read after upload: its rows and columns, and any columns that
look like personal data, show below.
Download links last 5 minutes. Don't paste them into the survey.

Codeframes  analysis/*.codeframe.json · coding open answers by hand and by rules
                                                          [ + New codeframe… ]
 Codeframe                      Codes      Themes   Updated
 why                            why        4        Sep 21, 2026        edit
   analysis/why.codeframe.json

Uploads and run outputs
 Name                         Size       Updated
 panel_wave2.csv              84.6 KB    Sep 28, 2026   [copy] [download] [delete]
   assets/panel_wave2.csv
   1,200 rows × 24 columns · possible missing codes in 3 columns
   ● Looks like personal data ⓘ
 report.html                  212.4 KB   Sep 20, 2026          [download] [delete]
   outputs/tables/report.html
 report_fig_1.png             31.0 KB    Sep 20, 2026          [download] [delete]
   outputs/tables/report_fig_1.png
 household_survey.xlsx        1.2 MB     Sep 12, 2026   [copy] [download] [delete]
   assets/household_survey.xlsx
   160 rows × 16 columns
```

The **Codeframes** section is described [below](#codeframes). Under
**Uploads and run outputs**:

| Column | Shows |
|---|---|
| **Name** | the file name, with its stored path underneath (for example `assets/panel_wave2.csv` for an upload, `outputs/tables/report_fig_1.png` for a run output), and an icon for images (`.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`, `.webp`), reports (`.md`, `.html`) and other files. Under an upload a **Data file** node can read, what Studio read from it, and a **Looks like personal data** mark when some of its columns look like personal data (see [What Studio reads from a data file](#what-studio-reads-from-a-data-file)). On a phone, the size and date show under the name instead of in their own columns |
| **Size** | the stored size |
| **Updated** | the date the file's content last changed. For an upload, uploading new content under the same name changes it, uploading the same content again does not. For a run output, a run that writes the file with new content changes it, and a run that writes the same content again does not |

The list is newest first by **Updated**, so an output that a run has just
rewritten with new content moves to the top.

Each row has icon buttons:

| Button | Tooltip | What it does |
|---|---|---|
| Copy (uploads only) | "Copy the path a flow reads it by: assets/*name*" | copies `assets/<name>`, the path a flow stores for the upload, to the clipboard ("Copied to clipboard"). A **Data file** node lists the uploads by name, so you need the path only in your own code |
| Download | "Download (the link lasts 5 minutes)" | downloads the file ([below](#download-a-file)) |
| Delete | "Delete" | deletes the file after a confirmation ([below](#delete-a-file)) |

With no files the section says **No files yet** — "Uploaded files (a data
file for a flow to read, a sample) and the outputs your flows produce show up
here." — with **Upload a file**.

Because the stored path is shown under each name, two files with the same name
from different flows (`outputs/tables/report_fig_1.png`,
`outputs/brand/report_fig_1.png`) can be told apart in the list.

## Upload a file

1. Click **Upload** (or **Upload a file** on an empty screen).
2. In **Upload file**, drag a file onto the box ("Drag & drop a file here, or
   click to browse") or click it to choose one. The box then shows the name and
   size. Above the box the dialog says which files a **Data file** node reads:
   "A Data file reads CSV and other text tables (.csv, .tsv, .txt; any
   encoding; separated by commas, semicolons, tabs or vertical bars), Excel
   (.xlsx, .xlsm, .xls), SPSS (.sav), Stata (.dta) and Parquet files, up to
   50 MB."
3. Before you upload, the dialog says the name Files will store the file
   under when that is not the name it has (see below), and anything else worth
   knowing about this file.
4. Click **Upload**. You see "Uploaded *name*", with the stored name. The file
   is stored as `assets/<name>`, and a **Data file** node lists it under that
   name.

You can also upload from a **Data file** node: **Upload…** under its **File**
list opens the dialog as **Upload a data file** (or **Upload a dictionary**
under **Dictionary (JSON)**). There it takes only what the field can use — a
file of another kind, even one dragged onto the box, is refused and
**Upload** stays off — and once the file is stored, the node chooses it. See
[Where files go](Studio-Node-Reference#where-files-go).

Rules:

- **Any file type** is accepted here, one file per upload, up to **50 MB**. A
  larger file is refused in the dialog before it is sent — "*name* is 52.0 MB;
  Files takes up to 50 MB. Save it as Parquet, or split it." for a data file
  — and an empty one with "empty file".
- **A file a flow cannot read as data** — a picture for a report, a PDF, a
  codebook — is uploaded and kept like any other, and the dialog says so
  quietly: "A flow can't read logo.png as data; it's kept in Files."
- **A workbook over 20 MB** gets a warning: "A workbook this large reads
  slowly: saved as CSV or Parquet it reads in a fraction of the time."
- **Names are cleaned.** Cyrillic letters (Russian and Ukrainian) are spelled
  in Latin and accents are dropped (`café.csv` → `cafe.csv`). No other letters
  are spelled in Latin: other Cyrillic letters (Serbian `ђ`, Kazakh `қ`,
  Belarusian `ў`), Greek letters, and letters such as `ß`, `æ`, `ø` and `ł`
  are left to the next step. Then every run of characters other than Latin
  letters (A–Z, a–z), digits, `.`, `_` and `-` becomes `_`, leading and
  trailing dots and underscores are removed, and the name is cut to 128
  characters, **keeping its extension**: `Logo final (v2).png` is stored as
  `Logo_final_v2_.png`, `Волна 2.csv` as `Volna_2.csv`, `Straße.csv` as
  `Stra_e.csv`. A name with nothing left in Latin letters, such as one in
  Chinese or Greek, is stored as `upload_<8 characters>.<extension>` — the
  same for the same name. A browser sends a double quote in a file name as
  `%22`, so `Survey "A".csv` is stored as `Survey_22A_22.csv`.
- **The dialog says the stored name** in one sentence that says what happened
  to this name, such as "It will be saved in Files as Volna_2.csv: Cyrillic
  letters are spelled in Latin and spaces become _.", "It will be saved in
  Files as Stra_e.csv: letters Studio can't spell in Latin become _." or
  "Studio can't spell this name in Latin letters, so it will be saved in
  Files as upload_431a963b.csv." A name with nothing to keep, such as `...`,
  is refused ("Nothing of this name can be kept: …"), and so is a name with
  `..` in it ("A flow can never read a file whose name has “..” in it. …"):
  no run would ever bring such a file in.
- **The same name replaces the existing file.** The dialog warns first:
  "Files already has *name*: this upload replaces it, and every flow that
  reads it reads the new file from its next run." Rename the file on your
  computer first if you want to keep both.
- **A data file is read at once** — see
  [What Studio reads from a data file](#what-studio-reads-from-a-data-file).
- Uploading and deleting need the member role or higher; any member can list
  and download.

## Storage quota

Stored files count against a per-organization quota — the total of **all files
in all projects of the organization, including run outputs**:

| Plan | Storage |
|---|---|
| Free | 250 MB |
| Plus | 5 GB |
| Pro | 50 GB |
| Corporate | unlimited |

An upload that would exceed it is refused with "the *Plan* plan allows up to
*N* MB of stored files; delete files or upgrade to add more". Replacing a file
only counts the difference in size. The quota is checked when you upload; flow
runs still store their outputs when you are over it.

## Download a file

**Download** fetches the file through a temporary link that is valid for **5
minutes** and always downloads (the browser does not open it in a tab). You see
"Downloaded *name*".

## Delete a file

**Delete** asks for confirmation:

> **Delete file** — Delete *name* from this project's files.
> Permanent — there is no trash. Anything that reads this path (a flow's Data
> file node, a report figure) will fail on its next run.

Click **Delete**; you see "Deleted *name*". Deleted run outputs come back the
next time their flow runs.

## Run outputs

Every file a flow run produces — reports, charts, tables — is stored and listed
here:

- a flow's outputs are kept under `outputs/<flow>/<file>` and **replaced every
  time that flow runs**, so Files always holds the latest run's version (earlier
  runs keep their own file lists in the run history); its **Updated** date
  moves only when the run changed its content;
- **Run all** stores each flow's report (the `.md`, its `.html` and the
  figures it shows) under `outputs/<flow>/` as soon as that flow finishes, as a
  run of that flow alone would, and then its combined report, by default
  `reports/report.md` (set under
  [Settings → Reports](Studio-Project-Settings#reports)). When a flow fails,
  the reports of the flows that succeeded are still stored, and the combined
  report is written from them under the title "Combined report (incomplete)",
  opening with a section "Missing from this report" that names each flow left
  out and why (see [The combined report](Studio-Flows#the-combined-report));
- each run stores at most **50 files** and **200 MB**; files beyond that are
  skipped. When a run produces more, the report documents (`.md`, `.html`)
  are kept ahead of figures and other files, so a flow that draws many charts
  still stores its report.

Reports also appear on the **Reports** tab. See [[Analysis Flows|Studio-Flows]]
and [[Reports|Studio-Reports]].

---

## What Studio reads from a data file

When you upload a file a **Data file** node can read (`.csv`, `.tsv`, `.txt`,
`.xlsx`, `.xlsm`, `.xls`, `.sav`, `.dta`, `.parquet`), the engine reads it at
once, in the same isolated sandbox flows run in, the way a **Data file** node
reads it with its default options. Studio keeps what it found with the
upload — **never an answer**, only what describes the file: its rows and
columns, how it was read (format, encoding, delimiter, sheet, header rows),
and for each column its name, label, type, scale, value labels, declared
missing codes, the codes that look like missing codes, and whether it looks
like personal data. A file of more than 50,000 rows is described from its
first 50,000 (the row count then ends in `+`).

Under the file's name, the row then says:

- "*rows* rows × *columns* columns", and "· possible missing codes in *n*
  columns" when some columns hold codes that look like missing codes: negative
  codes such as -1 to -9, -97 to -99 or -997 to -999 in a column whose other
  values are not negative, or 97, 98, 99, 997 … far above a column's other
  codes. A column of real negative amounts, such as a balance, is not
  flagged. Until you declare them (the node's **Missing codes**, or
  **Mark them as missing in these columns** in its
  [Columns panel](Studio-Node-Reference#the-columns-panel)), such codes count
  as answers: they show in frequencies and change a mean.
- **Looks like personal data**, a short warning mark, when some columns'
  names (in English or Russian) or values look like an email or IP address, a
  location, a name, a phone number, an address or a participant ID (Prolific,
  MTurk). Its **ⓘ** (point at it or click it; `Esc` closes it) names those
  columns, each with its kind — "`email` (e-mail)" — then, in a paragraph of
  its own, "Leave these out early, in one of two ways:", followed by a list:
  "in a flow: the Data file node can add a Select columns node without them"
  and "here in Files: delete the file and upload it without them". A screen
  reader reads the same words as the **ⓘ** button's description. It is a
  hint, never a drop: nothing is removed until you act (see
  [Data files you upload](Studio-Security-and-Privacy#data-files-you-upload)).
- "Reading its columns…" while the file is being read. The screen asks again
  every few seconds until it can say what the file holds. A reading that has
  not answered in five minutes is dropped from the row; a **Data file** node
  that reads the file asks for it again.
- "A Data file node cannot read it as it is: …" with the reason, when the
  file cannot be read with the default options. The node's **Reading
  options** may still read it (see
  [Data file](Studio-Node-Reference#data-file)).

Uploading new content under the same name reads the file again. A **Data
file** node that reads the file with other options — a sheet, a delimiter,
missing codes, a dictionary — has it read that way too, and keeps that
reading beside the default one; it shows in the node, not on this screen.

## Analyzing a dataset collected elsewhere

Upload a data file here and a flow can read it: a panel file, an earlier wave,
a national survey, a dataset from another tool. Uploading a file never adds
rows to the `responses` table.

1. Upload the file — here, or from the node in step 2. A CSV can come as
   Excel saves it with any regional settings: `;` between the fields, a
   decimal comma, Windows-1251 or UTF-16 ("Unicode text"). If the file has a
   dictionary (`<name>.dictionary.json`), upload it too.
2. In the flow, add a **Data file** node and choose the file by name in its
   **File** list, such as `panel_wave2.csv`. Each upload in the list has its
   size and upload date under its name (for a data file **Files** has read,
   its rows × columns first), and a long name wraps; the note under the
   field gives the chosen file's rows × columns, size and upload date. If
   you uploaded its dictionary, **Dictionary (JSON)** offers it: click
   **Use panel_wave2.dictionary.json**.
3. Check the node's **Columns** panel: how the file was read, where its labels
   and scales come from, and its columns. If a title was read as the names or
   the wrong sheet was read, set the option it names under **Reading
   options**.
4. If the panel finds codes that look like missing codes, click **Mark them as
   missing in these columns**, and add a **Missing values** node below to turn
   them into blanks. If it shows **Looks like personal data** (its **ⓘ**
   names the columns), click **Add a Select columns node without them** beside
   it.
5. Add your analyses below. Their pickers list the file's columns under the
   heading "From panel_wave2.csv", each column's label and scale under its
   name; a list of more than ten has a filter box ("Filter variables…"). The
   questionnaire's variables are offered too only when the file is this
   survey's data.
6. Click **Run to here** on a node to see its result, or save and run the
   flow (or **Run all**).

The node, its options and the panel are described in
[Data file](Studio-Node-Reference#data-file). Data collected in Qualtrics has
a route of its own that keeps the survey's codes and labels: see
[Bringing in Qualtrics data](Studio-Importing-Questionnaires#bringing-in-qualtrics-data).

A run, **Run all**, a scheduled run and **Run to here** / **Preview all** copy
the uploads their flows name into the run before it starts — only those, not
every file under Files. If one cannot be copied, the run's log says why:

| Log line | Meaning |
|---|---|
| "note: assets/*name* is not among this project's Files" | nothing is uploaded under that name — check the spelling, or upload it |
| "note: assets/*name* is listed under Files but its content is gone" | the stored file is missing; upload it again |
| "note: uploads cannot be read (*reason*)" | storage is not reachable just now; try again later |

When it copies an upload, the log says which version it read: "read
assets/panel_wave2.csv (sha256 …)", the start of the content's hash, so two
runs over a replaced upload can be told apart (see
[Which upload a run read](Studio-Reproducibility#which-upload-a-run-read)).

The **Data file** node that reads a missing file then fails with the path it
looked for. Replacing an upload (same name) takes effect on the next run;
deleting it makes the next run fail.

A research bundle downloaded **With the responses so far** brings the uploads
its flows name, at the same `assets/<name>` path, so the scripts find them
there too; a bundle without data leaves them out, and its README says where to
put them. See [[Reproducibility|Studio-Reproducibility]].

> **Tip.** Another way in is to import the data into a project table with a
> connector — **Supabase (Postgres)** *(Plus)* or **Your database (Postgres)**
> *(Pro)* in the ← import direction — and read it with a **Project table**
> node. Imported columns arrive as text. See
> [Importing a table](Studio-Connectors#importing-a-table).

## Codeframes

The **Codeframes** section ("analysis/*.codeframe.json · coding open answers
by hand and by rules") lists the project's codeframes: the coding schemes of
its open questions, which a flow's **Code open answers** node applies. They
are documents of the project, not uploads — each change is saved with a
**Save** and shows in **History** — but this is where you would look for
them.

| Column | Shows |
|---|---|
| **Codeframe** | its name, with its path underneath (`analysis/<name>.codeframe.json`) |
| **Codes** | the open-text variable it codes |
| **Themes** | how many themes it has |
| **Updated** | when it was last saved |

- **edit** on a row opens the codeframe in the codeframe editor; **Back to
  Files** returns here.
- **New codeframe…** starts one: it asks for the open-text variable and a
  name, and opens the editor. The new codeframe is listed here once you have
  saved it.
- With none: "No codeframe yet. A Code open answers node in a flow applies
  one; start it here or from the node."
- A viewer can open and read a codeframe; **New codeframe…** is disabled for
  them ("Your role in this project lets you read codeframes, not start one").
- There is no **Delete** for a codeframe; one that no node names does nothing.

See [[Coding Open Answers|Studio-Open-Answer-Coding]].

## What Files is not for

### Logos and question media

> **Current limitation.** Files has no permanent public link. The only link it
> gives is the 5-minute download link, so a logo or image pasted from Files
> stops showing within minutes.

For the survey's **Logo URL** (Builder → **Theme**, or your organization's house
style) and for a question's **Media URL**, use a **stable public URL** — for
example an image on your institution's website or another public host. The
hints say so: **Logo URL** — "a public https:// address of the image — a file
under Files has no public link" (in the house style: "… a file under a
project's Files has no public link"); **Media URL** (a question's
**Advanced** section) — "image / video shown with the question — a public
https:// address; a file under Files has no public link".
See [[Theme and Branding|Studio-Theme-and-Branding]].

## See also

- [[Analysis Flows|Studio-Flows]]
- [[Reports|Studio-Reports]]
- [[Connectors|Studio-Connectors]]
- [[Theme and Branding|Studio-Theme-and-Branding]]
- [[Limits and Quotas at a Glance|Studio-Limits-Reference]]

<!-- studio-nav -->
---

← [[Reproducibility: Code, Bundles and Citation|Studio-Reproducibility]] · [Studio contents](Studio-Overview#all-pages) · [[Connectors|Studio-Connectors]] →
