# Files

**Project → Files** lists everything the project keeps in storage that is not
a document: the files you upload and the output files your flow runs produce.
This page covers uploading, downloading and deleting, the storage quota,
reading an uploaded data file in a flow, and what files cannot be used for.

---

## The Files screen

```
Files   assets · run outputs                                        [ Upload ]

A flow reads an upload by its path, assets/<name> — the File of a Data file
node. Download links are made when you click and expire after 5 minutes: they
are not addresses to paste into the survey's theme or text.

 Name                         Size       Updated
 panel_wave1.sav              1.2 MB     9/12/2026   [copy] [download] [delete]
   assets/panel_wave1.sav
 report.html                  212.4 KB   9/20/2026          [download] [delete]
   outputs/tables/report.html
 report_fig_1.png             31.0 KB    9/20/2026          [download] [delete]
   outputs/tables/report_fig_1.png
```

| Column | Shows |
|---|---|
| **Name** | the file name, with its stored path underneath (for example `assets/panel_wave1.sav` for an upload, `outputs/tables/report_fig_1.png` for a run output), and an icon for images (`.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`, `.webp`), reports (`.md`, `.html`) and other files |
| **Size** | the stored size |
| **Updated** | the date the file first appeared under that path (replacing a file keeps the original date) |

Each row has icon buttons:

| Button | Tooltip | What it does |
|---|---|---|
| Copy (uploads only) | "Copy the path a flow reads it by: assets/*name*" | copies `assets/<name>` to the clipboard ("Copied to clipboard"), ready to paste into a **Data file** node |
| Download | "Download (the link lasts 5 minutes)" | downloads the file ([below](#download-a-file)) |
| Delete | "Delete" | deletes the file after a confirmation ([below](#delete-a-file)) |

With no files the screen says **No files yet** — "Uploaded files (a data file
for a flow to read, a sample) and the outputs your flows produce show up
here." — with **Upload a file**.

Because the stored path is shown under each name, two files with the same name
from different flows (`outputs/tables/report_fig_1.png`,
`outputs/brand/report_fig_1.png`) can be told apart in the list.

## Upload a file

1. Click **Upload** (or **Upload a file** on an empty screen).
2. In **Upload file**, drag a file onto the box ("Drag & drop a file here, or
   click to browse") or click it to choose one. The box then shows the name and
   size.
3. Click **Upload**. You see "Uploaded *name*". The file is stored as
   `assets/<name>`, the path a flow reads it by.

Rules:

- **Any file type** is accepted, one file per upload, up to **50 MB**. Larger
  files are refused with "file exceeds the 50 MB upload limit"; empty files with
  "empty file".
- **Names are cleaned**: every character other than letters, digits, `.`, `_`
  and `-` becomes `_`, leading and trailing dots and underscores are removed,
  and the name is cut to 128 characters. `Logo final (v2).png` is stored as
  `Logo_final_v2_.png`.
- **The same name replaces the existing file** without asking. Rename the file
  on your computer first if you want to keep both.
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

An upload that would exceed it is refused with "plan '*plan*' allows up to *N*
MB of stored files; delete files or upgrade to add more". Replacing a file only
counts the difference in size. The quota is checked when you upload; flow runs
still store their outputs when you are over it.

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
  runs keep their own file lists in the run history);
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

## Analyzing a dataset collected elsewhere

Upload a data file here and a flow can read it: a panel file, an earlier wave,
a dataset from another tool.

1. Upload the file. It is stored as `assets/<name>` — the path shown under its
   name. Click the copy button on its row to copy that path.
2. In the flow, add a **Data file** node and paste the path into its **File**
   field (hint: "assets/<name> — a file uploaded under Files"). The node reads
   Parquet, CSV, Excel, SPSS and Stata files. If the file has a dictionary
   (`<name>.dictionary.json`), upload it too and name it in **Dictionary
   (JSON)**.
3. Click **Run to here** on the node to see the rows, or save and run the flow
   (or **Run all**).

A run, **Run all**, a scheduled run and **Run to here** / **Preview all** copy
the uploads their flows name into the run before it starts — only those, not
every file under Files. If one cannot be copied, the run's log says why:

| Log line | Meaning |
|---|---|
| "note: assets/*name* is not among this project's Files" | nothing is uploaded under that name — check the spelling, or upload it |
| "note: assets/*name* is listed under Files but its content is gone" | the stored file is missing; upload it again |
| "note: uploads cannot be read (*reason*)" | storage is not reachable just now; try again later |

The **Data file** node that reads a missing file then fails with the path it
looked for. Replacing an upload (same name) takes effect on the next run;
deleting it makes the next run fail. The node itself is described in
[Data file](Studio-Node-Reference#data-file).

A research bundle downloaded **With the responses so far** brings the uploads
its flows name, at the same `assets/<name>` path, so the scripts find them
there too; a bundle without data leaves them out, and its README says where to
put them. See [[Reproducibility|Studio-Reproducibility]].

> **Tip.** Another way in is to import the data into a project table with a
> connector — **Supabase (Postgres)** *(Plus)* or **Your database (Postgres)**
> *(Pro)* in the ← import direction — and read it with a **Project table**
> node. Imported columns arrive as text. See
> [Importing a table](Studio-Connectors#importing-a-table).

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
