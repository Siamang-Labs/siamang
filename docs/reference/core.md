# `siamang.core` — domain model reference

This page is the authoritative reference for every public class and
function in `siamang.core`. Every object is a frozen dataclass (immutable
after construction) unless noted otherwise.

**Quick import:**

```python
import siamang as sg                       # top-level convenience
from siamang.core import (                  # explicit
    Variable, MissingValue, ValidationIssue, VariableMap,
    Expression, VarRef, AND, OR, NOT, compare,
    Question, SingleChoice, MultiChoice, LikertScale,
    NumericInput, OpenText, Matrix, Ranking,
    Page, Block, Option, Media, Quota, Script, FilterRule,
    Questionnaire, LintWarning,
)
```

---

## Variables

### `Variable`

```python
@dataclass(frozen=True, slots=True)
class Variable:
    name: str
    scale: str                                # "nominal" | "ordinal" | "interval" | "ratio"
    label: str | None = None
    labels: dict[Any, str] = {}               # {code: label}
    missing_values: tuple[Any, ...] = ()      # legacy plain-code tuple
    dtype: str | None = None                  # "int" | "float" | "str" | "bool" | "category" | "datetime"
    role: str | None = None                   # "input" | "target" | "weight" | "id" | "grouping" | "derived"
    description: str | None = None
    construct: str | None = None
    source: str | None = None
    valid_range: tuple[Any, Any] | None = None
    missing_labels: dict[Any, str] = {}
    missing: tuple[MissingValue, ...] = ()    # structured missing values
```

The atomic measurement unit of a questionnaire.

**Recommended call style** — pass `scale` as a keyword argument so that
calls remain readable as the codebook grows:

```python
age    = sg.Variable("age",    scale="ratio",   label="Age")
gender = sg.Variable("gender", scale="nominal", label="Gender",
                    labels={1: "Male", 2: "Female"})
```

The positional form `Variable("age", "ratio", …)` also works (both are
just standard dataclass arguments) but the keyword form is what the
manual and cookbook use throughout.

After construction, the following normalisations happen in
`__post_init__`:

- `scale`, `dtype`, `role` are lower-cased and stripped; unknown values
  raise `ValueError`.
- `missing` (structured `MissingValue` objects) is merged with the legacy
  `missing_values` codes and `missing_labels` dict into one canonical
  `missing` tuple.
- `missing_labels` is augmented with labels from the structured
  `missing` entries. Codes appearing only in `missing_labels` (without a
  corresponding `missing_values` entry) raise `ValueError`.
- `valid_range` is enforced to be a 2-tuple ordered `(min, max)`.

**Comparison helpers** — every method returns an `Expression` that can be
attached to `show_if` / `hide_if`:

| Method | Equivalent operator | Example |
|--------|---------------------|---------|
| `var.eq(x)` | `==` | `gender.eq(1)` |
| `var.ne(x)` | `!=` | `gender.ne(0)` |
| `var.gt(x)` | `>` | `age.gt(17)` |
| `var.ge(x)` | `>=` | `age.ge(18)` |
| `var.lt(x)` | `<` | `age.lt(65)` |
| `var.le(x)` | `<=` | `age.le(64)` |
| `var.isin([…])` | `in` | `region.isin([1, 2])` |
| `var.notin([…])` | `not in` | `region.notin([99])` |

`Variable` also implements `__gt__`, `__ge__`, `__lt__`, `__le__`, so
`age > 18` produces the same `Expression` as `age.gt(18)`. (Equality
uses `eq()` explicitly because `__eq__` is reserved for dataclass
identity.)

**Other methods:**

- `structured_missing_values() -> tuple[MissingValue, ...]` — alias for
  `self.missing`.
- `missing_kinds_dict() -> dict[Any, str]` — `{code: kind}` for each
  structured missing entry.
- `is_missing(value) -> bool` — `value in self.missing_values`.

### `MissingValue`

