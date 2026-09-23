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
The address check can fail on a slow network or after several attempts in a
minute, and Studio then assumes the address is new. Go **← Use a different
email**, wait a moment, and enter the address again.

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
The **Create organization** button is offered only to accounts that belong to
no organization. If you need a separate workspace for a client or a grant,
write to support. → [[Organizations and Team|Studio-Organizations-and-Team]]

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
Almost always the question's **Id** differs from its variable name — every
preset starts that way (`q5` / `nps_5`), and renaming a variable in the
Inspector does not rename the Id. Set **Advanced → Id** to exactly the variable
name, **Save** and republish. → [[The Builder|Studio-Builder-Overview]]

**A branch rule never fires.**
A rule with an empty condition never matches, even though it shows
"otherwise". Give it a condition, or use **Default next** for "everyone else".
→ [[Logic and Branching|Studio-Logic-and-Branching]]

**Skip to jumps for every answer, not just one.**
That is how **Skip to** works: when the question is answered, Next goes to the
chosen page. For a jump that depends on the answer, use a **Branch (next if)**
rule on the page.

**Save failed: "…'label' is a required property".**
Missing codes entered in the **Codebook** tab are saved without labels, which
the engine refuses. Remove them from the Codebook tab and see
[[Codebook and Variables|Studio-Codebook-and-Variables]] for the workaround.

**Save failed: "MultiChoice wide mode expects vars to be a non-empty list of Variables."**
The **wide** data layout cannot currently be switched on from the Builder. Set
**Data layout** back to **array**; use the **Explode multiple choice** node in a
flow to get one 0/1 column per option.

**Save failed: "…Additional properties are not allowed ('completion_title' was unexpected)".**
Clear **Theme → Completion screen → Title**. Use the **Message** field, or end
the survey on a **Final** page with its own title and body.

**"…references unknown variables: …" and the Save is `errors`.**
A condition reads a variable that no question collects — for example the arm
of **Assign to a condition**, or a variable that exists only in the codebook.
Conditions can only read variables that questions collect.
→ [[Logic and Branching|Studio-Logic-and-Branching]]

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
The variable name is wrong, the question has not been answered yet at that
point, or the question's Id differs from the variable name (see above).

**I renamed a variable and a condition or flow broke.**
Renaming does not update conditions, quotas, piping, scripts or flow
parameters. Update them, or rename back.

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

**There is no progress bar in my published survey.**
A current limitation: published surveys show no progress bar whatever the
**Progress** setting (the canvas preview does show one).
→ [[Theme and Branding|Studio-Theme-and-Branding]]

**A quota cell is full but respondents keep coming.**
Quota cells are counted, not enforced. Add a branch rule that screens out the
full cell's value and republish; the environment's response cap is the only
automatic stop. → [[Quotas and Randomization|Studio-Quotas-and-Randomization]]

**The survey did not close at the deadline.**
Deadlines and "Closes" dates are shown on the card but do not close the survey.
Press **Close** on the card. → [[Publishing and Environments|Studio-Publishing-and-Environments]]

**Respondents answered everything and then saw "This survey is paused" / "Thank you for your interest…".**
Pause and the response cap take effect when a respondent submits. Their
answers are not stored. Resume, or raise the cap (new projects cap `main` at
1,200 and `pilot` at 50).

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

**Prolific / Cint outcomes show no respondent ids.**
A current limitation of the **Outcomes** block for id parameters in capital
letters. The completed / screened-out / partial counts are right; match ids
from a **Data** export (`meta` column) if you need them.
→ [[Panel Providers|Studio-Panel-Providers]]

---

## Data

**The numbers in Data and in my flow disagree.**
Data counts every row — all environments, partials, screen-outs. Flows usually
filter (environment, **Only completed responses**, dedup, speeders, filters).
Run to each node and watch the row count.

**I cannot find a response in the grid.**
The grid loads only the first 100 rows of a table. Export the table to find
the row; to delete it, see [[Recipes|Studio-Recipes]] (*Handle a data erasure
request*).

**My export has no URL parameters or durations.**
Exports from Data leave out the `meta` column. Those values are available in
flows (`url_<name>`, `duration_s`) — write them out with an **Export file**
node. → [[Data Exports|Studio-Data-Exports]]

**SPSS labels are missing or look wrong.**
Exports are labeled with the **current** Save's codebook. Fill in labels in
**Builder → Codebook**, Save, and export again. If a column is named like a
question Id (`q5`) rather than its variable, see the Id rule above.

**Two columns where I expect one.**
A variable was renamed mid-fieldwork. Harmonize the two in a flow with
**Recode** or **Derive** rather than editing the raw table.

**"Respondents" equals "Responses".**
Studio does not identify people across sessions, so each completed interview
counts as a respondent.

**"Delete" fails with a permission error.**
Only owners and admins can delete responses.

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

**Run all ran my flows in the wrong order.**
**Run all** runs flows in alphabetical order of their names and stops at the
first failure. Name the flow that writes a table so it sorts first
(`a_clean`, `b_tables`).

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

**My webhook never fires.**
Leave **Events** unselected when you add it — selecting an event currently
stops deliveries. → [[Schedules and Webhooks|Studio-Schedules-and-Webhooks]]

**Slack rejects the webhook.**
Slack needs a `text` field that Studio's payload does not have. Point the
webhook at a relay (Zapier, Make or your own endpoint) that posts to Slack.

**Saving a connector fails with "…String should match pattern…".**
Connector names may contain only lower-case letters, digits and `_`, and must
start with a letter. → [[Connectors|Studio-Connectors]]

**Can I use a project secret in a flow?**
No — secrets are used by connectors and deposits only; flow runs have no
network access.

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
