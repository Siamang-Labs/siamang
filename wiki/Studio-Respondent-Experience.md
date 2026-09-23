# What Respondents See

This page follows a respondent from opening your link to the thank-you page:
what they see at each step, what happens when something goes wrong, and what
Studio records about them. Read it before you write your invitation and your
consent text, and use it to answer respondents' questions.

---

## Opening the link

- Respondents need **no account**. The survey is served from the survey host
  (`study.siamang.org`), which shares no cookies or session with the Studio app.
- Published surveys ask search engines not to index them.
- A link whose first build has not finished yet shows a plain "not found" page.
- A closed environment shows "This survey is closed — The researchers have
  stopped collecting responses." instead of the survey.
- A survey past the questionnaire's deadline still opens; the "closed" notice
  comes at submit (see [below](#paused-closed-and-full-surveys)).

What they see first depends on your setup: the access-code gate (if you use
codes), then your first page.

---

## The access-code gate

With [access codes](Studio-Distribution-Channels#access-codes) on, the survey
opens with:

```
Access required
Please enter the access code to begin this survey.
[ Enter access code ]   [Continue]
```

**Continue** is enabled once something is typed; **Enter** also submits. A code
that does not match exactly (including upper/lower case) shows "Invalid access
code. Please try again." A correct code opens the survey. The code is not stored
with the response.

---

## Intro and consent

There is no built-in welcome or consent step: the first page of your
questionnaire is the first thing respondents see. Use a page with a **Body**
(intro text above the questions) for the introduction, and a required question
for consent, with a branch to a **Screen-out** page for those who decline. See
[[The Builder|Studio-Builder-Overview]] and
[[Logic and Branching|Studio-Logic-and-Branching]].

Things your consent text should reflect (details below):

- progress is saved to your database **before** the respondent submits, so
  unfinished interviews are recorded;
- if you use personal links or panel ids, responses are linked to a person.

---

## Answering

```
┌────────────────────────────────────────────────┐
│  [logo]  Brand Awareness 2026                  │   header: logo, title, institution, subtitle
│          Institute of …                        │
├────────────────────────────────────────────────┤
│  1  How often do you …?  *                     │
│     ○ Never  ○ Rarely  ○ Sometimes  …          │
│                                                │
│  [← Previous]              [Next section →]    │
├────────────────────────────────────────────────┤
│  Institute · Privacy · Contact research team   │   footer
│                  (moon)                        │   light/dark switch
└────────────────────────────────────────────────┘
```

**Navigation.** **← Previous** and **Next section →** move between pages; on
the last page the button reads **Submit responses**. With **Allow going back**
turned off (Builder → Theme → Respondent experience), there is no Previous
button.

**Required questions.** Moving on with a required question unanswered shows
"This question requires an answer." under it and scrolls to it. Format checks
(email, phone, web address, date, time) show their own messages.

**Progress.** Unless you hide it, a progress bar runs across the top of every
question page. Beside it stands "Welcome" on the questionnaire's first page,
"Section N of M" on the pages after it and "Final thoughts" on its last page
(fixed English texts). These labels follow each page's position in the
questionnaire, end pages included, not the respondent's path: M counts the
end pages too, and because a **Final**, **Screen-out** or **Redirect** page
shows no bar, a survey that ends on one never shows "Final thoughts". Page
counts shift under branching, so the bar is approximate on routed surveys. The
setting is Builder → Theme → Appearance → **Progress**:

| Progress | Respondents see |
|---|---|
| **bar** (default) | the progress bar |
| **dots** or **both** | the progress bar and, under it, a row of dots, one per page |
| **hidden** | no progress bar; dots chosen earlier stay |

The published survey follows this setting the same way the Builder's previews
do. An environment keeps the build it was last published with, so one
published before Studio added the bar to published surveys usually shows none
until you republish it.
See [[Theme and Branding|Studio-Theme-and-Branding]].

> **Current limitation.** The page dots can be clicked, and a respondent can
> jump **forward** to any page, past unanswered required questions and your
> routing. Prefer **bar** when routing or required answers matter.

**Light and dark.** Unless you fixed the color mode (Theme → Respondent
experience → **Color mode**: **Always light** / **Always dark**), a small
moon/sun button under the survey switches between light and dark, and the
browser remembers the choice. See [[Theme and Branding|Studio-Theme-and-Branding]].

**Header and footer.** The header shows your logo or logo text, the survey
title (if **Show the survey title** is on), the institution and the study
subtitle. The footer shows the institution, a **Privacy** link (your **Privacy
URL**), **Contact research team** (your **Contact email**) and your ethics
statement, when you set them.

**Keyboard and touch.**

| Input | Does |
|---|---|
| `Enter` or `Space` (outside a text field) | next page (or submit on the last) |
| `Esc` | previous page (when going back is allowed) |
| `1`–`9` | picks that point on the page's first rating scale |
| swipe left / right | next / previous page on touch screens |

---

## Saving progress

Respondents can leave and come back — **in the same browser, within 24
hours**.

- **In the browser.** Two seconds after each answer the survey saves the
  answers in the browser's own storage (a small **Saving…** indicator
  appears). The saved answers are kept for 24 hours.
- **Coming back.** Reopening the link in that browser within 24 hours shows a
  banner: "We saved your progress from earlier. Would you like to resume?"
  with **Resume** (back to the page they left) and **Start over**. After 24
  hours, or in another browser or device, they start from the beginning.
- **Leaving the page.** Closing or reloading the tab with answers given asks
  the browser's usual "Leave site?" question.
- **To your database.** Each time the respondent moves to another page, and
  when they switch away from the tab, the answers so far are sent to Studio as
  a **partial** response (at most 60 times per visit). The final submission
  replaces that partial row. This is what feeds the drop-off funnel and lets an
  invitation show as `started`. It needs a reasonably modern browser; very old
  browsers send only the final submission.

---

## Submitting

On the last page, **Submit responses** shows "Submitting your responses…".
Then the thank-you page:

```
✓  Thank you for participating
   Your responses help inform open research.

   Response ID   4817
   Submitted     6/4/2026, 2:41:07 PM
```

- The message is yours to set (Builder → Theme → Respondent experience →
  **Completion screen** → **Message**). The title "Thank you for participating"
  cannot be changed there; for a title of your own, end the survey on a
  **Final (thank you)** page, whose title and body you write (see
  [Ending on a special page](#ending-on-a-special-page)).
- **Response ID** is the row number of the response — the `id` column in the
  Data tab. It is the simplest way for a respondent to identify their answers
  in a withdrawal or erasure request: ask them to note it, and see
  [Finding a respondent](Studio-Responses-and-Data#finding-a-respondent).
- If the survey redirects on completion (for example back to a panel), the
  page adds "You will be redirected in 5 seconds. Click here if not
  redirected."
- After completing, the same browser can start the survey again as a **new**
  respondent: nothing prevents someone from answering twice, other than
  [access codes](Studio-Distribution-Channels#access-codes) (which are
  reusable) or your own checks in the analysis.

### Ending on a special page

| Page kind (Builder) | Respondent sees | Recorded as |
|---|---|---|
| **Final (thank you)** | the page's title and body (or the default thank-you texts) with Response ID | completed |
| **Screen-out** | the page's title (default "Thank you") and body — no Response ID | submitted with `__status` = `screened_out` |
| **Redirect** | "Redirecting you now. Continue if you are not redirected." — then the page's URL after its delay (5 s by default) | completed |

Reaching one of these pages submits the response at once; any redirect happens
only after the response is stored. A screened-out response counts toward the
environment's response cap. Panel redirects are covered in
[[Panel Providers|Studio-Panel-Providers]].

---

## When submitting fails

If the answers cannot be saved (a network problem, a rejected captcha, or an
interview whose answers exceed 256 KB — a whole submission over 2 MB is
refused before it is even read), a dialog appears:

```
Submission failed
We could not save your responses. Attempt 1 of 3.
[Try again]   [Save locally and finish]
```

- **Try again** sends the answers again.
- **Save locally and finish** shows the thank-you page, but the answers are
  **only kept in that browser** (for 24 hours) — they **never reach you**. If a
  respondent tells you they used it, ask them to reopen the link in the same
  browser within 24 hours, **Resume**, and submit again.
- After the third failed attempt: "Submission error — We could not save your
  responses. Please refresh and try again."

---

## Paused, closed and full surveys

These notices cover the whole page. Most of them appear **when the respondent
submits** — not when they open the link — so someone can fill in the whole
questionnaire first.

| Situation | When the respondent sees it | Title | Text |
|---|---|---|---|
| Environment **paused** | at submit | **This survey is paused** | "The researchers have paused collection. Please try again later." |
| Environment **closed** | on opening the link; or at submit if they already had the page open | **This survey is closed** | "The researchers have stopped collecting responses." |
| Questionnaire **deadline** passed | at submit — the survey itself still opens | **This survey is closed** | "The researchers have stopped collecting responses." |
| **Response cap** reached | at submit | **Thank you for your interest** | "We have already reached our target sample for participants like you." — followed, after 3 seconds, by the panel's quota-full URL if you set one |
| **Preview** deployment | at submit | the "Submission failed" dialog | previews never collect |

A paused respondent's answers stay in their browser for 24 hours: if you resume
collection within that time and they reopen the link, they can pick up where
they left off. While a survey is paused, closed or past its deadline, progress
of unfinished interviews is not saved to your database either. These notices
are fixed texts and cannot be reworded. See
[Deadlines](Studio-Publishing-and-Environments#deadlines).

> **Current limitation.** Full quota cells do not yet turn respondents away;
> only the environment's response cap does. See
> [Response caps](Studio-Publishing-and-Environments#response-caps).

---

## What is recorded about respondents

| Recorded | Detail |
|---|---|
| Answers | one field per variable (see [[Responses and the Data Tab\|Studio-Responses-and-Data]]) |
| `started_at`, `duration_seconds` | when the page was opened, and how long until submission |
| `last_page` | the page they were on |
| URL parameters | `url_<name>` for up to 8 parameters of the link (a panel id, a source tag, an invitation token) |
| `tab_switches`, `hidden_seconds`, `pastes` | how often they left the tab, for how long in total, and how many times they pasted — counts only, no content |
| `captcha` | `pass` or `unavailable`, when the captcha is on |
| `respondent_id` | a random identifier created in their browser to connect the partial and final saves; it is not derived from anything about the person |

**Not recorded:** IP address, browser or device details, location, keystrokes,
or which access code was entered. (Network addresses are used briefly to limit
abuse, and are not stored with responses.)

**In the respondent's browser**, the survey keeps the autosaved answers (24
hours), the random respondent id and the light/dark choice.

**Identifiable responses.** A response becomes linked to a person when the link
carried something personal: an [[email invitation|Studio-Email-Invitations]]
token (`url_inv`, which Studio matches to the contact), a panel id, or a
parameter you added yourself. Say so in your consent text.

**Captcha.** With the [captcha](Studio-Distribution-Channels#captcha) on, the
page loads Cloudflare Turnstile, which checks the browser invisibly when the
respondent submits.

See also [[Security and Privacy|Studio-Security-and-Privacy]].

---

## Accessibility

- A **Skip to questionnaire** link is the first thing a keyboard user reaches.
- The questionnaire is a labeled main region; each page change is announced to
  screen readers ("Page 2 of 5"), and so is saving.
- The submission-failed dialog is a proper modal dialog; the light/dark button
  is labeled "Switch to dark mode" / "Switch to light mode".
- Every step works with the keyboard (see the table above).

---

## Changing the wording

Most fixed phrases can be reworded — or translated — in **Builder → Theme →
Wording**, grouped as **Buttons and navigation** (Next, Previous, Submit,
"Page", "of"), **Answering** (the required-question message and more),
**Saving and resuming** ("Submitting your responses…", "Saving…", the resume
prompt and its buttons), **When something fails** (the submission-failed dialog
and its buttons) and **Access code** (the gate's title, text, field and
button). The thank-you message is under **Theme → Respondent experience →
Completion screen**; the thank-you title, the progress labels ("Welcome",
"Section N of M", "Final thoughts") and the paused, closed and cap notices
cannot be changed. See
[[Theme and Branding|Studio-Theme-and-Branding]].

## See also

- [[Links, QR Codes, Embeds and Access Control|Studio-Distribution-Channels]]
- [[Publishing and Environments|Studio-Publishing-and-Environments]]
- [[Theme and Branding|Studio-Theme-and-Branding]]
- [[Responses and the Data Tab|Studio-Responses-and-Data]]
- [[Security and Privacy|Studio-Security-and-Privacy]]

<!-- studio-nav -->
---

← [[Email Invitations|Studio-Email-Invitations]] · [Studio contents](Studio-Overview#all-pages) · [[Live Monitoring|Studio-Live-Monitoring]] →
