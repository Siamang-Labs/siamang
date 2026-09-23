# Working Together

A survey team works best with one person editing a document at a time and
everyone else able to watch and comment. Studio is built that way: one editor
per document, others following the edits live, comments on questions, pages
and flow nodes, and a Save that notices when someone else saved first. This
page covers edit locks, drafts, comments, Save conflicts and roles.

---

## One editor per document

### What is locked

| Document | Locked when |
|---|---|
| The questionnaire | someone has the **Builder** open (once the questionnaire has been saved at least once) |
| Each flow, separately | someone has that flow open on its canvas (once the flow has been saved at least once) |

The questionnaire and each flow lock independently, so one person can build
the instrument while another builds the analysis. Project settings (study
metadata, runtime, reports, connectors) are not locked. A brand-new flow that
has never been saved is private to the person creating it.

### Timing

- Opening the Builder or a flow takes the lock; Studio renews it every **30
  seconds** while you are on that screen.
- Leaving the screen releases it at once. If your browser closes or loses its
  connection, the lock lapses **2 minutes** after the last renewal.
- When the editor leaves, the first colleague still following takes the lock
  automatically and can edit.

### When someone else is editing

You see a banner above the tabs:

> **Anna** is editing — you are following their changes live (last edit 2 min
> ago). Your own edits are off until you take over; comments stay open.
> **[Take over]**

While you follow:

- your screen shows Anna's unsaved work, refreshed every few seconds (her edits
  reach the server about 1.5 seconds after she stops typing);
- the version chip reads **Version 17 · being edited**;
- **Save** is disabled (its tooltip says "Anna is editing"), editing and
  undo/redo do nothing, and `Ctrl/Cmd + S` has no effect;
- you can still select things, read the Inspector, preview, and **comment**.

### Take over

Click **Take over** to move the lock to you. You can edit immediately.

The previous editor learns at their next renewal — within 30 seconds — with the
message "*your name* took over editing — you are now following their changes".
Their screen switches to following you. Their unsaved edits stay stored as
their own private draft, but they get those edits back only if the document
has not been saved in the meantime. Otherwise Studio says "An unsaved draft from
an older version was not restored — the document has been saved since."

> **Tip.** Before taking over, ask the editor to save — or leave a comment. Take
> over is for when someone left a tab open and went to lunch, not for
> tug-of-war.

---

## Drafts are per person

