# Question Types

A `Question` binds a respondent-facing prompt to one variable (or many, for `Matrix`
and wide `MultiChoice`). siamang ships **seven** concrete question types, all frozen
dataclasses inheriting the shared `Question` fields. This page documents the base
class, every type, and the `Option` and `Media` helpers that enrich answer choices.

```python
from siamang.core import (
    SingleChoice, MultiChoice, LikertScale, NumericInput,
    OpenText, Matrix, Ranking, MaxDiff, Conjoint, Attribute, Option, Media,
)
```

## The `Question` base class

`Question` is the shared base; you instantiate its subclasses, not `Question`
itself. Every type accepts these fields.

```python
@dataclass(frozen=True, slots=True)
class Question:
    text: str
    var: Variable | list[Variable]
    required: bool = False
    hint: str | None = None
    show_if: Any = None
    hide_if: Any = None
    skip_to: str | None = None
    randomize: bool = False
    other_specify: bool = False
    tag: str | list[str] | None = None
    id: str | None = None
    name: str | None = None
    media: Media | list[Media] | None = None
    metadata: dict[str, Any] = {}
```

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `text` | `str` | *required* | The prompt shown to the respondent. Must be non-empty. |
| `var` | `Variable \| list[Variable]` | *required* | The bound variable(s); answers are stored under their names. |
| `required` | `bool` | `False` | Respondent must answer before advancing. |
| `hint` | `str \| None` | `None` | Helper text shown beneath the prompt. |
| `show_if` | `Expression \| str \| None` | `None` | Render only when this evaluates true. |
| `hide_if` | `Expression \| str \| None` | `None` | Hide when this evaluates true. |
| `skip_to` | `str \| None` | `None` | Jump to a target page/question id after answering. |
| `randomize` | `bool` | `False` | Shuffle the answer choices, once per respondent when the survey loads. "None of the above", a `MultiChoice`'s `exclusive` answers and a choice that is the question's "Other" (`metadata["other_code"]`) keep their place; the runtime's own "Other" always comes last. |
| `other_specify` | `bool` | `False` | `SingleChoice` / `MultiChoice`: add an "Other (please specify)" choice with a text box — see [Other, None and N/A codes](#other-none-and-na-codes). |
| `tag` | `str \| list[str] \| None` | `None` | Tag(s) for categorization/filtering. |
| `id` | `str \| None` | `None` | Explicit question id; defaults to the variable name — except for `Matrix` and wide-mode `MultiChoice`, where the fallback is `matrix_<first var>` / `multi_<first var>`. |
| `name` | `str \| None` | `None` | The key the answer is stored under. A question that writes one variable stores its answer under that variable's name, with or without a `name` — a `name` that differs is a `validate()` error. For `Matrix`, wide-mode `MultiChoice`, `MaxDiff` and `Conjoint`, which write several variables, each variable is stored under its own name and `name` (default: the id) is only the item's handle — what a script targets and a validation message is keyed by. |
| `media` | `Media \| list[Media] \| None` | `None` | Image/video/audio attached to the prompt. |
| `metadata` | `dict[str, Any]` | `{}` | Free-form extra parameters. The runtime reads `other_code`, `other_label`, `other_placeholder` and `none_code` (below). |

`show_if` / `hide_if` / `skip_to` are detailed in
[[Visibility and Branching|Visibility-and-Branching]]; `media` is covered under
[Media](#media) below.

`text` and `hint` are **plain text** — no Markdown, no HTML. They can pipe an
earlier answer:

| Placeholder | Inserts |
| :--- | :--- |
| `{answer:x}` / `{var:x}` | the stored value of variable `x` (a list is joined with ", ") |
| `{label:x}` | the label of the chosen option(s) of `x` — a choice's label, a matrix column header, a MaxDiff item — or the value itself when `x` has no options |

An unanswered variable leaves the placeholder as written, so an author sees what
is missing. The same placeholders work in a page's `title` and `body`, the final and
screen-out pages included (see [[Pages, Blocks and Structure|Pages-Blocks-and-Structure]]).

---

## `SingleChoice`

One mutually-exclusive answer from a set of options.

```python
@dataclass(frozen=True, slots=True)
class SingleChoice(Question):
    display: str = "radio"            # "radio" | "dropdown" | "buttons"
    none_of_above: bool = False
    choices: list[Option] | None = None
```

| Field | Default | Description |
| :--- | :--- | :--- |
| `display` | `"radio"` | UI style: `"radio"`, `"dropdown"`, or `"buttons"` (segmented). |
| `none_of_above` | `False` | Append a "None of the above" option; it stores the code `metadata["none_code"]`, default `-77` (see [below](#other-none-and-na-codes)). |
| `choices` | `None` | Explicit `Option` list; if `None`, derived from the variable's `labels`. |

`var` must be a single `Variable`. When `choices` is omitted, the options come from
`var.labels`.

```python
import siamang as sg

gender = sg.Variable("gender", scale="nominal", label="Gender",
                     labels={1: "Male", 2: "Female", 3: "Other"})

q_gender = sg.SingleChoice(
    "What is your gender?", var=gender,
    display="buttons", required=True,
)
```

---

## `MultiChoice`

Select one or more options. Supports two storage layouts — **array** (one column
holding a list of selected codes) and **wide** (one binary column per option).

```python
class MultiChoice(Question):
    min_answers: int = 1
    max_answers: int | None = None
    exclusive: list[int] = []
    mode: str = "array"               # "array" | "wide"
    choices: list[Option] | None = None
```

| Field | Default | Description |
| :--- | :--- | :--- |
| `min_answers` | `1` | Minimum selections. Once the question is answered, Next is refused below it with "Select at least N more" (the counter under the options says the same); an unanswered question is held only by `required`, so an optional one may be left empty. An `exclusive` answer is complete by itself and is not held by the minimum. |
| `max_answers` | `None` | Maximum selections; in wide mode cannot exceed the number of variables. |
| `exclusive` | `[]` | Codes that clear all other selections when chosen (e.g. "None"). |
| `mode` | `"array"` | `"array"` stores a list of the chosen codes in one variable; `"wide"` stores 1/0 in one variable per option (below). |
| `choices` | `None` | Explicit `Option` list; if `None`, derived from `labels`. |

Pass **`var=`** (a single `Variable`) for array mode, or the keyword-only **`vars=`**
(a non-empty list of `Variable`) to switch to wide mode automatically. Passing both
`var` and `vars` raises `ValueError`.

```python
# Array mode — one column, list of selected codes
hobbies = sg.Variable("hobbies", scale="nominal",
                     labels={1: "Music", 2: "Sport", 3: "Reading", 99: "None"})
q_hobbies = sg.MultiChoice(
    "Which hobbies do you have?", var=hobbies,
    min_answers=1, max_answers=3,
    exclusive=[99],            # picking "None" clears the others
)

# Wide mode — one binary column per source
sources = [sg.Variable(f"src_{n}", scale="nominal", labels={0: "No", 1: "Yes"},
                       label=f"Source {n}") for n in ("tv", "radio", "web")]
q_sources = sg.MultiChoice("Where do you get news from?", vars=sources)
```

In **wide** mode each variable is stored under its own name: `1` when its option is
chosen, `0` when the question is answered and it is not, and nothing at all while the
question is unanswered (unticking every option clears them). Nothing is stored under
the question's id. A condition or a quota therefore reads `src_tv = 1`. The options
come from `choices` when there is one per variable — choice *i* is variable *i*, and
`exclusive` names choice codes, as in array mode — and otherwise from the variables
themselves (label = the variable's label; `exclusive` then names variable names):

```python
none_var = sg.Variable("src_none", scale="nominal", labels={0: "No", 1: "Yes"},
                       label="None of these")
q_sources = sg.MultiChoice(
    "Where do you get news from?", vars=sources + [none_var],
    choices=[sg.Option(1, "TV"), sg.Option(2, "Radio"), sg.Option(3, "Web"),
             sg.Option(99, "None of these")],
    exclusive=[99],
)
```

---

## Other, None and N/A codes

"Other (please specify)", a `SingleChoice`'s "None of the above" and a scale's or a
matrix's "Not applicable" are answers like any other, so they store **codes of the
question's variable** — never a sentinel string in a column of numbers:

| Answer | Code stored | Set by |
| :--- | :--- | :--- |
| Other (please specify) | `-66` (`siamang.core.question.DEFAULT_OTHER_CODE`) | `metadata={"other_code": …}` |
| None of the above (`SingleChoice`) | `-77` (`DEFAULT_NONE_CODE`) | `metadata={"none_code": …}` |
| Not applicable (`LikertScale`, `Matrix`) | the variable's first `missing` value of kind `not_applicable`; the text `"na"` when there is none | the codebook |

The **text typed into Other** is stored apart, under `<variable>_other` (for a
wide `MultiChoice`, `<name or id>_other`): present — `""` if nothing was typed —
exactly while Other is chosen, and removed when the respondent picks something
else. `{label:x}` of an Other answer pipes the text typed.

```python
fruit = sg.Variable("fruit", scale="nominal",
                    labels={1: "Apple", 2: "Pear", 96: "Other", 97: "None of these"})
q_fruit = sg.SingleChoice("Favourite fruit?", var=fruit,
                          choices=[sg.Option(1, "Apple"), sg.Option(2, "Pear")],
                          other_specify=True, none_of_above=True,
                          metadata={"other_code": 96, "none_code": 97})
# answers: {"fruit": 96, "fruit_other": "Kiwi"}  or  {"fruit": 97}
```

`other_code` may name one of the question's own choices: that choice then *is* the
Other option (it gets the text box, and no second "Other" is added). Label every
added code in the codebook — `lint()` reports `ADDED_CODE_WITHOUT_LABEL` for an
unlabelled Other or None code and `NA_STORED_AS_TEXT` for an N/A with no
`not_applicable` code (strict lint). `validate()` refuses a code that is not a number or a string,
a "None of the above" whose code is already an answer's, a question whose choices
already use the *default* Other code, and an Other text key that is another
question's variable or key. A condition may read the Other text
(`fruit_other != ""`). N/A is declared as a missing value so the analysis leaves it
out of means:

```python
sat = sg.Variable("sat", scale="ordinal",
                  labels={1: "1", 2: "2", 3: "3", 4: "4", 5: "5", -1: "Not applicable"},
                  missing=(sg.MissingValue(-1, "Not applicable", "not_applicable"),))
```

Before these codes existed the runtime stored `{"code": "__other__", "text": …}`
for a single answer, `{"selected": […, "__other__"], "otherText": …}` for a
multiple one, `"__none__"` and `"na"`; responses collected then keep those values,
and answers a respondent saved in the browser are converted when they resume.

---

## `LikertScale`

A symmetric ordinal rating scale.

```python
@dataclass(frozen=True, slots=True)
class LikertScale(Question):
    points: int = 5                   # must be >= 2
    left_label: str | None = None
    right_label: str | None = None
    na_option: bool | str = False
```

| Field | Default | Description |
| :--- | :--- | :--- |
| `points` | `5` | Number of scale points. Must be `>= 2`. |
| `left_label` | `None` | Anchor label on the far left (e.g. `"Strongly disagree"`). |
| `right_label` | `None` | Anchor label on the far right (e.g. `"Strongly agree"`). |
| `na_option` | `False` | `True` adds a "Not applicable" choice; a string sets its label. It stores the variable's `not_applicable` missing code, or the text `"na"` when the codebook declares none (see [below](#other-none-and-na-codes)). |

`var` must be a single `Variable` (ideally `ordinal`).

```python
trust = sg.Variable("trust", scale="ordinal", label="Trust in government",
                   labels={1: "No trust", 2: "Low", 3: "Medium", 4: "High", 5: "Full"})

q_trust = sg.LikertScale(
    "How much do you trust the government?", var=trust, points=5,
    left_label="No trust", right_label="Full trust",
    na_option=True,
)
```

---

## `NumericInput`

A continuous numeric value.

```python
@dataclass(frozen=True, slots=True)
class NumericInput(Question):
    display: str = "input"            # "input" | "slider"
    unit: str | None = None
    step: int | float = 1             # must be > 0
```

| Field | Default | Description |
| :--- | :--- | :--- |
| `display` | `"input"` | `"input"` (number box) or `"slider"`. |
| `unit` | `None` | Unit shown next to the field (e.g. `"years"`, `"%"`). |
| `step` | `1` | Increment for sliders/number inputs. Must be `> 0`. |

`var` must be a single `Variable`. If the variable has `valid_range=(min, max)`, the
React runtime forwards it as the input's `min`/`max` (the slider's ends) and enforces it:
a number below or above it shows "Minimum value is *min*" / "Maximum value is *max*"
when the field is left, and Next is refused until it is corrected. An empty optional
field is not checked.

```python
age = sg.Variable("age", scale="ratio", label="Age", valid_range=(18, 99))

q_age = sg.NumericInput(
    "How old are you?", var=age,
    display="input", step=1, unit="years", required=True,
)
```

---

## `OpenText`

Free-form text.

```python
@dataclass(frozen=True, slots=True)
class OpenText(Question):
    multiline: bool = False
    max_chars: int | None = None      # must be > 0 when set
    placeholder: str | None = None
```

| Field | Default | Description |
| :--- | :--- | :--- |
| `multiline` | `False` | Render a multiline `<textarea>` instead of a single line. |
| `max_chars` | `None` | Character limit. Must be `> 0` when set. |
| `placeholder` | `None` | Ghost text shown while the field is empty. |

```python
comments = sg.Variable("comments", scale="nominal")

q_open = sg.OpenText(
    "Anything else you would like to add?", var=comments,
    multiline=True, max_chars=500, placeholder="Optional comments…",
)
```

---

## `Matrix`

A grid of subquestions (rows) sharing a common column scale. Efficient for batteries
of Likert items.

```python
@dataclass(frozen=True, slots=True)
class Matrix(Question):
    var: list[Variable]               # one variable per row; required, non-empty
    subquestions: list[str] | None = None
    column_labels: list[str] | None = None
    na_option: bool | str = False
```

| Field | Default | Description |
| :--- | :--- | :--- |
| `var` | *required* | Non-empty list of `Variable` — one per row. |
| `subquestions` | `None` | Row labels; default to each variable's `label`. |
| `column_labels` | `None` | Column headers; default to the first row variable's value `labels`, in code order. |
| `na_option` | `False` | `True` adds a "Not applicable" column; a string sets its header. A cell stores its row variable's `not_applicable` missing code, or the text `"na"` when the codebook declares none (see [below](#other-none-and-na-codes)). |

```python
def trust_dim(name, label):
    return sg.Variable(name, scale="ordinal", label=label,
                      labels={1: "No trust", 2: "Low", 3: "Medium", 4: "High", 5: "Full"})

q_trust_matrix = sg.Matrix(
    "How much do you trust each of the following?",
    var=[
        trust_dim("trust_govt",   "The government"),
        trust_dim("trust_courts", "The courts"),
        trust_dim("trust_media",  "The press"),
    ],
)
```

Each row is stored under **its own variable** (`trust_govt: 4`), so a `show_if`, a
quota or `{answer:trust_govt}` names the row's variable. A cell stores a **code of the
row variables' codebook**, not the column's position —
`Matrix.columns()` returns the `(code, header)` pairs the runtime uses. Without
`column_labels` the columns are the first row variable's value labels in code order,
so a codebook `{1: …, 5: …, 9: "Refused"}` stores 9 for "Refused" — less the
`not_applicable` code when `na_option` is on, since the N/A column stores it. With
`column_labels`, each header takes the code of the value label with the same text
(when every header names exactly one); else the label in the same position (when
there are as many labels as headers: headers `0` … `10` over labels coded 0 … 10
store 0 … 10); else the same with the codebook's declared missing codes set apart —
a header naming one of them (say "Don't know") takes its code, and the others line
up with the remaining labels, so a labelled N/A −1 or refusal 77 does not shift
`0` … `10`; else 1, 2, 3 … in column order, which is all there is to go on when
the codebook says nothing.

---

## `Ranking`

Sort options into an order of preference (drag-and-drop).

```python
@dataclass(frozen=True, slots=True)
class Ranking(Question):
    max_ranked: int | None = None     # must be > 0 when set
    choices: list[Option] | None = None
```

| Field | Default | Description |
| :--- | :--- | :--- |
| `max_ranked` | `None` | How many items must be ranked (e.g. "rank your top 3"). Must be `> 0`. |
| `choices` | `None` | Explicit `Option` list; if `None`, derived from `labels`. |

`var` must be a single `Variable`.

```python
brands = sg.Variable("brand_rank", scale="ordinal",
                    labels={1: "Acme", 2: "Globex", 3: "Initech"})

q_rank = sg.Ranking("Rank these brands from best to worst", var=brands, max_ranked=3)
```

---

## `MaxDiff`

Best–worst scaling. A few items at a time, and for each set the respondent picks
the best and the worst. Asking people to rate twenty things gets twenty ratings
that all cluster at the top, because nothing forces a choice; here the
trade-off *is* the measurement.

```python
@dataclass(frozen=True, slots=True)
class MaxDiff(Question):
    var: list[Variable]                 # 2 × tasks + 1
    choices: list[Option] | None = None
    per_task: int = 4
    tasks: int = 8
    versions: int = 20
    seed: int | None = None
    best_label: str = "Best"
    worst_label: str = "Worst"
    design: dict | None = None
```

| Field | Default | Description |
| :--- | :--- | :--- |
| `per_task` | `4` | Items shown at once. Must be at least 2 and fewer than the number of items — showing all of them makes the design complete, and nothing is learned from which items met. |
| `tasks` | `8` | Sets one respondent answers. |
| `versions` | `20` | Independent blocks of the design; different respondents get different tasks, so together they cover far more of the item space than any one respondent could sit through. |
| `seed` | `None` | Fixes the design. Left unset, a seed is derived from the question itself, so the design is still the same on every compile. |
| `design` | `None` | A frozen design (`siamang.design.maxdiff_design(...).to_dict()`). Generated from the parameters when absent. |

`var` holds **two variables per task plus one**: best and worst for each task,
then the version of the design the respondent was shown. The version is a
variable rather than bookkeeping because without it the answers cannot be read —
knowing somebody chose item 7 says nothing until you know what 7 was up against.
Each is stored under its own name (`md_t1_best: 3`, `md_version: 12`), like any
other answer.

Items come from the answer variables' labels, the way a matrix takes its columns
from `var[0]`; `choices` overrides them.

```python
items = {1: "Price", 2: "Quality", 3: "Speed", 4: "Support", 5: "Range"}
md = [
    sg.Variable(f"md_t{t}_{side}", scale="nominal", labels=items)
    for t in range(1, 9)
    for side in ("best", "worst")
]
md.append(sg.Variable("md_version", scale="nominal", label="Design version"))

q_md = sg.MaxDiff("Which matters most, and least?", md, per_task=4, tasks=8, seed=7)
```

Reading the answers:

```python
data.report.maxdiff("q_md")            # counting score, utilities, shares
siamang.data.maxdiff.respondent_scores(data, "q_md")   # one score per person
siamang.io.choice.write_maxdiff_choices(data, "q_md", "choices.csv")  # for HB in R
```

On weighted data (`data.with_weight("w")`) every column of the table is
weighted — Shown, Best and Worst are sums of weights, and the utilities come
from a conditional logit on the weighted choices, its weights rescaled to
Kish's effective base so the standard errors are not those of a bigger sample.
The footer names the `Weight` and gives the base as `N respondents (W
weighted)`. The HB export carries no weight column.

---

## `Conjoint`

Choice-based conjoint. Whole products side by side; the respondent picks one.
Asking how important price is gets an answer everybody gives the same way;
showing three products that differ in price *and* in everything else makes the
respondent spend something to get something, and what they gave up is the
measurement.

```python
@dataclass(frozen=True, slots=True)
class Conjoint(Question):
    var: list[Variable]                     # tasks + 1
    attributes: list[Attribute] = []
    alternatives: int = 3
    tasks: int = 10
    versions: int = 20
    seed: int | None = None
    none_label: str | None = None
    design: dict | None = None
```

| Field | Default | Description |
| :--- | :--- | :--- |
| `attributes` | `[]` | What the products vary on. At least two — a trade-off needs two things to trade. |
| `alternatives` | `3` | Products shown per task. |
| `tasks` | `10` | Choices one respondent makes. |
| `versions` | `20` | Independent blocks of the design. |
| `seed` | `None` | Fixes the design; derived from the question when unset. |
| `none_label` | `None` | Adds a "none of these" alternative. It changes what the question measures: with it, shares are of a market including people who buy nothing. |

`var` holds **one variable per task plus one**: which alternative was chosen,
then the version of the design shown. One per task rather than one per attribute
— the answer *is* the choice, and which levels it carried lives in the design.
Each is stored under its own name (`cbc_t1: 2`, `cbc_version: 4`).

```python
attributes = [
    sg.Attribute("brand", [sg.Option(1, "Acme"), sg.Option(2, "Globex")], label="Brand"),
    sg.Attribute("price", [sg.Option(10, "£10"), sg.Option(20, "£20")], label="Price"),
]
cbc = [sg.Variable(f"cbc_t{t}", scale="nominal") for t in range(1, 11)]
cbc.append(sg.Variable("cbc_version", scale="nominal", label="Design version"))

q_cbc = sg.Conjoint("Which would you buy?", cbc, attributes=attributes, seed=7)
```

Reading the answers:

```python
data.report.conjoint("q_cbc")                                   # part-worths + importance
data.report.conjoint_shares("q_cbc", {"Ours": {...}})           # share of preference
siamang.data.conjoint.shares(data, "q_cbc", {"Ours": {...}})    # the same rows, bare
siamang.io.choice.write_conjoint_choices(data, "q_cbc", "cbc.csv")  # for HB in R
```

On weighted data the part-worths — and so the importances and the shares — are
fitted on the weighted choices, and the tables' footers name the `Weight`.

`lint()` refuses a design that cannot be estimated — too few tasks for the
number of levels — before anyone is interviewed, rather than after the model
fails to converge.

---

## `Attribute`

One dimension a conjoint product varies on, and the values it takes. Levels are
`Option`s, so a level may carry an image for the same reason an answer option
may.

```python
@dataclass(frozen=True, slots=True)
class Attribute:
    name: str                       # a plain identifier: it becomes a column
    levels: list[Option] = []       # at least two
    label: str | None = None        # what the respondent reads
```

The **first level is the reference**: its part-worth is zero and every other
level of that attribute is read against it.

---

## `Option`

Use `Option` instead of a plain `{code: label}` mapping when a choice needs
conditional visibility or a media attachment. `Option` is accepted by the `choices=`
field of `SingleChoice`, `MultiChoice`, `Ranking` and `MaxDiff`.

```python
@dataclass(frozen=True, slots=True)
class Option:
    code: Any
    label: str
    show_if: Expression | str | None = None
    hide_if: Expression | str | None = None
    media: Media | None = None
```

| Field | Default | Description |
| :--- | :--- | :--- |
| `code` | *required* | The stored code if chosen. Must match the type used in `Variable.labels`. |
| `label` | *required* | Displayed text; overrides the variable's registered label. Non-empty. |
| `show_if` / `hide_if` | `None` | Per-option visibility condition. |
| `media` | `None` | A single `Media` attachment for this option. |

Option codes within a `choices` list must be unique; duplicates raise `ValueError`.

```python
from siamang.core import Option, Media

q_color = sg.SingleChoice(
    "Pick a colour", var=fav,
    choices=[
        Option(1, "Red",   media=Media("https://cdn.example.com/red.png")),
        Option(2, "Blue",  media=Media("https://cdn.example.com/blue.png")),
        Option(3, "Pink",  hide_if=gender.eq(1)),
        Option(4, "Green", show_if=age.ge(18)),
    ],
)
```

## `Media`

An image, video, or audio attachment for a question (`media=`) or option.

```python
@dataclass(frozen=True, slots=True)
class Media:
    url: str
    kind: str | None = None           # "image" | "video" | "audio"
    alt: str | None = None
    caption: str | None = None
    autoplay: bool = False
    loop: bool = False
    controls: bool = True
```

| Field | Default | Description |
| :--- | :--- | :--- |
| `url` | *required* | URL to the media file. Non-empty. |
| `kind` | `None` | `"image"`/`"video"`/`"audio"`; inferred from the URL extension if omitted. |
| `alt` | `None` | Accessibility text (HTML `alt`). |
| `caption` | `None` | Caption shown beneath the media. |
| `autoplay` | `False` | Auto-play video/audio when visible. |
| `loop` | `False` | Loop playback. |
| `controls` | `True` | Show playback controls. |

`kind` is inferred from the file extension (`png`/`jpg`/… → image, `mp4`/`webm`/… →
video, `mp3`/`wav`/… → audio). A URL **without a recognisable extension** requires
`kind` to be passed explicitly, otherwise construction raises `ValueError`.

```python
from siamang.core import Media

q_clip = sg.SingleChoice(
    "Did you find the clip persuasive?", var=persuasion,
    media=Media("https://cdn.example.com/intro.mp4", caption="Watch before answering."),
)

# Extensionless URL: kind is required
logo = Media("https://cdn.example.com/asset?id=42", kind="image", alt="Brand logo")
```

## See also

- [[Variables and Measurement|Variables-and-Measurement]] — the variables questions bind to.
- [[Pages Blocks and Structure|Pages-Blocks-and-Structure]] — placing questions on pages and in blocks.
- [[Visibility and Branching|Visibility-and-Branching]] — `show_if`, `hide_if`, and `skip_to`.
- [[Quotas]] — capping responses per category.
