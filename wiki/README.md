# Wiki source

This folder is the **source of truth** for the project's GitHub Wiki. The wiki
itself lives in a separate git repository (`https://github.com/hanelias/siamang.wiki.git`);
these files are authored here (so they are reviewable in pull requests) and then
**published** to that wiki repository.

The wiki covers **three products** in one place:

- **Library** — the `siamang` Python package (pages without a prefix).
- **Cloud Platform** — the `siamang_cloud` platform (pages prefixed `Cloud-`).
- **Siamang Studio** — the visual survey platform (pages prefixed `Studio-`).
  Studio's in-app **Documentation** link opens this wiki, so `Studio-Overview`
  is the entry point Studio users arrive at from `Home`.

## Conventions

- One Markdown file per page. The filename becomes the page title with dashes
  rendered as spaces (`Question-Types.md` → "Question Types").
- `Home.md` is the landing page; `_Sidebar.md` is the navigation; `_Footer.md`
  is the footer shown on every page.
- Link between pages with wiki links: `[[Display text|Target-Page]]`
  (e.g. `[[Question Types|Question-Types]]`). All links are internal — the
  Library, Cloud and Studio sections live in the **same** wiki.
- Cloud pages use the `Cloud-` filename prefix and Studio pages the `Studio-`
  prefix, to keep the sections visually separate and avoid name clashes with
  Library pages (`Question-Types` vs `Studio-Question-Types`).
- Studio pages are end-user documentation: exact UI labels in **bold**, plan
  requirements as *(Plus)* / *(Pro)*, and no repository paths. A link to a
  section of another page uses a plain Markdown link with the heading's anchor,
  e.g. `[Publishing](Studio-Publishing-and-Environments#publishing)`.
- The Studio pages end with generated *Previous / Next* navigation in sidebar
  order; keep that line when you edit a page.

## Publishing

```bash
bash wiki/sync.sh
```

The script clones the wiki repository, copies every `*.md` page from this folder
(excluding this `README.md` and `sync.sh`), commits, and pushes.

**Prerequisite:** the wiki must be enabled and initialized. If `git clone` of the
`.wiki.git` fails with "not found", open the repository's **Settings → Features →
Wikis**, ensure Wikis are enabled, then create the first page (Home) once via the
GitHub UI. After that the wiki git repo exists and `sync.sh` can push to it.

To target a different wiki remote, set `WIKI_REMOTE`:

```bash
WIKI_REMOTE=https://github.com/<owner>/<repo>.wiki.git bash wiki/sync.sh
```
