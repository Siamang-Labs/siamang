# Panel Providers

Sample providers such as Prolific, Respondent, Cint and Dynata send
respondents to your survey with an id in the link, and expect them back on a URL that says how the
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
     completed                screened out       sample full (quota cell or cap)
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
environment serves a survey (live, paused, or a failed rebuild whose previous
version still serves), not on previews: publish `pilot` and `main` before you
set up a panel, then publish the panel's Save to both. The header reads
**Panel provider · not set** until you save a setup, then the provider's name.

| Field | What to enter |
|---|---|
| **Provider** | **— none —**, **Prolific**, **Respondent**, **Cint**, **Dynata** or **Custom**. Choosing a preset fills the next four fields |
| **Respondent id parameter** | the query parameter that carries the provider's id (letters, digits and `_` only). Hint: "the query parameter in the entry link" |
| **Entry link for the provider** | read-only, with a copy button: your survey link plus the id parameter and the provider's macro. Paste it into the provider's project. With **Prolific**, the plain survey link (hint: "paste into Prolific's study link field"): Prolific adds its parameters itself. With **Respondent**, the plain survey link too (hint: "paste into Respondent's Link to Task field"). Shown once the environment has a link and the id parameter is set |
| **Completed → return URL** | where respondents go after completing |
| **Screened out → return URL** | where respondents go after reaching a screen-out page |
| **Quota full → return URL** | where respondents go when a full quota cell or a full response cap turns them away |

Notes the panel may show:

- the preset's own advice (see the table below);
- "Replace the <…> placeholders with the codes or tokens from the provider's
  project page before saving." — while a URL still contains a placeholder such
  as `<COMPLETION_CODE>`;
- "Pages with their own redirect keep it: `<page names>`. Clear a page's
  redirect in the Builder if the provider's URL should apply there."