```python
@dataclass(frozen=True, slots=True)
class MissingValue:
    code: Any
    label: str
    kind: str = "system_missing"   # | "refusal" | "dont_know" | "not_applicable" | "not_asked"
```

Structured representation of a missing-value code. `__post_init__`
normalises `kind` (lower-cased, stripped) and rejects unknown kinds or
empty labels.

- `to_dict() -> {"code", "label", "kind"}`
- `MissingValue.from_dict(payload) -> MissingValue`

### `ValidationIssue`

```python
@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str           # e.g. "MISSING_COLUMN", "OUT_OF_RANGE"
    severity: str       # "error" | "warning"
    message: str
    variable: str | None = None
    column: str | None = None
```

A single issue returned by `Variable`/`VariableMap` / `SurveyData`
validators. No invariants.

### `VariableMap`

```python
class VariableMap(dict[str, Variable]):
    ...
```

Dictionary subclass indexed by `Variable.name`. The aggregate registry
used by `Questionnaire(variables=…)`, `SurveyData`, all readers, all
writers.

Methods (all return new objects when stated; raise as noted):

| Method | Returns | Behaviour |
|--------|---------|-----------|
| `add(variable)` | `None` | Adds; raises `KeyError` on duplicate name. |
| `add_many(variables)` | `None` | Repeated `add`. |
| `require(name)` | `Variable` | Raises `KeyError` if not present. |
| `by_scale(scale)` | `list[Variable]` | Case-insensitive filter. |
| `by_role(role)` | `list[Variable]` | Case-insensitive filter. |
| `labels_dict()` | `{name: label}` | Falls back to name if label unset. |
| `value_labels_dict()` | `{name: {code: label}}` | Per-variable code→label. |
| `missing_dict()` | `{name: [code, …]}` | Legacy plain missing-value codes. |
| `missing_labels_dict()` | `{name: {code: label}}` | Labels for missing codes. |
| `missing_kinds_dict()` | `{name: {code: kind}}` | Kinds for structured missing. |
| `validate_frame(frame, raise_on_error=False)` | `list[ValidationIssue]` | Checks dtype, range, label compatibility, role constraints (`weight` numeric, `id` unique). Optionally raises on first error. |
| `to_dict()` | `dict` | Full serialisation. |
| `VariableMap.from_dict(payload)` | `VariableMap` | Round-trip; integer codes inside `labels`/`missing_labels` are re-coerced from string keys (JSON loses int-key information). |

---

## Expressions

### `VarRef`

```python
@dataclass(frozen=True, slots=True)
class VarRef:
    name: str
```

A reference to a variable inside an `Expression` tree.

- `evaluate(answers: dict) -> Any` — `answers.get(self.name)`.
- `variables() -> {self.name}`
- `to_dict() -> {"type": "var", "name": …}`
- `VarRef.from_dict(payload)` — round-trip.
- `str(var_ref)` — `"{name}"` (the SurveyJS interpolation form).

### `Expression`

```python
@dataclass(frozen=True, slots=True)
class Expression:
    op: str             # "=" | "!=" | ">" | ">=" | "<" | "<=" | "in" | "not in" | "and" | "or" | "not" | "raw"
    left: Any = None
    right: Any = None
```

The typed expression DSL. Construction:

```python
sg.compare("age", ">=", 18)            # → Expression(">=", VarRef("age"), 18)
age.ge(18)                              # → identical
age >= 18                               # → identical (Variable.__ge__)

sg.AND(age.ge(18), gender.eq(2))        # n-ary AND (requires ≥ 2 args)
sg.OR(region.eq(1), region.eq(2))       # n-ary OR  (requires ≥ 2 args)
sg.NOT(age.lt(13))                      # negation
age.ge(18) & gender.eq(2)               # __and__
age.ge(18) | age.ge(65)                 # __or__
~ age.isin([99])                        # __invert__
Expression.raw("{age} >= 18")           # opaque SurveyJS string (cannot be evaluated)
```

`Expression` operators:

| Symbol | Family |
|--------|--------|
| `=`, `!=`, `>`, `>=`, `<`, `<=` | comparison |
| `in`, `not in` | membership (right side is a list/tuple/set) |
| `and`, `or`, `not` | logical |
| `raw` | unparsed SurveyJS string (escape hatch) |

Methods:

- `evaluate(answers: dict) -> bool` — evaluates the tree against an
  `{variable_name: value}` mapping. Raises `ValueError` on `raw`
  expressions (they cannot be evaluated in Python).
- `variables() -> set[str]` — every variable name referenced.
- `validate(variables)` — `variables` is either a `Mapping` (uses keys)
  or a `set`; raises `ValueError` if the tree references an unknown
  variable, contains an unsupported operator, or contains a `raw` node.
- `to_dict()` / `Expression.from_dict(payload)` — JSON round-trip.
- `to_surveyjs() -> str` — render to the SurveyJS `{var} op literal`
  string dialect (used by the SurveyJS-based renderer and stored in the
  compiled `SurveySchema`).
- `Expression.raw(text)` (classmethod) — escape hatch for SurveyJS
  strings that the typed DSL cannot express.

### `compare(var_name, op, value) -> Expression`

```python
sg.compare("trust", ">=", 4)
```

Equivalent to `Expression(op, VarRef(var_name), value)`. The recommended
way to build expressions from raw strings (e.g. when the variable name
comes from a config file).

### `AND(*exprs) / OR(*exprs) / NOT(expr) -> Expression`

Left-associative composition helpers. `AND` and `OR` require ≥ 2
expressions (raise `ValueError` otherwise).

---

## Questions

### `Question` (base)

```python
@dataclass(frozen=True, slots=True)
class Question:
    text: str
    var: Variable | list[Variable]
    required: bool = False
    hint: str | None = None
    show_if: Any = None                # Expression | str | None
    hide_if: Any = None                # Expression | str | None
    skip_to: str | None = None         # page or question id
    randomize: bool = False
    other_specify: bool = False
    tag: str | list[str] | None = None
    id: str | None = None              # explicit id (else derived from var)
    name: str | None = None            # output column name (else from id)
    media: Media | list[Media] | None = None
    metadata: dict[str, Any] = {}
```

Rules enforced in `__post_init__`:

- `text` must be non-empty after `.strip()`.
- If `id` is provided it must be non-empty.
- If `name` is provided it must be non-empty.
- If `media` is set, it must be a `Media` or a list of `Media`.

You normally instantiate one of the **subclasses** below, not `Question`
itself.

| Subclass | Selects | Notes |
|----------|---------|-------|
| `SingleChoice` | one code | `display ∈ {"radio", "dropdown", "buttons"}` |
| `MultiChoice` | many codes | `mode ∈ {"array", "wide"}` |
| `LikertScale` | 1…N | `points ≥ 2` |
| `NumericInput` | number | `display ∈ {"input", "slider"}`, `step > 0` |
| `OpenText` | string | `multiline`, `max_chars` |
| `Matrix` | dict | rows are variables, columns are options |
| `Ranking` | ordered list | drag-and-drop ranking |

#### `SingleChoice`

```python
@dataclass(frozen=True, slots=True)
class SingleChoice(Question):
    display: str = "radio"             # "radio" | "dropdown" | "buttons"
    none_of_above: bool = False
    choices: list[Option] | None = None
```

