# FAQ and Troubleshooting

Quick answers to the questions people ask most, and fixes for the messages
you are most likely to see. Each answer links to the page with the full story.
Messages are quoted exactly as Studio shows them.

---

## Account and access

**I never got the confirmation email.**
Check spam, and make sure you typed the address correctly. You can also sign in
with **Continue with Google** or **Continue with Microsoft** for the same
address. Still nothing: write to `info@siamang-team.org`.
→ [[Sign Up and Sign In|Studio-Sign-Up-and-Sign-In]]

**A confirmation or password-reset link opened the app instead of a form.**
You were already signed in, and the sign-in page sends signed-in people to the
app. Sign out (or use a private window) and open the link again.

**"Could not check your email. …" on the sign-in card.**
Studio looks up the address before it asks for a password, and that lookup
failed. The message says why — for example "Too many sign-in attempts from
your network just now — wait a minute and try again." (more than 10 attempts
in a minute for the same address, or 20 from one network across all
addresses; a busy office or campus network can reach that) or "The server
could not be reached — check your connection and try again." Wait a moment
and press **Continue** again. A failed lookup never sends you to **Create
your account**: only a definite "no account" does.

**"Your session expired. Please sign in again."**
Sign in again: Studio opens the screen you were on. Unsaved Builder and flow
edits are kept as your server-side draft and come back when you reopen the
editor.

