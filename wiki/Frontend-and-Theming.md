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
none. Both get the typefaces the stylesheet uses under `fonts/` (see
[Typography](#typography)).

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
On a radio button or a checkbox — where a click on a choice or a picture leaves the
focus — and on a slider, Enter goes on and Space is the control's own: it checks the
radio, checks or unchecks the box.
Right after a click, while the focus the mouse left on a button or a link is still
there, Enter and Space go on: the key would otherwise click again, and a MaxDiff or
conjoint pick, which a second click takes back, would be lost. Esc goes back when
going back is allowed. A matrix is a grid the arrow keys move through (see
[[Question Types|Question-Types]]).

A rating scale — numbers (a 0–10 NPS too) or stars — is one radio group: Tab stops on
it once (on the chosen point, else the first), the arrow keys move the choice and the
focus with it, Home and End go to the ends, and an arrow stops at an end; with Alt,
Ctrl or Cmd an arrow is the browser's (Alt+Left goes back). A screen reader hears each
point as a radio of the group, checked or not, the end labels with the end points, and
a star by its count. A digit answers the scale the focus is in — "1" then "0" within
0.8 s is 10, "0" is the first point of a scale that starts at 0 — or, when the focus
is in no question, the page's only scale; from another question, or with two scales
on the page and the focus in neither, a digit does nothing.

Tabbing through a choice or a set of boxes rings the option's row, and a scale's
number the same way (2 px, the accent mixed toward the text color, 3:1 or more on the
card in light and dark; in forced colors every focus is an outline in the system's
text color, and a scale's chosen number is drawn in its Highlight). A scale's numbers
are written in the page's text color, so a dark theme's card shows them. A text
field, a text box and a number field are named by their question's title as the
respondent reads it, and say `aria-invalid` while their error shows, with the error
named by `aria-describedby`; a choice's, an image choice's and a scale's radio
group say `aria-required`, and the same two while the error shows; a set of boxes
says the last two.

A step dot is a 24 px button around the same 10 px dot, so the dots stand 24 px
apart; under a finger a button is 32 px, narrowing down to 24 px when the survey's
steps would not fit one row at 32 px. Dots too many for one row even then wrap (on a
390 px phone, more than 14), and the second row moves the page down.

A scale's numbers are cells of one width: all in one row where each keeps its least
width (`--sd-rating-min`: 44 px, 40 px on a phone) and the gaps fit, else two even
rows (0–5 and 6–10 of a 0–10 scale), and more only where two are still too narrow.
The runtime measures the scale itself, not the window, and sets the number of
columns (`--sd-rating-cols`) through the CSSOM, so a narrow theme or embed wraps
where a window as wide would not.

A required question left unanswered says so as the focus leaves it — after the press
that left it is over (the mouse button let go, a tap's click), so the message coming
in above the next question never moves it from under the pointer. A press whose end
never reaches the page (the button let go in another window) ends at the next key, a
mouse moving with no button down or the window losing the focus.

Both inherit the `RuntimeAdapter` interface (`render_html`, `render_closed_page`,
`stylesheet`, `static_assets`) — see
[`docs/reference/frontend.md`](https://github.com/Siamang-Labs/siamang/blob/main/docs/reference/frontend.md).

### YouTube and Vimeo videos wait for a press

A question's or an option's YouTube or Vimeo video (`Media(kind="embed")`, see
[[Question Types|Question-Types]]) is a play button until the respondent presses
it: nothing is requested from the provider before. The press loads the player on
`www.youtube-nocookie.com` or `player.vimeo.com` (with `dnt=1`), its address built
from the provider and the video's id, never from the media's url.

A page body's players — the YouTube and Vimeo frames the sanitizer keeps — are frames
as the author wrote them, unless the host asks otherwise:
`FrontendBuilder(click_to_play=True)` (or `RuntimeRenderContext(click_to_play=True)`)
sets `SURVEY.clickToPlay`, and each body player becomes the same play button, in a box
of the frame's `width`/`height` shape (16:9 without them; 200 px each way at the
least), named after its `title` (an untitled player — the sanitizer titles it "YouTube
video player" — shows no title and is named "Play video: YouTube video"). The frame's
address is kept on the box and checked again when the button is pressed; the player
then starts at once (`autoplay=1`, and `dnt=1` alone on Vimeo, whatever `dnt` the body
repeated). It is off by default: a body's players are frames, as before.

A page that cannot play a video — the player gets no referrer there, and YouTube and
Vimeo refuse it — says so: in a design preview (`window.SIAMANG_DESIGN`) the box reads
`media_preview_blocked_text` and the runtime posts
`{source: "siamang-runtime", type: "siamang:embed-blocked", provider}` to its host; in
a sandboxed page (`window.origin` is `"null"`, such as a page served in a sandboxed
iframe or under a CSP `sandbox`) the press opens the video's page on YouTube or Vimeo
in a new tab, with no way back to the survey's (`opener` cleared), and says it cannot
play when the browser refuses the tab.

### A Content-Security-Policy for the bundle

What an author writes reaches the survey's page only as data: every text travels in
the page's inline `<script>` written so it cannot end the element, a page's body is
sanitized (see [[Pages, Blocks and Structure|Pages-Blocks-and-Structure]]), a theme
token has a strict format, and an address a respondent is sent to is `http(s)`. A
Content-Security-Policy is the second line, binding whatever gets past the first.
Custom scripts (`Script`) and `UIConfig.custom_css` are unchanged: they run as the
author wrote them, by design, so a host whose authors are not trusted should not
offer them.
`FrontendBuilder(csp=policy)` (or `RuntimeRenderContext.csp`) writes it in a
`<meta http-equiv="Content-Security-Policy">` right after `<meta charset>` of
`index.html` and `closed.html`; None, the default, writes none. A host that writes the
policy after the build puts it there with `siamang.frontend.csp.insert_csp_meta`,
which refuses a page that does not start as the runtime's.

`siamang.frontend.csp.survey_csp(page, connect_src=[ingest], captcha=…)` builds what
the React runtime needs:

| Directive | Sources | Why |
| :--- | :--- | :--- |
| `default-src` | `'none'` | Anything the rows below do not name. |
| `script-src` | `'self'`, `'unsafe-eval'`, the inline script's hash (or `'unsafe-inline'` without `page`), Turnstile with `captcha=True` | `bundle.js`, `vendor/react*.js`, `env.js`; `window.SURVEY`/`window.PAGES` (`inline_script_hashes`). **`'unsafe-eval'` is required**: show/hide and routing conditions are compiled with `new Function` and custom scripts run as an `AsyncFunction` — without it every condition reads as true (a `show_if` always shows, a `hide_if` always hides, the first routing rule wins) and no custom script runs. With the hash and no `'unsafe-inline'`, no inline handler or `javascript:` address can run. |
| `style-src` | `'self' 'unsafe-inline'` | `style.css`; a body's `style=""`. |
| `font-src` | `'self'` | The bundled typefaces in `fonts/`; add the hosts a custom stylesheet's `@font-face` uses. |
| `img-src`, `media-src` | `'self' https: data:` | The logo, a question's and an option's media, a body's pictures and media (narrow them to the survey's own, below). |
| `frame-src` | `https://www.youtube-nocookie.com https://player.vimeo.com` (+ Turnstile) | The players a question, an option or a body may hold. |
| `connect-src` | `'self'` + the ingest origin | Where `env.js` sends the answers, and a custom script's `api.get`/`api.post`. |
| `object-src`, `base-uri`, `form-action` | `'none'` | The runtime has no plug-in, `<base>` or `<form>`. |

A `<meta>` policy cannot carry `frame-ancestors`, `report-to` or `sandbox`; send those
as a header (both are enforced, the stricter winning).

#### The media a survey uses

`siamang.frontend.csp.media_uses(document)` lists every picture, sound, video and
player a questionnaire document holds for its pages (an option's media in a dropdown
and a conjoint level's too, which a page never draws), as `MediaUse(pointer, where,
directive, url, kind)`:

| Field | What |
| :--- | :--- |
| `pointer` | A JSON pointer into the document: `/pages/0/items/2/media/0`, `/pages/0/items/2/choices/1/media`, `/pages/1/items/0/attributes/0/levels/2/media`, `/ui/logo_url`, `/pages/3/body`, `/ui/custom_css` |
| `where` | `question`, `option` (an answer option or a conjoint level), `logo`, `body`, `css` |
| `directive` | `img-src` (pictures, a video's poster, the logo, a stylesheet's `url()`), `media-src` (video, audio, a `<source>` or `<track>` of one), `frame-src` (players) |
| `url` | What the page loads: a file's address as written; an embed's player (`Media.player_src`); a body's address as `sanitize_html` keeps it (one use per `srcset` candidate); a stylesheet's `url()` outside `@font-face` and `@import` |
| `kind` | `image`, `video`, `audio` or `embed`; `None` in a body or a stylesheet |

It walks every question (a block's and a nested block's too), each option's and
level's media, the logo, each page's body and the custom stylesheet, and passes over
what is not a media a page could show. `media_sources(document)` turns them into the
sources of each directive — `MediaSources(img, media, frame)`, sorted, each once: the
origin of each `http(s)` address (`https` for a protocol-relative one), `data:` for a
picture written into the document; nothing for a relative address (the page's own
`'self'`). A policy that lets the survey load its own media and nothing else:

```python
from siamang.frontend.csp import insert_csp_meta, media_sources, survey_csp

sources = media_sources(document)
policy = survey_csp(page, connect_src=[ingest], img_src=sources.img,
                    media_src=sources.media, frame_src=sources.frame)
page = insert_csp_meta(page, policy)
```

A survey without players gets `frame-src 'none'`. Neither function judges an address:
which hosts a survey may use is the host's own policy.

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

While `submit()` runs, the page shows "Submitting your responses…" — on an ending page
too, which sends the answers as it opens and shows its own title and body, and the
response id, only once they are stored: a completion code or a link back to a panel in
its text is not in the page before then (a design preview shows it as it opens). Only
once `submit()` has returned does the respondent get a way on: an ending page's redirect
and its "Redirecting you now" link, the completion screen's countdown to `redirect_url`.
When it throws, the respondent gets the retry dialog (`retry_title`, `retry_body`,
"Attempt 1 of 3."). **Try again** calls `submit()` again. **Save locally and finish**
keeps the answers in the browser and, in place of the page (an ending page too, whose
text may hold a completion code), says they were not sent (`saved_locally_title`,
`saved_locally_body`), with no redirect, no link on and no response id; opening the
survey's link again in that browser within 7 days offers Resume, which sends them. After
the third failure comes the closed screen (`error_title`, `error_body`). A transport
that knows why the answers did not go, and what the respondent can do about it, puts
that on the error it throws as `respondentMessage`; the retry dialog shows it in place
of `retry_body`:

```js
const err = new Error("submit failed: 429");
err.respondentMessage = "The security check could not run in your browser. Allow it and try again.";
throw err;
```

The other calls, all optional on the transport:

| Call | When | Answer the runtime expects |
| :--- | :--- | :--- |
| `checkQuota(variable, value)` | leaving a page, for each quota variable with a value not yet found open (`value` is a list for a `MultiChoice`) | `{ok: true}`, or `{ok: false}` when a cell holding the value is full — the interview then ends as "quota full". A throw or a slow answer (4 s) never stops anyone. See [[Quotas]]. |
| `pickQuota(variable, values)` | a balanced `Script.assign_condition` before the first page | `{ok: true, value}` — the arm to assign |
| `onPage({name, index, total})` | every page change | nothing |
| `respondentId()` | once, when the survey loads | the respondent's id (a string), which becomes `answers.__respondent__` for seeded draws; without it the runtime keeps its own random id for the interview. Keep it in the browser only from `onStart()`: the visitor may never start |
| `onStart()` | once per page load, at the respondent's first answer or first move between pages (Resume and Start over count; the theme button does not) | nothing — from here the transport may keep what it needs in the browser (Studio: its respondent id) |

What the runtime keeps in the respondent's browser (`localStorage`) is keyed by the
survey: the transport's `survey_id` (`SIAMANG_ENV.survey_id`), or `SURVEY.surveyId` when
the host page sets one. The autosave is `siamang_answers_<survey id>` (the answers
without `__` keys, the page, the path taken, the page order it was dealt and when the
interview started; offered back for a week — removed, and never written again, as soon
as the interview is submitted or ended by a full quota), the theme choice
`siamang_theme_<survey id>` and the runtime's own respondent id
`siamang_interview_<survey id>`. A host's transport may read the autosave — Studio's
posts it as a partial response — and keeps its own keys beside these (Studio:
`siamang_respondent_<survey id>`, `siamang_ended_<survey id>`).

The autosave is written 2 s after the last answer (a field's text is taken 600 ms
after its last key), and at once when the page is hidden or left — another tab, the
app switcher, a locked phone, the tab closed or reloaded (`visibilitychange` to
hidden and `pagehide`, in the capture phase on `window`): the save still waiting is
written then, with the text still in a field. `visibilitychange` is the document's,
so the save is written before a transport's own listener on the document reads it;
leaving the page, `pagehide` comes first and the document turns hidden after it. A
`pagehide` listener a transport puts on `window` before the runtime's runs before
it, as a window's own listeners run in the order they were put on: a transport
reads the save at `visibilitychange`. An answer given a moment before leaving is in
the partial response and offered back on the next visit. "Saving…" (`saving_text`)
shows for 0.8 s after a save the timer wrote, above the page card's right corner, on
one line that ends in "…" where the page is narrower. It takes no room, so nothing
on the page moves. A screen reader is told once, at the first save of a sitting, and
not after every answer. A saved interview's offer to resume is on the page when it
is first drawn.

- **Nothing before the respondent starts.** Opening a survey writes nothing: the
  interview's id is drawn in memory and kept at the first answer or the first move
  between pages (Resume and Start over count), and the transport's `onStart()` is called
  then. A reload before that is a new visitor — nothing of theirs was kept or sent —
  and draws anew. The theme button keeps the choice alone.
- **A week without the survey, and it is gone.** `siamang_kept_<survey id>` notes when
  the survey last wrote here. Every survey page that opens drops, for each survey on the
  origin (its own included), the `siamang_answers_`, `siamang_respondent_`,
  `siamang_interview_`, `siamang_ended_` and `siamang_theme_` keys and the note once the
  note is 7 days old. A key found without a note (kept by an earlier runtime) is dated
  then and goes a week later.
- **The one-response mark stays.** `siamang_done_<survey id>`, which a host writes when
  the researcher asks for one response per browser (Studio does), is never dropped:
  forgetting it after a week would let the same browser answer again. It is a mark in the
  browser, so the survey's consent text should mention it.
- **In memory only.** A host page that should leave nothing in the browser — a preview —
  sets `window.SIAMANG_STORAGE = "memory"` before the bundle loads: the runtime keeps its
  state in memory for the life of the page and does not read, write or sweep
  `localStorage` (a transport that reads the autosave finds none).

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

The colors, sizes and font stacks are written into the stylesheet, so each has a
strict format, checked when the `UIConfig` is made (`ValueError` otherwise;
`siamang.frontend.theme.tokens`): a **color** is `#rgb`, `#rgba`, `#rrggbb`,
`#rrggbbaa`, `rgb()`/`rgba()`/`hsl()`/`hsla()`/`hwb()`/`lab()`/`lch()`/`oklab()`/
`oklch()` of numbers, or a CSS color name; a **length** (`font_size`, `width`,
`radius`) is a number with a unit (`15.5px`, `1.1rem`, `60%`), `0`,
`calc()`/`min()`/`max()`/`clamp()` of those or a keyword (`auto`, `medium`…);
`line_height` may also be a number alone; a **font stack** is family names
separated by commas, a name with digits or punctuation in quotes
(`"Source Serif 4", Georgia, serif`). None can hold `; { } < > \ @` or `url()` —
that is what `custom_css` is for. The addresses a respondent opens or is sent to
(`privacy_url`, `redirect_url`, `screen_out_redirect_url`,
`quota_full_redirect_url`) are `http://` or `https://` written out.

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
the default), `"modern"` (Inter everywhere), or `"humanist"` (Nunito). The three
families ship with the package (SIL Open Font License 1.1; variable weights, the
`latin`, `latin-ext` and `cyrillic` subsets) and are served with the survey: the
stylesheet declares the ones its font stacks name with `@font-face` pointing at
`fonts/` next to it, and the bundle carries those files and their license texts. No
request goes to Google Fonts or any other font CDN. A family that is not bundled
(`font_family='"Roboto", sans-serif'`) is used where the respondent's device has it,
the next family of the stack otherwise; declare a web font of your own with
`@font-face` in `custom_css`. Fine-grained overrides: `font_family`,
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

Where the respondent is: every page they answer has a label above its title —
"Welcome" on the first, "Final thoughts" on the last, "Page *n* of *m*" between —
and the progress bar shows the same label beside it. The count is the respondent's own:
the pages they go through, in their order (after `randomize_pages`, say), without the
end pages (final, screen-out, redirect), so the last question page is at 100 % and
the second of four is "Page 2 of 4". `show_section_numbers=False` drops the labels,
and the bar says "Page *n* of *m*" on every page (`page_text`, `of_total_text`);
`show_progress_text=False` leaves the bar without text. The page dots, too, are one
per page the respondent answers, and a page without a title names its dot by the same
count ("Page 2").

The header appears when there is something in it: the title (`show_title=True`), a
logo or an institution. `show_title=False` hides the questionnaire's title even when
the header is shown for a logo or an institution.

### Footer

`privacy_url`, `contact_email`, and `ethics_statement` (e.g. an IRB reference).

### I18n UI strings

Every fixed phrase the runtime shows has a `UIConfig` field; `None` (the default) keeps
the English text in the table. Replacing all of them is how a survey runs in another
language. In a template, `{name}` is replaced by the value named (`{page}`, `{pages}`,
`{n}`, `{minutes}`, …) and `{link}` is where the link goes.

| Field | English default | Where |
| :--- | :--- | :--- |
| `next_button_text` / `prev_button_text` / `submit_button_text` | `Next →` / `← Previous` / `Submit responses` | the page's buttons |
| `submitting_text` / `saving_text` | `Submitting your responses…` / `Saving…` | while submitting / for a moment at each autosave, above the page card's top right corner |
| `required_text` | `This question requires an answer.` | an unanswered required question |
| `required_rows_text` | `Please answer every row.` | a required matrix answered in some rows but not all (`{n}`: the rows left); the rows are marked |
| `welcome_text` / `section_text` / `final_section_text` | `Welcome` / `Page {page} of {pages}` / `Final thoughts` | the label above a page's title and beside the progress bar: on the first page, the pages between, the last page. Without a `section_text` the pages between read "Page *n* of *m*" in `page_text` and `of_total_text`, so one translation covers the label and the bar. `{page}` and `{pages}` count the pages the respondent answers; `{n}` and `{total}` leave the first page out (page 2 of 4 is "1" of "3"), as the earlier default "Section {n} of {total}" did, so a text written for it reads as it did |
| `page_text` / `of_total_text` | `Page` / `of` | "Page *n* of *m*": beside the bar without page labels, between the first and the last page without a `section_text`, and for screen readers; `page_text` also names a step dot of a page without a title ("Page 2") |
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
| `media_play_text` / `media_loads_from_text` | `Play video` / `Plays from {service} when you press play` | a YouTube or Vimeo video's play button: its name ("Play video: *alt*") and the line under it (`{service}`: YouTube or Vimeo) |
| `media_close_text` | `Close` | the window an option's video plays in |
| `media_preview_blocked_text` | `This preview can't play videos.` | a preview that cannot play a video (a design preview, a sandboxed page that cannot open the video's page) |
| `resume_title` / `resume_action` / `restart_action` | `We saved your progress from earlier. Would you like to resume?` / `Resume` / `Start over` | the resume banner |
| `retry_title` / `retry_body` / `retry_action` / `save_local_action` / `attempt_text` | `Submission failed` / `We could not save your responses.` / `Try again` / `Save locally and finish` / `Attempt {n} of {max}.` | a failed submission |
| `saved_locally_title` / `saved_locally_body` | `Your answers are saved in this browser` / `They have not been sent yet. To send them, open this survey's link again in this browser within 7 days and choose Resume.` | after **Save locally and finish**, in place of the page; it sends the respondent nowhere |
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

css: str = compile_css(ui)                     # font_base="fonts/"
```

Compiles a `UIConfig` into a CSS stylesheet string using CSS custom properties. This
is the fallback `style.css` when a runtime does not supply its own (the React
runtime ships a full design system). Useful for inspecting the generated theme or
embedding it elsewhere. It opens with the `@font-face` rules of the bundled typefaces
its stacks name, their files at `font_base` — where you serve
`siamang.frontend.theme.fonts.font_file(name)` when the stylesheet is not next to a
bundle's `fonts/`.

---

See also: [[Deployment]] · [[CLI Reference|CLI-Reference]] · [[Cookbook]] ·
[[API Reference Index|API-Reference-Index]]
