# Keyboard Shortcuts

Every shortcut Studio has, grouped by where it works. `Ctrl/Cmd` means `Cmd`
on macOS and `Ctrl` elsewhere. Tooltips name the keys of your keyboard:
**Undo (Ctrl+Z)** and **Redo (Ctrl+Shift+Z)** on Windows, Linux and Android,
**Undo (⌘Z)** and **Redo (⇧⌘Z)** on a Mac, iPad or iPhone.

> **Note.** `Ctrl/Cmd + S` saves only in the **Builder** and on a **flow's
> canvas**. On other screens it does nothing in Studio, and your browser's own
> "Save page" dialog appears instead. Studio has no command palette.

---

## Everywhere

| Keys | Action |
|---|---|
| `Tab` (first press on a page) | shows **Skip to content**; press `Enter` to jump past the topbar and tabs to the screen itself |
| `Tab` / `Shift + Tab` | move between controls |
| `Enter` or `Space` | activate a focused row or card that opens something (a Save in History, a list row) |
| `Esc` | close the open menu or popover: the account menu, the organization/project switcher, **More** menus, a row's **⋮** menu, the Builder's **+ Question**, **Library**, **+ Page** and **Add script** menus, the Data export menu; the focus goes back to the button that opened it |
| `↑` / `↓`, `Home` / `End` in an open menu | move through its items (the menu takes the focus when it opens): the account menu, the organization/project switcher, a row's **⋮** menu, the Builder's **+ Question**, **Library**, **+ Page** and **Add script** menus, the Data export menu |
| `Tab` in an open menu | close the menu and move on to the next control; in a toolbar's **More** menu (the Builder, Flows and a flow, the codeframe editor, History, Distribute), `Tab` first moves through its items, and leaving it closes it |
| `←` / `→`, `Home` / `End` on a focused tab | move between the tabs of **Organization settings**, **Profile settings**, **Project settings**, a Save in **History** and the codeframe editor (**Answers**, **Suggested words**, **Test a phrase**), without opening one |
| `Enter` or `Space` on a focused tab | open that tab (a settings tab with unsaved changes asks **Discard unsaved changes?** first); `Tab` then moves into the tab's content |

Messages at the foot of the screen are read out by a screen reader as they
appear. A confirmation goes after a few seconds; an error stays until you
dismiss it with its ✕ (**Dismiss**), or until the next message takes its
place, never sooner than you can read it. A message that tells you what to
do first, such as "Save first — a preview is built from a Save", is read out
without interrupting and goes by itself once you have had time to read it; a
longer one stays longer. While the pointer rests on a message, or the focus is
on its **Dismiss** button, it stays where it is.

## Dialogs

| Keys | Action |
|---|---|
| `Esc` | close the dialog without doing anything; clicking outside it does the same; either way the focus goes back to what opened it (from a tab bar, to the tab that is open) |
| `Tab` / `Shift + Tab` | move between the dialog's controls; focus stays inside the dialog and wraps around. A group of radio buttons, such as **Start from** in **New project**, is one stop: the arrow keys choose within it |
| `Enter` | submit, in these fields: **Name** in **New project** (Create) · **Organization name** in **Create organization** (Create) · **Title** or **File name** in **New flow** (Open canvas) · **Name** in **Rename *flow*** and **Duplicate *flow*** (Rename / Duplicate) · **Message** in **Save** (Save; not while a conflict is shown) · **Email** in **Invite member** (Send invite) · **Value** in **Add secret** (Add secret) · **Name** in **Save … to library** (Save to library) |
| `↓` on the template picker, then `↑` / `↓` | open the template list in **New project**, then move through the templates |
| `Esc` in the template list | close the list (not the dialog) |
| `Enter` or `Space` on the drop area | choose a file in **Import questionnaire** |

Other dialogs (for example **Deposit**, **Connect …**, **Schedule a run**,
**Upload file**) have no `Enter` shortcut; use their buttons.

A dialog opens with the focus in its first field, so you can type at once; a
dialog that only asks you to confirm takes the focus itself.

## Other fields with Enter

