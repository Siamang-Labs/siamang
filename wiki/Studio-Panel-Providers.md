# Panel Providers

Sample providers such as Prolific, Cint and Dynata send respondents to your
survey with an id in the link, and expect them back on a URL that says how the
interview ended — completed, screened out, or turned away because the sample
was full. The **Panel** chip on an environment card sets this up and gives you
the counts to reconcile with the provider's invoice.

---

## How it works

```
 provider ──entry link──▶  study.siamang.org/<survey-id>/?RID=8f2…      (id arrives as a URL parameter)
                                   │
                         respondent answers
                                   │
        ┌──────────────────────────┼───────────────────────────┐
     completed                screened out               sample full (cap)
        │                          │                           │
   Completed → return URL    Screened out → return URL    Quota full → return URL
        └──────────── each URL carries the id back: …&RID={url:RID} ────────┘
```

- The respondent's id is an ordinary [URL parameter](Studio-Distribution-Channels#url-parameters):
  it is stored with the response and reaches your flows as a `url_<name>`
  column (lower-cased: `RID` becomes `url_rid`, `PROLIFIC_PID` becomes
  `url_prolific_pid`).
- The three return URLs are part of the **questionnaire** — they are built into
  the published survey. Saving the panel setup creates a new Save; the
  environment uses it after you **republish**.
- The provider's name and the id parameter are project settings.

---

## The Panel chip

Open an environment card's **Panel** chip. It is available while the
environment serves a survey (live or paused), not on previews. The header reads
**Panel provider · not set** until you save a setup, then the provider's name.

| Field | What to enter |
|---|---|
| **Provider** | **— none —**, **Prolific**, **Cint**, **Dynata** or **Custom**. Choosing a preset fills the next four fields |
| **Respondent id parameter** | the query parameter that carries the provider's id (letters, digits and `_` only). Hint: "the query parameter in the entry link" |
| **Entry link for the provider** | read-only, with a copy button: your survey link plus the id parameter and the provider's macro. Paste it into the provider's project. Shown once the environment has a link and the id parameter is set |
| **Completed → return URL** | where respondents go after completing |
| **Screened out → return URL** | where respondents go after reaching a screen-out page |
| **Quota full → return URL** | where respondents go when the environment's response cap refuses their submission |

Notes the panel may show:

- the preset's own advice (see the table below);
- "Replace the <…> placeholders with the codes or tokens from the provider's
  project page before saving." — while a URL still contains a placeholder such
  as `<COMPLETION_CODE>`;
- "Pages with their own redirect keep it: `<page names>`. Clear a page's
  redirect in the Builder if the provider's URL should apply there."

**Save panel setup** (enabled once something changed) saves a new version:
"Saved as #18 — republish main to apply the return URLs". When the published
Save is older, the panel reminds you: "Published Save #17 may differ from the
current #18 — republish to apply."

---

## Presets

| Provider | Id parameter | Entry link adds | Completed | Screened out | Quota full |
|---|---|---|---|---|---|
| **Prolific** | `PROLIFIC_PID` | `?PROLIFIC_PID={{%PROLIFIC_PID%}}&STUDY_ID={{%STUDY_ID%}}&SESSION_ID={{%SESSION_ID%}}` | `https://app.prolific.com/submissions/complete?cc=<COMPLETION_CODE>` | `…?cc=<SCREENOUT_CODE>` | `…?cc=<QUOTA_FULL_CODE>` |
| **Cint** | `RID` | `?RID=[%RID%]` | `https://s.cint.com/Survey/Complete?ProjectToken=<PROJECT_TOKEN>&RID={url:RID}` | `https://s.cint.com/Survey/EarlyScreenOut?ProjectToken=<PROJECT_TOKEN>&RID={url:RID}` | `https://s.cint.com/Survey/QuotaFull?ProjectToken=<PROJECT_TOKEN>&RID={url:RID}` |
| **Dynata** | `psid` | `?psid=[%psid%]` | `https://dkr1.ssisurveys.com/projects/end?rst=1&psid={url:psid}` | `…?rst=2&psid={url:psid}` | `…?rst=3&psid={url:psid}` |
| **Custom** | `id` (change it) | `?id=<RESPONDENT_ID>` | empty | empty | empty |

The preset notes, as shown in the panel:

- **Prolific:** "Prolific identifies outcomes by completion codes: paste the
  codes from the study's page into the three URLs."
- **Cint:** "Cint passes the respondent as RID and expects it back on every
  return URL; the project token is on the project page."
- **Dynata:** "Dynata's return status: rst=1 complete, 2 screen-out, 3 quota
  full. Confirm the endpoint with your project manager."
- **Custom:** "Any provider: name the query parameter that carries their
  respondent id and put {url:<param>} where the return URL needs it."

The presets are starting points: always check the URLs against the
provider's current documentation and your project page.

---

## Placeholders in return URLs

| Placeholder | Replaced by |
|---|---|
| `{url:NAME}` | the value of URL parameter `NAME` the respondent arrived with, exactly as the provider named it (e.g. `{url:RID}`, `{url:PROLIFIC_PID}`) |
| `{answer:var}` | the respondent's answer to variable `var` (codes; several answers joined with commas) |
| `{label:var}` | the label of that answer |

Values are URL-encoded. A placeholder that has no value is removed rather than
sent to the provider as literal braces. In the **Quota full** URL only
`{url:NAME}` is filled in.