**Signing in or creating an account says the browser blocks cookies and site data.**
Studio keeps your sign-in in the browser. Allow cookies and site data for the
Studio site (in a private window too), reload the sign-in page, and sign in
again. If the message came after **Create account**, the account already
exists: sign in with it.
→ [Troubleshooting](Studio-Sign-Up-and-Sign-In#troubleshooting)

**I created my account from a colleague's invitation. Where am I?**
In your colleague's organization: the invitation is accepted as your account
is created, and the invitation link takes you straight into the inviting
organization. You also get an organization of your own, on its own trial;
switch between the two with the workspace chip in the topbar. If the
invitation page says "Could not load the invitation." followed by a reason,
the server was busy or could not be reached — the link itself is fine; press
**Try again**. "This invitation has expired. …" and "This invitation link is
invalid or has already been used." are about the link itself: ask for a new
invitation. The second one can also mean you were already added to the
organization directly: sign in and open the link again, or pick the
organization in the workspace chip.
→ [If you create your account from the invitation](Studio-Sign-Up-and-Sign-In#if-you-create-your-account-from-the-invitation)

**I landed in my own workspace, not my colleague's.**
After sign-in Studio opens your oldest membership. If you had an account
before you were invited, that is your own workspace; switch with the
workspace chip. → [[Organizations and Team|Studio-Organizations-and-Team]]

**How do I create a second organization?**
Open the workspace chip in the topbar and choose **Create organization** (the
**Organizations** screen has the same button). The dialog shows the address
the organization will get, checked with the server so that it is free. The
new organization starts on the **Free** plan with you as its owner, and the
topbar shows no trial pill in it — the Pro trial comes once per email
address, with the organization you got at sign-up.
→ [Creating another organization](Studio-Organizations-and-Team#creating-another-organization)

**"Could not update profile. Name must be 200 characters or fewer." (or another
"… must be …" message).**
The server refused a value you entered. The message names the field as the
form labels it and says the rule it broke: a length ("must be 200 characters
or fewer"), a required value ("is required"), a number range ("must be at most
730") or a format ("is not in a form Studio accepts"). Most fields stop at
their limit as you type, so you rarely see these messages; correct the field
it names and try again.
→ [[Limits and Quotas at a Glance|Studio-Limits-Reference]]

**"Only owners and admins can create projects" (or rename a project, add a
secret, run a connector).**
Your role in this organization is **member**. Members build, publish and
analyze, but creating, renaming and deleting projects, adding or deleting
secrets, running connectors, deleting responses, managing webhooks, deleting
a library item another member saved and reading the organization's
**Activity** are for owners and admins; those controls are disabled or hidden
for you, and hovering a disabled one says who can use it. Ask an owner or
admin, or to be made an admin.
→ [Things members may notice](Studio-Organizations-and-Team#things-members-may-notice)

**My trial ended. What changed?**
The organization is now on the **Free** plan, or on Plus if Plus or the Plus
year was bought for after the trial. Nothing is deleted. On Free, surveys
keep collecting within Free limits — 1,000 completed interviews per project,
all its environments together, counting the ones it already has; you cannot
add projects or members beyond Free's caps, schedules and live recomputation
stop, and Saves with custom JavaScript or CSS can no longer be published.
→ [[Plans, Trial and Billing|Studio-Plans-and-Billing]]

**"This workspace is frozen and read-only."**
Support has frozen the organization. Everything stays viewable and
exportable; contact support to resolve it. (This is not what happens at the
end of a trial.)

---

## Building the questionnaire

**My show-if / branch rule / piping does nothing in the published survey.**
Conditions, piping and quotas read a question's **variable name**, and the
answer is stored under that name, so the question's Id does not matter. Check,
in this order:

- **An old build.** A published survey keeps the runtime it was built with.
  Several things only work in a survey built with the current one: logic on
  a question whose Id differs from its variable (every preset, `q5` /
  `nps_5` — earlier builds stored the answer under the Id), conditions on a
  Matrix row, a MaxDiff or Conjoint task, or a per-choice variable of a wide
  Multiple choice (`brands_1 = 1`), `{label:…}` showing a label rather than a
  code, and piping in the title and body of Final, Screen-out and Redirect
  pages. **Save** (with nothing changed, Save re-validates with the current
  engine) and press **Republish #N** on the environment's card.
- **A name inside custom JavaScript.** Renaming a variable in the Builder
  updates the conditions, branch rules, quotas, piping, script targets and
  `answers.<name>` accesses that use it, but a string in custom code that
  merely holds the name is not changed — edit it yourself.
- **The rule itself.** Take the path in **Test → Walkthrough**: the side panel
  shows which conditions fired.

→ [Question Id and variable name](Studio-Builder-Overview#question-id-and-variable-name)

**"Question '…' has the id under which question '…' stores its answer".**
One question's **Id** is another question's variable name, so the survey
could not tell which one a script or a **Skip to** means. Change that Id
(**Advanced → Id**) or rename one of the variables, then Save. "Duplicate
answer key in questionnaire: questions '…' and '…' both store their answer
under '…'" is the same clash with a Matrix, MaxDiff, Conjoint or wide Multiple
choice, which store their answers under their Id: change that question's Id.
Studio now catches both before you save: the **Id** field shows "Another
question already has this id." or "This is the variable … stores its answer
under — the engine refuses an id that is another question’s variable.", and
**Validation → Structure** lists the question. New questions never get such
an Id; you meet this after typing one, or in an imported or older document.

**"Question '…' stores its answer under '…', but '…' is also …".**
The question's **Id** differs from its variable and is a name the survey
stores something else under: a Matrix row or another variable of a question
("…is also a variable question 'grid' stores an answer under"), another
question's Other text ("…the key question 'brand' stores its “Other (please
specify)” text under"), the arm an **Assign to a condition** writes, a
codebook variable a custom script writes, or a name starting with `__`.
Studio translates a script's `answers["<id>"]` to the question's variable, so
a script meaning the other thing would reach the question instead. Change
the question's **Advanced → Id**, then Save. The **Id** field and
**Validation → Structure** say which name it is before you save. One
exception: when the name is a codebook entry an earlier Builder left behind
on renaming the question's variable, and an older script prefills the
question by its Id (`answers.q2 = …`), delete that entry in **Builder →
Codebook** instead — the message then says so too ("…or, if the codebook
entry 'q2' is left over from renaming this question's variable, delete that
entry…"). A new Id would leave the script writing the entry.
→ [Names an Id may not take](Studio-Builder-Overview#names-an-id-may-not-take)

**"…the codebook still declares a variable "q2" that no question collects and nothing writes…" in Validation → Structure.**
An earlier version of the Builder left the old codebook entry behind when
you renamed the question's variable or deleted the question. The Id is fine:
delete the entry in **Builder → Codebook**, where it is listed **unused**.
Deleting a question now takes its entries along, except those something
still refers to or that label answers already collected; the Codebook lists
those as **referred to by …** or **answers collected**, and the Save's
`UNUSED_VARIABLE` warning for them is expected.
→ [When a question is deleted](Studio-Codebook-and-Variables#when-a-question-is-deleted)

**My variable label changed when I edited the question text.**
A variable's label follows the question — its text, a Matrix statement, a
wide choice — for as long as it is the label Studio gave it, so a label that
read "q8" becomes "How often do you drive?" as you type. One **Undo**
restores both. Write a label of your own in the **Variable** section or the
Codebook tab and it stays, whatever you change in the question afterward.
→ [Labels that follow the question](Studio-Codebook-and-Variables#labels-that-follow-the-question)

**I deleted a question, but its variable is still in the Codebook.**
Its entry stayed because something still refers to it — the Codebook's
**Used by** reads "referred to by …" — or because the survey has been
published and exports label the answers already collected under it (**answers
collected**). The message after the deletion said which. Change what refers
to it first if that is left over too, then **Delete** the entry; Studio asks
before deleting such an entry.
→ [When a question is deleted](Studio-Codebook-and-Variables#when-a-question-is-deleted)

**A branch rule never fires.**
A rule with an empty condition never matches — it is not an "otherwise".
**+ Rule** no longer adds a rule until its condition is complete (**Add
rule** stays disabled), but a rule can lose its condition (**Clear**) or
arrive without one from an import. Studio says so under the rule ("Add a
condition — an empty rule never fires."), on the Logic map ("no condition —
never fires") and in **Validation → Structure**. Give it a condition, or use
**Default next** for "everyone else". Also check the page for a **Skip to**:
it is checked before the page's branch rules, so for anyone who answers that
question no rule fires.
→ [[Logic and Branching|Studio-Logic-and-Branching]]

**Respondents cannot get past a Matrix: "Please answer every row."**
**Required** on a Matrix asks for an answer in every row; a row answered
"Not applicable" counts. **Next** marks the rows still empty. If only some
rows matter, turn **Required** off, or turn on **Offer “N/A”** so that
respondents can answer the rest with it. A survey published before this rule
lets respondents on after one row until you republish it.
→ [Matrix](Studio-Question-Types#matrix)

**Skip to jumps for every answer, not just one.**
That is how **Skip to** works (its hint: "on Next, after any answer to this
question — checked before the page’s Branch rules"): when the question is
answered, Next goes to the chosen page. For a jump that depends on the
answer, use a **Branch (next if)** rule on the page.

**How do I enter missing codes?**
In **Builder → Codebook**, open the variable's row and type each code followed
by its label, separated by commas: `-9 Refused, -8 Don't know` (`-7=Not asked`
works too). A code typed without a label borrows the value label for that
code, or is labeled `Missing (<code>)`.
→ [Missing codes](Studio-Codebook-and-Variables#missing-codes)

**I want one 0/1 column per option of a Multiple choice question.**
**Options → Data layout → wide** turns the question into one 0/1 variable
per choice (`brands_1`, `brands_2`, …; a question whose options come from its
variable's value labels gets them as its choices first) and keeps them in step
with the choices; **array** turns them back into one variable. A published
survey stores each chosen option's variable as `1` and the others as `0` once
the question is answered (an option hidden by its own condition stays empty),
exclusive choices such as "None of these" clear the others, and conditions and
quotas on `brands_1 = 1` work. A survey published before this worked needs to
be published again; its earlier answers are read as 1/0 columns in Data and
exports. → [Multiple-choice layouts](Studio-Codebook-and-Variables#multiple-choice-layouts)

**What are the `-66`, `-77` and `<variable>_other` values in my data?**
The codes of the answers added with a switch: "Other (please specify)" is
stored as `-66` in the question's column, with the typed text in
`<variable>_other`; "None of the above" is `-77`; "Not applicable" is `-1`,
declared as a missing code (where the codebook declares no such code, N/A is
stored as the text `na`). The Inspector's hint beside each switch says what
is stored ("stored as -66; the text goes to brand_other"), and the codebook
labels the codes. A choice that already uses one of these codes pushes the
added answer to the next free one (`-67`). Responses collected before these
codes were written are read the same way (older exports showed `__other__`,
`__none__` or `code` / `text` columns instead).
→ [Codes for Other, None of the above and N/A](Studio-Question-Types#codes-for-other-none-of-the-above-and-na)

**How do I change the title of the completion screen?**
**Theme → Respondent experience → Completion screen → Title** (the default
is "Thank you for participating") and **Message**. They are shown where the
survey ends without its own ending text: on **Submit** of a question page, or
on a Final page with no title (or body). A Final page's own **Title** and
**Body** win, and the hints beside the two fields say so. Save and publish
again. → [Completion screen](Studio-Theme-and-Branding#completion-screen)

**"…references unknown variables: …" and the Save is `errors`.**
A condition names a variable that nothing in the questionnaire writes: no
question collects it, no **Assign to a condition** script assigns it, and the
codebook does not declare it. Usually it is a typo or a variable that no
longer exists. Conditions may read the arm of **Assign to a condition** and
variables declared only in the codebook (for example a value your custom
JavaScript writes), but not URL parameters.
→ [Assignment and "embedded data"](Studio-Logic-and-Branching#assignment-and-embedded-data)

**The Save badge says `errors`.**
Click it (it opens the Save in History) or open **Builder → Validation**. The
questionnaire does not pass the engine's validation (for example a page
nothing leads to, or a quota on an unknown variable), and such a Save cannot
be published. Red lint findings such as `EMPTY_PAGE` leave the badge at
`warnings` — the Save toast says "Saved #N — the questionnaire has 1 error
(see Builder → Validation)" — and can be published after the confirmation
"Publish #N with errors" → **Publish anyway**. A flow with errors leaves the
badge at `warnings` too.
→ [What blocks publishing](Studio-Testing-Your-Survey#what-blocks-publishing)

**"Unreachable pages in navigation graph" or "Cycle detected in page navigation graph."**
Open **Logic map → Pages**: some page has no route leading to it, or routing
loops back. Wire the page up (or delete it), or break the loop.

**A condition says it "can never be true".**
It reads an answer given later in the interview. Move the question earlier or
the condition later.

**My page's Body text does not appear.**
A page's **Body** is shown on every kind of page except a Redirect page: on a
page with questions, above them. It is HTML, not Markdown — Markdown marks
such as `**` appear as typed. A survey published before the Body was shown on
question pages shows it there only after you publish it again: **Save**, then
**Republish #N**. A text-only page (a Body and no questions) made in the
Builder before this update showed respondents only its title: make any edit
in the Builder — Studio then stores the page so that its Body is shown — and
**Save** and republish.

**Piping shows `{answer:x}` literally.**
The variable name is wrong (piping uses the variable name, not the question's
Id), or the question has not been answered yet at that point. In a survey
published before piping worked in the title and body of Final, Screen-out and
Redirect pages, those pages show the placeholder until you publish again.

**I renamed a variable and a flow broke.**
Renaming a variable in the Builder updates the questionnaire — conditions,
branch rules, quotas, piping and scripts — but not your flows: a node
parameter that names the old variable now names one the codebook does not
have. Update the flow, or rename back. Once the survey is in the field,
answers are stored under the variable name, so renaming a variable and
republishing leaves you with two columns (see *Two columns where I expect
one* below); on a published questionnaire the Inspector's **Variable**
section says so: "This questionnaire has been published. Renaming a variable
renames its column in the data: answers already collected keep the old name,
answers collected after you publish again get the new one."

**I cannot edit — "*Name* is editing".**
A colleague holds the edit lock; you are following their draft live. **Take
over** claims the lock, or leave a comment. → [[Working Together|Studio-Collaboration]]

**"Apply or revert your source edits before saving."**
You changed the JSON in **More ▾ → Source**. Press **Apply** (or **Revert**)
there, then Save.

---

## Publishing and fieldwork

**The Publish button is disabled.**
The panel says why: the project has never been saved, the current Save has
errors (its questionnaire does not validate), or the environment already runs
that Save ("…nothing to publish"). A flow with errors does not stop
publishing, and a Save with lint errors or warnings is published after a
confirmation.

**My survey was published before the latest Studio update. Do I need to do
anything?**
Publish it again: **Save** (a Save with nothing changed will do), then
**Republish #N** on the environment's card. A deployment keeps the survey
runtime it was built with, so until then it lacks, among other things:
quota cells that stop respondents, the closed / paused / full notice as the
page opens, **One per browser**, partial responses and the drop-off funnel,
the page Body above the questions, "About N minutes", the completion
**Title**, the newer Wording fields, auto-height in the script embed,
option shuffles that keep "None of the above" in place, a required Matrix
that asks for every row, answering a Matrix row by row from the keyboard,
answers that say they are keyed by variable name, so Studio stores them
exactly as sent, fonts served from the survey host instead of Google Fonts, a
captcha that loads only at submit and sends its token (an older build marks
every response `captcha: unavailable`), and browser storage that waits for
the respondent to start and lasts a week instead of 24 hours. Responses it
already collected need nothing: Data, exports and flows read them in today's
layout.
The one exception is a quota cell on a Matrix row or on a per-choice variable
of a wide Multiple choice: it counts only responses collected after the
republish.
→ [Older surveys and responses](Studio-Question-Types#older-surveys-and-responses)

**"Custom JavaScript in the questionnaire is included from Plus…" / "Custom CSS in the theme is included from Plus…"**
Your plan does not include custom code in published surveys. Remove the script
or the custom CSS, or upgrade. → [[Plans, Trial and Billing|Studio-Plans-and-Billing]]

**I published but the link shows the old questions.**
Check that the card's `#N` is the Save you expect — press **Republish #N** if
not — and hard-refresh the page (browsers cache survey files).

**The published survey's progress indicator differs from the preview.**
Published surveys follow **Theme → Progress** (**bar**, **dots**, **both** or
**hidden**; the bar when you never chose), like the Builder's previews:
**bar** shows only the bar and its text, **dots** only the page dots,
**hidden** nothing at all. **Section labels** and **Progress text** switch off
the words above the page title and beside the bar. A survey published with an
earlier version of Studio can show a different indicator until you publish it
again — **Save**, then **Republish #N**.
→ [Question style and progress](Studio-Theme-and-Branding#question-style-and-progress)

**A quota cell is full but respondents keep coming.**
A full cell stops only the respondents whose answer falls into it, when they
leave the page with that answer; everyone else goes on. If people with that
answer still get through:

- the survey was published before quota cells closed — publish it again;
- you are looking at a **preview**: previews never check quotas;
- the count includes only **completed** interviews — screen-outs and
  unfinished interviews do not fill a cell, so a cell can show fewer than you
  expect;
- they left that page before the cell filled: each answer is checked once,
  when its page is left, and the submission does not check quota cells again,
  so a cell can end a little over its limit;
- the server did not answer the check within 4 seconds — the respondent is
  let through and checked again on a later page.

→ [When a cell is full](Studio-Quotas-and-Randomization#when-a-cell-is-full)

**The survey closed on its date. How do I extend it?**
Once the closing date passes, the card reads **○ Closed** ("Closed —
deadline passed *date*") and anyone who opens the link sees "This survey is
closed". Press **Extend** on the card, pick a later date and **Extend to this
date**: the survey collects again at once, without a new Save or a rebuild.
The date can come from the questionnaire's deadline, the environment's
`closes_at` in `studio/settings.json` (the earlier of the two wins), or the
**Closing date** chip. → [Set or extend a closing date](Studio-Recipes#set-or-extend-a-closing-date)

**Respondents answered everything and then saw "This survey is paused" / "This survey is closed" / "Thank you for your interest…".**
The survey page checks as it opens whether the environment is paused, closed
(by **Close** or its closing date) or full (a response cap reached), and shows
the notice at once. Someone who already had the survey open when that
happened meets it when they submit, and their interview is not stored as
completed. Resume, extend the closing date, or raise the cap (new projects cap
`main` at 1,200 and `pilot` at 50 completed interviews; on Free the project
stops at 1,000). A survey published before the check as the page opens shows
these notices only at submit until you publish it again.
→ [Paused, closed and full surveys](Studio-Respondent-Experience#paused-closed-and-full-surveys)

**The count is not moving.**
Check you are looking at the right environment, that it is not paused or
closed, and that interviews are being *completed*. With a cap, the
**Responses** tile and bar count completed interviews only — partials and
screen-outs show in Data but not there (the tooltip gives the total of all
rows).

**The build failed.**
Open **Build log** on the card. If a republish failed, the previous version is
still serving the link. Fix the cause, **Save**, and publish again. A failed
card with no earlier version still live behind it offers **Deploy current
Save #N** (**Retry Save #N** when the failed build was already the current
Save).

**Access codes are not asked for.**
Generating codes creates a new Save; republish the environment.

**The header "Preview" survey shows "Preview — answers are not stored".**
That is what a preview build is: it never stores answers, says so in a banner
at the bottom, and ends on the survey's normal completion page. A preview
built before this banner existed ends with "Submission failed" instead;
**Preview** again to rebuild it. To test real submissions, use the `pilot`
environment. → [[Testing Your Survey|Studio-Testing-Your-Survey]]

**Where do I get the panel ids to reconcile with Prolific / Cint?**
From **Outcomes · reconcile with the provider** at the end of the **Panel**
chip on a live environment's card: its completed, screened-out and partial
CSVs list each respondent's provider id, for every response of that outcome.
The id parameter is matched however it is capitalized (`PROLIFIC_PID`, `RID`).
→ [Reconciling outcomes](Studio-Panel-Providers#reconciling-outcomes)

---

## Data

**The numbers in Data and in my flow disagree.**
Data counts every row — all environments, partials, screen-outs. Flows usually
filter (environment, **Only completed responses**, dedup, speeders, filters).
Run to each node and watch the row count.

**I cannot find a response in the grid.**
The grid loads the **newest** 100 rows of a table (25 per page), and typing
in **Filter loaded rows…** narrows those rows only. Press `Enter` (or **Search
all rows**) to search **every** row of the table on the server: a row
matches when any of its values contains the text — an answer, the response
`id`, the `respondent_id`, or a panel id or invitation token in `meta`. The
note then reads "N rows of the whole table match “…”", with the newest 100
matches loaded; **Clear search** goes back. To delete the row you find, see
[Handle a data erasure request](Studio-Recipes#handle-a-data-erasure-request).

**Where are the URL parameters and durations in my export?**
In columns of their own, after the answers: `url_<name>` for each link
parameter (up to 8), `duration_s`, `started_at`, `captcha`, `tab_switches`,
`hidden_seconds` and `pastes` — in every format of **Export ▾**, and in flows
under the same names. The Data grid itself still shows them together in the
`meta` column. An export you downloaded before this change has no such
columns; export again. → [[Data Exports|Studio-Data-Exports]]

**My matrix answers changed from 1–11 to 0–10.**
A Matrix answer is its column's code from the codebook: a 0–10 scale stores
0–10. Surveys built before this stored the column's position (1–11); Data,
exports and flows now read those older responses as the column's code too, so
old and new responses sit on one scale. An export or a flow result you made
before therefore differs from one you make now. Surveys published before the
change store positions until you publish them again, and are read correctly
either way.
→ [Older surveys and responses](Studio-Question-Types#older-surveys-and-responses)

**SPSS labels are missing or look wrong.**
Exports are labeled with the **current** Save's codebook. Fill in labels in
**Builder → Codebook**, Save, and export again.

**Two columns where I expect one.**
Usually a variable was renamed mid-fieldwork. Another cause: a column named
like a question's Id (`q5`) next to its variable (`nps_5`). Earlier versions
of Studio stored answers under the question's Id; Studio has since moved
those answers to the variable name, except where the move could have mixed
two questions' answers — those stay under the Id. Either way, harmonize the
two in a flow with **Recode** or **Derive** rather than editing the raw
table.

**Can the same person answer twice? Why is there no "respondents" count?**
Studio does not identify people, so every interview is a response of its own.
The totals on **Data → Insights** and **Live** therefore read **responses**
(every row: completed, screened-out and partial) and **completed** (submitted
interviews that did not end on a screen-out page — what quota cells and
response caps count). To refuse a second interview from the same browser,
switch on **One per browser** on the environment's card; for one answer per
person, use email invitations or a panel's own checks.
→ [Accept one response per browser](Studio-Recipes#accept-one-response-per-browser)

**There is no Delete button on the rows.**
Only owners and admins can delete responses, so only they see **Delete** on
the rows of the `responses` table. Ask one of them to handle the request.

**I deleted a response. What else changed?**
The response counts and any quota cell it had filled go down: the survey's
cells are recounted from the responses that remain. The deletion is recorded
in the Activity log, without the response's content.

---

## Flows and reports

**"Could not start the preview. The preview limit for this hour is reached on your plan."**
**Run to here** is limited per person per project per hour (Free 30, Plus 120,
Pro 600). Wait, or use **Run**. "…A preview is already running" — wait for it
to finish.

**A flow shows a red "errors" pill and its Run button is disabled.**
The flow did not pass the engine check at the current Save, so it was saved
without code and cannot run ("Fix this flow's errors and save first"). The
pill's tooltip lists the errors node by node, and opening the flow shows them
in a banner. Only that flow is affected: the questionnaire can be published,
and the other flows, **Run all** and previews work — in Run all it fails with
"flow '*name*' did not pass the engine check at Save #N, so it has no script
to run: open it, fix its errors and save". Press **Check**, fix what it
lists and **Save**. → [A flow with errors](Studio-Flows#a-flow-with-errors)

**"edges/*N*/from: Additional properties are not allowed ('title', 'type' were unexpected)".**
An earlier version of Studio saved an output added with **+ Add output** in
the **Report** view in a form the engine rejects. Open the flow: Studio
repairs its connections and says "Studio repaired this flow's connections."
Click **Save changes**, and the flow runs again.
→ [A flow with errors](Studio-Flows#a-flow-with-errors)

**In what order does Run all run my flows?**
In dependency order: a flow that reads a table another flow writes (through a
**Project table** node, or a **Responses** node set to that table) runs after
the flow with the **Write table** node. Flows that do not depend on each other
run in alphabetical order of their names; you do not need to name flows so
that a writer sorts first. The flows table, the pipeline strip and the **Run
flow** dialog list the flows in that order. Flows that read each other's
tables get an amber **cycle** pill and run one after another in alphabetical
order. → [Run all](Studio-Flows#run-all)

**Run all failed, but some flows ran.**
One failed flow does not stop the run. The others still run, except those
that read a table the failed flow did not write — their log line reads
"skipped: needs *flow*, which failed". The run ends as failed (its last log
line, "failed: *names*", lists them), and **View logs** lists every flow as
ok or failed, with each error. The flows that succeeded keep their reports
under **Reports**, and the combined report is written anyway, titled
"Combined report (incomplete)": its first section, "Missing from this
report", names each missing flow and why. Fix the flows it names and run all
flows again for the complete report.

**The Schedules section shows "Requires Plus" instead of "Schedule a run".**
Schedules are available from the Plus plan ("Schedules are available from the
Plus plan"); on Free the button opens the plans. Run flows by hand, or
upgrade. → [[Schedules and Webhooks|Studio-Schedules-and-Webhooks]]

**How do I delete, rename or duplicate a flow?**
With the **⋮** at the end of its row on **Flows** (**Rename…**,
**Duplicate…**, **Delete…**) or the editor's **More ▾** (**Rename flow…**,
**Duplicate flow…**, **Delete flow…**). Each is a Save of its own, so
restoring an earlier Save undoes it. A rename moves the flow's schedules and
comments; a delete pauses its schedules; past runs and reports keep the old
name. → [Rename, duplicate or delete a flow](Studio-Recipes#rename-duplicate-or-delete-a-flow)

**"*flow* has unsaved changes. Open it and save them (or undo them) first …"**
A rename takes the flow as it was last saved, so Studio refuses it while you
have unsaved changes to that flow. Save (or undo) them, then rename.

**My Data file node cannot find the file I uploaded.**
Choose it by name in the node's **File** list, or upload it from there with
**Upload…**. Files may store a file under another name than it had on your
computer (`Опрос.csv` becomes `Opros.csv`); the Upload dialog says the stored
name before you upload. A value saved earlier as a path, such as
`./assets/panel_wave2.csv`, shows under "Other location, kept as it was
written" — "A run only brings in files uploaded under Files, so it won't
find this one." — with **Use the uploaded panel_wave2.csv** when Files has
it. An upload deleted since shows as "*name* — not in Files". If the run log
says "note: assets/*name* is not among this project's Files", the name is
wrong or the file was deleted.
→ [Where files go](Studio-Node-Reference#where-files-go) · [[Files|Studio-Files]]

**The topbar and the project tabs are gone in the flow editor.**
Focus mode is on: it gives the **Canvas** view the whole window. Press `F`
(outside a text field), or `Esc` once nothing is selected, or click **Focus
mode** under the canvas's zoom buttons ("Exit focus mode (F or Esc)").
**List** and **Report** always show the topbar and tabs, and so does every
screen outside the editor; the Save badge sits beside the flow's name while
the mode is on. Studio remembers the choice in this browser.
→ [Focus mode](Studio-Flows#focus-mode)

**Can Run to here change a project table?**
No. A preview never writes project tables: a **Write table** node it reaches
says "Not written: a preview never writes project tables. A run writes N rows
to table '*name*' …", and the Live tiles are not touched. Only a run of the
flow — **Run**, **Run all**, a schedule — writes the table.

**Is there a t-test? Which test does Group means run?**
Yes. The **t-test** node compares two groups (Welch's by default, or
Student's), two answers of the same respondents (**Design** `paired`) or one
mean against a value (`one_sample`), with t, df, p, the mean difference and
its CI, and Cohen's d. **Group means** chooses a test for you with **Test**
`auto` — Student's t-test or a one-way ANOVA for interval data, Mann-Whitney
or Kruskal-Wallis for ordinal — or runs the one you name: `student`,
`welch`, `anova`, `welch_anova`, `mannwhitney`, `kruskal` — and after
`anova`, `welch_anova` or `kruskal`, a post-hoc comparison of every pair. Rank tests are
also in **Compare groups** (with Dunn's test), paired ones in **Paired tests**
(Wilcoxon, McNemar, Friedman, Cochran's Q), Fisher's exact test in
**Crosstab**, and Pearson, Spearman or Kendall in **Correlation** and
**Correlation matrix**. For an ordered outcome there is **Regression** with
**Model** `ordinal`.
→ [Which test](Studio-Node-Reference#analyze)

**"Tukey's HSD follows a one-way ANOVA — set Test to anova, or Post-hoc to none."**
A post-hoc test belongs to one test: Tukey's HSD to `anova`, Games-Howell to
`welch_anova`, Dunn's test to `kruskal` (in **Compare groups**, to `kruskal`
or `auto`). Change **Test** or **Post-hoc** as the message says. It is an
error: the flow cannot run until you do. A warning such as "Post-hoc is not
run while Significance test is off." only names a setting the node would
ignore. → [Rules between parameters](Studio-Node-Reference#reading-this-page)

**A field I filled in disappeared from the inspector.**
The node does not read it with its current choices — a t-test's **Groups**
once **Design** is `paired`, TURF's **Portfolio** unless **Search** is
`fixed`. It is kept, and named under the other fields: "Not used with these
choices, and kept for when they apply: …", with **Clear it**. It is not
checked while it is not read, so a stale value there never stops the flow.
Switch the choice back and it is used again. → [Parameters and variable pickers](Studio-Flows#parameters-and-variable-pickers)

**Group means with Test auto and with kruskal give different Kruskal-Wallis results.**
The codebook's missing codes. A test you choose by hand leaves them out
("Missing codes left out = …"); `auto` counts them as answers, as it always
has, so that stored flows keep their numbers — and says so: "Missing codes
counted as answers = Trust: Acme: 44 (9 = Refused); run Missing values first
to leave them out". Put **Missing values** before the node and both agree.
The same holds for **Compare groups** with and without Dunn's test, and for
**Correlation** with `spearman` and with the other methods.

**The test line reads "Test = not run: …".**
The data cannot carry the test, and the rest of the line says why and what to
choose instead — for example "Welch's t-test (unequal variances) compares two
groups and Region has 3 — choose anova or welch_anova". A group of one, or
answers without any spread, give such a line too, rather than a number.

**"Gender has 3 answers (…); a t-test compares two — name them in Group A and Group B, unless the data this node reads holds only two of them." / "Gender has 3 groups (…); a t-test compares two — name them in Group A and Group B."**
The first is a warning of the **Checks** block, before any run: **Groups**
has more than two answers in the codebook and neither **Group A** nor **Group
B** is named — "Gender has 3 answers (1 = Male, 2 = Female, 3 = Other); a
t-test compares two — name them in Group A and Group B, unless the data this
node reads holds only two of them." It does not stop the flow, since a filter
upstream may leave two. If none does, the run then stops with the second,
"Gender has 3 groups (1 = Male, 2 = Female, 3 = Other); a t-test compares two
— name them in Group A and Group B." A t-test compares two groups. Pick them in **Group A** and **Group B** (the
dropdowns list the answers of **Groups**), or use **Group means** with
`anova` or `welch_anova` for all three. A multiple-choice **Groups** is
refused because its groups overlap: run **Explode multiple choice** and
compare by one option's 0/1 column.

**A Result chart says "Kind 'scree' does not suit the table output of …".**
A Result chart draws what the connected output holds: a Group means table has
means, not eigenvalues. The message names what that output draws, and when
another output of the same analysis draws the kind you chose it says so —
"Kind 'scree' does not suit the loadings output of Principal components (p),
which draws 'loadings'; its variance output draws 'scree'." — so connect that
one. Leave **Kind** at `auto` and the chart draws the first kind the result
suits; the inspector lists them under the field and marks the others "(not
for this result)". → [Result chart](Studio-Node-Reference#result-chart)

**"A Result chart cannot draw the table output of Frequencies (…)".**
A Result chart draws the results of analyses — means, tests, TURF, MaxDiff,
factor analyses, regressions, key drivers, maps, prices (the message lists
them all). A frequency table is a distribution: draw it with a **Bar chart**
(**Show** `percent`), from the data. "The stat output of Regression (r) only
tells a chart its weight and base; connect the output it draws, table, too."
means the same: connect the analysis's table as well.

**A Likert chart says "The items of a Likert chart must share one scale, and these do not: …".**
A diverging bar needs one middle, so every item needs the same answers — the
same value labels in the codebook, missing codes aside. The message names
both scales. Draw the items of each scale in their own chart, or recode them
onto one scale first; recode a scale that runs high to low (1 = Strongly
agree) so that it runs low to high. A multiple-choice item, or items with no
value labels, no whole-number valid range and no Likert scale question behind
them, are refused the same way. → [Likert chart](Studio-Node-Reference#likert-chart)

**"Split by needs one answer per respondent, and … allows several: …".**
A **Bar chart** split into groups needs each respondent in one group. Draw
the multiple-choice question as the **Variable** and split it by a
single-answer question instead, or split by one of its options after
**Explode multiple choice**. A multiple-choice **Variable** can be split, but
its options overlap, so they are drawn side by side (**Layout** `grouped`),
never stacked. → [Bar chart](Studio-Node-Reference#bar-chart)

**My Bar chart looks different since I changed Sort (or Show).**
At the defaults — **Show** `count`, no **Split by**, **Sort** `code`, no
**Top N**, **Confidence intervals** off, a bar layout — the Bar chart is the
one it has always been. Any other setting (a histogram and a donut too)
draws the newer chart: its own colors, the base and notes under the plot,
and the codebook's missing codes left out (the classic chart draws a
"Refused" as a bar). Set them back to their defaults for the classic chart.

**My Bar chart shows no significance letters.**
Letters are drawn on a chart split into groups, in percentages, side by side:
**Split by** set, **Show** `percent`, **Layout** `grouped` — the rules on the
node say which is missing ("Significance letters compare the groups of Split
by — set Split by.", "… compare percentages, as the Banner table's do — set
Show to percent.", "… are drawn on bars side by side (Layout grouped), not on
stacks."). With all three, the note under the chart says why a bar has none:
"No group's share of any answer is significantly higher than another's.", or
"Not tested, fewer than 30 respondents who answered: …" for a small group.
→ [Bar chart](Studio-Node-Reference#bar-chart)

**The letters on my Bar chart differ from the tab book's.**
The comparisons are the same; the letters are not. The chart letters the
groups of its **Split by** A, B, C, …; a tab book letters every column of its
banner in one run — A–C for gender, then D–F for region — so its letters
match the chart's only when **Split by** is the banner's first variable. A
**Banner table** can differ in its numbers too: it counts a missing code as
an answer and tests on everyone in a column, while the chart and the tab book
leave missing codes out and test on those who answered.

**"bins: The bins' edges must increase from one to the next, …".**
A histogram's **Bins** is `auto`, a number of bins from 1 to 100, or the
edges in increasing order, separated by commas: `18, 25, 35, 50, 65, 100`.
The field suggests all three as you type. A histogram of a nominal or ordinal
question is refused ("A histogram draws the distribution of a number, and
Region is nominal: draw its answers as bars (Layout = grouped).") — draw it as
bars. → [Bar chart](Studio-Node-Reference#bar-chart)

**"Age is a number with 84 different values given, and this chart draws a bar for each: …".**
Percent bars, a split or a donut draw a bar or a slice per value, and refuse
a number of more than 30 values. Set **Layout** `histogram`, cut it into
ranges with **Bands** first and draw the bands, or set **Top N** to 30 or
fewer to draw only the values given most (a Top N over 30 says "… and top=40
draws a bar for each of the 40 given most: give top=30 or fewer, …"). The
check warns before the run when the codebook's valid range holds more than 30
whole numbers ("Age is a number of up to 84 values, and bars draw each value
given: …"); it does not warn of the chart of the defaults (Show count, no
Split by, Sort code), which draws every value as it always did.

**My Trend has no `created_at` to pick.**
It is at the end of the **Time** dropdown, under **Beside the answers**, with
`updated_at` and `started_at` — the timestamps the survey's responses carry,
which the codebook does not list. (There is no `submitted_at`: Studio's
responses do not have one, and the check calls it an unknown variable.) A flow
that reads an uploaded file or simulated data has them only when the data has
those columns: the node warns ("time: "created_at" is a timestamp of the
survey's responses, and this node reads Data file: the run stops unless that
data has a column created_at. …"), and the run stops with "The data has no
column 'created_at' to read Time from." when it does not.
→ [Trend](Studio-Node-Reference#trend)

**"created_at spans 905 days: too many points for one chart. Choose a longer Period."**
A Trend draws at most 500 points. Two and a half years by day is more; by
week or month it fits. A **Time** of more than 500 different codes ("… has
731 different values: not wave codes. …") is not a wave variable — pick the
wave's variable or a date.

**My Trend's points are hollow, or the bands are gone.**
A point with fewer respondents than **Minimum base** (30) is drawn hollow and
without its band, and its table row says "base below 30"; the table still
gives its interval. With more than four lines the bands would hide one
another, so none is drawn ("No bands: the 95% intervals of 5 lines would hide
one another; the table gives each point's.") and each line's points take a
shape of their own. Use a longer **Period**, fewer groups, or the table.

**"9 (Refused) is a missing code of Trust: Acme, not an answer: …".**
A Trend's **Answer codes** are answers; a missing code is left out of every
base. Check the answers you track — `4` and `5` for a top-2 box. The checklist
does not offer missing codes; this appears for a code typed or stored before.

**Where is my tab book?**
A run of the flow writes it under the node's **File name** and keeps it as
`outputs/<flow>/<name>.xlsx` — a Tab book added from the palette is named
`<flow>_tabbook` — on the **Reports** screen (with an **Excel** button), in
**Files** and on the run's card. The field says where: "After a run: Files →
outputs/*flow*/*name*.xlsx". A preview runs the node but keeps no file ("Not
kept: a preview never keeps the files nodes write. …"). A path saved earlier
outside `outputs/` is not kept at all; the field shows it under "Other
location" with "This file isn't in outputs/, so a run doesn't keep it under
Files." and a one-click fix.
→ [Tab books](Studio-Reports#tab-books)

**My tab book left a question out.**
The Contents and Notes sheets say why, as does the node's statistic
(**Skipped**): with **Questions** empty, open answers and rankings are left
out, and so are interval and ratio questions (name them for their means); a
question nobody answered, or one of more than 30 different answers without
answer labels that is not a number, is left out whatever you name. Check the question in
**Questions**, code an open answer first (**Code open answers**), or derive a
ranking's first choice (**Derive**).
→ [Tab book (Excel)](Studio-Node-Reference#tab-book-excel)

**"… holds multiple-choice answers, and a banner column is a group of respondents that no one else is in. …".**
A tab book's banner columns must not overlap. Run **Explode multiple choice**
and use the 0/1 column of each option you want as a banner variable, or
choose another variable.

**My charts do not take the report's colors.**
Only a chart whose **Palette** is `theme` (a **Heatmap**'s **Color map**
`theme`) takes the **Chart colors** of its **Save report**'s **Look**; a
named palette keeps its own. A chart in two reports takes each report's
colors in that report. On its node's preview and on a Live tile it is drawn
in the flow's **Save report** look — in the default colors when the flow has
no **Save report**, or several with different looks. The house style reaches
a flow only when it is stamped into its **Save report** node (**Use the house
style**, **Apply to every flow**). → [Chart colors](Studio-Reports#chart-colors)

**"theme: chart_text_color: '#cccccc' on the charts' white background has a contrast of 1.6:1; …".**
The **Look**'s chart colors must read on white: text at 4.5:1 or more, a bar
or a line at 1.3:1 or more. Pick a darker shade; a color checker shows the
ratio. The node names each problem — a color that is not hex (`#2a78d6`),
fewer than 2 or more than 12 series colors, a color given twice, two equal
diverging ends. → [Chart colors](Studio-Reports#chart-colors)

**Regression says "Region is nominal: its answers (…) have no order, …".**
**Model** `ordinal` is for ordered answers — dissatisfied to satisfied. A
nominal outcome has no order, and the model would take one from its codes.
Use `logit` for an outcome of two answers, or make an ordered variable with
**Recode** (**Scale** `ordinal`) first. The check says so before the run; for
a variable a node of the flow makes nominal, it is a warning and the run
refuses it. → [Regression](Studio-Node-Reference#regression)

**Where are my report's tables in Excel?**
Check **Also Excel** in the Report view (the **Save report** node's **Also
save tables to Excel**) and run the flow (or **Run all**): `<report>.xlsx` is
written beside the report — on the Reports screen under **Excel**, in
**Files**, and among the run's outputs. A run without the box does not delete
an earlier one, so the **Excel** button then offers the workbook of the
flow's last run that wrote it: check the box and run again to bring it up to
date. → [Tables in Excel](Studio-Reports#tables-in-excel)

**My research bundle stops at a t-test, Export file, Result chart, Trend or Tab book node.**
The bundle's engine pin may lag behind Studio: at the last merged upstream
commit, the new statistics nodes, **Key drivers**, **Perceptual map**,
**Price sensitivity**, the **Likert chart**, the **Result chart**, the
**Trend** and the **Tab book (Excel)**, every **Export file**, **Code open
answers** and **TURF** node, a **Bar chart** with **Show** `percent`,
**Split by**, **Sort** `value`, **Top N**, **Confidence intervals** or
**Layout** `histogram` or `donut`, a **Heatmap** with Pearson or Kendall, a
chart whose **Palette** (a Heatmap's **Color map**) is `theme`, a **Save
report** whose **Look** names chart colors, Regression's `ordinal` model,
**Save report**'s tables in Excel and a test chosen by hand stop with an
error. The bundle's README says so; install the engine revision it names.
→ [Installing the engine](Studio-Reproducibility#installing-the-engine)

**The report is empty or missing.**
A report needs a **Report section** connected to a **Save report** node, and the
flow must have run. The node's **File name** field keeps the report in
`outputs/`; a path saved earlier outside it shows as "Other location", with a
fix. **Run all** keeps only the report that is the flow's **Report path**;
another **Save report** is kept by a run of that flow on its own, and its
field says so.
→ [[Reports|Studio-Reports]]

**"The table clean_responses does not exist yet: it is written by 1. Clean raw responses. Run that flow (or Run all) first, then this one."**
The flow reads a project table (a **Project table** node) that no run has
written yet — a preview never writes one. Run the flow the message names,
or **Run all**, which runs it first; then preview or run this flow again. A
new project started from the example study is in this state: its flows
after `cleaning` read `clean_responses`, and `segments` reads
`scored_responses`, which `wellbeing` writes. See
[Tables between flows](Studio-Flows#tables-between-flows).

**A flow is missing from the combined report, or Run all says "report … was not written".**
The combined report takes each flow's **Report path** (flow settings), a
list of the flow's **Save report** nodes. A flow with **— none —** is left
out. A path the flow does not write — saved earlier, or set through the API
— fails that flow, and the list shows it as "*path* — no node saves this":
"report outputs/*x*.md was not written: the flow's Report path names a file
none of its nodes saves — set it to the Path of its Save report node". The
flow's tables were still written, so the flows that read them run, and the
combined report is marked incomplete. The Save warns about this beforehand
(`REPORT_PATH_UNWRITTEN`: "The flow's Report path is “…”, but no Save report
step saves there: Run all will fail this flow. Set it to the Path of a Save
report step, or clear it."). Choose one of the flow's reports in **Report
path**. Changing the **File name** of a flow's **Save report** node moves
the Report path along with it, and deleting the node clears it.

**Live tiles are stale.**
Tiles show the flow's last *completed* run, or a newer **Run all** that ran
it; a failed run leaves the previous tiles in place (check "updated …"), and
previews never change them. On Free,
press **Recompute now**; automatic recomputation is Plus and above and needs
**Live: recompute on new responses** checked and saved. A failed automatic
recompute does not email the owners. → [[Live Monitoring|Studio-Live-Monitoring]]

**The public live link shows "page not found".**
It was revoked or rotated, or the organization's plan no longer includes Live.

---

## Coding open answers

**Where is Code open answers… — coding with the AI assistant?**
Switched off on this platform. It sent the text your respondents wrote to the
AI provider, so its buttons (**Code open answers…**, **Code more answers…**)
and its dialog are gone. Build the codeframe yourself: on the **Code open
answers** node, **New codeframe…** (or **Files → Codeframes → New
codeframe…**) opens the codeframe editor, where you code answers by hand and
write word rules that code the rest. Codeframes the assistant built earlier
keep working. → [[Coding Open Answers|Studio-Open-Answer-Coding]]

**"AI coding of open answers is switched off on this platform."**
The API's answer to a request to start a coding job, and the log of a coding
job queued before the switch (in **Run history**). Nothing was read or
charged. Use the codeframe editor instead.

**An answer I expected to get a theme is uncoded.**
Type it into **Test a phrase**: it shows each rule that fired, was vetoed or
met a negation. The usual reasons: the word is **negated** (*wasn't late* —
`late` finds only mentions that are not; `not_late` finds the negated ones);
a **Must also contain** word is in **another clause** (a comma or *but* ends
one — set **Reads** to **the whole answer**); the term misses a **word form**
(`delay` does not find *delayed*; write `delay*`); a **But not** word is
there; or the answer is in another language than the term. Add a term, or
code the answer by hand. → [Writing rules](Studio-Open-Answer-Coding#writing-rules)

**"2 errors — the codeframe cannot be applied or saved until they are fixed."**
The list under it (and the mark beside each term or setting at fault) says
what: "the codeframe has no themes" for a new one — **Add theme**; a term
beginning `re:` — "regular expressions are not supported: …"; a theme without
a label, the same words replaced twice. **Save changes** stays disabled
("Fix the codeframe's errors first") until they are gone.
→ [Mistakes the editor catches](Studio-Open-Answer-Coding#mistakes-the-editor-catches)

**"This codeframe is version 1: a theme for each answer it was built from, and no rules. …"**
An older codeframe — built by the assistant, or the example study's. The node
applies it as before. Editing it makes it version 2: its decisions are kept,
its example answers are left out (version 2 keeps only fingerprints).
→ [Older codeframes](Studio-Open-Answer-Coding#older-codeframes-version-1)

**The themes add up to more than 100 %.**
The codeframe gives an answer several themes, and every % is of the
respondents who answered; the table's **Percentages** says so. A net's row
counts each respondent once.
→ [The table](Studio-Open-Answer-Coding#the-table)

**The theme table and a Frequencies of the theme variable give different numbers.**
The theme table counts everyone who answered, with **No theme** and
**Uncoded** rows. In the theme variable, an answer coded as no theme and an
uncoded one are empty, so a **Frequencies** of it counts only the
respondents with a theme. Quote the theme table for shares of those who
answered.

**A Split by, a donut, a banner or a Likert chart refuses my theme variable.**
The codeframe gives several themes an answer, so its theme variable is
multiple-choice, and these refuse it as they refuse a multiple-choice
question. Use it where a multiple-choice question goes (a **Frequencies**, a
**Crosstab**'s rows, a **Bar chart**'s variable), or turn off **An answer may
have several themes**.

**The nodes after Code open answers do not offer its theme variable.**
The codeframe is not saved yet: a codeframe started from the node is kept only
in its browser tab until you save it in its editor, and the node says so
("*path* is not saved yet: it is kept in this tab until you save it in its
editor."). Save it, and save the flow.

**"analysis/… is not saved in this project: it was started and never saved. Start it again, or choose another codeframe."**
The node names a codeframe that was started from it in a tab that is now
closed, and never saved. **New codeframe…** starts it again under the same
name, or choose another codeframe.

**Answers that just arrived are not in the codeframe editor.**
The editor reads the answers again once its last reading is a minute old.
Check **Answers from** and **Only completed responses** too: they choose which
responses it lists.

---

## Email invitations

**"Import contacts" or "New mailing" is disabled.**
Invitations need a paid plan (Plus and above) — during an unpaid trial they
stay locked — plus a published, live environment and at least one subscribed
contact. An environment that has closed by its closing date is not offered.
If the button's tooltip reads "Mailings are paused for this organization",
see the next answer. → [[Email Invitations|Studio-Email-Invitations]]

**"Mailings are paused for this organization — …"**
Mailings were paused automatically after too many bounces or spam
complaints; the panel names the reason and adds "Contact support to resume
them." A mailing that was sending when this happened reads "Paused — *reason*;
the rest stays queued until support resumes it." Contact support.

**Who gets a reminder?**
**Remind** goes to the invitees of that mailing who have not completed —
through the invitation or any earlier reminder — so someone who answered
through a reminder's link is not reminded again, and a second reminder is
safe. Its tooltip and the reminder dialog give the number, and the preview
shows the message as its first recipient will get it ("Preview · as
*email*"). The mailing's **Completed** column adds "+N via reminders".

---

## Integrations

**My webhook does not fire for some events.**
A webhook receives only the events selected under **Events** when it was
added — **Deploys**: live, failed, stopped; **Runs**: completed, failed — and
every event when none is selected. Webhooks added with an earlier version of
the chips (`deploy`, `run`) have been switched to the matching events and now
receive them. One that subscribed only to `terminal` shows an amber pill
"never fires: terminal" — nothing emits that event, so delete the webhook and
add it again with the events you want. An **unsigned** pill means its
deliveries carry no `X-Siamang-Signature` header; add it again with a secret
to sign them. Check **Recent deliveries** for errors from your endpoint.
Webhooks are *(Plus)*, and only owners and admins can see and manage them:
for members the **Webhooks** card holds only that notice.
→ [[Schedules and Webhooks|Studio-Schedules-and-Webhooks]]

**Can a webhook post to Slack?**
Yes. Add the Slack incoming-webhook URL as the endpoint: every payload carries
a one-line `text` (for example `deploy.live · acme/pulse (main) · <link>`),
which Slack posts as the message.
→ [Slack and other chat tools](Studio-Schedules-and-Webhooks#slack-and-other-chat-tools)

**Saving a connector fails with "…String should match pattern…".**
Connector names may contain only lower-case letters, digits and `_`, and must
start with a letter. → [[Connectors|Studio-Connectors]]

**Can I use a project secret in a flow?**
No — as the Secrets tab says, connectors and repository deposits read them by
key; flow runs cannot, and they have no network access anyway.

**The Zenodo DOI starts with 10.5072 / points to sandbox.zenodo.org.**
**Use sandbox.zenodo.org** is checked by default in the Deposit dialog. Deposit
again with it unchecked and a production Zenodo token.
→ [[History and Versions|Studio-History-and-Versions]]

---

## Still stuck?

- **Profile → Support** links to documentation, examples, the issue tracker
  and feature requests, and **Contact team** writes to support.
- Email `info@siamang-team.org` with the organization slug, the project slug
  and the Save number — that is usually enough to reproduce anything.

## See also

- [[Recipes|Studio-Recipes]]
- [[Limits and Quotas at a Glance|Studio-Limits-Reference]]
- [[Glossary|Studio-Glossary]]
- [[Key Concepts|Studio-Key-Concepts]]

<!-- studio-nav -->
---

← [[Keyboard Shortcuts|Studio-Keyboard-Shortcuts]] · [Studio contents](Studio-Overview#all-pages) · [[Glossary|Studio-Glossary]] →
