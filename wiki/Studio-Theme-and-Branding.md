# Theme and Branding

**Builder → Theme** decides how the survey looks and reads to respondents:
colors, type, logo, what a respondent can do, and every fixed phrase the
survey shows. This page describes each control and what it really does in the
published survey. It also covers the organization's house style, which gives
every new study the same look.

The Theme tab is under **More** in the Builder's tab strip. Every setting is
stored in the questionnaire, versioned with each Save, and built into the
published survey and the downloaded `questionnaire.py`.

---

## The Theme tab

The tab is one scrolling form with an index on the left, ordered by the
question you are answering:

| Section | Blurb | Answers |
|---|---|---|
| **Appearance** | "How the questionnaire looks to respondents." | colors, typography, question style, progress |
| **Branding** | "Whose study this is, and what carries its name." | logo, institution, subtitle |
| **Respondent experience** | "What a respondent can see, do and read." | light/dark, navigation, survey information, completion screen |
| **Wording** | "Every fixed phrase the runtime shows." | the 22 runtime texts |
| **Advanced** | "Rarely needed, and nothing here is checked for you." | measurements, typefaces, custom CSS |

- The number beside a section in the index is how many settings **this
  study** makes there (tooltip "N set by this study"), not how many controls
  the section has.
- A section with settings shows **Reset N** in its header. It asks "Reset
  <Section>?": "This drops the N setting(s) this study makes in <Section> and
  lets the engine's defaults answer again. Nothing is saved until you press
  Save." Press **Reset** to confirm.
- An empty field shows the default as its placeholder, so what you read is
  what a respondent gets.
- The Theme tab has no preview of its own. Switch to **Structure →
  Preview** to see changes (it re-renders about half a second after each
  edit), and check the published result with the header **Preview** (see
  [[Testing Your Survey|Studio-Testing-Your-Survey]]).
