# `siamang.core` — Core API Reference

This document provides the authoritative, comprehensive API reference for all public classes and functions within the `siamang.core` package. The `siamang` library is designed as a research-as-code framework for sociological surveys [1]. It enforces strict type safety, automatic data schema validation, and seamless integration between Python-defined surveys and their web-based deployments [2].

All classes documented on this page are implemented as frozen Python dataclasses, meaning they are immutable after instantiation. This architectural choice ensures that survey definitions remain side-effect free, thread-safe, and deterministic across compilation, simulation, and analysis phases.

```python
import siamang as sg
from siamang.core import (
    Variable, MissingValue, ValidationIssue, VariableMap,
    Expression, VarRef, AND, OR, NOT, compare,
    Question, SingleChoice, MultiChoice, LikertScale,
    NumericInput, OpenText, Matrix, Ranking,
    Page, Block, Option, Media, Quota, Script, FilterRule,
    Questionnaire, LintWarning,
)
```

---

## Variables and Metadata

In sociological and survey research, variables represent the atomic units of measurement [3]. A variable binds a data column to a specific measurement scale, data type, logical role, and metadata (such as value labels and missing value definitions).

### `Variable`

The `Variable` class represents a single question's measurement or an analytical dimension. It is used to validate collected responses, generate database schemas, and facilitate statistical analyses.

#### Properties

| Property | Type | Default | Description & Allowed Values |
| :--- | :--- | :--- | :--- |
| `name` | `str` | *Required* | The unique identifier of the variable. Must be non-empty and should conform to standard database column naming conventions (lowercase alphanumeric and underscores). |
| `scale` | `str` | *Required* | The level of measurement. Allowed values are: `"nominal"`, `"ordinal"`, `"interval"`, or `"ratio"`. Case-insensitive. |
| `label` | `str \| None` | `None` | A human-readable label or short description of the variable, often used as the variable label in statistical packages like SPSS or Stata. |
| `labels` | `dict[Any, str]` | `{}` | A mapping of valid category codes to their textual labels (e.g., `{1: "Yes", 0: "No"}`). |
| `missing_values` | `tuple[Any, ...]` | `()` | A legacy tuple of plain codes representing missing responses. Normalized in `__post_init__` into the `missing` property. |
| `dtype` | `str \| None` | `None` | The physical data type. Allowed values are: `"int"`, `"float"`, `"str"`, `"bool"`, `"category"`, or `"datetime"`. If omitted, it is inferred during validation. |
| `role` | `str \| None` | `None` | The analytical role of the variable. Allowed values are: `"input"`, `"target"`, `"weight"`, `"id"`, `"grouping"`, or `"derived"`. |
| `description` | `str \| None` | `None` | A long-form textual description of what this variable measures, its context, or historical origin. |
| `construct` | `str \| None` | `None` | The latent psychological or sociological construct being measured (e.g., `"trust_in_institutions"`). |
| `source` | `str \| None` | `None` | The source of the question wording or variable design (e.g., `"ESS Wave 10"`). |
| `valid_range` | `tuple[Any, Any] \| None` | `None` | A 2-item tuple representing the inclusive minimum and maximum allowed values `(min, max)`. |
| `missing_labels` | `dict[Any, str]` | `{}` | A dictionary mapping missing value codes to their descriptions. |
| `missing` | `tuple[MissingValue, ...]` | `()` | A tuple of structured `MissingValue` instances defining the missing codes, labels, and kinds. |

#### Methods

* **`missing_kinds_dict() -> dict[Any, str]`**:
  Returns a dictionary mapping missing value codes to their `kind` string (e.g., `{98: "dont_know", 99: "refusal"}`).
* **`structured_missing_values() -> tuple[MissingValue, ...]`**:
  Returns the canonical tuple of `MissingValue` objects, resolving legacy fields if necessary.
* **`is_missing(value: Any) -> bool`**:
  Returns `True` if the provided value matches any registered missing value code.

#### Comparison Helpers

To build conditional routing and visibility expressions, `Variable` instances provide helper methods that return `Expression` trees:

| Method | Equivalent Operator | Example Code |
| :--- | :--- | :--- |
| `var.eq(value)` | `==` | `gender.eq(1)` |
| `var.ne(value)` | `!=` | `gender.ne(1)` |
| `var.gt(value)` | `>` | `age.gt(18)` |
| `var.ge(value)` | `>=` | `age.ge(18)` |
| `var.lt(value)` | `<` | `age.lt(65)` |
| `var.le(value)` | `<=` | `age.le(65)` |
| `var.isin(list)` | `in` | `region.isin([1, 2, 3])` |
| `var.notin(list)` | `not in` | `region.notin([99])` |

The `Variable` class also overloads Python's comparison operators (`>`, `>=`, `<`, `<=`), allowing expressions to be written naturally as `age >= 18`. Explicit equality (`==`) cannot be overloaded because it is reserved for dataclass structural identity; therefore, `var.eq(value)` must be used.

---

### `MissingValue`

The `MissingValue` class provides a structured representation of non-substantive responses (e.g., refusals, don't know, not applicable). Distinguishing between different types of missing data is a core requirement for high-quality sociological analysis [4].

#### Properties

| Property | Type | Default | Description & Allowed Kinds |
| :--- | :--- | :--- | :--- |
| `code` | `Any` | *Required* | The value stored in the database representing this missing state (typically an integer like `9`, `99`, or `-1`). |
| `label` | `str` | *Required* | The human-readable description of the missing state (e.g., `"Don't know"`). |
| `kind` | `str` | `"system_missing"` | The classification of the missing value. Must be one of: `"refusal"`, `"dont_know"`, `"not_applicable"`, `"not_asked"`, or `"system_missing"`. |

---

### `VariableMap`

A `VariableMap` is a specialized dictionary subclass that indexes `Variable` objects by their `name` property. It acts as the centralized registry for all variables in a survey and provides comprehensive validation for pandas DataFrames.

#### Methods

* **`add(variable: Variable) -> None`**:
  Registers a new variable. Raises a `KeyError` if a variable with the same name is already registered.
* **`add_many(variables: list[Variable]) -> None`**:
  Convenience method to register multiple variables sequentially.
* **`require(name: str) -> Variable`**:
  Retrieves a variable by name. Raises a `KeyError` if the variable is not found.
* **`by_scale(scale: str) -> list[Variable]`**:
  Returns all registered variables matching the specified scale (case-insensitive).
* **`by_role(role: str) -> list[Variable]`**:
  Returns all registered variables matching the specified role (case-insensitive).
* **`labels_dict() -> dict[str, str]`**:
  Returns a dictionary mapping variable names to their `label` strings.
* **`value_labels_dict() -> dict[str, dict[Any, str]]`**:
  Returns a nested dictionary mapping variable names to their category code labels.
* **`missing_dict() -> dict[str, list[Any]]`**:
  Returns a dictionary mapping variable names to a list of their missing codes.
* **`missing_labels_dict() -> dict[str, dict[Any, str]]`**:
  Returns a dictionary mapping variable names to a dictionary of their missing value labels.
* **`missing_kinds_dict() -> dict[str, dict[Any, str]]`**:
  Returns a dictionary mapping variable names to a dictionary of their missing value kinds.
* **`to_dict() -> dict[str, dict[str, Any]]`**:
  Serializes the entire variable map to a nested dictionary representation.
* **`validate_frame(frame: pd.DataFrame, raise_on_error: bool = False) -> list[ValidationIssue]`**:
  Validates a pandas DataFrame against the registered variable schemas. It checks for:
  * Missing columns for required variables.
  * Data type compatibility (e.g., ensuring numeric columns contain numeric data).
  * Out-of-range values based on `valid_range`.
  * Category code consistency based on defined `labels` and `missing_values`.
  * Role-specific constraints (e.g., ensuring an `"id"` column has unique values, and a `"weight"` column contains positive numbers).

---

## Expressions and Branching Logic

Conditional branching and item visibility are essential for modern web surveys. Siamang provides a typed Domain Specific Language (DSL) to represent logical expressions. These expressions can be evaluated in Python (e.g., during survey simulation) and are compiled into native JavaScript functions for execution in the React frontend bundle [2].

### `Expression`

An `Expression` represents a logical condition or comparison.

#### Properties

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `op` | `str` | *Required* | The logical or comparison operator. Allowed operators: `"="`, `"!="`, `">"`, `">="`, `"<"`, `"<="`, `"in"`, `"not in"`, `"and"`, `"or"`, `"not"`, or `"raw"`. |
| `left` | `Any` | `None` | The left-hand operand (usually a `VarRef` or nested `Expression`). |
| `right` | `Any` | `None` | The right-hand operand (usually a literal value, a list of values, or a nested `Expression`). |

#### Methods

* **`evaluate(answers: dict[str, Any]) -> bool`**:
  Evaluates the expression against a dictionary of current answers. Returns a boolean value. Throws a `ValueError` if the expression contains a `"raw"` operator, as raw expressions cannot be safely evaluated in Python.
* **`variables() -> set[str]`**:
  Returns a set of all variable names referenced within the expression tree.
* **`to_surveyjs() -> str`**:
  Compiles the expression into a SurveyJS-compatible expression string (e.g., `"{age} >= 18"`).
* **`to_dict() -> dict[str, Any]`**:
  Serializes the expression tree to a JSON-compatible dictionary.
* **`validate(variables: set[str] | Mapping[str, Any]) -> None`**:
  Validates that all variables referenced in the expression are present in the provided variable registry. Raises a `ValueError` on validation failure.
* **`Expression.raw(text: str) -> Expression`** *(classmethod)*:
  Creates an opaque expression from a raw SurveyJS string. This serves as an escape hatch for complex logic that cannot be represented by the typed DSL.

---

### `VarRef`

The `VarRef` class represents a reference to a variable name within an `Expression`. It is used to defer variable evaluation until answers are provided.

#### Properties

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `name` | `str` | *Required* | The name of the referenced variable. |

#### Methods

* **`evaluate(answers: dict[str, Any]) -> Any`**:
  Extracts the value of the referenced variable from the answers dictionary. Returns `None` if the variable is not found.
* **`variables() -> set[str]`**:
  Returns a set containing only the referenced variable name.
* **`to_dict() -> dict[str, str]`**:
  Serializes the variable reference to a dictionary representation.

---

## Questions

Questions bind user prompts to variables and define the user interface components used to collect responses. All question types inherit from the base `Question` class.

### `Question` (Base Class)

The base `Question` class defines the properties shared by all question types. It cannot be instantiated directly.

#### Shared Properties

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `text` | `str` | *Required* | The primary prompt or question text displayed to the respondent. Must be non-empty. |
| `var` | `Variable \| list[Variable]` | *Required* | The variable or list of variables bound to this question. Responses are stored under these variable names. |
| `required` | `bool` | `False` | If `True`, the respondent must answer this question before advancing to the next page. |
| `hint` | `str \| None` | `None` | Explanatory helper or hint text displayed beneath the question text. |
| `show_if` | `Expression \| str \| None` | `None` | An expression determining when this question should be visible. |
| `hide_if` | `Expression \| str \| None` | `None` | An expression determining when this question should be hidden. |
| `skip_to` | `str \| None` | `None` | The ID of a target page or question to jump to if this question is answered. |
| `randomize` | `bool` | `False` | If `True`, the display order of the answer choices will be randomized. |
| `other_specify` | `bool` | `False` | If `True`, adds an "Other (please specify)" choice with a text entry field. |
| `tag` | `str \| list[str] \| None` | `None` | Optional tag or list of tags for categorization and filtering. |
| `id` | `str \| None` | `None` | Explicit unique identifier for the question. If omitted, it is automatically derived from the bound variable name. |
| `name` | `str \| None` | `None` | The output column name in the exported dataset. Defaults to the question ID. |
| `media` | `Media \| list[Media] \| None` | `None` | A `Media` instance or list of media attachments (images, videos, or audio) to display with the question. |
| `metadata` | `dict[str, Any]` | `{}` | Extensible dictionary for custom parameters (e.g., `{"other_placeholder": "Specify..."}`). |

---

### `SingleChoice`

The `SingleChoice` question presents a list of mutually exclusive options.

#### Additional Properties

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `display` | `str` | `"radio"` | The UI representation. Allowed values are: `"radio"`, `"dropdown"`, or `"buttons"` (segmented button group). |
| `none_of_above` | `bool` | `False` | If `True`, appends a "None of the above" option that deselects other choices. |
| `choices` | `list[Option] \| None` | `None` | Explicit list of `Option` instances. If `None`, choices are automatically populated from the bound variable's `labels`. |

---

### `MultiChoice`

The `MultiChoice` question allows respondents to select one or more options from a list.

#### Additional Properties

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `min_answers` | `int` | `1` | The minimum number of choices that must be selected (if `required` is `True`). |
| `max_answers` | `int \| None` | `None` | The maximum number of choices that can be selected. |
| `exclusive` | `list[int]` | `[]` | A list of category codes that are mutually exclusive (e.g., "None of the above" code). Selecting an exclusive option deselects all other choices. |
| `mode` | `str` | `"array"` | Determines how the data is structured. Allowed values: `"array"` (stores selected codes as a list in a single column) or `"wide"` (stores binary indicators across multiple columns). |
| `choices` | `list[Option] \| None` | `None` | Explicit list of `Option` instances. If `None`, choices are populated from the bound variable's `labels`. |

---

### `LikertScale`

The `LikertScale` question presents a symmetric, horizontal rating scale representing an ordinal continuum.

#### Additional Properties

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `points` | `int` | `5` | The number of points on the scale. Must be greater than or equal to 2. |
| `left_label` | `str \| None` | `None` | Text label displayed on the far-left end of the scale (e.g., `"Strongly disagree"`). |
| `right_label` | `str \| None` | `None` | Text label displayed on the far-right end of the scale (e.g., `"Strongly agree"`). |
| `na_option` | `bool \| str` | `False` | If `True`, adds a "Not applicable" option. If a string is provided, that string is used as the option's label. |

---

### `NumericInput`

The `NumericInput` question collects continuous numerical values (integers or floating-point numbers).

#### Additional Properties

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `display` | `str` | `"input"` | The UI representation. Allowed values: `"input"` (a numeric text box) or `"slider"` (an interactive horizontal slider). |
| `unit` | `str \| None` | `None` | Text representing the unit of measurement displayed next to the input field (e.g., `"years"`, `"%"`, `"USD"`). |
| `step` | `int \| float` | `1` | The step increment for sliders or number inputs. Must be greater than 0. |

---

### `OpenText`

The `OpenText` question collects unstructured, free-form text responses.

#### Additional Properties

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `multiline` | `bool` | `False` | If `True`, renders a large multiline `<textarea>` instead of a single-line text input. |
| `max_chars` | `int \| None` | `None` | The maximum number of characters allowed. Must be greater than 0 when set. |
| `placeholder` | `str \| None` | `None` | Ghost placeholder text displayed inside the input field when it is empty. |

---

### `Matrix`

The `Matrix` question displays a grid of subquestions (rows) sharing a common set of rating options (columns). This is highly efficient for batteries of Likert items [5].

#### Additional Properties

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `var` | `list[Variable]` | *Required* | A list of `Variable` instances, where each variable represents a row in the matrix. Must be non-empty. |
| `subquestions` | `list[str] \| None` | `None` | A list of row labels displayed to the respondent. If `None`, row labels default to each variable's `label` property. |
| `column_labels` | `list[str] \| None` | `None` | A list of column labels. If `None`, column labels default to the rating category labels defined in the variables' `labels` dictionary. |
| `na_option` | `bool \| str` | `False` | If `True`, appends a "Not applicable" column. If a string is provided, that string is used as the column header. |

---

### `Ranking`

The `Ranking` question presents a list of options that respondents must sort into an order of preference using drag-and-drop.

#### Additional Properties

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `max_ranked` | `int \| None` | `None` | The maximum number of items the respondent is required to rank (e.g., "Rank your top 3"). Must be greater than 0. |
| `choices` | `list[Option] \| None` | `None` | List of `Option` instances to rank. If `None`, choices are derived from the bound variable's `labels`. |

---

## Options and Media

### `Option`

The `Option` class represents an individual answer choice within choice questions (`SingleChoice`, `MultiChoice`, `Ranking`). Use `Option` instead of simple `labels` dictionaries when choices require advanced features like conditional visibility or media attachments.

#### Properties

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `code` | `Any` | *Required* | The category code stored in the database if this option is chosen (typically an integer or string). |
| `label` | `str` | *Required* | The text displayed to the respondent. Must be non-empty. |
| `show_if` | `Expression \| str \| None` | `None` | Condition determining when this specific option should be shown. |
| `hide_if` | `Expression \| str \| None` | `None` | Condition determining when this specific option should be hidden. |
| `media` | `Media \| None` | `None` | A `Media` instance representing an image, video, or audio file attached to this option. |

---

### `Media`

The `Media` class represents an external visual or auditory asset attached to a question or an option.

#### Properties

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `url` | `str` | *Required* | The absolute or relative URL pointing to the media file. Must be non-empty. |
| `kind` | `str \| None` | `None` | The media type: `"image"`, `"video"`, or `"audio"`. If `None`, the type is automatically inferred from the file extension. |
| `alt` | `str \| None` | `None` | Text description of the asset, used for screen readers and web accessibility (HTML `alt` attribute). |
| `caption` | `str \| None` | `None` | Text caption displayed immediately beneath the media element. |
| `autoplay` | `bool` | `False` | If `True`, the media starts playing automatically upon becoming visible (videos/audio only). |
| `loop` | `bool` | `False` | If `True`, the media plays in an infinite loop. |
| `controls` | `bool` | `True` | If `True`, displays media playback controls (play, pause, volume, etc.). |

---

## Pages and Blocks

Surveys are organized into screens (pages) and logical groups (blocks).

### `Page`

A `Page` represents a single screen shown to the respondent. It contains questions, blocks, and page-level routing logic.

#### Properties

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `name` | `str` | *Required* | Unique identifier for the page. Used for branching and skip logic. |
| `title` | `str \| None` | `None` | Optional title displayed at the top of the page. |
| `items` | `list[Question \| Block]` | `[]` | List of questions or blocks rendered on this page. |
| `next_if` | `list[tuple[str, str]]` | `[]` | List of routing rules: `[(condition_expression, target_page_name), ...]`. Evaluated in order. |
| `default_next` | `str \| None` | `None` | The default next page name if no `next_if` condition matches. |
| `randomize_blocks` | `bool` | `False` | If `True`, randomizes the display order of immediate `Block` items on this page. |
| `show_if` | `Expression \| str \| None` | `None` | Condition determining whether this page should be displayed. |
| `hide_if` | `Expression \| str \| None` | `None` | Condition determining whether this page should be hidden. |

#### Methods

* **`flatten_questions() -> list[Question]`**:
  Flattens all nested blocks and questions on this page into a single flat list of `Question` objects.

---

### `Block`

A `Block` is a logical container that groups questions or nested blocks together on a single page. It is used to apply bulk visibility rules or to randomize a subset of questions.

#### Properties

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `title` | `str \| None` | `None` | Optional header displayed above the block items. |
| `items` | `list[Question \| Block]` | `[]` | List of questions or nested blocks inside this block. |
| `randomize` | `bool` | `False` | If `True`, shuffles the order of items inside this block. |
| `show_if` | `Expression \| str \| None` | `None` | Bulk condition determining when this entire block is visible. |
| `hide_if` | `Expression \| str \| None` | `None` | Bulk condition determining when this entire block is hidden. |

---

## Quotas and Scripts

### `Quota`

A `Quota` defines limits on the number of accepted responses matching specific criteria, ensuring sample representativeness [6].

#### Properties

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `variable` | `str` | *Required* | The name of the variable to monitor. |
| `target_value` | `Any` | *Required* | The category code to count. |
| `limit` | `int` | *Required* | The maximum number of accepted responses matching this category. |

---

### `Script`

The `Script` class allows researchers to inject custom JavaScript snippets into the survey runtime. This enables advanced dynamic behavior such as custom validation, external API calls, and complex option randomization without modifying the core React application [2].

#### Properties

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `code` | `str` | *Required* | The raw JavaScript source code. Must be non-empty. |
| `trigger` | `str` | `"onPageEnter"` | The lifecycle event that triggers execution. Allowed triggers: `"onInit"`, `"onPageEnter"`, `"onPageExit"`, `"onQuestionShow"`, `"onAnswer"`, `"onSubmit"`, or `"onRandomize"`. |
| `name` | `str \| None` | `None` | Optional identifier used for debugging and logging. |
| `target` | `str \| None` | `None` | Limits the scope of the script to a specific page name or question ID. |
| `context` | `dict[str, Any]` | `{}` | Static data dictionary passed into the script's execution context. |
| `sandbox` | `bool` | `True` | If `True`, executes the script in a sandboxed iframe to prevent direct DOM access and maintain security. |

---

## Questionnaire

The `Questionnaire` class is the aggregate root of a survey design. It combines variables, pages (or blocks), quotas, and lifecycle scripts into a cohesive survey definition.

### Properties

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `title` | `str` | *Required* | The primary title of the survey. |
| `blocks` | `list[Question \| Block]` | `[]` | List of items for single-page surveys. Cannot be combined with `pages`. |
| `pages` | `list[Page]` | `[]` | List of pages for multi-page surveys. Cannot be combined with `blocks`. |
| `deadline` | `datetime \| None` | `None` | The expiration date and time. After this deadline, the survey is closed. |
| `variables` | `VariableMap \| None` | `None` | Explicit `VariableMap` registry. If omitted, it is inferred from the questions. |
| `scripts` | `list[Script]` | `[]` | List of custom `Script` objects to execute during survey lifecycles. |

### Methods

* **`all_questions() -> list[Question]`**:
  Flattens all pages and blocks into a single, ordered list of questions.
* **`validate(strict: bool = False) -> None`**:
  Performs comprehensive structural and logical checks:
  * Ensures all question and page identifiers are unique.
  * Verifies that all `skip_to` and navigation targets point to valid pages or questions.
  * Checks that all expressions reference only registered variables and evaluate without error.
  * Validates that scripts are bound to existing questions or pages.
  * If `strict=True`, also runs linting heuristics and raises a `ValueError` on any errors.
* **`lint(level: str = "basic") -> list[LintWarning]`**:
  Analyzes the survey structure for logical anti-patterns, such as unreachable pages, unused variables, or empty pages.
* **`compile(**options) -> SurveySchema`**:
  Compiles the questionnaire into an intermediate `SurveySchema` representation ready for bundle building [2].
* **`deploy(backend: str = "local", frontend: str = "local", **options) -> DeployResult`**:
  Deploys the survey to a specified environment (e.g., local server or cloud services like Supabase and Vercel) [2].
* **`simulate(n: int = 100, seed: int = 42) -> SurveyData`**:
  Generates `n` synthetic, logically valid responses using Monte Carlo simulation, which is useful for testing analytical pipelines before data collection [1].
* **`preview() -> str`**:
  Renders a static text preview of the survey structure, including routing logic and page hierarchy.
* **`collect()`**:
  Retrieves responses collected from active deployments (available for cloud backends).
* **`to_dict() -> dict`**:
  Serializes the entire survey definition to a nested dictionary representation.
* **`validate_for_export(target: str = "surveyjs") -> None`**:
  Validates that the questionnaire structure is fully compatible with the export target format.

---

### `LintWarning`

The `LintWarning` class represents a structural or logical warning discovered during survey linting.

#### Properties

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `code` | `str` | *Required* | Unique warning code (e.g., `"unreachable_page"`, `"unused_variable"`). |
| `severity` | `str` | *Required* | Severity level: `"info"`, `"warning"`, or `"error"`. |
| `message` | `str` | *Required* | Human-readable explanation of the warning. |
| `location` | `str \| None` | `None` | Location identifier indicating where the issue was found (e.g., `"page:welcome"`). |

---

## References

1. Siamang Team. *Siamang: A Research-as-Code Framework for Sociological Surveys*. Siamang Documentation, 2026.
2. Manus AI. *Technical Architecture and Deployment Pipeline of Siamang*. Siamang Reference, 2026.
3. Babbie, Earl R. *The Practice of Social Research*. Cengage Learning, 15th edition, 2021.
4. AAPOR (American Association for Public Opinion Research). *Standard Definitions: Final Dispositions of Case Codes and Outcome Rates for Surveys*. AAPOR, 2016.
5. Dillman, Don A., Smyth, Jolene D., and Christian, Leah Melani. *Internet, Phone, Mail, and Mixed-Mode Surveys: The Tailored Design Method*. John Wiley & Sons, 4th edition, 2014.
6. Bethlehem, Jelke. *Applied Survey Methods: A Statistical Perspective*. John Wiley & Sons, 2009.
