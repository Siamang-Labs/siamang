# Links, QR Codes, Embeds and Access Control

Once an environment is live, you hand out its link — directly, as a QR code,
embedded in your own web page, tagged with URL parameters — and decide who may
answer: anyone with the link, holders of an access code, only real people
(captcha), or one response per browser. Everything on this page lives in the
chips of an environment card on **Distribute**. Panel providers and email invitations have their own pages:
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
  have stopped collecting responses." If the environment declares a post-close
  redirect, the page adds "Redirecting you now. Continue if you are not
  redirected." and sends the visitor there after 3 seconds.
- After the environment's [closing date](Studio-Publishing-and-Environments#deadlines)
  — the questionnaire's deadline, the environment's `closes_at`, or a date set
  in the **Closing date** panel — the survey page shows that same notice as it
  opens, and sends the visitor on to the post-close redirect if there is one.
  While the environment is paused, the page says "This survey is paused"
  instead, and once a response cap is full, "Thank you for your interest". (A
  survey built before this check existed shows these notices only at submit,
  until you republish it.)
- Surveys published before the switch to survey-id links may also answer on an
  older `…/<organization>/<project>/<environment>/` address; those links keep
  working. A survey published with a survey-id link from the start answers
  only there.
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
The frame grows and shrinks with the survey: each time a page gets longer or
shorter, the survey tells the loader its height, so your visitors never scroll
inside a scrolling page. Optional attributes on the `div`:

| Attribute | Effect |
|---|---|
| `data-height` | minimum height of the frame, e.g. `data-height="900px"` (default `720px`): the frame never gets shorter than this |
| `data-title` | the frame's accessible title (default `Survey`) |

Several placeholders on one page each get their own frame.

