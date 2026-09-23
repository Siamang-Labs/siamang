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

**Studio asked me to create an account although I have one.**
The address check can fail on a slow network or after too many attempts in a
minute — 10 for the same address, or 20 from one network across all
addresses (a busy office or campus network can reach that) — and Studio then
assumes the address is new. Go **← Use a different email**, wait a minute,
and enter the address again.

**"Your session expired. Please sign in again."**
Sign in again. Unsaved Builder and flow edits are kept as your server-side
draft and come back when you reopen the editor.

**I created my account from a colleague's invitation and the link now says
"This invitation link is invalid or has already been used."**
You are already a member — the invitation was accepted when your account was
created. Switch to the organization with the workspace chip in the topbar. If
it is not listed, reload the page.

**I landed in my own workspace, not my colleague's.**
Every new account also gets its own trial organization. Switch with the
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
analyze, but creating and renaming projects, adding or deleting secrets,
running connectors, deleting responses, managing webhooks and reading the
organization's **Activity** are for owners and admins; those controls are
disabled or hidden for you. Ask an owner or admin, or to be made an admin.
→ [Things members may notice](Studio-Organizations-and-Team#things-members-may-notice)

**My trial ended. What changed?**
The organization is now on the **Free** plan. Nothing is deleted and surveys
keep collecting within Free limits (1,000 completed responses per
environment); you cannot add projects or members beyond Free's caps, schedules
and live recomputation stop, and Saves with custom JavaScript or CSS can no
longer be published. → [[Plans, Trial and Billing|Studio-Plans-and-Billing]]

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

- **A renamed variable.** Renaming a variable does not update the conditions,
  piping and quotas that use the old name. Find them with the **Logic map**
  and update them.
- **An old build.** Earlier versions of Studio stored an answer under the
  question's **Id**, so logic on a question whose Id differs from its variable
  (every preset, `q5` / `nps_5`) never matched. A survey published before that
  change keeps its old build until you publish it again: **Save** (with
  nothing changed, Save re-validates with the current engine) and press
  **Republish #N** on the environment's card.
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

**A branch rule never fires.**
A rule with an empty condition never matches — it is not an "otherwise".
Studio says so under the rule ("Add a condition — an empty rule never
fires."), on the Logic map ("no condition — never fires") and in **Validation
→ Structure**. Give it a condition, or use **Default next** for "everyone
else". → [[Logic and Branching|Studio-Logic-and-Branching]]

**Skip to jumps for every answer, not just one.**
That is how **Skip to** works: when the question is answered, Next goes to the
chosen page. For a jump that depends on the answer, use a **Branch (next if)**
rule on the page.

**How do I enter missing codes?**
In **Builder → Codebook**, open the variable's row and type each code followed
by its label, separated by commas: `-9 Refused, -8 Don't know` (`-7=Not asked`
works too). A code typed without a label borrows the value label for that
code, or is labeled `Missing (<code>)`.
→ [Missing codes](Studio-Codebook-and-Variables#missing-codes)

**I want one 0/1 column per option of a Multiple choice question.**
**Options → Data layout → wide** turns the question into one 0/1 variable
per choice (`brands_1`, `brands_2`, …) and keeps them in step with the
choices; **array** turns them back into one variable. The published survey
does not yet store real answers in that shape, though, so for fieldwork keep
**array** and add an **Explode multiple choice** node in the flow.
→ [Multiple-choice layouts](Studio-Codebook-and-Variables#multiple-choice-layouts)

**How do I change the title of the completion screen?**
You cannot: **Theme → Completion screen** offers only the **Message**, and the
title is always "Thank you for participating". For your own title and text,
end the survey on a **Final** page with its own **Title** and **Body**.
→ [Completion screen](Studio-Theme-and-Branding#completion-screen)

**"…references unknown variables: …" and the Save is `errors`.**
A condition names a variable that nothing in the questionnaire writes: no
question collects it, no **Assign to a condition** script assigns it, and the
codebook does not declare it. Usually it is a typo or a variable that no
longer exists. Conditions may read the arm of **Assign to a condition** and
variables declared only in the codebook (for example a value your custom
JavaScript writes), but not URL parameters.
→ [Assignment and "embedded data"](Studio-Logic-and-Branching#assignment-and-embedded-data)

**The Save badge says `errors`.**
Click it (it opens the Save in History) or open **Builder → Validation**. A Save
with errors cannot be published; warnings can be, after a confirmation.
→ [[Testing Your Survey|Studio-Testing-Your-Survey]]

**"Unreachable pages in navigation graph" or "Cycle detected in page navigation graph."**
Open **Logic map → Pages**: some page has no route leading to it, or routing
loops back. Wire the page up (or delete it), or break the loop.

**A condition says it "can never be true".**
It reads an answer given later in the interview. Move the question earlier or
the condition later.

**My page's Body text does not appear.**
On a page with questions the Body is not shown; it appears on text-only,
**Final**, **Screen-out** and **Redirect** pages. Put introductory text in a
question's **Hint**.

**Piping shows `{answer:x}` literally.**
The variable name is wrong (piping uses the variable name, not the question's
Id), or the question has not been answered yet at that point.

**I renamed a variable and a condition or flow broke.**
Renaming does not update conditions, quotas, piping, scripts or flow
parameters. Update them, or rename back. Answers are stored under the
variable name, so renaming a variable and republishing during fieldwork
leaves you with two columns (see *Two columns where I expect one* below).

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
errors, or the environment already runs that Save ("…nothing to publish").

**"Custom JavaScript in the questionnaire is included from Plus…" / "Custom CSS in the theme is included from Plus…"**
Your plan does not include custom code in published surveys. Remove the script
or the custom CSS, or upgrade. → [[Plans, Trial and Billing|Studio-Plans-and-Billing]]

**I published but the link shows the old questions.**
Check that the card's `#N` is the Save you expect — press **Republish #N** if
not — and hard-refresh the page (browsers cache survey files).

**The published survey's progress indicator differs from the preview.**
Published surveys follow **Theme → Progress** (**bar**, **dots**, **both** or
**hidden**; the bar when you never chose), like the Builder's previews. A
survey published with an earlier version of Studio shows no bar until you
publish it again — **Save**, then **Republish #N**. To show no indicator at
all, choose **bar** and then **hidden**.
→ [Question style and progress](Studio-Theme-and-Branding#question-style-and-progress)

**A quota cell is full but respondents keep coming.**
Quota cells are counted, not enforced. Add a branch rule that screens out the
full cell's value and republish; the environment's response cap is the only
automatic stop. → [[Quotas and Randomization|Studio-Quotas-and-Randomization]]

**The deadline passed but the card still says ● Live.**
That is expected. When the questionnaire's deadline passes, the environment
stops accepting responses — anyone who submits sees "This survey is closed" —
but the card does not change and the link still opens the survey. Press
**Close** when you want the link itself to show the closed page. A closing
date or redirect declared for the **environment** in `studio/settings.json`
is only displayed on the card; it does not close anything.
→ [Deadlines](Studio-Publishing-and-Environments#deadlines)

**Respondents answered everything and then saw "This survey is paused" / "This survey is closed" / "Thank you for your interest…".**
Pause, the questionnaire's deadline and the response cap take effect when a
respondent submits — and so does **Close**, for someone who already had the
survey open. Their answers are not stored. Resume, move the deadline in a new
Save, or raise the cap (new projects cap `main` at 1,200 and `pilot` at 50).

**The count is not moving.**
Check you are looking at the right environment, that it is not paused, and
that interviews are being *completed* — partials show in Data but do not count
toward caps.

**The build failed.**
Open **Build log** on the card. If a republish failed, the previous version is
still serving the link. Fix the cause, then publish again.

**Access codes are not asked for.**
Generating codes creates a new Save; republish the environment.

**The Header "Preview" survey says "Submission failed".**
Preview builds never accept answers. Test with the `pilot` environment
instead. → [[Testing Your Survey|Studio-Testing-Your-Survey]]

**Where do I get the panel ids to reconcile with Prolific / Cint?**
From **Outcomes · reconcile with the provider** at the end of the **Panel**
chip on a live environment's card: its completed, screened-out and partial
CSVs list each respondent's provider id (up to 5,000 responses). The id
parameter is matched however it is capitalized (`PROLIFIC_PID`, `RID`).
→ [Reconciling outcomes](Studio-Panel-Providers#reconciling-outcomes)

---

## Data

**The numbers in Data and in my flow disagree.**
Data counts every row — all environments, partials, screen-outs. Flows usually
filter (environment, **Only completed responses**, dedup, speeders, filters).
Run to each node and watch the row count.

**I cannot find a response in the grid.**
The grid loads the **newest** 100 rows of a table (25 per page), and
**Filter loaded rows…** and sorting work on those rows only. For an older
response, export the table to find the row; to delete it, see
[Handle a data erasure request](Studio-Recipes#handle-a-data-erasure-request).

**My export has no URL parameters or durations.**
Exports from Data leave out the `meta` column. Those values are available in
flows (`url_<name>`, `duration_s`) — write them out with an **Export file**
node. → [[Data Exports|Studio-Data-Exports]]

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

**"Respondents" equals "Responses".**
Studio does not identify people across sessions, so each completed interview
counts as a respondent.

**There is no Delete button on the rows.**
Only owners and admins can delete responses, so only they see **Delete** on
the rows of the `responses` table. Ask one of them to handle the request.

---

## Flows and reports

**"Could not start the preview. The preview limit for this hour is reached on your plan."**
**Run to here** is limited per person per project per hour (Free 30, Plus 120,
Pro 600). Wait, or use **Run**. "…A preview is already running" — wait for it
to finish.

**Every run fails with "…has no generated code (it did not pass the engine check at Save)".**
One flow in the project was saved with engine errors, and that stops every run
and blocks publishing from that Save. Open that flow, press **Check**, fix it
and **Save**. → [[Analysis Flows|Studio-Flows]]

**In what order does Run all run my flows?**
In dependency order: a flow that reads a table another flow writes (through a
**Project table** node, or a **Responses** node set to that table) runs after
the flow with the **Write table** node. Flows that do not depend on each other
run in alphabetical order of their names; you do not need to name flows so
that a writer sorts first. → [Run all](Studio-Flows#run-all)

**Run all failed, but some flows ran.**
One failed flow does not stop the run. The others still run, except those
that read a table the failed flow writes — their log line reads "skipped:
needs *flow*, which failed". The run ends as failed and no combined report is
written; **View logs** lists every flow as ok or failed, with each error. Fix
the flows it names and run again.

**The Schedules section shows "Requires Plus" instead of "Schedule a run".**
Schedules are available from the Plus plan ("Schedules are available from the
Plus plan"); on Free the button opens the plans. Run flows by hand, or
upgrade. → [[Schedules and Webhooks|Studio-Schedules-and-Webhooks]]

**How do I delete, rename or duplicate a flow?**
Not possible from the interface yet. Restoring a Save made before the flow
existed removes it; otherwise contact support.

**My Data file node cannot find the file I uploaded.**
Files uploaded under **Files** are not available to flow runs. Bring the data
in with a connector import into a project table, or run the downloaded flow
script on your own computer with the file beside it.
→ [[Files|Studio-Files]]

**Run to here changed a project table.**
A preview that reaches a **Write table** node does write the table. Disconnect
the node while experimenting.

**The report is empty or missing.**
A report needs a **Report section** connected to a **Save report** node, and the
flow must have run. Output paths must be under `outputs/`.
→ [[Reports|Studio-Reports]]

**A flow is missing from the combined report, or Run all fails with just a file path.**
The combined report takes each flow's **Report path** (flow settings). A flow
without one is left out; a path the flow does not write fails the Run all.

**Live tiles are stale.**
Tiles show the last *completed* run; a failed run leaves the previous tiles in
place (check "updated …"). On Free, press **Recompute now**; automatic
recomputation is Plus and above and needs **Live: recompute on new responses**
ticked and saved. → [[Live Monitoring|Studio-Live-Monitoring]]

**The public live link shows "page not found".**
It was revoked or rotated, or the organization's plan no longer includes Live.

---

## Email invitations

**"Import contacts" or "New mailing" is disabled.**
Invitations need a paid plan (Plus and above) — during an unpaid trial they
stay locked — plus a published, live environment and at least one subscribed
contact. → [[Email Invitations|Studio-Email-Invitations]]

**The invitations panel shows an upgrade message although we are on Plus.**
Mailings may have been paused automatically after bounces or spam complaints.
Contact support.

**Someone who already answered got a second reminder.**
Send **one** reminder per invitation: people who completed through a
reminder's link still count as not completed on the original invitation.

---

## Integrations

**My webhook does not fire for some events.**
A webhook receives only the events selected under **Events** when it was
added — **Deploys**: live, failed, stopped; **Runs**: completed, failed — and
every event when none is selected. A webhook whose row lists `deploy`, `run`
or `terminal` was added with an earlier version of the chips: those names
match no event, so it receives nothing — delete it and add it again. Check
**Recent deliveries** for errors from your endpoint. Webhooks are *(Plus)*,
and only owners and admins can see and manage them: for members the
**Webhooks** card holds only that notice.
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