- If your organization has a house style that this study does not follow, a
  banner offers **Use the organization's house style** (see
  [below](#the-organizations-house-style)).

There are no ready-made theme presets. The closest thing is the **Font
preset**, and the house style gives you your own starting point.

---

## Appearance

### Colors

| Label | Default | Used for |
|---|---|---|
| **Primary** | `#2c5f8a` | buttons, selected answers, the progress bar |
| **Background** | `#fbfbfb` | the page |

**More colors** (folded away):

| Label | Default |
|---|---|
| **Accent** ("falls back to the primary color") | same as Primary |
| **Cards and panels** | `#ffffff` |
| **Text** | `#1a1a1a` |
| **Muted text** | `#5a5a5a` |
| **Borders** | `#e6e4df` |

Each color has a picker and a text field. The text field accepts hex
(`#1f5fd6`) or any CSS color.

**Contrast readouts.** Under the colors Studio prints the contrast ratio of
the pairs that decide whether the survey can be read:

- "Body text on the page reads at X:1", which should be at least 4.5:1;
- "The primary colour reads at X:1", at least 3:1 (non-text);
- inside **More colors**: "Muted text reads at X:1", at least 4.5:1.

Above the floor the line ends "— above the N:1 floor". Below it, the line
turns red: "— below the N:1 WCAG floor; respondents will struggle to read it".
It is a measurement, not a veto; you can still save and publish. Only hex
colors get a readout. A named color or `rgb(…)` shows none.

### Typography

| Label | Options | Default |
|---|---|---|
| **Font preset** | **academic** (Source Serif 4 for text, Inter for buttons and labels), **humanist** (Nunito), **modern** (Inter) | academic |
| **Density** ("type size, leading and the air between questions") | **comfortable**, **compact**, **spacious** | comfortable |

The fonts load from Google Fonts. To use your own typefaces, see
[Measurements and typefaces](#measurements-and-typefaces).

### Question style and progress

| Label | Options | Default |
|---|---|---|
| **Style** | **plain**, **carded**, **divided**, **accent** | plain |
| **Progress** ("hidden removes the indicator entirely") | **bar**, **dots**, **both**, **hidden** | bar |

> **Current limitation.** The **Progress** setting does not yet behave as its
> labels say, and published surveys differ from the Builder's previews:
>
> | Progress | Published survey (and the header **Preview**) | Builder previews (canvas, Walkthrough, share link) |
> |---|---|---|
> | **bar** | no progress indicator | a bar with a section label |
> | **dots** | a row of page dots | the bar **and** the dots |
> | **both** | a row of page dots | the bar and the dots |
> | **hidden** | nothing; but if **dots** or **both** was chosen before, the dots stay | no bar; dots stay as on the left |
>
> - To show **no indicator anywhere**: choose **bar**, then **hidden**.
> - To show a **bar in the published survey**: open the **Source** tab, add
>   `"show_progress": true` inside `"options"`, press **Apply** and Save.
>   Clicking a Progress pill later removes it again.
> - Questionnaires started from a library template already carry that
>   setting, so their published surveys show the bar until you click a
>   Progress pill.
> - The text beside the bar is always "Welcome" on the first page, "Section N
>   of M" in between and "Final thoughts" on the last page. It cannot be
>   changed.
> - The page dots can be clicked. Respondents can jump **forward** to any
>   page, past unanswered required questions and your routing. Prefer the bar
>   when routing or required answers matter.

---

## Branding

### Logo

| Label | What to enter |
|---|---|
| **Logo URL** (hint "upload under Files and paste the link") | the web address of your logo image. A live preview shows beside the field |
| **Position** | **left** (default), **center**, **right** |

> **Tip.** Use a **stable public address** for the logo, such as the logo on
> your institution's website. A link copied from **Files** is a download link
> that expires after a few minutes, and the logo then disappears for
> respondents.

### Study identity

| Label | Notes |
|---|---|
| **Institution** (placeholder "Institute of …") | shown in the header under the title, and in the footer (the part before a "—") |
| **Study subtitle** | shown in the header under the institution |
| **Logo text** ("shown when there is no logo image") | short text shown *instead of* an image when **Logo URL** is empty. It is not alt text. Left empty, the survey uses the initials of the institution's first two words, which is what the placeholder shows |

The header shows, left to right, the logo (image or logo text), the survey
title, the institution and the subtitle.

---

## Respondent experience

### Light and dark

| Label | Options | Default |
|---|---|---|
| **Color mode** ("a look half the sample can change is a variable you did not mean to have") | **Respondent chooses**, **Always light**, **Always dark** | Respondent chooses |
| **Starts on** ("system follows the respondent's device; they can change it either way"), shown only with **Respondent chooses** | **light**, **dark**, **system** | light |

With **Respondent chooses**, a small moon / sun button under the footer
switches between light and dark. The survey remembers the choice in that
browser, for this survey only. **Starts on** is only where respondents begin.

With **Always light** or **Always dark** the button is not shown and every
respondent sees the same thing. Do that when the presentation is part of the
measurement: color-coded scales, image stimuli, anything whose contrast you
would not want to vary between respondents. Otherwise leave the choice with
the respondents; reading on a dark screen is an accessibility need for some
people.

### Navigation

- **Show the survey title** (on by default). Turned off, it hides the
  whole header only when **Institution** and **Logo URL** are both empty. If
  either is set, the header stays, and the title stays with it.

  > **Tip.** To hide just the title while keeping a logo *(Plus)*: add
  > `.siamang-header__title { display: none; }` under **Custom CSS**.

- **Allow going back** (on by default). Turned off, it hides **← Previous**
  and disables going back with the `Esc` key, the swipe gesture and the page
  dots. Use it for experiments where later answers must not revise earlier
  ones.

### Survey information

| Label | Where respondents see it |
|---|---|
| **Estimated minutes** | nowhere (see below) |
| **Contact email** | footer of every page, as a **Contact research team** email link |
| **Privacy URL** | footer of every page, as a **Privacy** link (opens in a new tab) |
| **Ethics statement** | footer of every page, as a paragraph under the links |

The footer also carries the institution's name, and it appears on end pages
and on the completion screen too.

> **Current limitation.** **Estimated minutes** is saved but **not shown**
> to respondents. Say how long the survey takes in the first page's text or
> in the **Study subtitle**.

### Completion screen

When the survey ends on a content page, the respondent presses **Submit
responses** and sees the completion screen: a title, a message, their
**Response ID** and the **Submitted** time.

| Label | Placeholder |
|---|---|
| **Title** | "Thank you for participating" |
| **Message** | "Your responses help inform open research." |

> **Current limitation.** Setting **Title** makes the questionnaire
> **invalid**: Save is refused and the canvas preview stops rendering. If you
> set it, clear the field again. The title respondents see is always "Thank
> you for participating".
>
> **Message** works. If you leave it empty, respondents see "Thank you for
> your participation!", not the placeholder.
>
> For your own title and text, end the survey on a **Final (thank you)** page
> instead. It shows its own title and body (see
> [[Logic and Branching|Studio-Logic-and-Branching]]).

---

## Wording

Every fixed phrase the survey shows can be replaced. This is how a survey
runs in another language today. The section opens with: "Leave a field empty
and the respondent sees the default under it. Replacing all of them is how a
survey runs in another language today — one questionnaire is still one
language."

- **Search wording…** searches labels, defaults and your own texts.
- Filter chips: **All**, **Buttons**, **Answering**, **Saving**, **Failures**,
  **Access**.
- "N of 22 replaced" counts your replacements. **Reset all** asks "Reset every
  runtime text?" ("This drops the N phrase(s) this study replaces and puts the
  runtime's own wording back. Nothing is saved until you press Save.").
- A replaced field shows "default: …" under it and a **×** (tooltip "Back to
  “…”") that restores that one field.

| Group | Label | Default |
|---|---|---|
| Buttons and navigation | **Next button** | `Next section →` |
| | **Previous button** | `← Previous` |
| | **Submit button** | `Submit responses` |
| | **Progress: “Page”** | `Page` (screen readers only, see below) |
| | **Progress: “of”** | `of` (screen readers only) |
| | **“of” elsewhere** | no effect (see below) |
| Answering | **Unanswered required question** | `This question requires an answer.` |
| | **Dropdown placeholder** | no effect |
| | **“selected” counter** | no effect |
| Saving and resuming | **While submitting** | `Submitting your responses…` |
| | **While saving** | `Saving…` |
| | **Resume prompt** | `We saved your progress from earlier. Would you like to resume?` |
| | **Resume button** | `Resume` |
| | **Start over button** | `Start over` |
| When something fails | **Failed submission title** | `Submission failed` |
| | **Failed submission text** | `We could not save your responses.` |
| | **Try again button** | `Try again` |
| | **Save locally button** | `Save locally and finish` |
| Access code | **Access code: title** | `Access required` |
| | **Access code: text** | `Please enter the access code to begin this survey.` |
| | **Access code: field** | `Enter access code` |
| | **Access code: button** | `Continue` |

The four access-code texts only appear when the survey requires an access code
(see [Access codes](Studio-Distribution-Channels#access-codes)).

> **Current limitation.** Not every word is replaceable yet:
>
> - **“of” elsewhere**, **Dropdown placeholder** and **“selected” counter**
>   have no effect. The dropdown always reads "— Select —" and the
>   multiple-choice counter "N of M selected".
> - **Progress: “Page”** and **Progress: “of”** are only read out by screen
>   readers. The visible progress text is "Welcome", "Section N of M" and
>   "Final thoughts".
> - These texts stay in English: "Select at least N more", "Other", "None of
>   the above", "No options found", the format messages ("Please enter a valid
>   email address." and similar), "Response ID" and "Submitted", the redirect
>   notices ("You will be redirected in 5 seconds. Click here if not
>   redirected.", "Redirecting you now. Continue if you are not redirected."),
>   the closed and full-sample screens ("Survey closed", "Thank you for your
>   interest", …), the footer's "Privacy" and "Contact research team", "Invalid
>   access code. Please try again.", "Attempt N of 3." and the default titles
>   of the completion screen and screen-out pages.
>
> For another language, translate your questions and these 19 fields, and end
> the survey on a Final page with your own title and text.

---

## Advanced

### Measurements and typefaces

| Label | Placeholder (default) |
|---|---|
| **Content width** | `700px` |
| **Corner radius** | `4px` |
| **Font size** | `15.5px` |
| **Line height** | `1.6` |
| **Body typeface** ("a CSS font stack; overrides the preset") | preset default |
| **Heading typeface** | preset default |
| **Interface typeface** ("buttons, labels, the progress strip") | preset default |
| **Monospace typeface** | preset default |

The values are CSS: sizes with units, typefaces as font stacks
(`"Georgia", serif`). The font preset covers all four typefaces until you set
one here. A typeface you name must be available to respondents, either
installed on their device or loaded by your custom CSS.

### Custom CSS *(Plus)*

A box for your own stylesheet (placeholder
`.siamang-progress { margin-bottom: 40px; }`): "Appended after the generated
stylesheet, so it wins. Unlike everything above it is not checked by anything
— a bad rule reaches respondents. Preview before you publish."

On every plan you can write it, see it in the Builder's previews, and Save.
Below Plus, **publishing** a Save that carries custom CSS is refused with
"Custom CSS in the theme is included from Plus — clear it under Theme →
Custom CSS or upgrade to deploy this Save".

---

## What the form does not offer

A few theme settings exist in the questionnaire format but are not offered
here. Some have no visible effect in the current survey, and others are set
elsewhere: return URLs on the Panel chip (see
[[Panel Providers|Studio-Panel-Providers]]), access codes on Distribute. The
**Source** tab lets you edit the questionnaire directly if you need to, at
your own risk. Its **Check** button runs the engine's check on your edits
before you **Apply** and Save them.

---

## The organization's house style

A lab that runs twenty studies has one logo, one palette, one typeface and
one privacy link. The house style holds them once.

**Organization → Settings → Branding** ("The look every new study starts
from") is a narrower form than the Theme tab: only what an institution owns,
nothing that belongs to one study. It has no wording, no subtitle, no
estimated time and no redirects.

| Control | Options |
|---|---|
| **Typeface** ("the preset the questionnaire starts from") | academic, humanist, modern |
| **Questions** | plain, divided, carded, accent |
| **Density** | compact, comfortable, spacious |
| **Progress** | bar, dots, both |
| **Theme** | Respondent chooses, Always light, Always dark; plus **Starts on** (light, dark, system) |
| **Logo and institution** | **Institution** (placeholder "Independent Polling Lab"), **Logo text**, **Logo URL**, **Logo position**, **Show the study title above the questions** |
| **What a respondent can reach** | **Privacy policy**, **Contact email**, **Ethics statement** |
| **Colors** | the seven colors of the Theme tab |
| **Measurements and typefaces** | **Measure** (content width), **Corner radius**, **Font size**, **Line height**, the four typefaces |
| **Custom CSS** | see below |

The note at the top says: "A control you have not touched shows the engine's
default and is **not** part of your house style — only what you set here is
copied into a new study."

**Save changes**, **Discard** and **Clear** ("Clear the house style?" — "New
studies will start from the engine's defaults again. The studies you already
have keep their look.") are for owners and admins. Members see "Only owners
and admins can set the house style." See
[Branding](Studio-Organizations-and-Team#branding).

### A stamp, not a setting

When a project is created, the house style is **copied** into its
questionnaire. After that, the study's own Theme tab is the only thing that
decides; nothing reads the organization's copy while the survey runs. That is
deliberate: the look travels in the questionnaire, so a colleague who
downloads the bundle and re-runs `questionnaire.py` gets the instrument you
fielded, not what your organization's settings say today.

- **A starting document wins.** A questionnaire taken from your library, or
  a template that asks for a particular look, keeps its own settings. The
  house style fills in only what it leaves unsaid. For an empty project,
  that is everything.
- **Changing the house style changes nothing that already exists.** To bring
  a study up to date, open its Theme tab. The banner "Your organization has a
  house style this study does not follow." offers **Use the organization's
  house style**. The confirmation names what will change ("This changes N of
  this study's look settings to your organization's — primary color, logo
  url, …"). Here the house values win, because pressing the button is you
  asking for them. It is an ordinary unsaved edit: it shows in the Save's
  changes, and restoring an earlier Save undoes it.
- A questionnaire created with **Draft from a brief** starts without the
  house style. Use the button afterwards.

### Custom CSS in the house style

Custom CSS is a *(Plus)* feature at publishing time:

- Below Plus it is **left out** of the projects the house style starts, so you
  are not handed a study that cannot be published. Upgrade, and the next
  project you create carries it.
- **Use the organization's house style** and the Builder's **Create
  questionnaire** button (in a project with no questionnaire yet) copy the
  custom CSS **whatever the plan**. Below Plus, clear it under **Theme →
  Custom CSS** before you publish.
- Below Plus the form says: "Custom CSS is included from Plus. You can write
  it here, but on the Free plan it is left out of the projects this style
  starts — a Save carrying it does not deploy."

## See also

- [[The Builder|Studio-Builder-Overview]]
- [[What Respondents See|Studio-Respondent-Experience]]
- [[Organizations and Team|Studio-Organizations-and-Team]]
- [[Scripts|Studio-Scripts]]
- [[Testing Your Survey|Studio-Testing-Your-Survey]]

<!-- studio-nav -->
---

← [[MaxDiff and Conjoint|Studio-MaxDiff-and-Conjoint]] · [Studio contents](Studio-Overview#all-pages) · [[Scripts|Studio-Scripts]] →
