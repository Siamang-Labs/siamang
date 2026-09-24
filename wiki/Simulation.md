# Simulation

Every `Questionnaire` can generate synthetic respondents with a single call.
Simulation is the fastest way to test a survey end to end before you collect a
single real response: you get a fully-populated [[Working with Data|Working-with-Data]]
`SurveyData` object you can immediately run [[Analysis]], [[Reporting Tables|Reporting-Tables]],
and [[Reporting Charts|Reporting-Charts]] against.

---

## `Questionnaire.simulate`

```python
from siamang.core import Questionnaire

def simulate(self, n: int = 100, seed: int | None = 42) -> "SurveyData": ...
```

Generates `n` synthetic respondents and returns a `SurveyData` whose `frame`
holds one row per respondent, with the questionnaire's `VariableMap` and the
questionnaire itself attached.

**Parameters**

- **`n`** — number of synthetic respondents (default `100`).
- **`seed`** — RNG seed for reproducibility (default `42`). Pass `seed=None`
  for a fresh draw each call; pass a fixed integer to get the same dataset every
  time — invaluable in tests and documentation.

If the questionnaire has no explicit `variables` registry, `simulate` builds one
on the fly from the bound question variables, so the returned `SurveyData` always
carries metadata (labels, scales) for reporting. The questionnaire's scripts are
run too (see [Scripts and quotas](#scripts-and-quotas-simulate_survey) below).

### How values are drawn

Each question type produces plausible values:

| Question type | Simulated value |
| :--- | :--- |
| `NumericInput` | uniform integer within the variable's `valid_range` (else `18–70`). |
| `LikertScale` | uniform integer in `1..points`. |
| `SingleChoice` | a random option code. |
| `MultiChoice` | a random subset honoring `min_answers`/`max_answers`/`exclusive`. |
| `Ranking` | a random ranked subset up to `max_ranked`. |
| `Matrix` | a random code per sub-variable from its labels. |
| `OpenText` | the placeholder string `"sample text"`. |

> **Note:** Simulation produces values drawn at random, *not* from any modeled
> correlation structure. Use it to exercise plumbing, validate logic, and
> preview report layouts — not to study real associations.

---

## The questionnaire's logic is replayed

When the questionnaire is defined with **pages**, each simulated respondent
starts on the first page and moves the way the runtime would move them. Every
condition is evaluated against the answers collected *so far*:

- A page's `show_if`/`hide_if` decides whether it is answered; a hidden page is
  passed over and **every variable on it is `NaN`** for that respondent.
- A **block's** `show_if`/`hide_if` does the same for the questions inside it,
  nested blocks included.
- A question's own `show_if`/`hide_if` hides it the same way.
- An **answer option's** `show_if`/`hide_if` decides whether it can be picked:
  a hidden option is never chosen, and a question whose options are all hidden
  is left unanswered. In a wide `MultiChoice` a hidden option's variable is
  `NaN`, not `0`: the respondent was never offered it.
- `skip_to` (on the first answered question, in the order shown), the page's
  `next_if` rules and `default_next` decide where "Next" lands; a visible
  terminal page — screen-out, final, redirect — ends the interview, and pages
  never reached stay `NaN`.

This means simulated data reproduces the *missingness pattern* your real data
will have. A question gated behind `consent == 1` will only have values for the
respondents whose simulated `consent` is `1`. See
[[Visibility and Branching|Visibility-and-Branching]] for the expression DSL.
A condition written as a string is not parsed here: it never hides anything.

```python
from siamang.core import Variable, SingleChoice, LikertScale, Page, Questionnaire

consent = Variable("consent", scale="nominal", label="Consent", labels={1: "Yes", 0: "No"})
autonomy = Variable("autonomy", scale="ordinal", label="Autonomy",
                    labels={1: "Very low", 2: "Low", 3: "Moderate", 4: "High", 5: "Very high"})

survey = Questionnaire(
    title="Autonomy Study",
    pages=[
        Page(name="consent", items=[SingleChoice("Do you consent?", var=consent, required=True)]),
        Page(name="main", items=[LikertScale("How much autonomy?", var=autonomy, points=5)],
             show_if=consent.eq(1)),   # only consenters see this page
    ],
)

data = survey.simulate(n=200, seed=123)

print(data.frame.shape)                 # (200, 2)
print(data.frame["consent"].value_counts(dropna=False).to_dict())
# autonomy is NaN for every respondent whose consent != 1:
print(int(data.frame["autonomy"].isna().sum()))
```

> In the legacy flat (`blocks`) mode every question is answered for every
> respondent; only answer-option conditions apply.

### Scripts and quotas: `simulate_survey`

`Questionnaire.simulate(n, seed)` is `siamang.local_simulator.simulate_survey(survey,
n=n, seed=seed)`: it runs the questionnaire's scripts listed below. Quotas are
not on the questionnaire — they are compiler options — so to see their effect
call `simulate_survey` with them:

```python
from siamang.local_simulator import simulate_survey

data = simulate_survey(survey, n=500, seed=42, quotas=options["quota"])
```

- **`Script.assign_condition`** — its variable gets a column, one arm per
  respondent drawn before the first page by the arms' weights, so pages and
  questions gated on the arm are shown to that arm only. With `balance=True`
  and a quota cell on every arm, each respondent goes to the arm furthest
  behind its own target (completes ÷ limit, ties drawn at random), as the
  platform picks it. The codebook gains a nominal variable for the arm,
  labeled with the arms, unless it already declares one.
- **`Script.randomize_pages`** — every respondent gets their own page order,
  with the first and last page and every terminal page kept in place, so a
  page gated on an answer the shuffle puts after it is hidden for those
  respondents, as it would be in the field.
- **`Block.randomize` / `Page.randomize_blocks`** change the order questions
  are shown in, which decides which `skip_to` is met first; nothing else in
  the data depends on order, and option shuffles are not drawn at all. As in
  the runtime, a shuffling block moves a nested block as one piece, in its
  own order.
- **Quotas** (given to `simulate_survey`) — leaving a page, a respondent holding a
  value in a full cell ends there (the runtime's "quota full" screen, not a
  complete): an answer given so far, a multiple-choice answer meeting every cell it
  names, and the assigned arm, which the first page left already holds. Only
  completes fill a cell — a screen-out never does — so the quota's effect on the
  sample shows: once ten owners have completed, the eleventh stops at the
  screener, and once an arm's cell is full its respondents stop on the first page
  (with `balance=True` too, once every arm's cell is full).

Other scripts are JavaScript and are not run. A flow's **Simulated data** node
(`source.simulated`) runs `simulate_survey` on the project's questionnaire, so
its arms and page shuffles are there; quotas are deploy options rather than
part of the questionnaire, so no cell closes in a flow. `simulate_questionnaire`
returns the same frame without the codebook, and `simulate_from_pages(pages, n, seed,
scripts=…, quotas=…)` is the walk itself. Every draw comes from one generator
seeded once: the same seed gives the same frame, scripts and quotas included.

---

## Using simulated data for testing and preview

Because `simulate` returns a real `SurveyData`, the full analysis and reporting
stack is available immediately:

```python
# Publication-ready frequency table straight from synthetic data
print(data.report.freq("autonomy").to_markdown())

# Quick descriptive: how complete is each variable?
print(data.describe_variables())

# Validate the synthetic frame against its metadata (should be clean)
issues = data.validate()
assert all(i.severity != "error" for i in issues)
```

Typical uses:

- **Unit tests** — seed the RNG (`seed=42`) and assert on report output or
  validation results without any network or database.
- **Report layout previews** — confirm tables and charts render before real data
  arrives.
- **Demos and documentation** — reproducible figures with a fixed seed.

---

See also: [[Working with Data|Working-with-Data]] · [[Analysis]] · [[Validation and Linting|Validation-and-Linting]] · [[Visibility and Branching|Visibility-and-Branching]] · [[Reporting Tables|Reporting-Tables]]
