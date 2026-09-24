# `siamang.model` reference

`siamang.model` turns a questionnaire into a plain JSON document and back.
The document is what a graphical survey builder stores and edits; the Python
file is what researchers get. Both describe the same survey, field for field.

```python
from siamang.model import to_document, from_document, validate_document, dumps

doc = to_document(survey, options)      # Questionnaire (+ options dict) -> dict
validate_document(doc)                  # JSON Schema check, raises DocumentError
loaded = from_document(doc)             # dict -> LoadedSurvey
loaded.survey.validate()
schema = loaded.survey.compile(**loaded.options)
print(dumps(doc))                       # canonical text form
```

The two functions are inverse of each other:

- `from_document(to_document(survey, options))` compiles to the same
  `SurveySchema` as `survey` itself, and
- `to_document(loaded.survey, loaded.options)` returns the document unchanged.

---

## Document layout (`schema_version` 1.0)

| Key | Content |
|-----|---------|
| `schema_version` | `"1.0"` |
| `title` | Questionnaire title. |
| `options` | Compiler settings from the module-level `options` dict: `language`, `description`, `completion_text`, `show_progress`, `allow_back`, `one_question_per_page`, `max_responses`, `metadata`. Only keys that were set. |
| `deadline` | ISO 8601 datetime or `null`. |
| `variables` | `{name: Variable}` in order of first use; variables that are only in the `VariableMap` registry come last. |
| `pages` | `[Page]`. A questionnaire built with `blocks=` is paged the way the compiler pages it. |
| `quotas` | `[{variable, target_value, limit}]` from `options["quota"]`. |
| `scripts` | Library scripts by name and parameters, everything else verbatim (see below). |
| `ui` | `UIConfig` fields that differ from the defaults (from `options["ui"]`). |
| `layout` | Optional, builder-owned, ignored by the engine. |

### Variable

```json
{
  "scale": "ordinal",
  "label": "Trust: Acme",
  "labels": [{"code": 1, "label": "No trust"}, {"code": 9, "label": "Refused"}],
  "missing": [{"code": 9, "label": "Refused", "kind": "system_missing"}],
  "valid_range": [16, null],
  "dtype": "int", "role": "input", "description": "…", "construct": "…", "source": "…"
}
```

`labels` is a list so that codes keep their type (`1` vs `"1"`) and their
order; the object form `{"1": "No trust"}` is accepted as shorthand, as are
`missing_values` / `missing_labels`. `to_document` always writes the list and
the structured `missing`.

### Page, Block, Question

