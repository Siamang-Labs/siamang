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
Sign in again. Unsaved Builder and flow edits are kept as your server-side
draft and come back when you reopen the editor.

**I created my account from a colleague's invitation. Where am I?**
In your colleague's organization: the invitation is accepted as your account
is created, and the invitation link takes you straight into the inviting
organization. You also get an organization of your own, on its own trial;
switch between the two with the workspace chip in the topbar. If the
invitation page says "Could not load the invitation." followed by a reason,
the server was busy or could not be reached — the link itself is fine; press
**Try again**. "This invitation has expired. …" and "This invitation link is
invalid or has already been used." are about the link itself: ask for a new
invitation.
→ [If you create your account from the invitation](Studio-Sign-Up-and-Sign-In#if-you-create-your-account-from-the-invitation)

**I landed in my own workspace, not my colleague's.**
After sign-in Studio opens your oldest membership. If you had an account
before you were invited, that is your own workspace; switch with the
workspace chip. → [[Organizations and Team|Studio-Organizations-and-Team]]

**How do I create a second organization?**
Open the workspace chip in the topbar and choose **Create organization** (the
**Organizations** screen has the same button). The new organization starts on
the **Free** plan with you as its owner — the Pro trial comes once per email
address, with the organization you got at sign-up.
→ [Creating another organization](Studio-Organizations-and-Team#creating-another-organization)

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
The organization is now on the **Free** plan. Nothing is deleted and surveys
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
you renamed the question's variable. The Id is fine: delete the entry in
**Builder → Codebook**, where it is listed **unused**.

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
per choice (`brands_1`, `brands_2`, …) and keeps them in step with the
choices; **array** turns them back into one variable. A published survey
stores each chosen option's variable as `1` and the others as `0` once the
question is answered (an option hidden by its own condition stays empty),
exclusive choices such as "None of these" clear the others, and conditions
and quotas on `brands_1 = 1` work. A survey published before this worked
needs to be published again; its earlier answers are read as 1/0 columns in
Data and exports. → [Multiple-choice layouts](Studio-Codebook-and-Variables#multiple-choice-layouts)

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
and answers that say they are keyed by variable name, so Studio stores them
exactly as sent. Responses it already
collected need nothing: Data, exports and flows read them in today's layout.
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
Give the node's **File** the upload's path, `assets/<name>` — the copy icon
on the file's row in **Files** copies it ("Copy the path a flow reads it by").
Runs, **Run all** and **Run to here** read it from there. If the run log
says "note: assets/*name* is not among this project's Files", the name is
wrong or the file was deleted.
→ [[Files|Studio-Files]]

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
(Wilcoxon, McNemar, Friedman), Fisher's exact test in **Crosstab**, and
Pearson, Spearman or Kendall in **Correlation** and **Correlation matrix**.
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

**My research bundle stops at a t-test (or Export file) node.**
The bundle's engine pin may lag behind Studio: at the last merged upstream
commit, the new statistics nodes, every **Export file** and **Code open
answers** node, and a test chosen by hand stop with an error. The bundle's
README says so; install the engine revision it names.
→ [Installing the engine](Studio-Reproducibility#installing-the-engine)

**The report is empty or missing.**
A report needs a **Report section** connected to a **Save report** node, and the
flow must have run. Output paths must be under `outputs/`.
→ [[Reports|Studio-Reports]]

**A flow is missing from the combined report, or Run all says "report … was not written".**
The combined report takes each flow's **Report path** (flow settings). A flow
without one is left out. A path the flow does not write fails that flow:
"report outputs/*x*.md was not written: the flow's Report path names a file
none of its nodes saves — set it to the Path of its Save report node". The
flow's tables were still written, so the flows that read them run, and the
combined report is marked incomplete. The Save warns about this beforehand
(`REPORT_PATH_UNWRITTEN`: "The flow's Report path is “…”, but no Save report
step saves there: Run all will fail this flow. Set it to the Path of a Save
report step, or clear it."). Changing the **Path** of a flow's **Save
report** node moves the Report path it had set along with it, and deleting
the node clears it.

**Live tiles are stale.**
Tiles show the flow's last *completed* run; a failed run leaves the previous
tiles in place (check "updated …"), and previews never change them. On Free,
press **Recompute now**; automatic recomputation is Plus and above and needs
**Live: recompute on new responses** ticked and saved. A failed automatic
recompute does not email the owners. → [[Live Monitoring|Studio-Live-Monitoring]]

**The public live link shows "page not found".**
It was revoked or rotated, or the organization's plan no longer includes Live.

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
**Use sandbox.zenodo.org** is ticked by default in the Deposit dialog. Deposit
again with it unticked and a production Zenodo token.
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
