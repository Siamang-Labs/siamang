# Scripts

A `Script` injects a custom JavaScript snippet that runs in the respondent's browser
at a chosen lifecycle trigger. Scripts cover behaviour the declarative model does not:
option/page randomization, cross-field validation, timed questions, external API
calls, A/B assignment, piped text, and custom event tracking — all without modifying
the core runtime.

```python
from siamang.core import Script
# or: import siamang as sg  →  sg.Script
```

## `Script`

```python
@dataclass(frozen=True, slots=True)
class Script:
    code: str
    trigger: str = "onPageEnter"
    name: str | None = None
    target: str | None = None
    context: dict[str, Any] = {}
    sandbox: bool = True
```

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `code` | `str` | *required* | JavaScript source. Must be non-empty. |
| `trigger` | `str` | `"onPageEnter"` | Lifecycle event that runs the script (see below). |
| `name` | `str \| None` | `None` | Optional identifier shown in logs; useful for debugging. |
| `target` | `str \| None` | `None` | Scope to a page name or question id; `None` runs globally at the trigger. |
| `context` | `dict[str, Any]` | `{}` | Static data passed into the script at runtime. |
| `sandbox` | `bool` | `True` | Run in a restricted scope (no DOM access). |

Construction validates the trigger (unknown triggers raise `ValueError`), requires
non-empty `code`, and rejects an empty `name`. `to_dict()` serializes the script for
the frontend bundle.

Scripts are attached to a survey through `Questionnaire(scripts=[...])`.
`Questionnaire.validate()` checks that every script has a known trigger and that a
non-`None` `target` matches an existing question id or page name.

## Trigger points

| Trigger | When it runs |
| :--- | :--- |
| `onInit` | Once when the survey loads, before the first page. |
| `onPageEnter` | A page becomes visible. |
| `onPageExit` | A page is left. |
| `onQuestionShow` | A question becomes visible (its `show_if` resolved). |
| `onAnswer` | Any answer changes. |
| `onSubmit` | Before submission — can modify answers. |
| `onRandomize` | Randomization is requested. |

## The JavaScript runtime context

Inside a snippet you have these globals:

- **`answers`** — the current respondent answers (read/write). Special keys the
  runtime understands include `answers.__options__[qid]` (per-question option order),
  `answers.__pages__` (page order), `answers.__errors__[field]` (validation messages),
  `answers.__timers__` (timer handles — the runtime cancels every timer kept there when
  the respondent leaves the page or submits) and `answers.__respondent__` — the
  interview's respondent id: the transport's `respondentId()` when it has one (Studio's
  platform transport returns the id of the response row), otherwise a random id the
  runtime keeps in the browser until the interview is submitted, so a reload keeps it.
  It is what a seeded `assign_condition` and the MaxDiff/Conjoint design version are
  drawn from. `__` keys are never submitted as answers.
- **`utils`** — helper functions: `shuffle(list, seed?)` (a shuffled copy), `sample(list,
  n, seed?)`, `clamp`, `debounce`, `now`, `formatDate`. With a `seed` (any string)
  `shuffle` and `sample` are deterministic: the same seed and list give the same order
  in every browser — a 32-bit FNV-1a hash of the seed starts a mulberry32 generator
  that drives a Fisher–Yates shuffle, the same draw a seeded `assign_condition` makes.
  For an order of the respondent's own, put their id in the seed:
  `utils.shuffle(list, "brands:" + answers.__respondent__)`.
- **`api`** — `{ get, post }` for external HTTP calls.
- **`context`** — exactly the static `context` dict you passed on the `Script`;
  the runtime injects nothing else into it.

```python
import siamang as sg

custom = sg.Script(
    name="log_exit",
    trigger="onPageExit",
    context={"endpoint": "/diagnostics"},
    code="""
        api.post(context.endpoint, { left_at: utils.now() });
    """,
)
```

## Factory classmethods

Five classmethods build ready-made scripts for the most common patterns. Each returns
a fully-configured `Script` (trigger, target, and name preset).

### `Script.randomize_options(question_id, seed=None)`