If `choices` is `None` the option list is derived from
`var.labels`. If supplied, the choices override the variable labels and
unlock per-option `show_if` / `hide_if` / `media`. See
[`Option`](#option) below.

#### `MultiChoice`

```python
@dataclass(frozen=True, slots=True, init=False)
class MultiChoice(Question):
    min_answers: int = 1
    max_answers: int | None = None
    exclusive: list[int] = []
    mode: str = "array"                # "array" | "wide"
    choices: list[Option] | None = None

    def __init__(
        self,
        text: str,
        var: Variable | list[Variable] | None = None,
        *,
        vars: list[Variable] | None = None,
        required: bool = False,
        hint: str | None = None,
        show_if: Any = None,
        hide_if: Any = None,
        skip_to: str | None = None,
        randomize: bool = False,
        other_specify: bool = False,
        tag: str | list[str] | None = None,
        id: str | None = None,
        name: str | None = None,
        media: Media | list[Media] | None = None,
        metadata: dict[str, Any] | None = None,
        min_answers: int = 1,
        max_answers: int | None = None,
        exclusive: list[int] | None = None,
        mode: str = "array",
        choices: list[Option] | None = None,
    ) -> None: ...
```

Two modes:

- **array** (default): one `Variable` whose `labels` (or `choices`)
  define the options; the respondent's answer is a list of selected
  codes, stored in a single column.
- **wide**: a list of binary `Variable`s — one column per option. Use
  the keyword-only `vars=[…]` argument; siamang switches `mode="wide"`
  automatically.

Validation:

- Exactly one of `var` / `vars`.
- `min_answers >= 0`; `max_answers >= min_answers` when set.
- In wide mode, `max_answers <= len(var)`.
- `exclusive` is a list of codes that, when chosen, force the answer
  to a single-element list (mutually-exclusive options).

#### `LikertScale`

```python
@dataclass(frozen=True, slots=True)
class LikertScale(Question):
    points: int = 5
    left_label: str | None = None
    right_label: str | None = None
    na_option: bool | str = False
```

A 2-to-N point ordinal scale. `na_option=True` shows a default
"Not applicable" choice; pass a string to override the label.

#### `NumericInput`

```python
@dataclass(frozen=True, slots=True)
class NumericInput(Question):
    display: str = "input"             # "input" | "slider"
    unit: str | None = None            # rendered next to the input
    step: int | float = 1
```

If the bound `Variable` defines `valid_range=(min, max)`, the React
runtime forwards it as the input's `min` / `max` constraint.

#### `OpenText`

```python
@dataclass(frozen=True, slots=True)
class OpenText(Question):
    multiline: bool = False
    max_chars: int | None = None
    placeholder: str | None = None
```

`max_chars` must be `> 0` when set.

#### `Matrix`

```python
@dataclass(frozen=True, slots=True)
class Matrix(Question):
    var: list[Variable]                # one variable per row (required, non-empty)
    subquestions: list[str] | None = None
    column_labels: list[str] | None = None
    na_option: bool | str = False
```

Each row is a variable; columns share the same `Variable.labels`
(usually a Likert scale). Use `column_labels` to override the labels in
the column header.

#### `Ranking`

```python
@dataclass(frozen=True, slots=True)
class Ranking(Question):
    max_ranked: int | None = None      # cap the number of items the user must rank
    choices: list[Option] | None = None
```

### Question helpers

- `question_variable_names(q) -> list[str]` — names of every `Variable`
  bound to the question.
- `question_fallback_id(q) -> str` — derives an id (`q.id` if set;
  otherwise `q.name`; otherwise `"matrix_<var0>"` or `"multi_<var0>"`
  for those types; otherwise the bound variable's name).
- `question_output_name(q) -> str` — output column name
  (`q.name or question_fallback_id(q)`).

---

## Pages and blocks

### `Page`

```python
@dataclass(frozen=True, slots=True)
class Page:
    name: str
    title: str | None = None
    items: list[Question | Block] = []
    next_if: list[tuple[str, str]] = []        # [(condition, next_page), …]
    default_next: str | None = None
    randomize_blocks: bool = False
    show_if: Expression | str | None = None
    hide_if: Expression | str | None = None

    def flatten_questions(self) -> list[Question]: ...
```

One screen of the survey. Navigation logic:

| Field | Used for |
|-------|----------|
| `show_if` / `hide_if` | Per-page visibility gate. |
| `next_if` | Conditional next-page targets evaluated in order. |
| `default_next` | Fallback next page if no `next_if` matches. |
| `randomize_blocks` | Shuffle the order of immediate `Block` items. |

### `Block`

```python
@dataclass(frozen=True, slots=True)
class Block:
    title: str | None = None
    items: list[Question | Block] = []
    randomize: bool = False
    show_if: Expression | str | None = None
    hide_if: Expression | str | None = None

    def flatten_questions(self) -> list[Question]: ...
```

A named, hide-able, randomisable container for questions and nested
blocks. When a page mixes blocks with loose questions, the compiler
wraps the loose ones into a synthetic untitled block so per-block
visibility rules survive serialisation.

### `Option`

```python
@dataclass(frozen=True, slots=True)
class Option:
    code: Any
    label: str
    show_if: Expression | str | None = None
    hide_if: Expression | str | None = None
    media: Media | None = None
```

An answer choice for `SingleChoice`, `MultiChoice`, or `Ranking`.
Provide it via the question's `choices=[Option(...), …]` argument. The
`code` becomes the value stored in the dataset; `label` is what the
respondent sees.

- `__post_init__` rejects empty labels and non-`Expression`/`str`
  conditions.
- `to_dict()` returns `{"code", "label", "show_if"?, "hide_if"?, "media"?}`.

### `Media`

```python
@dataclass(frozen=True, slots=True)
class Media:
    url: str
    kind: str | None = None            # "image" | "video" | "audio" (inferred from extension if None)
    alt: str | None = None
    caption: str | None = None
    autoplay: bool = False
    loop: bool = False
    controls: bool = True
```

A media attachment for a question (`Question.media = Media(...)` — also
accepts a list) or an option (`Option.media = Media(...)`).

- `kind` defaults from the URL extension (`jpg/jpeg/png/gif/webp/svg/avif`
  → `image`; `mp4/webm/mov/m4v/ogv` → `video`; `mp3/wav/ogg/m4a/flac` →
  `audio`). If the URL has no extension and `kind` is unset, the
  constructor raises `ValueError` — pass `kind=` explicitly.
- `url` must be non-empty.
- `to_dict()` / `Media.from_dict(payload)` round-trip.

---

## Quotas, scripts, filters

### `Quota`

```python
@dataclass(frozen=True, slots=True)
class Quota:
    variable: str          # variable name to count
    target_value: Any      # the cell value to match
    limit: int             # close the cell when this many responses match

    def reached(self, answers: list[dict[str, Any]]) -> bool: ...
```

Attach quotas to a `Questionnaire` via the `quota` deploy option (passed
into `compile_questionnaire`). When a respondent's answers would match a
filled quota cell, the backend rejects their submission with
`status="quota_full"` and the frontend shows the closed screen.

### `Script`

```python
@dataclass(frozen=True, slots=True)
class Script:
    code: str                          # raw JavaScript source
    trigger: str = "onPageEnter"       # see triggers below
    name: str | None = None
    target: str | None = None          # page name or question id (scopes the script)
    context: dict[str, Any] = {}
    sandbox: bool = True
```

Triggers:

| Trigger | When the snippet runs |
|---------|----------------------|
| `onInit` | Once, before the first page |
| `onPageEnter` | A page becomes visible |
| `onPageExit` | The respondent leaves a page |
| `onQuestionShow` | A question's `show_if` resolves to true |
| `onAnswer` | An answer changes (debounced) |
| `onSubmit` | Just before the final submission POST |
| `onRandomize` | Survey requests randomisation |

Available globals inside the snippet:

| Name | Provides |
|------|----------|
| `answers` | mutable `{variable: value}` map |
| `utils` | `shuffle`, `sample`, `clamp`, `debounce`, `now`, `formatDate` |
| `api` | `get(url)`, `post(url, data)` |
| `context` | merged `Script.context` + caller context |

Pre-baked factories (each returns a `Script`):

```python
Script.randomize_options(question_id, seed=None)
Script.randomize_pages()
Script.validate_fields_match(field_a, field_b, message="Fields do not match.")
Script.timed_question(question_id, seconds=30)
```

Also: `Script.to_dict()` — JSON serialisation embedded in the React
payload.

### `FilterRule`

```python
@dataclass(frozen=True, slots=True)
class FilterRule:
    predicate: Callable[[dict[str, Any]], bool]
    description: str | None = None

    def evaluate(self, answers: dict[str, Any]) -> bool: ...
```

A predicate-based visibility/branching rule for pipelines that need
custom Python logic during simulation or backend-side filtering. Not
serialisable to the frontend (use `Expression` for that).

---

## Questionnaire

```python
@dataclass(frozen=True, slots=True)
class Questionnaire:
    title: str
    blocks: list[Question | Block] = []
    pages: list[Page] = []
    deadline: datetime | None = None
    variables: VariableMap | None = None
    scripts: list[Script] = []
```

The aggregate root. Use **either** `pages` (recommended — explicit names,
navigation, visibility) **or** `blocks` (single implicit page). Mixing
both raises `ValueError`.

### Methods

| Method | Behaviour |
|--------|-----------|
| `all_questions() -> list[Question]` | Flattens pages and blocks into a single ordered list. |
| `preview() -> str` | One-line summary (`"Questionnaire<…> with N questions"`). |
| `validate(strict=False)` | Comprehensive structural & logical checks. See [Validation](#validation) below. Raises `ValueError` on failure. |
| `lint(level="basic"\|"strict") -> list[LintWarning]` | Non-fatal heuristics (empty pages, redundant `default_next`, unused variables, etc.). |
| `validate_for_export(target="surveyjs")` | Runs `validate()` plus a tighter check that every `show_if`/`hide_if` expression renders to a SurveyJS-allowed token set. |
| `compile(**options) -> SurveySchema` | Convenience wrapper around `siamang.frontend.compiler.compile_questionnaire`. |
| `deploy(backend="local", frontend="local", *, backend_kwargs=None, frontend_kwargs=None, **options) -> DeployResult` | Provision + build + publish. See [`reference/deploy.md`](deploy.md). |
| `simulate(n=100, seed=42) -> SurveyData` | Generate synthetic responses. |
| `collect()` | Always raises `NotImplementedError`. Use `survey.deploy(...).collect()` instead. |
| `to_dict() -> dict` | Serialise to a JSON-friendly structure. |

### Validation

`Questionnaire.validate(strict=False)` enforces:

1. **Unique question identifiers** (after the `id`/`name`/variable
   fallback chain) and that every `skip_to` target resolves to a known
   page or question.
2. **Unique page names** (when using `pages`), and a navigation graph
   that is acyclic and where every page is reachable.
3. **Scripts** — `trigger` ∈ the seven valid values, and any `target`
   resolves to a known question id or page name.
4. **No duplicate variables** across questions; when an explicit
   `variables` registry is provided, every bound `Variable` must match
   the registered instance exactly.
5. **Every `show_if` and `hide_if` expression** on pages, blocks,
   questions, and options:
   - is a `str` or an `Expression`,
   - references only known variables,
   - evaluates without raising against a probe `{var: 0}` map (catches
     incompatible operator/operand pairs).

If `strict=True`, the method also runs `lint(level="strict")` and
raises if any returned `LintWarning` has `severity="error"`.

### `LintWarning`

```python
@dataclass(frozen=True, slots=True)
class LintWarning:
    code: str          # e.g. "EMPTY_PAGE", "UNUSED_VARIABLE"
    severity: str      # "warning" | "error"
    message: str
    location: str | None = None
```

---

## Serialisation helpers

`siamang.core.serialization` provides `question_to_dict(question) ->
dict` — used by the SurveyJS-bound compiler and exposed for inspection.
The dict mirrors the SurveyJS schema convention (`type`, `name`,
`title`, `isRequired`, `choices`, …) plus siamang extensions for media
and per-option visibility.