- with **Prolific**, under the entry link: "In Prolific, choose **I'll use URL
  parameters**: Prolific adds `PROLIFIC_PID`, `STUDY_ID` and `SESSION_ID` to
  this link. Then check that the study link in Prolific shows each of them
  once."; and above **Save panel setup**, a line about the screen after **Save
  locally and finish** (see [Prolific](#prolific));
- with **Respondent**, under the entry link: "In Respondent, paste this link
  into **Link to Task** (Custom URL). Respondent adds `respondent_profile_id`,
  `respondent_user_id`, `respondent_project_id` and
  `respondent_screener_response_id` itself."; and the same line above **Save
  panel setup**, for Respondent (see [Respondent](#respondent)).

**Save panel setup** (enabled once something changed) saves a new version:
"Saved as #18 — republish main to apply the return URLs". When the published
Save is older, the panel reminds you: "Published Save #17 may differ from the
current #18 — republish to apply."

---

## Presets

| Provider | Id parameter | Entry link adds | Completed | Screened out | Quota full |
|---|---|---|---|---|---|
| **Prolific** | `PROLIFIC_PID` | nothing — Prolific adds `PROLIFIC_PID`, `STUDY_ID` and `SESSION_ID` itself once **I'll use URL parameters** is chosen | `https://app.prolific.com/submissions/complete?cc=<COMPLETION_CODE>` | `…?cc=<SCREENOUT_CODE>` | `…?cc=<QUOTA_FULL_CODE>` |
| **Respondent** | `respondent_user_id` | nothing — Respondent adds `respondent_profile_id`, `respondent_user_id`, `respondent_project_id` and `respondent_screener_response_id` to the project's **Link to Task** itself | `https://app.respondent.io/complete?cc=<projectCompletionId>` | empty | empty |
| **Cint** | `RID` | `?RID=[%RID%]` | `https://s.cint.com/Survey/Complete?ProjectToken=<PROJECT_TOKEN>&RID={url:RID}` | `https://s.cint.com/Survey/EarlyScreenOut?ProjectToken=<PROJECT_TOKEN>&RID={url:RID}` | `https://s.cint.com/Survey/QuotaFull?ProjectToken=<PROJECT_TOKEN>&RID={url:RID}` |
| **Dynata** | `psid` | `?psid=[%psid%]` | `https://dkr1.ssisurveys.com/projects/end?rst=1&psid={url:psid}` | `…?rst=2&psid={url:psid}` | `…?rst=3&psid={url:psid}` |
| **Custom** | `id` (change it) | `?id=<RESPONDENT_ID>` | empty | empty | empty |

The preset notes, as shown in the panel:

- **Prolific:** "Prolific identifies outcomes by completion codes: paste the
  codes from the study's page into the three URLs. What each code does to a
  submission is set in Prolific."
- **Respondent:** "A Respondent survey project has a single completion URL,
  its Completion Confirmation URL: paste it into Completed and leave Screened
  out and Quota full empty. Screening and quotas stay in Respondent, in its
  screener, before the invitation."
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
sent to the provider as literal braces. In the **Quota full** URL, answers are
filled in when a full quota cell ends the interview; when a full response cap
turns the respondent away (as the page opens, or at submit), only `{url:NAME}`
is filled in and `{answer:…}` / `{label:…}` are removed.

---

## Which URL applies when

| How the interview ends | Where the respondent goes | After |
|---|---|---|
| presses **Submit responses** on the last page (a page with questions and no end page after it) | **Completed → return URL** | 5 seconds ("You will be redirected in 5 seconds. Click here if not redirected.") |
| reaches a **Final (thank you)** page | the **Completed** URL | 5 seconds |
| reaches a **Screen-out** page | the **Screened out** URL | 5 seconds |
| reaches a **Redirect** page | the page's own **Redirect URL** (the **Completed** URL if the page has none) | the page's **Delay (s)**, 5 by default |
| leaves a page with an answer whose quota cell is full | the **Quota full** URL | 3 seconds after the "Thank you for your interest" screen, which adds "Redirecting you now. Continue if you are not redirected." |
| a response cap is full — the notice appears as the page opens, or at submit for someone already answering | the **Quota full** URL | 3 seconds after the "Thank you for your interest" notice |
| the environment is closed or past its [closing date](Studio-Publishing-and-Environments#deadlines) | the environment's post-close redirect (`redirect_after_close` in `studio/settings.json`), if it has one; otherwise the respondent stays on the "This survey is closed" notice | 3 seconds |
| the environment is paused | nowhere — the respondent stays on the "This survey is paused" notice | — |
| submitting fails and the respondent presses **Save locally and finish** | nowhere — the respondent stays on "Your answers are saved in this browser", with no end page | — |
| the survey page cannot reach Studio (its `env.js` did not load) | nowhere — every attempt to submit fails, with the **Try again** dialog; opening the link again or reloading the page, then **Resume**, sends the answers | — |

A terminal page with its own redirect keeps it — the page wins over the
survey-level URL; the Panel chip lists those pages. On terminal pages the
redirect happens only after the response has been stored, with "Redirecting you
now. Continue if you are not redirected."; the page's title and body appear
only then too. A terminal page cannot be left: `Esc`, which goes back on a
question page, does nothing there, so a respondent who reaches a Screen-out
page goes to the **Screened out** URL (or the page's own redirect), never to
the **Completed** one. When submitting fails, **Save locally and finish**
keeps the answers in the respondent's browser, unsent, and sends them
nowhere, so a provider's return URL is never followed, and a code in an end
page's body never shown, without a stored response (see
[When submitting fails](Studio-Respondent-Experience#when-submitting-fails)).
**Resume** reopens the page they were on by its name, even if you republished
in between, so someone saved on a Screen-out page is still stored as screened
out and sent to the **Screened out** URL; if you removed that page, it opens
the first page with their answers kept. Progress saved by a survey built
before **Resume** kept the page's name never reopens an end page by its
position: **Resume** opens the first page with the answers kept, and
**Next** leads the respondent to the end page those answers reach today, and
on to its URL. The survey page's source still holds
every page and return URL, codes included, so check the provider's list
against the completed outcomes below before you approve anyone (see
[Reconciling outcomes](#reconciling-outcomes)).

The quota-full rows depend on the survey page: a survey built before quota
cells could stop respondents, or before the page-open check existed, uses the
**Quota full** URL only when the response cap refuses a submission, until you
[republish](Studio-Publishing-and-Environments#republishing) it. How cells
fill and when they stop someone is described under
[When a cell is full](Studio-Quotas-and-Randomization#when-a-cell-is-full); the
caps under [Response caps](Studio-Publishing-and-Environments#response-caps).

Screen-outs are submitted responses: they are stored (with `__status` set to
`screened_out`), but they are not completed interviews — they fill no quota
cell and do not count toward a response cap. A screen-out is recorded even
when the cap is full.

---

## Recipes

### Prolific

1. In Prolific, create the study. Keep the page with the **completion codes**
   open. Create a code for each outcome you use (table below) and set what
   each code does to a submission in Prolific, before you publish the study.
   Keep its places below the environment's response cap and, on the Free
   plan, below the project's 1,000 completed responses (below the table).
2. In the Builder, set **Theme → Respondent experience → Estimated minutes**
   to the study's estimated time, and save: the Builder's Prolific warnings
   read it.
3. In **Distribute**, publish the current Save to `pilot` and to `main` if
   they are not published yet: the **Panel** chip is only on the card of an
   environment that serves the survey. Each keeps its link when you publish
   again, and nobody reaches `main` before you paste its link into Prolific
   (step 9).
4. Open either environment's **Panel** and choose **Prolific**.
5. Replace `<COMPLETION_CODE>`, `<SCREENOUT_CODE>` and `<QUOTA_FULL_CODE>` with
   Prolific's codes. If you do not use a screen-out or quota-full code, clear
   that field. A Screen-out page that needs a code of its own gets its own
   redirect: `redirect_url` on the page, in the Builder's **Source** tab (the
   **Redirect URL** field is on Redirect pages only).
6. **Save panel setup**. With Prolific saved as the provider, the Builder now
   shows Prolific's rules where a question meets them (below); save any
   change you make there.
7. Publish the latest Save to `pilot` and to `main`. The return URLs and the
   saved-in-browser text are part of the questionnaire, so both environments
   send respondents to the same codes; the provider and the id parameter are
   project settings.
8. Test on `pilot`: open its link with a made-up id
   (`?PROLIFIC_PID=test0000000000000000001&STUDY_ID=test&SESSION_ID=test`),
   finish the survey, check that you land on Prolific's completion page with
   the right code, and find the row in **Data**. Repeat for each Screen-out
   page. A later Save has to be published to both again before you test it.
9. Copy `main`'s **Entry link for the provider** — the plain survey link —
   into Prolific's study link field and choose **I'll use URL parameters**.
   Check that the study link Prolific shows has `PROLIFIC_PID`, `STUDY_ID` and
   `SESSION_ID` once each (and, if you preview the study from Prolific, the
   address of the survey page that opens). A study created through Prolific's
   API gets nothing appended: add
   `?PROLIFIC_PID={{%PROLIFIC_PID%}}&STUDY_ID={{%STUDY_ID%}}&SESSION_ID={{%SESSION_ID%}}`
   yourself.

**A study already live.** What the survey page does after a failed
submission, on an end page and when it cannot reach Studio is built into the
page when an environment is published, and an environment keeps the build it
was last published with. A survey published before the current Studio can
still send a participant on as completed after **Save locally and finish**,
let them go back from an end page, end as sent when its `env.js` did not
load, and restart a duration at a reload, even one followed by **Resume**.
Save in the Builder (a Save with no changes will do) and publish that Save to
`pilot` and `main` (see
[Republishing](Studio-Publishing-and-Environments#republishing)).

**The screen after Save locally and finish.** Its default text asks the
respondent to come back within 7 days; a Prolific submission times out in less
than 24 hours, and Prolific asks participants who hit a technical problem to
contact the researcher. So **Save panel setup** with Prolific sets
**Saved in this browser: text** (Builder → Theme → Wording), in the same Save
as the return URLs, to "They have not been sent yet. Please message the
researcher through Prolific. While the study is still open on Prolific, you
can also open its link again in this browser and choose Resume to send them."
It never replaces a text you wrote yourself, and a Save that moves the
provider away from Prolific takes it out again while it is still exactly that
text. The line above **Save panel setup** says which applies ("Save panel
setup also sets the screen after Save locally and finish to ask participants
to message the researcher through Prolific. …").

**Which code each outcome needs.** Prolific allows screening inside a study
only to re-check one of its prescreeners in its own wording, after a device
check at the start when the study's description states the requirement
("Incompatible device", with a request to return), for a participant who does
not consent, after failed attention checks that meet its policy, and after a
comprehension check failed twice; any other criterion goes through
Prolific's custom screening, with its fixed screen-out payment. Follow
Prolific's current guidance in its help center.

| Outcome in Studio | Studio sends the respondent to | Code in Prolific | Action set in Prolific |
|---|---|---|---|
| completed | **Completed** URL | the main completion code | approve, or manual review |
| a Screen-out page for those who do not consent | the page's own redirect, else **Screened out** | "No consent" | request a return |
| a Screen-out page for an answer that contradicts a Prolific prescreener | the page's own redirect, else **Screened out** | a Custom code, such as "Ineligible" | request a return |
| a Screen-out page for an incompatible device, after a device check at the start | the page's own redirect, else **Screened out** | "Incompatible device" | request a return |
| a Screen-out page for a criterion of your own | the page's own redirect, else **Screened out** | Prolific's custom screening code | custom screening's fixed payment |
| `failed_attention_checks`, the page of **End the survey after N failed attention checks** | the page's own redirect, else **Screened out** | "Failed attention checks" | as Prolific's attention-check policy allows |
| quota full as the page opens (a full response cap) | **Quota full** URL | a Custom code | request a return |
| quota full after answering (a full quota cell) | **Quota full** URL | Prolific's custom screening code | custom screening's fixed payment |
| quota full after completing (a response cap filled while they answered, and their submission was refused) | **Quota full** URL | the same code as the other quota cases | none fits: approve, and pay the full reward, as a bonus for the difference if the code auto-approved the submission at the screen-out reward |

All three quota cases share the **Quota full** URL. Two
[response caps](Studio-Publishing-and-Environments#response-caps) count
completed responses: the environment's own, and on the Free plan the
project's 1,000, counted over all its environments together, `pilot` tests
included. Prolific's places limit the sample, so keep them below both caps:
quota full then comes from quota cells only. A cap is also checked at
submit, and someone turned away there has completed the study: approve them
and pay the full reward, as a bonus for the difference if the **Quota full**
code auto-approved them at the screen-out reward.

**Attention checks.** Prolific needs at least two failed checks to screen
out or reject a participant in a study of 5 minutes or more, and checks used
to screen out come at the start of the study. Keep **Also end the survey for
respondents who fail** off; score the checks in the analysis, or use **End the
survey after 2 failed attention checks** (see
[Attention checks](Studio-Logic-and-Branching#attention-checks)). A
nonsensical statement ("I swim across the Atlantic to get to work") is
answered on a scale without a neutral option, so give its Likert scale an
even number of points, and needs no prior knowledge; any answer on the
correct side of the scale passes, and a statement to which an unexpected
answer can be justified is unsuitable. With Prolific as the provider, the
Builder warns about a check that screens out after one failure, notes a
Likert check with an odd number of points, and warns about Email, Phone and
Date questions (Prolific does not allow a phone number, nor a personal email
address or a date of birth without its written approval; ask for age in
years).

**Reviewing submissions.** Compare Prolific's submissions with the outcome
CSVs below before you approve. In short, as Prolific's rules stand:

- A participant who completed is approved unless there is a valid reason to
  reject: required key questions unanswered, failed attention checks under
  its policy, clearly low effort, an exceptionally fast submission (more than
  3 standard deviations below the mean time), a failed authenticity check.
- A submission with no stored response, or only a partial one, is not
  rejected for that. Check it: an exceptionally fast one may be rejected;
  otherwise message the participant, and approve when it looks like a
  technical problem. Consider a partial payment for the time spent: a partial
  row's `duration_seconds` runs to its last saved progress, a lower bound, so
  compare it with the time Prolific shows.
- A submission that came back with the **Quota full** code after the
  participant reached the end was refused by a full response cap: approve it
  and pay the full reward.
- A wrong code or `NOCODE` alone is not a reason to reject.
- Several responses with one id: keep one for the analysis and approve the
  submission.
- Speeders and quality flags are reasons to leave a response out of the
  analysis, not by themselves reasons to reject.

### Respondent

A Respondent **Survey** project opens the survey from its **Link to Task**
with Respondent's identifiers added, and at the end sends the participant to
the project's Completion Confirmation URL, the link-based integration
Respondent documents for survey tools. Studio does not use Respondent's API.

1. In Respondent, create a project with the **Survey** methodology. Set its
   audience, screener and incentive so that everyone Respondent invites
   qualifies for the whole survey: screening and quotas stay in Respondent,
   before the invitation. For the task, choose **Custom URL** with the
   **Completion Confirmation URL** option, and copy that URL
   (`https://app.respondent.io/complete?cc=…`).
2. In **Distribute**, publish the current Save to `pilot` and to `main` if
   they are not published yet: the **Panel** chip is only on the card of an
   environment that serves the survey. Each keeps its link when you publish
   again, and nobody reaches `main` before you paste its link into
   Respondent (step 7).
3. Open either environment's **Panel** and choose **Respondent**. The id
   parameter becomes `respondent_user_id`, **Completed** gets
   `https://app.respondent.io/complete?cc=<projectCompletionId>`, and
   **Screened out** and **Quota full** stay empty. Replace the Completed URL
   with the one you copied. If the panel lists pages with a redirect of their
   own, clear those redirects in the Builder unless they are meant to apply.
   **Save panel setup**.
4. In the Builder, make sure an invited participant can end the survey only
   by finishing it: by **Submit responses**, on a **Final (thank you)** page
   or on a **Redirect** page without a URL of its own. No branch leads to a
   **Screen-out** page, **Also end the survey for respondents who fail** and
   **End the survey after N failed attention checks** stay off, and there are
   no quota cells. With Respondent now saved as the provider, the Builder
   points out each of these (see [Respondent's warnings in the Builder](#respondents-warnings-in-the-builder)).
   A consent question whose decline leads to a Screen-out page may stay:
   write in that page's text that the participant should let the researcher
   know through Respondent's messages. Save any change.
5. Publish the latest Save to `pilot` and to `main`.
6. Test on `pilot`: open its link with made-up identifiers
   (`?respondent_profile_id=test&respondent_project_id=test&respondent_screener_response_id=test&respondent_user_id=test0001`),
   finish the survey, check that you land on `app.respondent.io/complete`,
   and that **Data** has the row with `url_respondent_user_id` `test0001`.
   For the whole path, invite a teammate with a Respondent participant
   account with the `pilot` link (Respondent lets you change the survey link
   when you invite someone), and check that they appear under **Completes**.
7. Copy `main`'s **Entry link for the provider** — the plain survey link —
   into **Link to Task** as it stands. Add no parameters of your own: the
   survey keeps the first 8 parameters of its link, and Respondent appends
   its four after any already there, sometimes with `participant_id` and
   `project_id`.
8. Publish the Respondent project and invite participants; review each
   completion before Respondent's Auto-Pay pays the participant, 48 hours
   after task completion (below).

Each response stores `url_respondent_profile_id`, `url_respondent_user_id`,
`url_respondent_project_id` and `url_respondent_screener_response_id`, on the
partial row and the submitted one, so no Participant ID question is needed.
Respondent recognizes the returning participant by their Respondent sign-in
in the same browser, so the completion URL needs no placeholder.

**Ending only at the completion URL.** A Respondent survey project has no
screen-out or quota-full return. A participant whom the survey stops on a
page of its own stays there and never reaches the completion URL, and their
task stays incomplete in Respondent until you resolve it by hand:

| How the interview ends | Where the participant goes |
|---|---|
| submits on the last question page, or reaches a **Final (thank you)** page or a **Redirect** page without a URL of its own | the Completion Confirmation URL, once the response is stored |
| reaches a **Screen-out** page | the page's own redirect, if it has one; otherwise nowhere |
| turned away by a full quota cell or response cap | nowhere — "Thank you for your interest" |
| submitting fails, or **Save locally and finish** | nowhere, until a later attempt or **Resume** stores the response |

Keep the number of participants you invite below the environment's
[response cap](Studio-Publishing-and-Environments#response-caps) and, on the
Free plan, below the project's 1,000 completed responses.

**The screen after Save locally and finish.** A participant whose answers
were not sent has not reached the completion URL. **Save panel setup** with
Respondent sets **Saved in this browser: text**, in the same Save as the
return URL, to "They have not been sent yet. Please message the researcher
through Respondent. You can also open this survey's link again in this
browser within 7 days and choose Resume to send them." As with Prolific's, it
never replaces a text you wrote yourself and goes again when the provider
moves away from Respondent while it is still exactly that text; moving a
setup between Prolific and Respondent replaces one provider's text with the
other's.

**Reviewing completions.** In a project created in Respondent's web
interface, as with this setup, reaching the completion URL marks the
participant complete at once, and Auto-Pay, on by default, pays the incentive
48 hours after that. To undo a completion, change the participant's
completion status in Respondent before Auto-Pay pays. In a project created
through Respondent's API, completion is marked 24 hours after the participant
reaches the URL. So review each completion within those 48 hours.
Respondent's **Completes** tab lists the participants who reached the
completion URL by their Participant ID, which Respondent documents as the same
ID as `respondent_user_id`, the id column of the outcome CSVs below.

| What you find in Studio | Action in Respondent |
|---|---|
| a completed response of acceptable quality | nothing more: the participant is already marked complete, and Auto-Pay pays them 48 hours after task completion |
| a completed response that does not meet the study's quality standards, such as failed attention checks | change the participant's completion status in Respondent before Auto-Pay pays; for a reduced incentive, or anything else, contact Respondent |
| a participant listed under **Completes** with no completed response in Studio | look for their partial row in **Data** and message them before Auto-Pay pays: they may have opened the completion URL without finishing, or hit a technical failure. If they did not complete the task, change their completion status |
| a completed response, or a partial row that reached the last page, and the participant is not under **Completes** | they did the whole survey but did not reach the completion URL: they may have closed the page before the redirect, or been turned away by a response cap that filled while they answered. Respondent does not mark them complete without it, so mark them as having attended in Respondent yourself |
| only a partial response, stopping before the last page, and the participant is not under **Completes** | message the participant through Respondent. Without the completion URL they are not marked complete, and Auto-Pay does not pay them |
| signs of fraud, such as one person answering under two different IDs | report the participant to Respondent |

Studio's quality signals inform the decision; it stays with you, under
Respondent's rules. The Median duration tile's "exceptionally fast" line is
Prolific's rule and is not shown with Respondent.

**Personal data.** Respondent appends its identifiers so that a survey need
not ask for an email address or other personal data, and prohibits collecting
a participant’s phone number, physical address or date of birth, among other
personal data, removing researchers who do from the platform. For a project
created in its web interface, its help center describes
an email visibility option, in which participants who opt in enter the email
of their Respondent account in the survey tool; otherwise Respondent does not
share participants' contact details with researchers. The Builder notes
Email, Phone and Date questions, and the Email note names that option.

#### Respondent's warnings in the Builder

With Respondent saved as the provider, the Builder says where the
questionnaire can end an interview short of the completion URL. The notes
never stop a Save; **Validation → Respondent** lists them all.

| Where | When | What it says |
|---|---|---|
| an attention check's Inspector | **Also end the survey for respondents who fail**, or **End the survey after N failed attention checks**, is on | "Respondent has one completion URL: a participant screened out on failed attention checks stays on Studio’s page and never reaches it; leave screening out off, score the checks in the analysis, and decide on the participant in Respondent before Auto-Pay pays them, 48 hours after task completion (24 hours for projects created through Respondent’s API)." |
| a **Screen-out** page's Inspector, under **Kind** | a participant can reach the page: a branch rule, a **Default next** or a **Skip to** leads there, or no page before it ends the survey for everyone (an attention check's own page is said at the check) | "Respondent has one completion URL: a participant who ends here stays on Studio’s page and never reaches it; screen in Respondent’s screener instead.", then "If you keep this page, as one for participants who decline consent, say in its text that they should let the researcher know through Respondent’s messages." |
| **Validation** only | the questionnaire has quota cells | "Quotas: Respondent has one completion URL: a participant a full quota cell turns away stays on Studio’s page and never reaches it; set quotas in Respondent instead." |
| **Validation** only | an environment has a response cap | "Response cap (pilot 50, main 1,200): Respondent has one completion URL: a participant the cap turns away stays on Studio’s page and never reaches it; keep the participants you invite in Respondent below it." |
| under **Format** of an Open text question | **Email**, **Phone** or **Date** | "Respondent recognizes participants by the IDs it adds to the survey link, not by an email address. Ask for an email only if the project uses Respondent’s email visibility option, in which participants who opt in enter the email of their Respondent account; for participants sourced through Respondent’s API, requesting personal data is a violation of its terms. Otherwise contact participants through Respondent’s messages." (Email), "Respondent prohibits collecting a participant’s phone number, and removes researchers found collecting personal data from the platform. Contact participants through Respondent’s messages." (Phone), and "If this asks for a date of birth: Respondent prohibits collecting it. Ask for age in years instead." (Date) |

Follow Respondent's current guidance in its help center ("Auto-Complete &
Auto-Pay for Research Studies", "Completion Confirmation URL: Surveys and
Unmoderated Studies", "Unmoderated Research Methodology") and developer
documentation ("URL Parameters for Project Link", "Completion URL").

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
(`<environment>-outcomes-<outcome>.csv`, e.g. `main-outcomes-completed.csv`)
has one row for **every** response of the environment with that outcome, with
`response_id`, `outcome`, a column named after your id parameter (spelled as
in **Respondent id parameter**, e.g. `PROLIFIC_PID` or `respondent_user_id`)
holding each respondent's
provider id, `submitted_at`, `duration_seconds` (whole seconds from the
start of the interview to the response's last save; empty when unknown — the
start is the opening of the survey page on which the respondent began, in
that browser; a reload followed by **Resume**, or **Save locally and finish**
followed by **Resume**, keeps it, and **Start over**, or answering after a
reload without choosing **Resume**, starts the count again), `duplicate_id`
(`yes` when the id is on another response of the environment too, whatever
its outcome) and `fast_outlier` (`yes` on a completed, not screened-out
response more than 3 standard deviations below the mean duration of those
responses, each taken as the longer of `duration_seconds` and the time
between the response's first and last save in Studio; with 10 or fewer timed
responses, none is). If the download fails,
the toast reads "Could not download the outcomes." followed by the reason. Each download is recorded
in **Settings → Activity** as `outcomes.export`, since the provider ids leave
Studio with it.

Under the counts, a line says how many responses carry an id — **`972` of
`1,184` responses carry a `PROLIFIC_PID`;** (or "Set the id parameter to see
provider ids;" before you set one) — followed by "quota-full returns are not
counted here — the response is refused, the provider's count is the record."
Respondents turned away by a full quota cell or cap leave no completed
response, so the provider's own report is the reference for them. Someone who
was turned away after answering a page or two may still appear under
**partial**, with the progress the survey had saved.

More lines follow: "3 IDs appear on more than one response." when an id is on
more than one response (with Prolific saved as the provider: "… Prolific's
advice: keep one response for the analysis and approve the submission."); "Each
CSV lists every response’s duration_seconds and marks duplicate_id on a
response whose ID is on another response too, and fast_outlier on a completed
response more than 3 SD below the mean time."; with Prolific: "On
Prolific, check a submission without a stored response: an exceptionally
fast one may be rejected; otherwise message the participant, and approve it
when it looks like a technical problem."; and with Respondent: "On
Respondent, a participant is marked complete as soon as they reach the
completion URL, and Auto-Pay (on by default) pays the incentive 48 hours after
that; for projects created through Respondent's API, completion is marked 24
hours after they reach it. Review each completion before Auto-Pay pays it. A
participant listed under Completes without a completed response here: look
for their partial row in Data and message them through Respondent before
deciding. One who finished here but is not under Completes was not marked
complete: mark them in Respondent yourself."

Partial rows arrive only from a survey built with the current runtime; for one
published earlier, **partial** stays at 0 until you
[republish](Studio-Publishing-and-Environments#republishing) it.

Studio stores URL parameter names in lower case (`url_prolific_pid`), and the
outcomes match your id parameter regardless of case, so the upper-case ids of
the Prolific (`PROLIFIC_PID`) and Cint (`RID`) presets are found like any
other.

> **Tip.** To put the provider id next to the answers, export the `responses`
> table from **Data**: the export carries the id as a `url_<parameter>` column
> in lower case (`url_prolific_pid`, `url_rid`, `url_psid`), next to
> `__status` and `partial` (see [[Data Exports|Studio-Data-Exports]]). A flow
> with an **Export file** node does the same after cleaning. See
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