| Where | `Enter` does |
|---|---|
| **Profile → API keys**, **Key name** | **Create key** |
| **Organization settings → Integrations**, **Endpoint URL** | **Add webhook** |
| **Project settings → Runtime**, package field | adds the package to the list |

## Builder

| Keys | Action | Notes |
|---|---|---|
| `Ctrl/Cmd + S` | open the **Save** dialog | works even while you type in a field; with nothing changed it offers to re-pin and re-validate; does nothing while you are following a colleague; with unapplied **Source** edits it switches to **Source** and says "Apply or revert your source edits before saving." |
| `Ctrl/Cmd + Z` | undo | not while the cursor is in a text field (the field's own undo works there) and not while following |
| `Shift + Ctrl/Cmd + Z` or `Ctrl/Cmd + Y` | redo | same conditions |
| `Enter` in an answer option's **Label** | add a new option below it, with the next code | Inspector → options |
| `Enter` in **Variable name** | apply the rename (leaving the field does the same) | question Inspector, variable card; conditions, quotas, piping and scripts that use the variable follow it |
| `Enter` in a page's **Name** | apply the new name (leaving the field does the same) | page Inspector; the name is not applied while you type |
| `Esc` in a page's **Name** | put the current name back | page Inspector |

Undo keeps up to **100 steps**. The undo history is cleared when you save,
when you switch projects, and while a colleague's edits are shown to you.

## Logic map

| Keys | Action |
|---|---|
| `Enter` (or double-click) on a page | open that page in **Structure** |
| `Enter` (or double-click) on a row of the dependency view | open that page or question in **Structure** |

## Flows canvas

| Keys | Action | Notes |
|---|---|---|
| `Ctrl/Cmd + S` | open the **Save** dialog | works while typing; does nothing while following |
| `Ctrl/Cmd + Enter` | **Run to here** on the selected node; with nothing selected, preview the whole flow | works while typing and in every view (Canvas, List, Report) |
| `Delete` / `Backspace` | delete the selected node | |
| `Ctrl/Cmd + D` | duplicate the selected node, with the same wires into it and none out of it | |
| `Ctrl/Cmd + Z` | undo | |
| `Shift + Ctrl/Cmd + Z` | redo | `Ctrl/Cmd + Y` does not redo on flows |
| double-click a node | select it and **Run to here** | Canvas view |
| `F` | turn [focus mode](Studio-Flows#focus-mode) on or off: the canvas takes the whole window, the palette and the inspector stay | Canvas view only, nothing in List or Report; the key marked F in any keyboard layout; not with `Ctrl`, `Cmd` or `Alt`; not on a list field of the inspector, where a letter picks a value |
| `Esc` | clear the selected node; with none selected, leave focus mode | Canvas view only; an open dialog, a menu, a list open in the inspector, an **ⓘ** tip or the text field that has the focus uses it first; a node or wire that has the keyboard focus while none is selected keeps it (press `F` instead); in full screen the first `Esc` leaves full screen |

`Delete`, `Backspace`, `Ctrl/Cmd + D` and undo/redo are ignored while the
cursor is in a field or on a list field of the inspector, open or closed, in
the **Report** view, and while a colleague holds the edit lock. `F` is
ignored while a text field or a list field has the focus and while a list, a
dialog or a menu is open (a focused checkbox or switch does not stop
it, nor does a **Data file** node's **Reading options** left open in the
inspector), and `Ctrl/Cmd + F` stays the browser's Find. With **More** open,
`Esc` closes it and the next `Esc` is the canvas's; `Tab` out of an open
**More** closes it too. On a flow, undo history
survives a Save and is cleared when you leave the flow.

With the keyboard, `Tab` reaches the canvas's buttons — **Zoom in**, **Zoom
out**, **Fit view**, **Focus mode** and, in focus mode, **Full screen** —
right after the palette, before the nodes and wires.

## Flow inspector lists

A parameter with a fixed set of values is a list in the flow inspector (see
[Lists in the inspector](Studio-Flows#lists-in-the-inspector)).

| Keys | Where | Action |
|---|---|---|
| `Enter`, `Space`, `↓` or `↑` | on the field | open the list on the chosen value (`Home` / `End`: on the first / last) |
| a letter | on the field | open the list on the first value that starts with it; a list of more than ten opens with the letter in its filter box. `F` does not toggle focus mode here |
| `↑` / `↓` | in the list | move one row; past the last, round to the first |
| `Home` / `End` | in the list | the first / the last row (in a filter box, only while it is empty) |
| `Page Up` / `Page Down` | in the list | about a screenful up / down, stopping at the first and the last row |
| letters | in a list of ten or fewer | jump to the first value that starts with them |
| letters | in a filter box | keep the entries that contain every word typed |
| `Enter` or `Space` | in the list | choose the lit row (`Space` types a space in a filter box) |
| `Esc` | in the list | close the list, back on the field; in a filter box with text, the first `Esc` empties the box and the second closes the list. Focus mode and the node's selection stay |
| `Tab` / `Shift + Tab` | in the list | close the list and move on to the next field / stay on the field |
| `Esc` | on the closed field | clear the selected node, as on any button of the inspector |

`Delete`, `Backspace`, `Ctrl/Cmd + D` and `Ctrl/Cmd + Z` do nothing to the
node from a list field, open or closed; `Ctrl/Cmd + S` and `Ctrl/Cmd +
Enter` still save and preview.

## Flows List view and the node picker

The **List** view shows the same flow as a table you can work from the
keyboard.

| Keys | Action |
|---|---|
| `↑` / `↓` | move between node rows (the focused node is selected) |
| `Enter` on a row | select the node and **Run to here** |
| `Ctrl/Cmd + K` | open **Add a node** (the **Node** picker under the table) |
| `↑` / `↓` in the picker | choose a node type |
| `Enter` in the picker | add the chosen node |
| `Esc` in the picker | close it |

The picker's footer repeats this: "↑ ↓ choose · Enter adds · Esc closes".
`Ctrl/Cmd + K` works only while the List view is showing.

## Comments

| Keys | Action |
|---|---|
| `Ctrl/Cmd + Enter` | post the comment (in any **Add a comment…** box) |

## Data

| Keys | Action |
|---|---|
| `Enter` in **Filter loaded rows…** | search **every** row of the table on the server, not only the loaded ones (the same as **Search all rows**) |
| `Enter` or `Space` on a focused column header | sort the loaded rows by that column |
| `↑` / `↓`, `Home` / `End` in the export menu | move through the formats; `Enter` exports |
| `Esc` | close the export menu; the focus goes back to **Export** |

## Panels and resizers

The divider between the canvas and an inspector or preview (Builder inspector,
flow node inspector, report preview) can be resized from the keyboard:

| Keys | Action |
|---|---|
| `←` | widen the panel by 16 pixels |
| `→` | narrow the panel by 16 pixels |
| `Home` | back to the default width |

Double-clicking the divider also resets it. The width is remembered in your
browser.

---

## Mouse and drag

| Gesture | Effect |
|---|---|
| Drag a question card | move it within the page, into or out of a block, or onto another page in the page rail |
| Drag a page in the rail | reorder the questionnaire (the **↑** / **↓** buttons above the page do the same) |
| Drag a node from the palette onto the canvas | add it where you drop it (clicking a palette item adds it too) |
| Drag a node on the canvas | move it: it follows the pointer with its wires, the minimap shows, and it settles on the grid when you let go; one **Undo** step; one node at a time; not while you follow a colleague |
| `Shift` + drag on the canvas | pan, as a plain drag on an empty spot does (there is no selection box) |
| Drag from a node's output to another node's input | connect them |
| Double-click a node | **Run to here** |
| Double-click a page in the Logic map | open it in **Structure** |
| Click a column header in **Data** | sort the loaded rows |
| Drag a panel divider | resize the panel; double-click to reset |

## See also

- [[The Builder|Studio-Builder-Overview]]
- [[Analysis Flows|Studio-Flows]]
- [[Working Together|Studio-Collaboration]]
- [[History and Versions|Studio-History-and-Versions]]

<!-- studio-nav -->
---

← [[Limits and Quotas at a Glance|Studio-Limits-Reference]] · [Studio contents](Studio-Overview#all-pages) · [[FAQ and Troubleshooting|Studio-FAQ-and-Troubleshooting]] →