> **Note.** The height comes from the survey page itself, so a survey built
> before auto-height existed keeps a frame of the minimum height (720 pixels,
> or your `data-height`) until you
> [republish](Studio-Publishing-and-Environments#republishing) the environment.
> The plain iframe never resizes.

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

- **Data** tab: inside the `meta` column of the `responses` table. Type a value
  in the filter and press `Enter` (or **Search all rows**) to find it in the
  whole table.
- **Exports** from the Data tab: as columns `url_source`, `url_wave`, … (see
  [[Data Exports|Studio-Data-Exports]]).
- **Flows**: as ordinary columns `url_source`, `url_wave`, … of the responses
  data, ready for filtering, crosstabs and joins.
- A **research bundle** keeps only the parameters one of its flows reads, and
  never the invitation token (see [[Reproducibility|Studio-Reproducibility]]).

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

Every Save that adds codes — generated or imported — is recorded in **Settings
→ Activity** as `access_codes.generate`, with the Save number (`#18`). The
activity log's **Export CSV** includes how many codes were added; the codes
themselves are never logged.

### Plan limits

| Plan | Access codes per questionnaire |
|---|---|
| Free | 100 |
| Plus | 5,000 |
| Pro, Corporate | no limit |

A Save that would go beyond the limit is refused: "the Free plan allows up to
100 access codes; this Save would have 150".

### What access codes are — and are not

The panel says it in bold, whether codes are on or off:

> **Checked in the browser only.** The codes are part of the published survey
> page and are compared there, not by the server: they keep casual visitors
> out, but anyone who reads the page source can find them, a code can be used
> any number of times, and the code a respondent entered is not stored with
> the response. For a closed list of participants, use email invitations (a
> personal link each).

> **Limitation.** Access codes are a light gate, not a security control.
> Because the code a respondent entered is not stored, you cannot tell who
> used which code ("Usage is not tracked yet: reconcile against the exported
> list"). Codes are matched exactly, including upper/lower case. For one link
> per person with completion tracking, use
> [[Email Invitations|Studio-Email-Invitations]].

---

## Captcha

The **Captcha** chip adds an invisible Cloudflare Turnstile check when the
respondent submits — no checkbox, no extra click for anyone real. It is off by
default. Nothing is loaded from Cloudflare before the respondent submits, so a
visitor who never sends their answers is never seen by it.

1. Open **Captcha** (**Captcha · off**) → **Turn on**. Studio saves a new
   version ("Turn on the captcha"): "Saved as #18 — republish main to apply".
2. Republish the environment.

The check runs behind the "Submitting your responses…" overlay. On the rare
submit where Cloudflare wants a click first, it comes on screen with "One more
step: please complete this check to send your answers.", and the respondent
has two minutes for it.

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
progress of an unfinished interview does not use up that allowance.) Past
that, the respondent sees the "Submission failed" dialog with "The security
check that protects this survey could not run in your browser, so your answers
could not be saved. If an ad blocker, a browser extension or your network
blocks challenges.cloudflare.com, allow it and try again." **Try again**
loads the check afresh, so it succeeds once they allow it. With the captcha
on, the panel says so: "Only a few such responses an hour are taken from one
network; past that, the respondent is asked to allow the check and try
again."

The verdict is written by Studio, never by the respondent's browser. Filter on
it in **Data** (the **Captcha unavailable** quick filter), in an export or in a
flow (the `captcha` column). See [[Data Quality|Studio-Data-Quality]].

The panel ends with a note on privacy:

> **Privacy.** The check loads from Cloudflare only when the respondent
> submits, so Cloudflare sees the IP address and browser of each respondent
> who sends their answers, and Studio sends Cloudflare the respondent’s IP
> address with the token to verify it. Name Cloudflare Turnstile in your
> survey’s privacy notice.

The captcha is a project setting, not part of the questionnaire: a
`questionnaire.py` you download and run yourself has no captcha. **Turn off**
works the same way as turning it on (a Save, then republish).

> **Note.** A survey published with the captcha on before this update loads
> the check as the page opens, and never sends its token: every response it
> stores is marked `captcha: unavailable`. Republish the environment to fix
> both.

---

## One response per browser

By default anyone with the link can answer as often as they like: every
interview is a new response, and Studio cannot tell whether two came from the
same person. The **One per browser** chip lets an environment refuse a second
interview from a browser that has already answered. It is off by default and is
offered on every published environment except previews.

1. Open **One per browser**. The panel reads **One response per browser ·
   off**: "Anyone with the link can answer again: every interview is a new
   response, and Studio cannot tell whether two came from the same person.
   Turn this on and the survey page keeps a mark in the respondent’s browser
   that the survey was answered there. Off by default."
2. Click **Turn on**. Toast: **One response per browser — on for main**. The
   chip now reads **One per browser · on**, and the panel: "A browser that has
   already sent a response to main — or ended on a screen-out or a full quota —
   sees “You have already taken part” instead of the questionnaire. It applies
   at once, without a new Save or a rebuild, to the interviews that end from
   now on."

**Turn off** allows repeat answers again (toast **Repeat answers allowed again
in main**). If the change fails: "Could not change repeat answers." followed by
the reason.

A browser that has already answered sees a full-page notice instead of the
questionnaire:

```
You have already taken part
This survey takes one response from each browser, and this browser has
already sent one. Thank you!
```

The same notice appears if the respondent had the survey open in a second tab
and tries to submit there. The setting belongs to the environment: a browser
that answered `pilot` can still answer `main`. It survives a republish, a
rebuild and **Reopen**, and every change is recorded in **Settings →
Activity** as `deploy.one_response_per_browser`.

> **Limitation.** The panel says what this is and is not: "Checked in the
> browser only. Nothing about the browser is sent to Studio, so cleared
> browser data, a private window, another browser or another device can
> answer again, and people who share one browser count as one. A survey
> published before this option existed needs one republish of main for its
> page to honor it." Interviews that ended before you turned it on are not
> remembered. For one answer per *person*, use
> [[Email Invitations|Studio-Email-Invitations]] or a panel provider's own
> checks.

**Mention it in your consent text.** The mark is the date and time this
browser answered, kept under the survey host's `siamang_done_<survey id>`.
Unlike the rest of what a survey keeps in the browser, it is not cleared after
a week: it stays until the respondent clears their browser data. The panel
says: "Mention it in your consent text. The mark stays on the respondent’s
device after they answer — the survey’s other browser data is cleared after a
week, the mark is not — so your survey’s consent text should say so. Unique
invitation links are more reliable, especially for respondents in the EU,
where keeping such a mark on a device needs the respondent’s consent: email
invitations give each respondent a personal link, and Studio records on its
side who has answered, whatever browser or device they use." See
[Cookies and browser storage](Studio-Security-and-Privacy#cookies-and-browser-storage).

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
| Discourage the same browser from answering twice | [One response per browser](#one-response-per-browser) |
| Know which channel a response came from | [URL parameters](#url-parameters) |

## See also

- [[Publishing and Environments|Studio-Publishing-and-Environments]]
- [[What Respondents See|Studio-Respondent-Experience]]
- [[Panel Providers|Studio-Panel-Providers]]
- [[Email Invitations|Studio-Email-Invitations]]
- [[Security and Privacy|Studio-Security-and-Privacy]]

<!-- studio-nav -->
---

← [[Publishing and Environments|Studio-Publishing-and-Environments]] · [Studio contents](Studio-Overview#all-pages) · [[Panel Providers|Studio-Panel-Providers]] →
