# Validation and Linting

Before you simulate, deploy, or analyze a survey, siamang can check it for
**hard errors** (`validate`) and **soft warnings** (`lint`). Validation guards
the structural invariants a questionnaire must satisfy; linting surfaces stylistic
and best-practice issues that won't crash the pipeline but probably indicate a
mistake. Both run in pure Python and back the [[CLI Reference|CLI-Reference]]
`siamang validate` command.

---

## `Questionnaire.validate`

```python
from siamang.core import Questionnaire

def validate(self, strict: bool = False) -> None: ...
```

Raises `ValueError` on the first structural problem it finds; returns `None`
when the questionnaire is sound. It is intentionally strict about anything that
would produce a broken survey:

- **Duplicate question IDs** and **duplicate variable names**.
- **Answer keys** — a question that writes one variable stores its answer under
  that variable, so a `name` that differs from it is rejected; two questions may
  not store their answers under one key, and no question's id may be the key of
  another. A question whose id is not its answer key (id `q1`, variable `nps_1`)
  is renamed wherever a script names it — `answers["q1"]` in a custom script
  becomes `answers["nps_1"]` — so its id may not also be a name the answers hold
  something else under: a variable of any question (a matrix's rows, and its
  own, included), an Other text key (`<variable>_other`), a variable a script
  assigns (`Script.assign_condition`, or a codebook variable no question
  collects that a custom script writes: `answers.panel = …`, `+=` and the like,
  `++`, `delete`, a destructuring or loop target — `[answers.panel, x] = …`,
  `for (answers.panel of …)` — or the value changed in place,
  `answers.panel.push(…)`, `answers.panel.k = …`, `(answers.panel || []).push(…)`,
  `Reflect.set(answers.panel, …)`; wherever the write stands, after `if (c)` or
  `else` and after a regular expression included), or a name beginning with `__`
  (the runtime's own state). A codebook variable nothing writes does not count —
  the runtime captures no embedded data — so an entry left over from a renamed
  variable leaves the id free. If a script does write it, the message offers two
  ways out: another id for the question, or — when the entry is a leftover and the
  script means the question, as a prefill from before answers were keyed by
  variable does — deleting the entry, after which the script's name is rewritten
  to the question's variable. An id that is its question's own key is renamed
  nowhere and may be any free name.
- **Unknown `skip_to` targets** — a question may only skip to a known question
  ID or page name.
- **Other and None codes** — an `other_code` / `none_code` must be a number or
  a string; a "None of the above" code may not be one of the question's answers
  or its Other code; a question whose choices already use the default Other code
  (`-66`) must name its own `other_code`; and the Other text key
  (`<variable>_other`) may not be a variable or an answer key of any question.
  See [[Question Types|Question-Types#other-none-and-na-codes]].
- **Page integrity** (pages mode): no empty/duplicate page names, every
  `show_if`/`hide_if`/`next_if` expression references only known variables and
  is itself evaluable, all navigation targets exist, every page is reachable
  from the first page, and the navigation graph contains **no cycles**.
- **Export-safety** of page `show_if` expressions for the SurveyJS frontend.
- **Script triggers/targets** — each script must use a known trigger and point
  at a real question or page.
- **Registry consistency** — if the questionnaire carries a `VariableMap`, every
  question variable must be equal (field-by-field) to the definition registered
  there. The comparison is by value, not identity, so an identical copy passes —
  but defining each `Variable` once and reusing that object remains the simplest
  way to keep the two in sync.

### `strict=True`

With `strict=True`, `validate` additionally runs `lint(level="strict")` and
**promotes any lint result with `severity == "error"` into a `ValueError`**.
This is how you fail a build on issues such as a `LikertScale` bound to a
non-ordinal variable. See the [[Visibility and Branching|Visibility-and-Branching]]
page for the expression rules that validation enforces.

```python
from siamang.core import Variable, LikertScale, SingleChoice, Page, Questionnaire

consent = Variable("consent", scale="nominal", label="Consent", labels={1: "Yes", 0: "No"})
autonomy = Variable("autonomy", scale="ordinal", label="Autonomy",
                    labels={1: "Very low", 2: "Low", 3: "Moderate", 4: "High", 5: "Very high"})

survey = Questionnaire(
    title="Autonomy Study",
    pages=[
        Page(name="consent", items=[SingleChoice("Do you consent?", var=consent, required=True)]),
        Page(name="main", items=[LikertScale("How much autonomy?", var=autonomy, points=5)],
             show_if=consent.eq(1)),
    ],
)

survey.validate()              # returns None — the survey is structurally valid
survey.validate(strict=True)   # also fails on strict-level lint *errors*
```

---

## `Questionnaire.lint`

```python
def lint(self, level: str = "basic") -> list[LintWarning]: ...
```

Returns a list of `LintWarning` objects (never raises, except on an invalid
`level`). Pass `level="basic"` (default) or `level="strict"`. Unlike `validate`,
linting reports *all* findings at once so you can triage them.

### `LintWarning`

```python
from siamang.core.questionnaire import LintWarning

@dataclass(frozen=True, slots=True)
class LintWarning:
    code: str            # machine-readable, e.g. "EMPTY_PAGE"
    severity: str        # "warning" or "error"
    message: str         # human-readable description
    location: str | None # page name / question id, when applicable
```

### What `basic` checks

Every run of `lint()` — including the default `level="basic"` — applies the
rules below. Four are structural:

| Code | Severity | Meaning |
| :--- | :--- | :--- |
| `EMPTY_QUESTIONNAIRE` | warning | No pages and no blocks. |
| `EMPTY_PAGE` | warning (error in strict) | A page has no items. |
| `REDUNDANT_NAVIGATION` | warning | `default_next` duplicates the implicit next page. |
| `MISSING_NAVIGATION` | warning | Any page other than the last one has no outgoing navigation edges. |

The others check codebook and logic consistency — a questionnaire that compiles
and runs but silently collects the wrong thing. All of them are warnings at
every level:

| Code | Severity | Meaning |
| :--- | :--- | :--- |
| `UNKNOWN_CONDITION_VALUE` | warning | A condition compares a variable to a value that is not among its defined categories. |
| `CONTRADICTORY_VISIBILITY` | warning | An object sets both `show_if` and `hide_if`; the combination may never show it. |
| `EXCLUSIVE_CODE_UNKNOWN` | warning | A `MultiChoice` marks a code `exclusive` that is not among its answer codes. |
| `OPTION_CODE_WITHOUT_LABEL` | warning | An `Option.code` has no matching value label on the bound variable. |
| `LIKERT_POINTS_LABEL_MISMATCH` | warning | A `LikertScale`'s `points` disagrees with the number of labelled codes. |
| `MISSING_CODE_NOT_IN_LABELS` | warning | A declared missing-value code is not among the variable's value labels. |
| `ADDED_CODE_WITHOUT_LABEL` | warning | A question stores "Other (please specify)" or "None of the above" as a code (`metadata["other_code"]`, default `-66`; `metadata["none_code"]`, default `-77`) that its variable has no value label for — the answer would arrive with no text. |
| `RANGE_LABEL_MISMATCH` | warning | A variable labels values that fall outside its `valid_range`. |

### Extra `strict` checks

`level="strict"` adds question-level, script and registry checks:

| Code | Severity | Meaning |
| :--- | :--- | :--- |
| `REQUIRED_CONDITIONAL` | warning | A required question also has conditional visibility. |
| `INCOMPATIBLE_QUESTION_SCALE` | error | `NumericInput` not on interval/ratio, or `LikertScale` not on ordinal. |
| `CATEGORICAL_WITHOUT_LABELS` | error | A `SingleChoice`/`MultiChoice` variable has no value labels. |
| `NA_STORED_AS_TEXT` | warning | A `LikertScale` or `Matrix` offers "Not applicable" but its variable declares no missing value of kind `not_applicable`, so N/A is stored as the text `"na"`; declare one (and label it) to store its code. |
| `SCRIPT_STALE_QUESTION_ID` | warning | A custom script still names a question whose answer is stored under a different key (its id is not its variable) as a string or a bare identifier — outside the `answers[…]` / `__errors__[…]` / `__options__[…]` / `__timers__[…]` accesses the compiler translates. Comments, regular expressions, and strings that merely mention the id, do not count. |
| `SCRIPT_TARGET_IS_A_PAGE` | warning | An `onQuestionShow` / `onAnswer` script targets a page name. The runtime dispatches those triggers with a question's key, so the script would never run. |
| `SCRIPT_TARGET_IS_A_QUESTION` | warning | An `onPageEnter` / `onPageExit` script targets a question. The runtime dispatches those triggers with a page's name, so the script would never run. |
| `UNUSED_VARIABLE` | warning | A registered variable is never used in the questionnaire. |

```python
from siamang.core import Variable, SingleChoice, Page, Questionnaire

gender = Variable("gender", scale="nominal", label="Gender", labels={1: "Male", 2: "Female"})

survey = Questionnaire(
    title="Demo",
    pages=[
        Page(name="p1", items=[SingleChoice("Gender?", var=gender)]),
        Page(name="p2", items=[]),     # empty page!
    ],
)

for w in survey.lint():
    print(f"[{w.severity}] {w.code}: {w.message} ({w.location})")
# [warning] EMPTY_PAGE: Page 'p2' has no items. (p2)
```

---

## Relationship to the `siamang validate` CLI

`siamang validate my_survey.py` is a thin wrapper: it loads the survey object,
calls `validate(strict=...)`, also validates the module-level `options` dict if
the module exports one (quotas live there), then prints all `lint()` warnings.
The exit code encodes the outcome:

| Exit code | Condition |
| :--- | :--- |
| `0` | Valid; no warnings, or only `warning`-severity lint findings. |
| `1` | Valid structure, but at least one printed lint finding had `severity == "error"`. |
| `2` | `validate()` (or the `options` check) raised a `ValueError` (structural failure). |

> **Note:** `error`-severity lint rules only exist at the strict level, and
> `--strict` runs `validate(strict=True)` first — which promotes those same
> findings into a `ValueError` (exit code `2`). With the current rule set,
> exit code `1` is therefore a reserved part of the contract rather than an
> outcome you will commonly see.

```bash
siamang validate my_survey.py            # basic lint
siamang validate my_survey.py --strict   # strict validation + lint
```

See the [[CLI Reference|CLI-Reference]] for the full command surface.

---

## Validating *data*, not just the questionnaire

`Questionnaire.validate`/`lint` check the **design**. To check a collected or
simulated **dataset** against its variable metadata (dtypes, ranges, value
labels, weight constraints), use `SurveyData.validate()`, which returns a list
of `ValidationIssue` objects. That workflow is documented on
[[Working with Data|Working-with-Data]].

---

See also: [[Visibility and Branching|Visibility-and-Branching]] · [[Simulation]] · [[Working with Data|Working-with-Data]] · [[CLI Reference|CLI-Reference]]
