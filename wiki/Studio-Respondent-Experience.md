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
  stopped collecting responses." instead of the survey, and then sends the
  respondent on to the environment's post-close redirect, if you set one.
- As the page opens, the survey asks Studio whether it is collecting. A
  survey that is paused, past its closing date or has reached its response cap
  shows its notice at once, before the first question (see
  [below](#paused-closed-and-full-surveys)). If Studio cannot be reached, the
  survey simply opens.
- With [One response per browser](Studio-Distribution-Channels#one-response-per-browser)
  on, a browser that has already answered sees "You have already taken part"
  instead of the questionnaire.
- A staged preview shows a bar along the bottom, "Preview — answers are not
  stored".

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
(HTML, shown above the questions — or the whole page, on a page without
questions) for the introduction, and a required question for consent, with a
branch to a **Screen-out** page for those who decline. If you set **Estimated
minutes** (Theme → Respondent experience), the first page says "About 6
minutes" under its title. See [[The Builder|Studio-Builder-Overview]] and
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
"This question requires an answer." under it and scrolls to it. A required
Matrix needs an answer in every row (a row answered "Not applicable"
counts): answered in some rows but not all, it shows "Please answer every
row." and marks the rows still empty until each is answered (see
[Matrix](Studio-Question-Types#matrix)). Format checks
(email, phone, web address, date, time) show their own messages. A Number
outside its range shows "Minimum value is 1" or "Maximum value is 10" when the
field is left and on **Next**, and a Multiple choice with **Min answers** and
too few options ticked shows "Select at least 1 more" — in both cases **Next**
waits until the answer is corrected. An exclusive answer such as "None of
these" is a whole answer on its own, so **Min answers** does not hold it, and
an optional question left empty can still be skipped.

**Progress.** Unless you hide it, a progress bar runs across the top of every
question page, with a section label beside it: "Welcome" on the first page the
respondent answers, "Section N of M" on the pages between and "Final thoughts"
on the last one. The same label stands above each page's title. The labels and
the bar count the question pages the respondent is shown, in the order they
see them: pages hidden by a **Show if** / **Hide if** and end pages (**Final**,
**Screen-out**, **Redirect**) are left out, so the last question page reads
"Final thoughts" with a full bar. A page that routing jumps over still counts,
so the bar can move in bigger steps on routed surveys. The settings are in
Builder → Theme → Appearance → Question style → **Progress**:

| Progress | Respondents see |
|---|---|
| **bar** (default) | the progress bar with its text |
| **dots** | only the page dots, one per question page, no bar |
| **both** | the bar and the dots |
| **hidden** | neither bar nor dots |

- **Section labels** (a checkbox in the same card) off: no label above the
  page title, and the text beside the bar reads "Page 2 of 5".
- **Progress text** off: the bar has no text.
- All these words can be changed in Theme → Wording.

**Page dots.** A dot goes back to a page the respondent has already been
through on the way to the current one; dots ahead, and dots of pages the
routing skipped, are greyed out and do nothing. With **Allow going back** off,
no dot goes back. Only pages actually visited are drawn as done.

The published survey follows these settings the same way the Builder's
previews do. An environment keeps the build it was last published with, so a
survey published before these rules keeps its older progress display — where
dots could jump forward past required questions — until you
[republish](Studio-Publishing-and-Environments#republishing) it.
See [[Theme and Branding|Studio-Theme-and-Branding]].

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
| `Enter` or `Space` (outside a text field) | next page (or submit on the last). Right after a mouse click on a button or link — a MaxDiff or Conjoint pick, a rating point, a matrix cell — the key still goes on, and every pick stays as it was clicked. Once the keyboard has brought the focus to a button or link (`Tab`, `Shift+Tab`, the arrow keys in a Matrix), the key does that control's own action instead: **← Previous** goes back, a rating point or a matrix cell is chosen, a chosen MaxDiff or Conjoint pick is released |
| `Enter` or `Space` on a video or audio player | the player's own keys (`Space` plays or pauses); they never go to the next page. The same holds for an expandable section or a widget in a page's own HTML, and typing in an editable area of it is like typing in a text field |
| `←` `→` / `↑` `↓` in a Matrix | move along the row, answering it with the cell reached (the N/A column included) / move to the same column in the row above or below; `Tab` leaves the grid. The cell in focus shows the focus ring, a chosen one included |
| `Enter`, `Space` or `↓` on a dropdown | opens its list, with the cursor in the search box. There `↓` / `↑` move through the options (starting from the chosen one), typing narrows the list to the matches and puts the cursor on the first, and `Enter` chooses the option and closes the list. `Esc` or `Tab` closes the list without choosing; `Esc` on the dropdown itself closes an open list rather than going back a page |
| `Esc` | previous page (when going back is allowed) |
| `1`–`9` (outside a text field) | picks that point on the page's first rating scale that has it, as a click does: the answer is autosaved and the question's error message goes. On a scale that starts at 0 the key is the point's number; a digit the scale does not have does nothing |
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
  with **Resume** (back to the page they left, along the path they took — in
  the same page order if your pages are shuffled) and **Start over**. After 24
  hours, or in another browser or device, they start from the beginning. Each
  survey keeps its own saved progress, so answers saved for one survey are
  never offered in another.
- **Once it is over.** When the interview is submitted, or ended by a full
  quota, the browser keeps no saved progress: reopening the link starts a new
  interview rather than offering to resume the finished one.
- **Leaving the page.** Closing or reloading the tab asks the browser's usual
  "Leave site?" question once the respondent has answered something in this
  sitting and the interview is still running — not for a survey they opened
  and left untouched.
- **To your database.** Each time the respondent moves to another page, and
  when they switch away from the tab, the answers so far are sent to Studio as
  a **partial** response (at most 60 times per visit). The final submission
  replaces that partial row, and an interview that has ended is never sent
  again as a partial, even if the thank-you page is reloaded. This is what
  feeds the drop-off funnel and lets an invitation show as `started`. It needs
  a reasonably modern browser; very old browsers send only the final
  submission. Progress saves and quota checks are rate-limited apart from
  submissions, so a class or an office answering from one network address
  does not use up what the final submissions need.

> **Note.** A survey published before the current runtime sends no partial
> responses and keeps one saved-progress slot shared by every survey on the
> survey host. Republish it to get the behavior above (see
> [Republishing](Studio-Publishing-and-Environments#republishing)); progress
> saved by the older build cannot be resumed in the new one.

---

## Submitting

On the last page, **Submit responses** shows "Submitting your responses…".
Then the thank-you page:

```
✓  Thank you for participating
   Thank you for your participation!

   Response ID   4817
   Submitted     6/4/2026, 2:41:07 PM
```

- The title and the message are yours to set (Builder → Theme → Respondent
  experience → **Completion screen** → **Title** and **Message**; the defaults
  are the two lines above). They are
  shown where the survey ends without text of its own — on **Submit
  responses**, or on a **Final (thank you)** page with no title or body; a
  Final page's own title and body win (see
  [Ending on a special page](#ending-on-a-special-page)). The words "Response
  ID" and "Submitted" can be changed in Theme → Wording.
- **Response ID** is the row number of the response — the `id` column in the
  Data tab. It is the simplest way for a respondent to identify their answers
  in a withdrawal or erasure request: ask them to note it, and see
  [Finding a respondent](Studio-Responses-and-Data#finding-a-respondent).
- If the survey redirects on completion (for example back to a panel), the
  page adds "You will be redirected in 5 seconds. Click here if not
  redirected."
- After completing, the same browser can start the survey again as a **new**
  respondent — unless the environment has
  [One response per browser](Studio-Distribution-Channels#one-response-per-browser)
  switched on, in which case reopening the link shows "You have already taken
  part". That check lives in the browser only: a private window or another
  device can still answer again, and
  [access codes](Studio-Distribution-Channels#access-codes) are reusable. For
  one answer per person, use personal links or your own checks in the
  analysis.

### Ending on a special page

| Page kind (Builder) | Respondent sees | Recorded as |
|---|---|---|
| **Final (thank you)** | the page's title and body (or the Completion screen's title and message) with Response ID | completed |
| **Screen-out** | the page's title (default "Thank you") and body (the Completion screen's message when the page has none) — no Response ID | submitted with `__status` = `screened_out` |
| **Redirect** | "Redirecting you now. Continue if you are not redirected." — then the page's URL after its delay (5 s by default) | completed |

Reaching one of these pages submits the response at once; any redirect happens
only after the response is stored. The title and body can pipe earlier answers
(`{answer:…}`, `{label:…}`). A screened-out response is stored even when the
response cap is full, and it does not count toward the cap or fill a quota
cell. Panel redirects are covered in
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
  **only kept in that browser** (for 24 hours) — they are **not submitted**; at
  most the progress the survey saved along the way reaches you, as a partial
  response. If a respondent tells you they used it, ask them to reopen the
  link in the same browser within 24 hours, **Resume**, and submit again.
- After the third failed attempt: "Submission error — We could not save your
  responses. Please refresh and try again."

---

## Paused, closed and full surveys

These notices cover the whole page. The survey checks its state **as the page
opens**, so someone who arrives at a paused, closed or full survey learns it
before answering anything. Someone who was already answering when the state
changed meets the same notice **when they submit** — or, for a pause or a
closing, in a survey with quotas, as soon as a quota check runs when they
leave a page.

| Situation | When the respondent sees it | Title | Text |
|---|---|---|---|
| Environment **paused** | on opening the link; at submit if they already had the page open | **This survey is paused** | "The researchers have paused collection. Please try again later." |
| Environment **closed** | on opening the link; at submit if they already had the page open | **This survey is closed** | "The researchers have stopped collecting responses." — then, after 3 seconds, the environment's post-close redirect if you set one (the static closed page also says "Redirecting you now. Continue if you are not redirected.") |
| **Closing date** passed | on opening the link; at submit if they already had the page open | **This survey is closed** | "The researchers have stopped collecting responses." — then, after 3 seconds, the post-close redirect if you set one |
| **Response cap** reached | on opening the link; at submit if they already had the page open | **Thank you for your interest** | "We have already reached our target sample for participants like you." — followed, after 3 seconds, by the panel's quota-full URL if you set one |
| **Quota cell** full | when they leave the page holding an answer whose cell is full | **Thank you for your interest** | the same text, plus "Redirecting you now. Continue if you are not redirected." when a quota-full URL is set; see [When a cell is full](Studio-Quotas-and-Randomization#when-a-cell-is-full) |
| **One response per browser**, already answered | on opening the link, or at submit in a second tab | **You have already taken part** | "This survey takes one response from each browser, and this browser has already sent one. Thank you!" |

A **preview** never shows these notices: it carries the banner "Preview —
answers are not stored" and ends on the survey's normal completion page.

A paused respondent's answers stay in their browser for 24 hours: if you resume
collection within that time and they reopen the link, they can pick up where
they left off. While a survey is paused, closed or past its closing date,
progress of unfinished interviews is not saved to your database either. If the
survey page cannot reach Studio as it opens, it opens normally, and the
submission is still checked.

The two "Thank you for your interest" texts follow Theme → Wording → **Quota
full: title** and **Quota full: text** when you reword them. The paused and
closed notices and "You have already taken part" are fixed English texts. See
[Deadlines](Studio-Publishing-and-Environments#deadlines) and
[Response caps](Studio-Publishing-and-Environments#response-caps).

> **Note.** The page-open check, the post-close redirect on the survey page,
> quota cells that stop respondents and One response per browser come with the
> current runtime. A survey published before it shows the paused, closed and
> cap notices only at submit, and lets everyone through a full quota cell,
> until you [republish](Studio-Publishing-and-Environments#republishing) it.

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
| `respondent_id` | a random identifier created in their browser to connect the partial and final saves (and to keep a seeded random draw, such as an assigned arm, the same after a reload); it is not derived from anything about the person, and the browser drops it when the interview ends |

**Not recorded:** IP address, browser or device details, location, keystrokes,
or which access code was entered. (Network addresses are used briefly to limit
abuse, and are not stored with responses. With the captcha on, the address is
also passed to Cloudflare to verify the check — see below.)

**In the respondent's browser**, the survey keeps the autosaved answers (24
hours, removed once the interview is submitted or ended by a full quota), the
random respondent id of an interview in progress, the time an interview in
this browser last ended, and the light/dark choice. With
[One response per browser](Studio-Distribution-Channels#one-response-per-browser)
on, it also notes that this browser has answered. Nothing of this is sent to
Studio beyond the responses themselves.

**Identifiable responses.** A response becomes linked to a person when the link
carried something personal: an [[email invitation|Studio-Email-Invitations]]
token (`url_inv`, which Studio matches to the contact), a panel id, or a
parameter you added yourself. Say so in your consent text.

**Captcha.** With the [captcha](Studio-Distribution-Channels#captcha) on, the
page loads Cloudflare Turnstile, which checks the browser invisibly when the
respondent submits. Cloudflare sees each respondent's IP address and browser,
and Studio sends Cloudflare the respondent's IP address with the token to
verify it. Name Cloudflare Turnstile in your privacy notice.

See also [[Security and Privacy|Studio-Security-and-Privacy]].

---

## Accessibility

- A **Skip to questionnaire** link is the first thing a keyboard user reaches.
- The questionnaire is a labeled main region; each page change is announced to
  screen readers ("Page 2 of 5"), and so is saving.
- The submission-failed dialog is a proper modal dialog; the light/dark button
  is labeled "Switch to dark mode" / "Switch to light mode".
- Every step works with the keyboard (see the table above), a Matrix and a
  searchable dropdown included. The control in keyboard focus always shows
  the focus ring, a chosen matrix cell or MaxDiff pick included. A dropdown's
  search box is announced as a combobox over its list of options, named
  after the question.
- When **Next** holds a required Matrix, the cells of its rows still without
  an answer are flagged as invalid to screen readers, as well as marked on
  screen.

---

## Changing the wording

Most fixed phrases can be reworded — or translated — in **Builder → Theme →
Wording**, grouped as **Buttons and navigation** (Next, Previous, Submit, the
section labels "Welcome", "Section {n} of {total}" and "Final thoughts",
"Page", "of", the estimated time), **Answering** (the required-question
message and a required matrix's "Please answer every row.", "Other", "None
of the above", "Not applicable", the range, format and too-few-choices
messages, and more), **Saving and resuming** ("Submitting your
responses…", "Saving…", the resume prompt and its buttons), **At the end**
("Response ID", "Submitted", the screen-out title, the redirect texts), **When
something fails** (the submission-failed dialog, its buttons and the error
screens), **Closed or full** (the quota-full title and text), **Around the
survey** (the Privacy and Contact links, the skip link) and **Access code**
(the gate's title, text, field, button and wrong-code message). In a text,
`{n}`, `{total}`, `{min}`, `{max}`, `{minutes}` and `{seconds}` are filled in
by the survey. The thank-you title and message are under **Theme →
Respondent experience → Completion screen**. The paused and closed notices
Studio shows, the static closed page and "You have already taken part" stay in
English; the **Survey closed** fields under **Closed or full** do not change
them. Screen-reader-only labels (the names of the page dots, "Loading
survey", the light/dark button) are English too. See
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