A page carries `name`, optional `kind` (`content`, `disqualification`,
`final`, `redirect`), `title`, `body`, `redirect_url`, `redirect_delay`,
`items`, `show_if`, `hide_if`, `next_if` (`[{condition, target}]`),
`default_next` and `randomize_blocks`. Structural booleans (`randomize_blocks`,
a block's `randomize`) appear only when true.

Items are `{"type": "Block", …}` or a question whose `type` is the engine
class name (`SingleChoice`, `MultiChoice`, `LikertScale`, `NumericInput`,
`OpenText`, `Matrix`, `Ranking`). A question always has `type`, `id`, `text`
and `var` (a variable name, or a list of names for `Matrix` and wide
`MultiChoice`); every other dataclass field is written explicitly unless it
is `None` or empty, so a stored document keeps its meaning even if an engine
default changes later. `id` is the question's own `id` or, when it has none,
the same fallback id the compiler uses.

### Conditions

`show_if`, `hide_if`, option gates and `next_if` conditions are either the
`Expression` AST as written by `Expression.to_dict()`:

```json
{"type": "expression", "op": "and",
 "left":  {"type": "expression", "op": ">=", "left": {"type": "var", "name": "age"}, "right": 18},
 "right": {"type": "expression", "op": "in", "left": {"type": "var", "name": "region"}, "right": [1, 2]}}
```

or a plain-string condition kept as text: `{"type": "raw", "text": "{age} >= 18"}`.
A `set` operand is written as a list in the order the compiler renders it.

### Scripts

A script made by one of the `Script` factories is stored by what it does —
`{"type": "timed_question", "question": "q_aware", "seconds": 45}`,
`{"type": "randomize_options", "question": "q1", "seed": "…"}`,
`{"type": "randomize_pages"}`,
`{"type": "validate_fields_match", "field_a": "…", "field_b": "…", "message": "…"}`
— and regenerated from the current engine on load. Detection is exact: the
factory, called with the recovered parameters, must reproduce the script
field for field; a hand-edited script becomes
`{"type": "custom", "name", "trigger", "target", "code", "context", "sandbox"}`.

---

## API

### `to_document(survey, options=None, *, layout=None, on_warning=None) -> dict`

Raises `DocumentError` for anything the format cannot hold: a callable
condition, a non-JSON value in `metadata`, an `options["quota"]` that is not a
list of `Quota`. Conversions that keep the compiled survey identical but
change its shape — a `blocks=` questionnaire becoming pages, an `options` key
the document does not carry (`runtime`, say) — are passed to `on_warning`.

### `from_document(document) -> LoadedSurvey`

Rebuilds the engine objects. `LoadedSurvey` has `survey` (a `Questionnaire`
with a `VariableMap` registry of every document variable), `options` (ready
for `compile(**options)` / `deploy(**options)` / `validate_options`; contains
`quota` as `Quota` objects and `ui` as a `UIConfig` when defined), `layout`
and `schema_version`; `quotas` and `ui` are convenience properties. Only the
structure is checked — a question naming an unknown variable, an unknown
field — with the location in the message (`question 'q_age': step must be > 0`).
Run `survey.validate()` and `survey.lint()` on the result as for any survey.

### `validate_document(document) -> None`

Checks the document against the JSON Schema
(`siamang/schemas/questionnaire-1.0.json`, draft 2020-12; `load_schema()`
returns it). Raises `DocumentError` naming the first offending location:
`pages/0/items/2/points: 1 is less than the minimum of 2`. The schema file is
generated from the dataclasses by `scripts/gen_document_schema.py` and is
meant to be reused by non-Python consumers.

### `import_module(path, attribute="survey") -> ImportResult`

Executes a questionnaire module (like `siamang validate` does) and returns
`ImportResult(document, warnings)`. This is what `siamang model import` runs.

### `import_qsf(payload) -> QsfImportResult`, `import_qsf_file(path)`

Converts a Qualtrics Survey Format export (the JSON of "Export survey") into
a document without touching Qualtrics: questions, choices with recodes,
"other" entries (the text-entry choice stays a choice and becomes the Other
option: `other_specify` with `metadata.other_code` set to its recode),
forced response, randomization, display logic on answers,
page breaks, the block order of the survey flow, branches (page `show_if`)
and end-of-survey elements inside branches (disqualification pages).
`QsfImportResult(document, warnings, skipped)`: `skipped` lists, per
question or flow element, what the format cannot hold and why (constant
sum, side-by-side, loop & merge, embedded data, quotas, logic on embedded
fields …); `warnings` lists what was transferred approximately (a block
randomizer, advanced randomization). A multi-select whose choices are
tested by logic is stored wide — one yes/no variable per choice, as
Qualtrics exports it, with the choices kept beside them (choice i on
variable i, so its exclusive answers and a text-entry choice still work) —
so the logic keeps working; other multi-selects keep one array variable.

### `import_lss(text) -> LssImportResult`, `import_lss_file(path)`

Converts a LimeSurvey survey structure export (the XML of "Export survey
structure", `.lss`, LimeSurvey 3 to 6) into a document: list, dropdown,
yes/no, gender, 5-point, multiple choice (subquestions as choices),
numerical (with sliders and ranges), multiple numerical, short/long text,
multiple short text, arrays (flexible labels and the fixed 5/10-point,
yes/no/uncertain, increase/same/decrease scales), ranking and text
displays; mandatory, "other", answer order, choice randomization, the
survey format (one page per group or per question), welcome and end texts,
back button, progress bar, language, question relevance (ExpressionScript
comparisons joined with and/or) and group relevance, legacy conditions
when a question carries no relevance equation. `LssImportResult(document,
warnings, skipped)` has the same shape as the Qualtrics result: `skipped`
lists arrays dual scale/numbers/texts, equations, file uploads, quotas,
assessments, validation regexes, comment fields and relevance the
expression language cannot express (functions, arithmetic); `warnings`
lists approximate transfers (a date question as free text, a
multilingual survey reduced to one language).

### `import_surveyjs(payload) -> SurveyJsImportResult`, `import_surveyjs_file(path)`, `looks_like_surveyjs(payload)`

Converts a SurveyJS survey definition (the JSON of the Survey Creator) into
a document: radiogroup / dropdown / imagepicker, checkbox / tagbox, boolean,
rating, text (number and range inputs, min/max, length), comment,
multipletext, matrix and single-column matrixdropdown, ranking, html;
panels are flattened (a randomized or conditional panel becomes a Block),
`isRequired`, "other" and "none" items, `choicesOrder`, `questionsOrder`,
`visibleIf` on questions, panels and pages (=, <>, <, <=, >, >=,
contains / notcontains, anyof, and / or / not), locale, back button,
progress bar, `completedHtml`, `navigateToUrl`. `skipped` lists file and
signature questions, dynamic panels and matrices, expressions, triggers,
calculated values, validators the format lacks and `visibleIf` it cannot
express (empty / notempty, allof, functions). `looks_like_surveyjs` tells a
SurveyJS JSON (pages of `elements`) from a questionnaire document (pages of
`items`), so a caller can route a `.json` upload.

### `dumps(document) -> str`, `loads(text) -> dict`

Canonical text form: two-space indent, keys in document order, UTF-8 as is,
trailing newline. Two runs over the same survey give the same bytes.

### `migrate(document) -> dict`

Brings a document written by an older engine up to the current
`schema_version`. There is one version so far; the function exists so
callers can route every document they load through it.

---

## CLI

```bash
siamang model import questionnaire.py [-o questionnaire.json] [--attribute survey]
siamang model import survey.qsf [-o questionnaire.json]
siamang model import survey.lss [-o questionnaire.json]
siamang model import survey.surveyjs.json [-o questionnaire.json]
siamang model check questionnaire.json [--strict]
```

`import` writes the document (stdout by default) and prints conversion
warnings on stderr; a `.qsf` (Qualtrics), `.lss` (LimeSurvey) or SurveyJS `.json` export is converted and
everything the format cannot hold is printed as `[skipped]` lines. `check` runs the JSON Schema, rebuilds the survey,
`validate()`, `validate_options()` and `lint()` — the same output and exit
codes as `siamang validate`, for a document instead of a module.