Every person has their own autosaved draft of each document. Studio writes it
about 1.5 seconds after you stop typing and clears it when you save or discard.
A draft is never validated or published, and nobody else sees it — except
colleagues following you live while you hold the lock. The sync messages and
what they mean are listed in
[Drafts and autosave](Studio-History-and-Versions#drafts-and-autosave).

---

## Comments

Comments are the place for "should this be single or multiple choice?" — not
email.

### Where you can comment

| On | Where the thread is |
|---|---|
| a question | the **Comments** section at the bottom of the Builder's Inspector when the question is selected |
| a page | the same section when the page is selected |
| a flow node | the **Comments** toggle in the node's inspector on the flow canvas |
| a whole flow | the **Comments** toggle in the flow's inspector when no node is selected |

Blocks, codebook entries, settings and Saves have no comment thread. In the
Builder the **Comments** section starts collapsed and shows the number of open
comments. Question cards and flow nodes with open comments show a small count
badge ("2 open comments").

### Writing and handling comments

- Type in **Add a comment…** and click **Comment**, or press `Ctrl/Cmd + Enter`.
  Up to 4,000 characters.
- Each comment shows its author, how long ago it was written ("just now", "5 min
  ago", "3 h ago", "2 d ago") and the text.
- **Resolve** closes a comment when it is handled; resolved comments fold away
  behind **Show *N* resolved**. **Reopen** brings one back. Anyone with the
  member role can resolve or reopen any comment.
- **Delete** removes a comment immediately, without asking. You can delete your
  own comments; owners and admins can delete anyone's.
- With nothing open the section says "No comments yet."

### What comments do not do

- **No mentions and no notifications.** Nobody is emailed or alerted; people see
  comments when they look at the element.
- **Not live.** Comments load when you open the project. To see colleagues' new
  comments, reload the page or reopen the project.
- **Tied to ids and names.** A thread belongs to a question's id, a page's name
  or a node's id. If you rename one, its comments no longer appear on it;
  renaming it back makes them reappear.
- Comments cannot be edited in the app, are not part of Saves and bundles, and
  are not recorded in Activity.
- Only the oldest 500 comments of a project are loaded.

---

## Save conflicts

Each Save records the Save it was built on. If anyone saved the project after
your Save dialog's starting point — a colleague, or you in another tab, on any
document — the dialog shows:

> **Anna saved #18** (“Reworded the screener”) while you were editing on top of
> #17. Reload their Save to see it (your edits stay as an unsaved draft), or
> save yours on top of it as #19.

with **Cancel**, **Reload #18** and **Save on top**:

- **Reload #18** loads the latest Save. Your unsaved edits stay on screen,
  now on top of #18, and you save when you are ready.
- **Save on top** saves your version as #19 anyway. **This replaces the
  document with yours; nothing is merged.** If Anna changed the same document,
  her changes are gone from #19 onward. They remain in #18, and
  **Compare with** in History shows exactly what differs. To recover them,
  re-apply them by hand or restore #18.

Settings changes (study metadata, runtime, reports, adding a connector) and
restores are saved without this check.

Because the edit lock normally keeps two people from editing the same document
at once, a conflict usually means someone saved a *different* document, or the
same person saved from two tabs. Reload unless you are sure.

---

## Roles in practice

Every member of an organization can see every project in it. What each role can
do in the areas on this page:

| | member | admin | owner |
|---|---|---|---|
| Edit, Save, restore, pre-register, deposit | yes | yes | yes |
| Take the edit lock, take over | yes | yes | yes |
| Comment, resolve, delete own comments | yes | yes | yes |
| Delete anyone's comments | — | yes | yes |
| Upload and delete files, create schedules, add connectors | yes | yes | yes |
| Run connectors, add or delete secrets, manage webhooks | — | yes | yes |
| Create, rename and delete projects; delete responses | — | yes | yes |
| See the organization-wide Activity | — | yes | yes |
| Billing, the AI assistant consent | — | — | yes |

Most owner-and-admin controls tell a member up front — they are disabled with
a short reason, or left out:

| Control | What a member sees |
|---|---|
| **New project** | disabled — "Only owners and admins can create projects"; an empty Projects screen adds "Only owners and admins can create projects — ask one to set it up." |
| **Save changes** on Settings → General (rename) | disabled — "Only owners and admins can rename a project." |
| **Add secret** and **Delete** on Settings → Secrets | disabled — "Only owners and admins can add or delete secrets." |
| **Run export** / **Run import** on a connector | disabled — "Only owners and admins can run a connector" |
| **Delete** on a row of the `responses` table (**Data** tab) | not shown |
| **Webhooks** card in Organization settings → Integrations | "Only owners and admins can see and manage the organization's webhooks." |
| **Activity** tab in Organization settings | not shown |

Two of these actions still answer only when used: **Delete project** in
Settings → **Danger Zone** ("Could not delete project. You do not have
permission to do this.") and **Save secret** inside a connector's dialog
("Could not add secret. You do not have permission to do this.").

The full matrix, and how to invite people and change roles, is in
[[Organizations and Team|Studio-Organizations-and-Team]].

---

## A workable team routine

1. **One person owns the questionnaire**; others review with comments.
2. **Reviewers without an account** use a share preview link — see
   [[Testing Your Survey|Studio-Testing-Your-Survey]].
3. **Save with real messages.** History becomes the project's changelog.
4. **Say "saving now" in a comment or chat** before a big Save, and reload when
   a colleague says the same.
5. **Publish to `pilot`** for internal testing and **`main`** for fieldwork.
6. **The analyst builds flows on simulated data** while the questionnaire is
   being finished, and switches the source to the responses on launch day.
7. **Resolve comments** as you act on them, so the open counts stay meaningful.
8. **Archive a research bundle** of each deliverable Save — see
   [[Reproducibility|Studio-Reproducibility]].

## See also

- [[History and Versions|Studio-History-and-Versions]]
- [[Organizations and Team|Studio-Organizations-and-Team]]
- [[The Builder|Studio-Builder-Overview]]
- [[Analysis Flows|Studio-Flows]]
- [[Keyboard Shortcuts|Studio-Keyboard-Shortcuts]]

<!-- studio-nav -->
---

← [[API and API Keys|Studio-API-and-API-Keys]] · [Studio contents](Studio-Overview#all-pages) · [[Security and Privacy|Studio-Security-and-Privacy]] →