---

## Which URL applies when

| How the interview ends | Where the respondent goes | After |
|---|---|---|
| submits the last page | **Completed → return URL** | 5 seconds ("You will be redirected in 5 seconds. Click here if not redirected.") |
| reaches a **Final (thank you)** page | the **Completed** URL | 5 seconds |
| reaches a **Screen-out** page | the **Screened out** URL | 5 seconds |
| reaches a **Redirect** page | the page's own **Redirect URL** (the **Completed** URL if the page has none) | the page's **Delay (s)**, 5 by default |
| submission refused because the environment's response cap is reached | the **Quota full** URL | 3 seconds after the "Thank you for your interest" notice |

A terminal page with its own redirect keeps it — the page wins over the
survey-level URL; the Panel chip lists those pages. On terminal pages the
redirect happens only after the response has been stored, with "Redirecting you
now. Continue if you are not redirected."

> **Current limitation.** The **Quota full** URL is used when the
> environment's **response cap** refuses a submission. Quota cells defined in
> the Builder are counted but do not yet turn respondents away, so a full cell
> does not send anyone to this URL. To stop a full sample, lower the
> environment's cap, or pause or close the environment. See
> [[Quotas and Randomization|Studio-Quotas-and-Randomization]] and
> [Response caps](Studio-Publishing-and-Environments#response-caps).

Screen-outs are submitted responses: they are stored (with `__status` set to
`screened_out`) and they count toward the environment's response cap.

---

## Recipes

### Prolific

1. In Prolific, create the study. Keep the page with the **completion codes**
   open.
2. In Studio, publish the environment (usually `main`), open **Panel**, choose
   **Prolific**.
3. Replace `<COMPLETION_CODE>`, `<SCREENOUT_CODE>` and `<QUOTA_FULL_CODE>` with
   Prolific's codes. If you do not use a screen-out or quota-full code, clear
   that field.
4. **Save panel setup**, then republish the environment.
5. Copy **Entry link for the provider** into Prolific's study URL field. Tell
   Prolific that you pass the participant id through URL parameters.
6. Test: open the entry link with a made-up id, finish the survey, and check
   that you land on Prolific's completion page.

### Cint

1. Choose **Cint**. The id parameter is `RID`.
2. Replace `<PROJECT_TOKEN>` in all three URLs with the token from the Cint
   project page. Keep `RID={url:RID}` — Cint expects its id back.
3. **Save panel setup**, republish.
4. Paste the entry link (`…?RID=[%RID%]`) into the Cint project.

### Dynata

1. Choose **Dynata**. The id parameter is `psid`; the three URLs differ only in
   `rst=1` (complete), `2` (screen-out), `3` (quota full).
2. Confirm the end-point host with your Dynata project manager and adjust the
   URLs if needed.
3. **Save panel setup**, republish, and send Dynata the entry link
   (`…?psid=[%psid%]`).

### Any other provider

1. Choose **Custom**.
2. Set **Respondent id parameter** to the parameter name the provider uses
   (for example `uid`).
3. Enter the three return URLs from the provider's documentation, putting
   `{url:uid}` wherever the provider needs its id back.
4. **Save panel setup**, republish, and give the provider the entry link,
   replacing `<RESPONDENT_ID>` with the provider's own macro for the id.

For all providers: mark the screener's disqualification ending as a
**Screen-out** page in the Builder so screened-out respondents are recognized
and sent to the right URL. See [[Logic and Branching|Studio-Logic-and-Branching]].

---

## Reconciling outcomes

While the environment is **live**, the Panel chip ends with **Outcomes ·
reconcile with the provider**:

| Count | Which responses |
|---|---|
| **completed** | submitted responses that did not end on a screen-out page (Redirect and Final pages count as completed) |
| **screened out** | responses that ended on a **Screen-out** page |
| **partial** | interviews started and not submitted |

Each count with at least one response has a **CSV** button. The file
(`<project>-<environment>-<outcome>.csv`) has one row per response with
`response_id`, `outcome`, a column named after your id parameter, and
`submitted_at`. The CSVs cover up to the first 5,000 responses of the
environment.

"… quota-full returns are not counted here — the response is refused, the
provider's count is the record." Respondents turned away by the cap leave no
response, so the provider's own report is the reference for them.

> **Tip.** The dependable place to read each respondent's provider id is a
> flow: the responses data carries it as `url_<parameter>` in lower case
> (`url_prolific_pid`, `url_rid`, `url_psid`), next to `__status` and
> `partial`. A small flow with an **Export file** node produces a
> reconciliation file for any number of responses. See
> [[Analysis Flows|Studio-Flows]].

The outcome block is not shown for paused or closed environments; for those,
use a flow or the Data tab.

## See also

- [[Links, QR Codes, Embeds and Access Control|Studio-Distribution-Channels]]
- [[Publishing and Environments|Studio-Publishing-and-Environments]]
- [[What Respondents See|Studio-Respondent-Experience]]
- [[Quotas and Randomization|Studio-Quotas-and-Randomization]]
- [[Logic and Branching|Studio-Logic-and-Branching]]

<!-- studio-nav -->
---

← [[Links, QR Codes, Embeds and Access Control|Studio-Distribution-Channels]] · [Studio contents](Studio-Overview#all-pages) · [[Email Invitations|Studio-Email-Invitations]] →
