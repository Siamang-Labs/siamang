# Links, QR Codes, Embeds and Access Control

Once an environment is live, you hand out its link — directly, as a QR code,
embedded in your own web page, tagged with URL parameters — and decide who may
answer: anyone with the link, holders of an access code, or only real people
(captcha). Everything on this page lives in the chips of an environment card on
**Distribute**. Panel providers and email invitations have their own pages:
[[Panel Providers|Studio-Panel-Providers]] and
[[Email Invitations|Studio-Email-Invitations]].

---

## The survey link

Each environment has one permanent link:

```
https://study.siamang.org/3f9a1c07b2de/
```

- The 12-character code is the environment's **survey id**. It is unguessable,
  it never changes when you republish or reopen the environment, and it is the
  value of the `survey_id` column of every response the environment collects —
  the easiest way to tell `pilot` from `main` in your data.
- **Copy** next to the link on the card copies it.
- After **Close**, the same link shows "This survey is closed — The researchers
  have stopped collecting responses."
- Surveys published before the switch to survey-id links may also answer on an
  older `…/<organization>/<project>/<environment>/` address; those links keep
  working.
- A preview deployment has a different, temporary address and never collects —
  do not hand it to respondents.

Respondents need no account. The survey host is separate from the Studio app
and shares no cookies or session with it.

---

## QR code

**QR** opens a panel with the code and the text "Points at the survey link.
Print it on flyers, posters or slides — the code stays valid while the
environment is published."

- **SVG** — vector, for print and slides.
- **PNG** — raster, for documents and social media.

Files are named `<environment>-qr.svg` / `.png`. The code encodes the
environment link, so it stays valid across republishes; after **Close** it
leads to the closed page. If the code cannot be drawn you see "Could not draw
the QR code" with **Retry**.

---

## Embedding the survey

**Embed** gives two snippets, each with a **copy** link:

**Inline frame** — a plain iframe, 720 pixels high:

```html
<iframe src="https://study.siamang.org/3f9a1c07b2de/" title="Survey"
  style="width:100%;height:720px;border:0" allow="clipboard-write"></iframe>
```

Change `height` to suit your page.

**Script (auto-height)** — a placeholder plus a small loader script that turns
it into an iframe:

```html
<div data-siamang-survey="https://study.siamang.org/3f9a1c07b2de/"></div>
<script async src="https://<studio api>/embed.js"></script>
```

Copy the snippet from the panel — it contains the correct script address.
Optional attributes on the `div`:

| Attribute | Effect |
|---|---|
| `data-height` | minimum height of the frame, e.g. `data-height="900px"` (default `720px`) |
| `data-title` | the frame's accessible title (default `Survey`) |

Several placeholders on one page each get their own frame.

> **Current limitation.** Despite its label, the script embed does not yet
> resize itself to the survey's content: it gives a frame at least 720 pixels
> high (or your `data-height`). Choose a height that fits your longest page, or
> link to the survey instead of embedding it.

Surveys may be embedded on any website.

---

## URL parameters

Anything you append to the link is recorded with the response:

```
https://study.siamang.org/3f9a1c07b2de/?source=newsletter&wave=2
```

Use parameters to tag channels (newsletter, social, QR on a poster) or to
carry an id from another system — without touching the questionnaire.

| Rule | Detail |
|---|---|
| How many | the first **8** parameters of the link; further ones are ignored |
| Names | lower-cased; characters other than `a–z`, `0–9` and `_` become `_`; at most **40** characters. `?Source=News` is stored as `url_source` |
| Values | at most **200** characters |
| When | read once, when the page opens |
| Stored as | `url_<name>` in the response's `meta` (e.g. `url_source`, `url_wave`) |

Where you find them:

- **Data** tab: inside the `meta` column of the `responses` table (searchable
  with the grid's filter).
- **Flows**: as ordinary columns `url_source`, `url_wave`, … of the responses
  data, ready for filtering, crosstabs and joins.
- **Not** in the files you export from the Data tab — exports leave `meta` out
  (see [[Data Exports|Studio-Data-Exports]]). To export them, use a flow with an
  **Export file** node.

Two parameters are used by Studio itself: `inv` carries an email invitation's
personal token ([[Email Invitations|Studio-Email-Invitations]]), and a panel
provider's respondent id arrives the same way
([[Panel Providers|Studio-Panel-Providers]]). Both count toward the 8.

---

## Access codes

Access codes restrict a survey to people you gave a code to. The survey shows
a gate before the first question:

```
Access required
Please enter the access code to begin this survey.
[ Enter access code ]  [Continue]
```

A wrong code shows "Invalid access code. Please try again." The four texts can
be reworded in **Builder → Theme → Wording → Access code** (see
[[Theme and Branding|Studio-Theme-and-Branding]]).

Access codes are part of the **questionnaire**, so every change is a new Save
and reaches the field only when you **republish** the environment.

### Generating codes

1. Open the **Access codes** chip. It reads **Access codes · off** ("Respondents
   enter freely. Turn on access codes to restrict the survey to invited
   participants…").
2. Click **Generate codes** (later **Generate more**).
3. In **Generate access codes**, set **How many** (1–5,000, default 50) and the
   **Prefix** (letters and digits, up to 8 characters, upper-cased; the default
   is the first four letters or digits of the project's slug).
4. Click **Generate N**. Studio adds the codes and saves a new version: "50
   codes saved as #18 — republish main to apply".
5. Republish the environment (the **Republish #18** chip).

Codes look like `BRND-0417`: the prefix, a hyphen and four random digits. One
prefix has room for 10,000 codes; when it runs short you see "Only N BRND-NNNN
codes were left — generating those", and when it is full "Every BRND-NNNN code
is already taken — choose another prefix".

### Import, export, turn off

| Button | What it does |
|---|---|
| **Import CSV** | reads codes from the first column of a `.csv` or text file (separated by comma, semicolon or tab; a `code` header is skipped), adds the new ones, turns codes on and saves a new version. "No new codes in that file" if nothing is new |
| **Export CSV** | downloads `<project>-access-codes.csv` with a `code` header — use it to distribute the codes |
| **Turn off** | removes the requirement (a new Save). The codes stay in the questionnaire; **Generate codes** or **Import CSV** turns the requirement on again |

While codes are on, the panel reads **Access codes · N codes** and tells you
whether the published Save has them ("Save #18 is published") or not yet ("the
published Save #17 may differ from the current #18 — republish to apply").

### Plan limits

| Plan | Access codes per questionnaire |
|---|---|
| Free | 100 |
| Plus | 5,000 |
| Pro, Corporate | no limit |

A Save that would go beyond the limit is refused: "plan 'free' allows up to 100
access codes; this Save would have 150".

### What access codes are — and are not

> **Current limitation.** Access codes are a light gate, not a security
> control. The check happens in the respondent's browser; a code can be used
> any number of times, by anyone who has it; and the code a respondent entered
> is not stored with the response, so you cannot tell who used which code
> ("Usage is not tracked yet: reconcile against the exported list"). Codes are
> matched exactly, including upper/lower case. For one link per person with
> completion tracking, use [[Email Invitations|Studio-Email-Invitations]].

---

## Captcha

The **Captcha** chip adds an invisible Cloudflare Turnstile check when the
respondent submits — no checkbox, no extra click for anyone real. It is off by
default.

1. Open **Captcha** (**Captcha · off**) → **Turn on**. Studio saves a new
   version ("Turn on the captcha"): "Saved as #18 — republish main to apply".
2. Republish the environment.

When the respondent submits, three things can happen:

| On submit | Result |
|---|---|
| A valid token arrives | stored, `captcha: pass` in the response's `meta` |
| The token is rejected | **refused** — forgery or a replayed token. The respondent sees the "Submission failed" dialog |
| No token at all (an ad blocker, a corporate proxy, a slow network), or the check service cannot be reached | **stored anyway**, marked `captcha: unavailable` |

The third case is deliberate: a finished questionnaire is too valuable to throw
away because a browser extension stopped the check. To keep a bot that simply
skips the check from getting anywhere, submissions **without** a token are
limited to **3 per hour** from one network address per survey. (Saving
progress of an unfinished interview does not use up that allowance.)

The verdict is written by Studio, never by the respondent's browser. Filter on
it in **Data** (the **Captcha unavailable** quick filter) or in a flow (the
`captcha` column). See [[Data Quality|Studio-Data-Quality]].

The captcha is a project setting, not part of the questionnaire: a
`questionnaire.py` you download and run yourself has no captcha. **Turn off**
works the same way as turning it on (a Save, then republish).

---

## Search engines

Published surveys tell search engines not to index, follow or archive them.
Your fieldwork does not turn up in search results, and nobody lands in your
sample from a search.

---

## Choosing how people get in

| You want | Use |
|---|---|
| Anyone with the link may answer | the plain link, QR code or embed |
| Only people you gave a code to | [Access codes](#access-codes) |
| One personal link per person, completion tracked, reminders | [[Email Invitations\|Studio-Email-Invitations]] *(Plus)* |
| Respondents from Prolific, Cint, Dynata … | [[Panel Providers\|Studio-Panel-Providers]] |
| Keep bots out | [Captcha](#captcha) |
| Know which channel a response came from | [URL parameters](#url-parameters) |

## See also

- [[Publishing and Environments|Studio-Publishing-and-Environments]]
- [[What Respondents See|Studio-Respondent-Experience]]
- [[Panel Providers|Studio-Panel-Providers]]
- [[Email Invitations|Studio-Email-Invitations]]
- [[Security and Privacy|Studio-Security-and-Privacy]]
