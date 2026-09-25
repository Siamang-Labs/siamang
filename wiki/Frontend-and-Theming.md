# Frontend and Theming

The `siamang.frontend` subpackage compiles a `Questionnaire` into a deployable
static bundle — HTML, CSS, JavaScript, and runtime config. Most of the time you
never touch it directly: `survey.deploy(...)` and `siamang preview` drive it for
you. This page documents the machinery so you can build bundles by hand, swap
runtimes, and fully control the visual design with `UIConfig` and theme presets.

```python
from siamang.frontend import (
    FrontendBuilder, UIConfig, get_preset, compile_css, compile_questionnaire,
    SurveySchema, SurveyBundle,
    SurveyJSRuntime, ReactRuntime,
    LocalClientTemplate, SupabaseClientTemplate, ClientEnv,
)
```

The pipeline is a small composition: **compile** a questionnaire to a
`SurveySchema`, hand that to a `FrontendBuilder` (which carries a `RuntimeAdapter`
and a `UIConfig`), and `build(...)` it with a backend `client` and a `ClientEnv`
into a `SurveyBundle`.

---

## `SurveySchema` — the intermediate representation

```python
from siamang.frontend import SurveySchema, compile_questionnaire

schema = compile_questionnaire(survey, options={"language": "en"})
```

`SurveySchema` is a frozen, platform-agnostic snapshot of a survey. It is produced
by `compile_questionnaire(survey, options=...)`; backends, runtimes, and themes all
consume it. Fields include `title`, `pages`, `variables`, `language`,
`description`, `completion_text`, `show_progress`, `allow_back`,
`one_question_per_page`, `deadline`, `max_responses`, `quotas`, and `metadata`.

Two render methods:

```python
schema.to_surveyjs()   # dict — SurveyJS-compatible payload (title/locale/pages/...)
schema.to_dict()       # dict — full JSON serialisation (format_version=1, ISO deadlines)
```

`to_surveyjs()` maps siamang concepts onto the SurveyJS dialect — e.g.
`show_progress` becomes `showProgressBar: "top"`, and `one_question_per_page`
becomes `questionsOnPageMode: "questionPerPage"`. Internal keys (`_quota_variable`,
`_meta`) are stripped from each page first.

---

## `FrontendBuilder` — the orchestrator

```python
from siamang.frontend import FrontendBuilder, SurveyJSRuntime, UIConfig

builder = FrontendBuilder(runtime=SurveyJSRuntime(), ui=UIConfig())

def build(
    self,
    schema: SurveySchema,
    *,
    client: BackendClientTemplate,
    env: ClientEnv,
    survey: Questionnaire | None = None,
) -> SurveyBundle: ...
```

Both constructor fields are optional and default to `SurveyJSRuntime()` and
`UIConfig()`. `build(...)` renders every artefact and returns an assembled bundle
whose filenames are content-hashed. `survey` is only needed by runtimes that
require the live `Questionnaire` (`ReactRuntime`); `SurveyJSRuntime` works from
`schema` alone.

The returned bundle contains five base files:

| File | Purpose |
| :--- | :--- |
| `index.html` | The survey entry point. |
| `closed.html` | Shown when the survey has expired, hit `max_responses`, or quotas are full. |
| `style.css` | The compiled theme (from the runtime, or `compile_css(ui)` as a fallback). |
| `env.js` | Runtime config emitted by the backend client template. |
| `manifest.json` | Metadata: runtime, client, backend, `survey_id`, `schema_hash`, build time. |

A runtime may add its own static assets on top: `ReactRuntime` contributes
`bundle.js` plus vendored React files under `vendor/`; `SurveyJSRuntime` adds
none.

### End-to-end example

```python
import siamang as sg
from siamang.frontend import (
    FrontendBuilder, UIConfig, LocalClientTemplate, ClientEnv, compile_questionnaire,
)

survey = sg.Questionnaire(title="Demo", pages=[...])

schema = compile_questionnaire(survey, options={"language": "en"})
builder = FrontendBuilder(ui=UIConfig(primary_color="#2c5f8a"))
env = ClientEnv(survey_id="abc123", backend="local", settings={})

bundle = builder.build(schema, client=LocalClientTemplate(), env=env)
bundle.write_to("./dist")          # writes index.html, style.css, env.js, ...
```

---

## `SurveyBundle`

```python
@dataclass(frozen=True, slots=True)
class SurveyBundle:
    files: dict[str, str | bytes]   # {relative_path: content}
    manifest: dict[str, Any]
```

