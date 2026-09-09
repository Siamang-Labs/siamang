# `siamang.codegen` reference

`siamang.codegen` turns a questionnaire document (see
[`siamang.model`](model.md)) into the Python file a researcher would have
written by hand.

```python
from siamang.codegen import generate_questionnaire

code = generate_questionnaire(document)          # dict -> str
Path("questionnaire.py").write_text(code)
```

The generated module defines `survey` (a `Questionnaire`) and, when the
document carries compiler settings, quotas or a theme, `options` — the two
names `siamang validate`, `siamang preview`, `siamang deploy` and the
platforms read. Running `siamang.model.to_document` over the executed module
gives the original document back, and generating twice gives the same bytes.

---

## What the file looks like

Sections, in order, each object preceded by a `# studio: …` marker so a
builder can map lines back to document objects:

1. **Docstring** — the title plus an explanatory paragraph (see `header`).
2. **Imports** — `import siamang as sg` and only what is used:
   `from siamang import Media, MissingValue, Option, Quota`,
   `from siamang.core import ContentPage, …`, `from siamang.frontend import UIConfig`,
   `from datetime import datetime`.
3. **Variables** — `age = sg.Variable("age", scale="ratio", …)` in document
   order. Missing values are written as `missing_values=[9], missing_labels={…}`
   when every kind is `system_missing`, and as `missing=(MissingValue(…, kind=…),)`
   otherwise.
4. **Questions** — `q_age = sg.NumericInput("How old are you?", var=age, …, id="q_age")`
   in reading order. Only fields that differ from the engine defaults are
   written; `id=` always is. Wide `MultiChoice` uses `vars=[…]`.
5. **Pages** — `page_screener = sg.Page(name=…, items=[…], next_if=[…])`;
   `content`, `disqualification`, `final` and `redirect` pages use the
   factories (`FinalPage("thanks", …)`) when their fields fit, `sg.Page(kind=…)`
   otherwise. Blocks are inlined.
6. **Scripts** — `scripts = [sg.Script.timed_question("q_aware", seconds=45), …]`;
   custom scripts are `sg.Script(name=…, trigger=…, code="""…""")`.
7. **Questionnaire** — `survey = sg.Questionnaire(title=…, pages=[…], scripts=scripts, deadline=…)`.
   When the document registers variables no question asks, a `codebook`
   `VariableMap` is built and passed as `variables=`.
8. **Options** — `options = {"description": …, "quota": [Quota(…)], "ui": UIConfig(…)}`.

### Conditions

| Document | Code |
|----------|------|
| `{op: "=", left: var, right: v}` | `age.eq(v)`; likewise `.ne .gt .ge .lt .le` |
| `in`, `not in` | `region.isin([1, 2])`, `region.notin([…])` |
| `and` / `or` of two simple comparisons (or their negation) at the top of a condition | `age.ge(18) & ~region.eq("south")` |
| any other `and` / `or` / `not` | `sg.AND(a, b, c)` (left-nested chains are flattened), `sg.OR(…)`, `sg.NOT(…)` |
| a `raw` string condition | the string itself, `"{age} >= 18"` |
| a comparison whose left side is not a variable | `sg.Expression(">", 3, sg.VarRef("age"))` |

### Identifiers

Variable names become identifiers as they are (`age`), sanitized when they
are not valid Python (`1st` → `v_1st`, `class` → `class_var`, `sg` → `sg_var`).
Question ids that would collide with a variable get a `q_` prefix; pages are
`page_<name>`. Names are assigned in document order, so they are stable
between generations.

---

## API

### `generate_questionnaire(document, *, header=None, format=True) -> str`

Validates the document against the JSON Schema first (`DocumentError` on
failure). `header` replaces the explanatory paragraph of the module
docstring; `{schema}` in it is substituted with the document's
`schema_version`. With `format=True` the output goes through `ruff format`
(`--isolated --line-length 100`); if ruff is not installed the generator's
own layout is returned — valid code, laid out the same way in almost every
case, but not guaranteed byte-identical to the formatted form.

Install ruff with the extra: `pip install "siamang[codegen]"`.

### `format_source(code) -> str`

The `ruff format` pass on its own. Raises `FormatterUnavailable` when ruff is
missing.

### `CODEGEN_VERSION`

`"1.0"`. Platforms store it next to generated files; a document generated
under a different version may format differently and is not regenerated
retroactively.

---

## CLI

```bash
siamang codegen questionnaire.json [-o questionnaire.py] [--no-format]
```

Writes to stdout by default. The result passes `siamang validate` and
`ruff check` (the engine's own rule set) and is a fixed point of
`ruff format`.
