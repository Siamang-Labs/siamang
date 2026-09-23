# Files

**Project → Files** lists everything the project keeps in storage that is not
a document: the files you upload and the output files your flow runs produce.
This page covers uploading, downloading and deleting, the storage quota, and
what files can and cannot be used for in the current build.

---

## The Files screen

```
Files   assets · run outputs                                        [ Upload ]

 Name                     Size       Updated
 logo.png                 48.2 KB    9/12/2026     [Download] [Delete]
 report.html              212.4 KB   9/20/2026     [Download] [Delete]
 fig_1.png                31.0 KB    9/20/2026     [Download] [Delete]
```

| Column | Shows |
|---|---|
| **Name** | the file name (without its folder), with an icon for images (`.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`, `.webp`), reports (`.md`, `.html`) and other files |
| **Size** | the stored size |
| **Updated** | the date the file first appeared under that name (replacing a file keeps the original date) |

Each row has **Download** and **Delete**. With no files the screen says **No
files yet** — "Uploaded assets (a logo for the survey theme, a sample file) and
outputs your flows produce show up here." — with **Upload a file**.

Two files with the same name from different flows look alike in the list,
because only the name is shown; download them to tell them apart.

## Upload a file

1. Click **Upload** (or **Upload a file** on an empty screen).
2. In **Upload file**, drag a file onto the box ("Drag & drop a file here, or
   click to browse") or click it to choose one. The box then shows the name and
   size.
3. Click **Upload**. You see "Uploaded *name*".

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
- **Run all** also stores its combined report under `reports/`;
- each run stores at most **50 files** and **200 MB**; files beyond that are
  skipped.

Reports also appear on the **Reports** tab. See [[Analysis Flows|Studio-Flows]]
and [[Reports|Studio-Reports]].

---

## What Files is — and is not — for

Files is where you keep and download material. Two things people expect from
it do not work in the current build.

### Logos and question media

> **Current limitation.** Files has no permanent public link. The only link it
> gives is the 5-minute download link, so a logo or image pasted from Files
> stops showing within minutes.

For the survey's **Logo URL** (Builder → **Theme**, or your organization's house
style) and for question media, use a **stable public URL** — for example an
image on your institution's website or another public host. The Theme tab's
hint "upload under Files and paste the link" does not give you such a link.
See [[Theme and Branding|Studio-Theme-and-Branding]].

### Analyzing a dataset collected elsewhere

> **Current limitation.** Files you upload here are not available to flow runs,
> so a flow's **Data file** node cannot read them.

To analyze external data today:

- **Run the flow on your own machine.** Download the flow's script (the `.py`
  or a research bundle — see
  [[Reproducibility|Studio-Reproducibility]]), put the data file beside it and
  run it with the `siamang` package; or
- **Import the data into a project table** with a connector — **Supabase
  (Postgres)** *(Plus)* or **Your database (Postgres)** *(Pro)* in the ← import
  direction — and read that table in a flow with a **Project table** node.
  Imported columns arrive as text. See
  [Import](Studio-Connectors#importing-a-table).

## See also

- [[Analysis Flows|Studio-Flows]]
- [[Reports|Studio-Reports]]
- [[Connectors|Studio-Connectors]]
- [[Theme and Branding|Studio-Theme-and-Branding]]
- [[Limits and Quotas at a Glance|Studio-Limits-Reference]]