Immutable container of the compiled files plus a manifest. Useful methods:

| Method | Returns | Description |
| :--- | :--- | :--- |
| `write_to(target)` | `Path` | Write every file under `target`, creating parents. |
| `to_zip()` | `bytes` | Deflate-compressed ZIP of all files. |
| `manifest_json()` | `str` | Pretty-printed manifest JSON. |
| `compute_digest()` | `str` | 16-char SHA-256 prefix over all contents. |
| `with_hashed_filenames()` | `SurveyBundle` | Renames `.js`/`.css` to include a content hash (HTML references updated). |

`FrontendBuilder.build(...)` already calls `with_hashed_filenames()` for you.

---

## Runtimes

A `RuntimeAdapter` turns a compiled schema into HTML pages and the client-side
behaviour. Two are bundled:

### `SurveyJSRuntime`

A lightweight, non-React runtime built on the **SurveyJS** core library. It is
the default only for a hand-built `FrontendBuilder`; it is highly compatible and
needs zero build tooling. This is what the full-pipeline example uses to produce
a standalone `.html` file. Note that it does not execute siamang's routing
payload (`skip_to` / `next_if` / `default_next`) — surveys that rely on routing
should use `ReactRuntime`.

### `ReactRuntime`

Compiles the questionnaire into a standalone **React 18** application with a
bundled design-system stylesheet.
Required for advanced interactive features (custom charts, custom widgets, complex
animations). Because it needs the live questionnaire, pass `survey=` to `build(...)`.
Both `survey.deploy(...)` and `siamang preview` use the React runtime by
default; `SurveyJSRuntime` is only the default when you construct a
`FrontendBuilder` yourself.

From the keyboard, Enter or Space goes to the next page (or submits on the last)
wherever the focus is not in a text field, on a button or on a link; on a button or a
link the key is its own — a matrix cell or a rating point is chosen, Previous goes
back, the dropdown opens — and so it is on a video or audio player (Space plays or
pauses), on a `<summary>` (it opens its details) and on the like in a page's own HTML.
Right after a click, while the focus the mouse left on a button or a link is still
there, Enter and Space go on: the key would otherwise click again, and a MaxDiff or
conjoint pick, which a second click takes back, would be lost. Esc goes back when
going back is allowed, and the digits 1–9 pick that point on the page's first rating
scale that has it. A matrix is a grid the arrow keys move through (see
[[Question Types|Question-Types]]).