Shuffle a question's answer options when it is first shown (`trigger="onQuestionShow"`,
scoped to `question_id`). Without a seed each showing draws a new order. With a `seed`
(stored in `context`) the order is drawn from `"<seed>:<respondent id>"`
(`answers.__respondent__`): the same respondent always gets the same order — a reload
or a resume does not reshuffle it — different respondents get different orders, and
the order a respondent saw can be recomputed from the seed and their id (see
`utils.shuffle` below). Two questions shuffled with the same seed and the same number
of options get the same order for a respondent, which keeps a list in one order
across questions; give them different seeds for independent orders.

```python
shuffle_party = sg.Script.randomize_options("q_party")
```

### `Script.randomize_pages()`

Shuffle the page order on `onInit`. The first (welcome) page, the last page and
every terminal page (`DisqualificationPage`, `FinalPage`, `RedirectPage`) keep
their place wherever they sit — a screen-out is gated on the questions before
it — and the remaining pages are shuffled among the remaining slots. Runs
globally.

```python
shuffle_pages = sg.Script.randomize_pages()
```

### `Script.assign_condition(variable, arms, seed=None, balance=False)`

Draw each respondent into one experimental arm before the first page (`onInit`) and
store the arm's code in `variable`, so `show_if` / `next_if`, quotas and the analysis
can use it like any answer. `arms` are `(code, label)` or `(code, label, weight)`
tuples; weights are positive integers (default 1) and set the shares.

- Without a `seed` the draw is random, once per interview.
- With a `seed` it is deterministic per respondent: the arm is drawn from
  `"<seed>:<respondent id>"` (`answers.__respondent__`, which the runtime sets for
  every interview), so the same respondent always lands in the same arm, respondents
  are spread over the arms by their weights, and the assignment can be recomputed
  from the generated `.py` and the respondent ids.
- `balance=True` sends each respondent to the arm furthest behind its quota (it
  needs a quota cell per arm on `variable`; the weighted draw stays as the fallback)
  and cannot be combined with a `seed`.

```python
split = sg.Script.assign_condition("condition", [(1, "Control"), (2, "Treatment")], seed="2026")
```

### `Script.validate_fields_match(field_a, field_b, message="Fields do not match.")`

Validate that two answer fields hold the same value (e.g. email confirmation). Runs on
`onAnswer` for every answer (it has no target), so correcting **either** field
re-checks the pair: on a mismatch it writes `message` to `answers.__errors__[field_b]`
— shown under `field_b`, and Next is blocked — and once they match it removes it.

```python
match_emails = sg.Script.validate_fields_match(
    "email_1", "email_2", message="Emails don't match.",
)
```

### `Script.timed_question(question_id, seconds=30)`

Show a question for a limited time, then auto-advance. Runs on `onQuestionShow`, scoped
to `question_id`, and sets a timer that calls the runtime's next-page hook after
`seconds`. The automatic Next is an ordinary one: an unanswered required question (or
any other message) on the page holds it. The timer belongs to its page — leaving the
page earlier (Next, Previous, a page dot) or submitting cancels it — and it runs once
per question, so coming back to the page does not start it again.

```python
timer = sg.Script.timed_question("q_party", seconds=30)
```

## Attaching scripts to a survey

Pass scripts to the questionnaire's `scripts=` list. `target` values must resolve to
real question ids or page names.

```python
import siamang as sg

shuffle_party = sg.Script.randomize_options("q_party")
timer         = sg.Script.timed_question("q_party", seconds=30)
match_emails  = sg.Script.validate_fields_match(
    "email_1", "email_2", message="Emails don't match.",
)
custom = sg.Script(
    name="log_exit",
    trigger="onPageExit",
    context={"endpoint": "/diagnostics"},
    code="""
        api.post(context.endpoint, { left_at: utils.now() });
    """,
)

survey = sg.Questionnaire(
    title="Political Trust — 2026",
    pages=[...],
    scripts=[shuffle_party, timer, match_emails, custom],
)

survey.validate()      # rejects unknown triggers or targets that don't exist
```

## See also

- [[Visibility and Branching|Visibility-and-Branching]] — declarative logic that runs before reaching for a script.
- [[Question Types|Question-Types]] — the question ids scripts target.
- [[Pages Blocks and Structure|Pages-Blocks-and-Structure]] — page names scripts target, and the `scripts=` field.
- [[Frontend and Theming|Frontend-and-Theming]] — how scripts run inside the runtime.
