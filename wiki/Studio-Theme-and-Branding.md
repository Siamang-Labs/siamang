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
| **Appearance** | "How the questionnaire looks to respondents." | colors, typography, question style, progress, section labels |
| **Branding** | "Whose study this is, and what carries its name." | logo, institution, subtitle |
| **Respondent experience** | "What a respondent can see, do and read." | light/dark, navigation, survey information, completion screen |
| **Wording** | "Every fixed phrase the runtime shows." | the 69 runtime texts |
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
- Everything here is built into the survey when you publish. A survey already
  in the field keeps the look and wording of the build it was published with
  until you publish it again.

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
(`#1f5fd6`) or any CSS color. The picker swatch follows the text field while
it holds a 3- or 6-digit hex value; for anything else (a named color,
`rgb(…)`, a half-typed value) it shows the default.

**Contrast readouts.** Under the colors Studio prints the contrast ratio of
the pairs that decide whether the survey can be read:

- "Body text on the page reads at X:1", which should be at least 4.5:1;
- "The primary color reads at X:1", at least 3:1 (non-text);
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

The preset fonts (Source Serif 4, Inter and Nunito) come with the survey and
load from the survey host — nothing is requested from Google Fonts or another
font service. The Builder's preview, the Walkthrough and share-preview links
load them from Studio. A survey published before this update loads them from
Google Fonts until you republish it. To use your own typefaces, see
[Measurements and typefaces](#measurements-and-typefaces).

### Question style and progress

| Label | Options | Default |
|---|---|---|
| **Style** | **plain**, **carded**, **divided**, **accent** | plain |
| **Progress** ("hidden removes the indicator entirely") | **bar**, **dots**, **both**, **hidden** | bar |
| **Section labels** ("“Welcome”, “Section 2 of 5”, “Final thoughts” above each page title; off, the progress text reads “Page 2 of 5”") | checkbox | on |
| **Progress text** ("the words beside the progress bar") | checkbox | on |

The published survey, the header **Preview** and the Builder's previews
(canvas, Walkthrough, share link) all show the same indicator:

| Progress | What respondents see |
|---|---|
| **bar** | the progress bar and its text |
| **dots** | a row of page dots, and no bar |
| **both** | the bar and the page dots |
| **hidden** | neither, whatever was chosen before |

Choosing **bar**, **dots** or **both** switches the indicator on;
**hidden** switches it off. A questionnaire that says nothing about progress
shows the bar.

**What the indicator counts.** The bar and the words count the question
pages open to the respondent, in the order they get them: pages hidden by
their Show if / Hide if, and end pages (Final, Screen-out, Redirect), are left
out. A page that a branch rule or Skip to jumps over still counts, so after
such a jump the bar moves on by more than one step. The last question page
reads "Final thoughts" with a full bar, also in a survey that ends on a Final
page followed by a Screen-out page.

**Section labels.** With **Section labels** on, each question page carries a
small label above its title: "Welcome" on the first page, "Section n of m" on
the pages between and "Final thoughts" on the last, and the same words stand
beside the bar. For a respondent who is shown five pages, that is Welcome,
Section 1 of 4, Section 2 of 4, Section 3 of 4, Final thoughts. Switched off,
the pages carry no label and the text beside the bar reads "Page 2 of 5". The
words themselves are Wording fields (**Section label: first page**, **Section
label: pages between**, **Section label: last page**, **Progress: “Page”**,
**Progress: “of”**). With **Progress text** off, the bar has no words at all.

**Page dots.** One dot per question page the bar counts; hidden pages and
end pages get none.
The dots let a respondent go **back**, never forward:

- a dot of a page they visited on the way to the current page takes them back
  there, and **← Previous** then continues from that page;
- dots ahead of the current page, and dots of pages the routing skipped, are
  grayed out and do nothing;
- only pages actually visited are drawn as completed;
- with **Allow going back** off, no dot goes back.

A respondent who resumes a saved interview can go back along the saved path.

> **Note.** A survey published before these fixes still shows its old
> indicator until you publish it again: there, **dots** showed the bar as
> well, **hidden** kept the dots when **dots** or **both** had been chosen
> before, the dots could jump **forward** past required questions and
> routing, and the section label counted every page, end pages included.
> Earlier still, surveys were published **without** the bar unless the
> questionnaire's `options` held `"show_progress": true`. Publish again to
> get the indicator described above.

---

## Branding

### Logo

| Label | What to enter |
|---|---|
| **Logo URL** (hint "a public https:// address of the image — a file under Files has no public link") | the web address of your logo image. A live preview shows beside the field |
| **Position** | **left** (default), **center**, **right** |

> **Tip.** Use a **stable public address** for the logo, such as the logo on
> your institution's website. A file uploaded under **Files** has no public
> link: its download links expire after 5 minutes, and the logo would then
> disappear for respondents.

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
(Surveys published before this fix shared one remembered choice across the
surveys of the host; after you publish again, a returning respondent starts
once more from **Starts on**.)

With **Always light** or **Always dark** the button is not shown and every
respondent sees the same thing. Do that when the presentation is part of the
measurement: color-coded scales, image stimuli, anything whose contrast you
would not want to vary between respondents. Otherwise leave the choice with
the respondents; reading on a dark screen is an accessibility need for some
people.

### Navigation

- **Show the survey title** (on by default). Turned off, it hides the survey
  title. The header stays when **Institution** or **Logo URL** is set, with
  the logo and the institution but without the title; with both empty, the
  whole header goes. (A survey published before this fix kept the title
  whenever a logo or an institution was set; publish it again.)

- **Allow going back** (on by default). Turned off, it hides **← Previous**
  and disables going back with the `Esc` key, the swipe gesture and the page
  dots. Use it for experiments where later answers must not revise earlier
  ones.

### Survey information

| Label | Where respondents see it |
|---|---|
| **Estimated minutes** | under the title of the first page, as "About N minutes" ("About 1 minute" for 1) |
| **Contact email** | footer of every page, as a **Contact research team** email link |
| **Privacy URL** | footer of every page, as a **Privacy** link (opens in a new tab) |
| **Ethics statement** | footer of every page, as a paragraph under the links |

The footer also carries the institution's name, and it appears on end pages
and on the completion screen too. The link texts and the estimate's wording
are Wording fields (**Contact link**, **Privacy link**, **Estimated time**,
whose `{minutes}` is filled in; a replaced text has no separate form for 1
minute).

The estimate appears on the first page the respondent is shown, only. A
survey published before this fix showed no estimate; publish it again.

### Completion screen

When the survey ends on a content page, the respondent presses **Submit
responses** and sees the completion screen: a title, a message, their
**Response ID** and the **Submitted** time.

| Label | Placeholder |
|---|---|
| **Title** | "Thank you for participating" |
| **Message** | "Your responses help inform open research." |

- **Title** is the heading. Left empty, respondents see "Thank you for
  participating".
- **Message** is the text under the title. If you leave it empty,
  respondents see "Thank you for your participation!", not the placeholder.
  If the questionnaire sets `ui.completion_body` in **Source**, the hint says
  "the completion text set in Source (ui.completion_body) is shown instead",
  and that text wins.

**Final pages.** A survey that ends on a **Final (thank you)** page shows that
page's own title and body (see
[End pages](Studio-Logic-and-Branching#end-pages)); a Final page Studio adds
comes with both. **Title** and **Message** fill in only what the Final page
leaves empty, and the fields say so when a Final page has its own:

- **Title** hint: "your Final page “<title>” shows its own title; this one is
  shown only where the survey ends without one — Submit on a question page,
  or a Final page with no title";
- **Message** hint: "your Final page “<title or name>” shows its own text; this
  one is shown only where the survey ends without it — Submit on a question
  page, or a Final page with no body".

To change what most respondents read at the end, edit the Final page. A
Screen-out page with no title shows the Wording field **Screen-out page
title** ("Thank you"); one with no body shows the **Message**, so give every
Screen-out page a body of its own.

---

## Wording

Every fixed phrase the survey shows can be replaced, apart from the few
listed at the end of this section. This is how a survey runs in another
language today. The section opens with: "Leave a field empty
and the respondent sees the default under it. Replacing all of them is how a
survey runs in another language today — one questionnaire is still one
language."

It goes on: "In a text, {n}, {total}, {min}, {max}, {minutes} and {seconds}
are filled in by the survey, and {link} is the link that follows."

- **Search wording…** searches labels, defaults and your own texts.
- Filter chips: **All**, **Buttons**, **Answering**, **Saving**, **Ending**,
  **Failures**, **Closed**, **Around**, **Access**.
- "N of 69 replaced" counts your replacements. **Reset all** asks "Reset every
  runtime text?" ("This drops the N phrase(s) this study replaces and puts the
  runtime's own wording back. Nothing is saved until you press Save.").
- A replaced field shows "default: …" under it and a **×** (tooltip "Back to
  “…”") that restores that one field.

With no field set, every text reads exactly as the defaults below.

| Group | Label | Default |
|---|---|---|
| Buttons and navigation | **Next button** | `Next section →` |
| | **Previous button** | `← Previous` |
| | **Submit button** | `Submit responses` |
| | **Section label: first page** | `Welcome` |
| | **Section label: pages between** | `Section {n} of {total}` |
| | **Section label: last page** | `Final thoughts` |
| | **Progress: “Page”** | `Page` |
| | **Progress: “of”** | `of` |
| | **Estimated time** | `About {minutes} minutes` |
| Answering | **Unanswered required question** | `This question requires an answer.` |
| | **Required matrix: rows left** | `Please answer every row.` |
| | **Dropdown placeholder** | `— Select —` |
| | **Dropdown search** | `Type to search…` |
| | **Dropdown search: nothing found** | `No options found` |
| | **“of” in “2 of 3 selected”** | `of` |
| | **“selected” in “2 of 3 selected”** | `selected` |
| | **Choice limit reached** | `Maximum reached` |
| | **Too few choices** | `Select at least {n} more` |
| | **“Other” option** | `Other` |
| | **“Other” text box** | `Please specify...` |
| | **“None of the above” option** | `None of the above` |
| | **“N/A” option** | `Not applicable` |
| | **Number below its minimum** | `Minimum value is {min}` |
| | **Number above its maximum** | `Maximum value is {max}` |
| | **Characters left** | `{n} characters remaining` |
| | **Ranking: how to answer** | `Tap or drag to rank` |
| | **Ranking: items not ranked yet** | `Remaining options` |
| | **Answer in the wrong format** | `Please check the format of your answer.` |
| | **Invalid email address** | `Please enter a valid email address.` |
| | **Invalid phone number** | `Please enter a valid phone number.` |
| | **Invalid web address** | `Please enter a valid web address (https://…).` |
| | **Invalid date** | `Please enter a valid date.` |
| | **Invalid time** | `Please enter a valid time.` |
| Saving and resuming | **While submitting** | `Submitting your responses…` |
| | **While saving** | `Saving…` |
| | **Resume prompt** | `We saved your progress from earlier. Would you like to resume?` |
| | **Resume button** | `Resume` |
| | **Start over button** | `Start over` |
| At the end | **Completion screen: “Response ID”** | `Response ID` |
| | **Completion screen: “Submitted”** | `Submitted` |
| | **Screen-out page title** | `Thank you` |
| | **Redirect page: countdown** | `You will be redirected in {seconds} seconds. {link} if not redirected.` |
| | **Redirect page: link** | `Click here` |
| | **Redirecting at once** | `Redirecting you now. {link} if you are not redirected.` |
| | **Redirecting at once: link** | `Continue` |
| When something fails | **Failed submission title** | `Submission failed` |
| | **Failed submission text** | `We could not save your responses.` |
| | **Submission attempt** | `Attempt {n} of {max}.` |
| | **Try again button** | `Try again` |
| | **Save locally button** | `Save locally and finish` |
| | **Submission error title** | `Submission error` |
| | **Submission error text** | `We could not save your responses. Please refresh and try again.` |
| | **Page error title** | `Something went wrong` |
| | **Page error text** | `An unexpected error occurred. Your previous answers have been saved.` |
| | **Survey error title** | `Survey temporarily unavailable` |
| | **Survey error text** | `We encountered an unexpected error. Your previous answers have been saved.` |
| | **Reload button** | `Reload survey` |
| Closed or full | **Quota full: title** | `Thank you for your interest` |
| | **Quota full: text** | `We have already reached our target sample for participants like you.` |
| | **Survey closed: title** | `Survey closed` |
| | **Survey closed: text** | `This survey is no longer accepting responses.` |
| Around the survey | **Privacy link** | `Privacy` |
| | **Contact link** | `Contact research team` |
| | **Skip link (keyboard and screen reader)** | `Skip to questionnaire` |
| Access code | **Access code: title** | `Access required` |
| | **Access code: text** | `Please enter the access code to begin this survey.` |
| | **Access code: field** | `Enter access code` |
| | **Access code: button** | `Continue` |
| | **Access code: wrong code** | `Invalid access code. Please try again.` |

Where some of them appear:

- **Section label** fields and **Progress: “Page”** / **Progress: “of”**: see
  [Question style and progress](#question-style-and-progress). The "Page 2 of
  5" words are also what screen readers announce on each page.
- **“of” in “2 of 3 selected”** and **“selected” in “2 of 3 selected”**: the
  counter under a multiple-choice question with **Max answers**. The "of" is
  also used in the screen-reader names of star ratings and MaxDiff and
  conjoint tasks.
- **Required matrix: rows left**: under a required Matrix answered in some
  rows but not all, when **Next** is pressed; `{n}` is the number of rows
  left (for example "Rows left to answer: {n}"). A required Matrix with no row
  answered shows **Unanswered required question**. See
  [Matrix](Studio-Question-Types#matrix).
- **Too few choices**: under a multiple-choice question with **Min answers**,
  as a hint and as the error when **Next** is pressed with too few choices.
  **Number below its minimum** / **above its maximum**: under a number
  question outside its valid range.
- **“Other” option**, **“None of the above” option** and **“N/A” option**:
  the labels of the options Studio adds to a question.
- **Redirect page: countdown** and its link: on the completion screen when a
  **Completed → return URL** sends respondents on (after 5 seconds).
  **Redirecting at once** and its link: on end pages that send respondents on
  (a Redirect page, or a Final or Screen-out page with a return URL), and on
  the quota-full screen with a **Quota full → return URL**.
- **Submission attempt**: in the **Submission failed** dialog ("Attempt 1 of
  3."). After the third failed attempt the survey shows **Submission error
  title** and **text**.
- **Quota full**: the screen a full quota cell shows (see
  [When a cell is full](Studio-Quotas-and-Randomization#when-a-cell-is-full)),
  and the notice of a survey whose sample is full as it opens.
- **Survey closed**: the engine's own closed screen. A survey published from
  Studio shows Studio's notice instead when it is closed or paused (see
  below).
- The access-code texts only appear when the survey requires an access code
  (see [Access codes](Studio-Distribution-Channels#access-codes)).

What stays in English whatever you set:

- labels only screen readers hear: the page dots' names, "Loading survey",
  the light/dark button, "Task n" of a MaxDiff and "Choice n" of a conjoint;
- Studio's own notices around the survey: "This survey is closed" / "The
  researchers have stopped collecting responses.", "This survey is paused" /
  "The researchers have paused collection. Please try again later.", "You
  have already taken part" (**One per browser**) and the preview banner
  "Preview — answers are not stored".

For another language, translate your questions, your page texts and end
pages, and the Wording fields; the notices above are the only fixed English
left. A survey published before these fields existed shows the English
defaults until you publish it again.

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
one here. Name Source Serif 4, Inter or Nunito in any of these fields and the
survey brings that font along. Any other typeface must be available to
respondents, either installed on their device or loaded by your custom CSS —
and a font your CSS loads from another site shows each respondent's IP address
to that site, so name it in your privacy notice (see
[Cookies and browser storage](Studio-Security-and-Privacy#cookies-and-browser-storage)).

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

A house style is copied into every new study, so its size is limited:
**Custom CSS** up to 64 KB, every other value up to 4 KB, and 128 KB for the
whole style. Over a limit, the form says so under the setting, by its label
("Custom CSS is longer than 64 KB. Shorten it to save the style."), and in a
line above **Save changes** that names every setting over its limit ("Shorten
Primary (4 KB at most) and Custom CSS (64 KB at most) to save the style.");
**Save changes** stays unavailable until you shorten it.

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
  house style**. The confirmation, "Use the organization's house style?",
  names what will change ("This changes N of this study's look settings to
  your organization's — primary color, logo url, …"). Here the house values
  win, because pressing the button is you asking for them. It is an ordinary
  unsaved edit: it shows in the Save's changes, and restoring an earlier Save
  undoes it.
- The Builder's **Create questionnaire** button (in a project with no
  questionnaire yet) and **Draft from a brief → Use this draft** start the
  questionnaire with the house style too. A draft keeps any look setting it
  makes itself; the house style fills in the rest.

### Custom CSS in the house style

Custom CSS is a *(Plus)* feature at publishing time, and below Plus the house
style's custom CSS is **left out** wherever the style is copied, so you are
not handed a study that cannot be published:

- in the projects the house style starts (upgrade, and the next project you
  create carries it);
- by **Use the organization's house style**, whose confirmation then adds
  " Its custom CSS is left out: custom CSS is included from Plus.";
- by **Create questionnaire** and by **Draft from a brief → Use this draft**.

Below Plus, custom CSS alone does not make a study "not follow" the house
style: the banner appears only when another setting differs. The form says:
"Custom CSS is included from Plus. You can write it here, but on the Free
plan it is left out of the projects this style starts — a Save carrying it
does not deploy."

## See also

- [[The Builder|Studio-Builder-Overview]]
- [[What Respondents See|Studio-Respondent-Experience]]
- [[Organizations and Team|Studio-Organizations-and-Team]]
- [[Scripts|Studio-Scripts]]
- [[Testing Your Survey|Studio-Testing-Your-Survey]]

<!-- studio-nav -->
---

← [[MaxDiff and Conjoint|Studio-MaxDiff-and-Conjoint]] · [Studio contents](Studio-Overview#all-pages) · [[Scripts|Studio-Scripts]] →