Both inherit the `RuntimeAdapter` interface (`render_html`, `render_closed_page`,
`stylesheet`, `static_assets`) — see
[`docs/reference/frontend.md`](https://github.com/hanelias/siamang/blob/main/docs/reference/frontend.md).

---

## Backend client templates

A `BackendClientTemplate` emits the `env.js` snippet that wires the in-browser
client to a backend. It registers a transport on `window.SIAMANG_TRANSPORTS` keyed
by `ClientEnv.backend` and sets `window.SIAMANG_ENV`.

```python
from siamang.frontend import ClientEnv, LocalClientTemplate, SupabaseClientTemplate
from siamang.frontend.client import GoogleSheetsClientTemplate

env = ClientEnv(survey_id="abc", backend="supabase", settings={"url": "...", "anon_key": "..."})
```

| Template | `backend` name | Notes |
| :--- | :--- | :--- |
| `LocalClientTemplate` | `local` | POSTs to the local FastAPI server (`/responses`, `/quota-check`). |
| `SupabaseClientTemplate` | `supabase` | POSTs `{survey_id, data}` to the shared `responses` table. |
| `GoogleSheetsClientTemplate` | `gsheets` | Submits via `values.append` or an Apps Script proxy URL. |

`ClientEnv` carries only **frontend-safe** values (URLs, anon keys). Secrets such as
service keys never reach the bundle. The `DeployPipeline` selects the matching
template for you based on the backend name (see [[Deployment]]).

### What the React runtime hands a transport

`submit(answers)` receives one object. Every key is a **codebook variable** and every
value one of its codes, plus `__status` (`"completed"`, `"screened_out"` or
`"redirect"` when a terminal page ended the survey):

| Question | Stored as |
| :--- | :--- |
| one variable (`SingleChoice`, `LikertScale`, `NumericInput`, `OpenText`, `Ranking`, array `MultiChoice`) | `{"<var>": code}` — a list of codes for `MultiChoice` / `Ranking` |
| `Matrix` | one key per row variable, value = the column's code |
| wide `MultiChoice` | one key per option variable: `1` chosen, `0` answered and not chosen (none for an option its condition hid) |
| `MaxDiff`, `Conjoint` | one key per task variable and the version variable |
| "Other (please specify)" | the Other code in the variable, the text under `"<var>_other"` |

The runtime's own state (`__pages__`, `__options__`, `__errors__`, `__timers__`) is
never sent. See [[Question Types|Question-Types]] for the codes.

The other calls, all optional on the transport:

| Call | When | Answer the runtime expects |
| :--- | :--- | :--- |
| `checkQuota(variable, value)` | leaving a page, for each quota variable with a value not yet found open (`value` is a list for a `MultiChoice`) | `{ok: true}`, or `{ok: false}` when a cell holding the value is full — the interview then ends as "quota full". A throw or a slow answer (4 s) never stops anyone. See [[Quotas]]. |
| `pickQuota(variable, values)` | a balanced `Script.assign_condition` before the first page | `{ok: true, value}` — the arm to assign |
| `onPage({name, index, total})` | every page change | nothing |
| `respondentId()` | once, when the survey loads | the respondent's id (a string), which becomes `answers.__respondent__` for seeded draws; without it the runtime keeps its own random id for the interview |

What the runtime keeps in the respondent's browser (`localStorage`) is keyed by the
survey: the transport's `survey_id` (`SIAMANG_ENV.survey_id`), or `SURVEY.surveyId` when
the host page sets one. The autosave is `siamang_answers_<survey id>` (the answers
without `__` keys, the page, the path taken, the page order it was dealt and when the
interview started; a day at most — removed, and never written again, once the interview
is submitted or ended by a full quota), the theme choice `siamang_theme_<survey id>` and
the runtime's own respondent id `siamang_interview_<survey id>`. A host's transport may read the autosave — Studio's
posts it as a partial response.

Inside an iframe the runtime also tells the parent page its height:
`window.parent.postMessage({type: "siamang:height", height: <px>}, "*")` when it loads and
whenever the survey's height changes (a new page, an error message, a window resize), so
an embedding page can size the frame to the survey — Studio's `embed.js` does.

---

## `UIConfig` — the design system

`UIConfig` is a frozen dataclass (~115 fields) that controls the entire look and wording of the
deployed survey. The defaults aim for a calm, research-grade aesthetic: a serif body
font, a narrow line measure, a single accent colour, and comfortable spacing. Pass
it to deployment via `survey.deploy(..., ui=UIConfig(...))` or to a
`FrontendBuilder`. The fields group into seven areas.

### Palette

| Field | Default | Meaning |
| :--- | :--- | :--- |
| `primary_color` | `"#2c5f8a"` | Brand colour for primary buttons and active states. |
| `accent_color` | `None` | Optional accent; falls back to `primary_color`. |
| `background_color` | `"#fbfbfb"` | Page background. |
| `surface_color` | `"#ffffff"` | Card / panel / input background. |
| `text_color` | `"#1a1a1a"` | Body text. |
| `muted_text_color` | `"#5a5a5a"` | Secondary text. |
| `border_color` | `"#e6e4df"` | Dividers and input borders. |
| `error_color` / `error_soft_color` | `"#b3261e"` / `"#fdf1f0"` | Validation error text and tint. |
| `warn_color` | `"#9a6a1a"` | Warning states. |

### Typography

`font_preset` is the high-level knob: `"academic"` (Source Serif 4 body + Inter UI,
the default), `"modern"` (Inter everywhere), or `"humanist"` (Nunito). Each preset
ships its own Google Fonts URL. Fine-grained overrides: `font_family`,
`heading_font_family`, `ui_font_family`, `mono_font_family`, `font_size`
(`"15.5px"`), `line_height` (`"1.6"`), and `font_pair` (`"serif"` | `"sans"` |
`"mixed"`).

### Layout

`width` (`"700px"` — kept under ~750px for a 60–75 character measure), `radius`
(`"4px"`), `density` (`"compact"` | `"comfortable"` | `"spacious"`), and
`question_style` (`"plain"` | `"divided"` | `"carded"` | `"accent"`).

### Branding / header

`logo_url`, `logo_text` (if unset, auto-derived from the initials of the first
two words of `institution_name` — e.g. "Riverside Health Collective" → "RH"),
`logo_position`, `show_title`, `institution_name`, `study_subtitle`,
`show_section_numbers`, `show_progress_text`, and `estimated_minutes`.

Where the respondent is: every page they answer has a section label above its title —
"Welcome" on the first, "Final thoughts" on the last, "Section *n* of *m*" between —
and the progress bar shows the same label beside it. The count is the respondent's own:
the pages they go through, in their order (after `randomize_pages`, say), without the
end pages (final, screen-out, redirect), so the last question page is at 100 %.
`show_section_numbers=False` drops the labels, and the bar says "Page *n* of *m*"
instead (`page_text`, `of_total_text`); `show_progress_text=False` leaves the bar
without text. The page dots, too, are one per page the respondent answers.

The header appears when there is something in it: the title (`show_title=True`), a
logo or an institution. `show_title=False` hides the questionnaire's title even when
the header is shown for a logo or an institution.

### Footer

`privacy_url`, `contact_email`, and `ethics_statement` (e.g. an IRB reference).

### I18n UI strings

Every fixed phrase the runtime shows has a `UIConfig` field; `None` (the default) keeps
the English text in the table. Replacing all of them is how a survey runs in another
language. In a template, `{name}` is replaced by the value named (`{n}`, `{total}`,
`{minutes}`, …) and `{link}` is where the link goes.

| Field | English default | Where |
| :--- | :--- | :--- |
| `next_button_text` / `prev_button_text` / `submit_button_text` | `Next section →` / `← Previous` / `Submit responses` | the page's buttons |
| `submitting_text` / `saving_text` | `Submitting your responses…` / `Saving…` | while submitting / autosaving |
| `required_text` | `This question requires an answer.` | an unanswered required question |
| `required_rows_text` | `Please answer every row.` | a required matrix answered in some rows but not all (`{n}`: the rows left); the rows are marked |
| `welcome_text` / `section_text` / `final_section_text` | `Welcome` / `Section {n} of {total}` / `Final thoughts` | the section label above a page's title and beside the progress bar |
| `page_text` / `of_total_text` | `Page` / `of` | "Page *n* of *m*": beside the bar without section labels, and for screen readers |
| `estimated_time_text` | `About {minutes} minutes` (`About 1 minute`) | under the first page's title, with `estimated_minutes` |
| `of_text` / `selected_text` | `of` / `selected` | a multiple choice's counter "2 of 3 selected" (and screen-reader labels) |
| `min_choices_text` / `max_reached_text` | `Select at least {n} more` / `Maximum reached` | a multiple choice's counter and its message on Next |
| `min_value_text` / `max_value_text` | `Minimum value is {min}` / `Maximum value is {max}` | a number out of its valid range |
| `invalid_format_text`, `invalid_email_text`, `invalid_phone_text`, `invalid_url_text`, `invalid_date_text`, `invalid_time_text` | `Please check the format of your answer.`, `Please enter a valid email address.`, `Please enter a valid phone number.`, `Please enter a valid web address (https://…).`, `Please enter a valid date.`, `Please enter a valid time.` | an open answer that does not match its format |
| `select_placeholder` / `search_placeholder` / `no_options_text` | `— Select —` / `Type to search…` / `No options found` | a dropdown |
| `other_text` / `other_placeholder` | `Other` / `Please specify...` | "Other (please specify)" — a question's `metadata["other_label"]` / `["other_placeholder"]` wins |
| `none_of_above_text` | `None of the above` | `SingleChoice(none_of_above=True)` |
| `not_applicable_text` | `Not applicable` | `na_option=True` on a Likert scale or a matrix (a string `na_option` wins) |
| `chars_remaining_text` | `{n} characters remaining` | an open answer near `max_chars` |
| `ranking_hint_text` / `ranking_remaining_text` | `Tap or drag to rank` / `Remaining options` | a ranking |
| `resume_title` / `resume_action` / `restart_action` | `We saved your progress from earlier. Would you like to resume?` / `Resume` / `Start over` | the resume banner |
| `retry_title` / `retry_body` / `retry_action` / `save_local_action` / `attempt_text` | `Submission failed` / `We could not save your responses.` / `Try again` / `Save locally and finish` / `Attempt {n} of {max}.` | a failed submission |
| `completion_title` / `completion_body` | `Thank you for participating` / the `completion_text` option (`Thank you for your participation!`) | the completion screen; `completion_body` wins over `completion_text` |
| `response_id_text` / `submitted_text` | `Response ID` / `Submitted` | the completion screen and a final page |
| `screen_out_title` | `Thank you` | a screen-out page without a title |
| `redirect_countdown_text` / `redirect_link_text` | `You will be redirected in {seconds} seconds. {link} if not redirected.` / `Click here` | the completion screen with `redirect_url` |
| `redirecting_text` / `redirecting_link_text` | `Redirecting you now. {link} if you are not redirected.` / `Continue` | an end page or the full-sample screen that redirects |
| `quota_full_title` / `quota_full_body` | `Thank you for your interest` / `We have already reached our target sample for participants like you.` | the full-sample screen |
| `closed_title` / `closed_body` | `Survey closed` / `This survey is no longer accepting responses.` | a closed survey (also the static closed page) |
| `error_title` / `error_body` | `Submission error` / `We could not save your responses. Please refresh and try again.` | after three failed submissions |
| `privacy_text` / `contact_text` | `Privacy` / `Contact research team` | the footer's links |
| `skip_link_text` | `Skip to questionnaire` | the keyboard skip link |
| `access_title` / `access_body` / `access_placeholder` / `access_button` / `access_error` | `Access required` / `Please enter the access code to begin this survey.` / `Enter access code` / `Continue` / `Invalid access code. Please try again.` | the access-code gate |
| `page_error_title` / `page_error_body` / `app_error_title` / `app_error_body` / `reload_action` | `Something went wrong` / `An unexpected error occurred. Your previous answers have been saved.` / `Survey temporarily unavailable` / `We encountered an unexpected error. Your previous answers have been saved.` / `Reload survey` | when the runtime itself fails |

A few screen-reader-only labels (the page dots' names, "Loading survey", the theme
button's name, a MaxDiff's "Task *n*" and a conjoint's "Choice *n*") are still English.

### Advanced (navigation, access, analytics)

`progress_style` (`"bar"` — the bar and its text, `"dots"` — the page dots only, or
`"both"`; the compiler option `show_progress=False` hides the indicator whatever the
style; a page dot takes the respondent back
to a page they have already seen on the way to the current one, never forward past
required questions or routing, and not at all with `allow_back=False`), `default_theme` (`"light"` |
`"dark"` | `"system"`) with `allow_theme_switch` (default `True`) deciding
whether the respondent may change it — off, the light/dark button is not shown
and the survey stays on `default_theme` for the whole sample —
`redirect_url`, `allow_back`, `enable_analytics` (injects
Vercel Analytics when `frontend="vercel"`), and an access gate:
`require_access_code`, `access_codes`, `access_title`, `access_body`,
`access_placeholder`, `access_button`. `custom_css` is a raw escape hatch appended
to the compiled stylesheet.

> `UIConfig.__post_init__` validates `logo_position`, `density`, `font_pair`,
> `question_style`, and `font_preset`; an unknown value raises `ValueError`.

---

## Theme presets

`get_preset(name)` returns a fully configured `UIConfig`. Six presets ship in
`THEME_PRESETS`:

```python
from siamang.frontend import get_preset

ui = get_preset("dark")
```

| Name | Typography | Look | Best for |
| :--- | :--- | :--- | :--- |
| `default` | academic | Serif, light grey background. | Standard academic studies. |
| `academic` | academic | Explicit academic styling (680px width). | Alias of `default`. |
| `dark` | academic | Dark slate (`#10131a`), blue accents. | Night reading, tech studies. |
| `modern` | modern | White, indigo accents, spacious, 16px. | Public-facing / consumer surveys. |
| `humanist` | humanist | Warm off-white, green accents, rounded. | Community / non-profit research. |
| `high_contrast` | modern | Black/white, bold borders, 18px text. | WCAG AAA accessibility. |

An unknown name raises `KeyError` listing the valid options.

### Example: start from a preset and customise

```python
import dataclasses
from siamang.frontend import get_preset

ui = dataclasses.replace(
    get_preset("modern"),
    institution_name="Independent Polling Lab",
    primary_color="#a8324b",
    estimated_minutes=8,
    # translate the navigation chrome to French
    next_button_text="Suivant",
    prev_button_text="Précédent",
    submit_button_text="Envoyer",
)

survey.deploy(backend="supabase", frontend="vercel", ui=ui)
```

`UIConfig` is frozen, so use `dataclasses.replace(...)` to derive a variant from a
preset.

---

## `compile_css`

```python
from siamang.frontend import compile_css

css: str = compile_css(ui)
```

Compiles a `UIConfig` into a CSS stylesheet string using CSS custom properties. This
is the fallback `style.css` when a runtime does not supply its own (the React
runtime ships a full design system). Useful for inspecting the generated theme or
embedding it elsewhere.

---

See also: [[Deployment]] · [[CLI Reference|CLI-Reference]] · [[Cookbook]] ·
[[API Reference Index|API-Reference-Index]]
