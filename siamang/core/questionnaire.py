"""Questionnaire aggregate and validation helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, NamedTuple

from siamang.core.block import Block
from siamang.core.expression import Expression, VarRef
from siamang.core.page import Page
from siamang.core.question import (
    LikertScale,
    MultiChoice,
    NumericInput,
    Question,
    SingleChoice,
    question_fallback_id,
    question_output_name,
)
from siamang.core.script import _VALID_TRIGGERS
from siamang.core.variable import VariableMap


@dataclass(frozen=True, slots=True)
class LintWarning:
    code: str
    severity: str
    message: str
    location: str | None = None


@dataclass(frozen=True, slots=True)
class Questionnaire:
    title: str
    blocks: list[Question | Block] = field(default_factory=list)
    pages: list[Page] = field(default_factory=list)
    deadline: datetime | None = None
    variables: VariableMap | None = None
    scripts: list = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("Questionnaire title must not be empty.")
        if self.blocks and self.pages:
            raise ValueError("Use either 'blocks' or 'pages', not both.")

    def all_questions(self) -> list[Question]:
        if self.pages:
            questions: list[Question] = []
            for page in self.pages:
                questions.extend(page.flatten_questions())
            return questions
        questions: list[Question] = []
        for item in self.blocks:
            if isinstance(item, Block):
                questions.extend(item.flatten_questions())
            else:
                questions.append(item)
        return questions

    def validate(self, strict: bool = False) -> None:
        self._validate_question_ids_and_skip_targets()
        if self.pages:
            page_names: set[str] = set()
            for page in self.pages:
                if not page.name.strip():
                    raise ValueError("Page name must not be empty.")
                if page.name in page_names:
                    raise ValueError(f"Duplicate page name in questionnaire: {page.name}")
                page_names.add(page.name)
            self._validate_page_expressions()
            self._validate_page_expressions_for_export("surveyjs")
            self._validate_page_navigation()
        # Validate scripts
        for script in self.scripts:
            if script.trigger not in _VALID_TRIGGERS:
                raise ValueError(f"Script '{script.name}' has unknown trigger '{script.trigger}'.")
            if script.target:
                all_q_ids = {question_output_name(q) for q in self.all_questions()}
                all_page_names = {p.name for p in (self.pages or [])}
                if script.target not in all_q_ids and script.target not in all_page_names:
                    raise ValueError(
                        f"Script '{script.name}' targets '{script.target}' "
                        f"which is not a known question ID or page name."
                    )
        names: set[str] = set()
        for q in self.all_questions():
            variables = q.var if isinstance(q.var, list) else [q.var]
            for var in variables:
                if var.name in names:
                    raise ValueError(f"Duplicate variable in questionnaire: {var.name}")
                names.add(var.name)
                if self.variables is not None:
                    known = self.variables.require(var.name)
                    if known != var:
                        raise ValueError(f"Variable '{var.name}' differs from registry instance.")
        if strict:
            errors = [issue for issue in self.lint(level="strict") if issue.severity == "error"]
            if errors:
                codes = ", ".join(issue.code for issue in errors)
                raise ValueError(f"Strict questionnaire validation failed: {codes}")

    def _validate_question_ids_and_skip_targets(self) -> None:
        question_ids: set[str] = set()
        duplicates: set[str] = set()
        for question in self.all_questions():
            question_id = question_fallback_id(question)
            if question_id in question_ids:
                duplicates.add(question_id)
            question_ids.add(question_id)
        if duplicates:
            raise ValueError(
                f"Duplicate question id in questionnaire: {', '.join(sorted(duplicates))}"
            )

        page_names = {page.name for page in self.pages}
        known_targets = question_ids | page_names
        for question in self.all_questions():
            if question.skip_to is not None and question.skip_to not in known_targets:
                raise ValueError(
                    f"Question '{question_fallback_id(question)}' skip_to references unknown target: {question.skip_to}"
                )

    def preview(self) -> str:
        return f"Questionnaire<{self.title}> with {len(self.all_questions())} questions"

    def compile(self, **options):
        """Compile to a SurveySchema IR (used by the frontend constructor)."""

        from siamang.frontend.compiler import compile_questionnaire

        return compile_questionnaire(self, options=options or None)

    def deploy(
        self,
        backend: str = "local",
        frontend: str = "local",
        *,
        backend_kwargs: dict | None = None,
        frontend_kwargs: dict | None = None,
        **options,
    ):
        """Compile the survey, provision the backend, build a bundle, publish.

        Returns :class:`siamang.deploy.DeployResult` whose ``collect()`` method
        fetches accumulated responses from the configured backend.
        """

        from siamang.deploy.pipeline import DeployPipeline
        from siamang.deploy.registry import backend_factory, frontend_factory
        from siamang.frontend import FrontendBuilder, ReactRuntime, UIConfig

        backend_cls = backend_factory(backend)
        frontend_cls = frontend_factory(frontend)
        backend_obj = backend_cls(**(backend_kwargs or {}))
        frontend_obj = frontend_cls(**(frontend_kwargs or {}))

        ui = options.pop("ui", None) or UIConfig()
        runtime = options.pop("runtime", None) or ReactRuntime()
        builder = FrontendBuilder(ui=ui, runtime=runtime)
        pipeline = DeployPipeline(backend=backend_obj, frontend=frontend_obj, builder=builder)
        return pipeline.run(self, options=options or None)

    def simulate(self, n: int = 100, seed: int | None = 42):
        from siamang.data.survey_data import SurveyData
        from siamang.local_simulator import simulate_dataframe, simulate_from_pages

        if self.pages:
            frame = simulate_from_pages(self.pages, n=n, seed=seed)
        else:
            frame = simulate_dataframe(self.all_questions(), n=n, seed=seed)
        variables = self.variables or VariableMap()
        if not variables:
            variables = VariableMap()
            for question in self.all_questions():
                vars_in_question = (
                    question.var if isinstance(question.var, list) else [question.var]
                )
                for variable in vars_in_question:
                    if variable.name not in variables:
                        variables.add(variable)
        return SurveyData(frame=frame, variables=variables, questionnaire=self)

    def collect(self):
        raise NotImplementedError(
            "Direct collect() requires a DeployResult. Use survey.deploy(...).collect() "
            "or pass the survey_id / backend to a BackendAdapter explicitly."
        )

    def to_dict(self) -> dict:
        from siamang.core.serialization import question_to_dict

        if self.pages:
            pages = [_page_to_dict(page, question_to_dict) for page in self.pages]
            return {"title": self.title, "pages": pages}
        if self.blocks and all(isinstance(item, Block) for item in self.blocks):
            pages = []
            for index, block in enumerate(self.blocks, start=1):
                assert isinstance(block, Block)
                page_name = _slugify(block.title) if block.title else f"page{index}"
                pages.append(
                    _page_to_dict(
                        Page(name=page_name, title=block.title, items=block.items),
                        question_to_dict,
                    )
                )
            return {"title": self.title, "pages": pages}
        elements = [question_to_dict(q) for q in self.all_questions()]
        return {"title": self.title, "pages": [{"name": "page1", "elements": elements}]}

    def _validate_page_navigation(self) -> None:
        pages = self.pages
        _validate_targets_exist(pages)
        graph = _build_navigation_graph(pages)
        _validate_reachability(pages, graph)
        if _contains_cycle(graph):
            raise ValueError("Cycle detected in page navigation graph.")

    def _validate_page_expressions(self) -> None:
        known_vars = {
            variable.name
            for question in self.all_questions()
            for variable in (question.var if isinstance(question.var, list) else [question.var])
        }
        pattern = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")
        probe_answers = {name: 0 for name in known_vars}

        for ref in _iter_conditions(self.pages, self.blocks):
            condition, field, location = ref.condition, ref.field, ref.location
            if not isinstance(condition, (Expression, str)):
                raise ValueError(f"{location} {field} must be str or Expression.")
            if isinstance(condition, Expression):
                referenced = condition.variables()
                expr = condition
            else:
                referenced = set(pattern.findall(condition))
                expr = None
            unknown = referenced - known_vars
            if unknown:
                raise ValueError(
                    f"{location} {field} references unknown variables: {', '.join(sorted(unknown))}"
                )
            if expr is None:
                continue
            try:
                expr.validate(known_vars)
                expr.evaluate(probe_answers)
            except Exception as exc:
                raise ValueError(f"{location} has invalid {field} expression: {exc}") from exc

    def _validate_page_expressions_for_export(self, target: str) -> None:
        if target != "surveyjs":
            raise ValueError(f"Unsupported export target for expression validation: {target}")
        allowed_pattern = re.compile(r"^[\s\w{}<>=!.'&|()\-+*/]+$")
        for page in self.pages:
            if page.show_if is None:
                continue
            expr_text = (
                page.show_if.to_surveyjs()
                if isinstance(page.show_if, Expression)
                else str(page.show_if)
            )
            if not allowed_pattern.match(expr_text):
                raise ValueError(
                    f"Page '{page.name}' show_if contains tokens unsupported by {target}: {expr_text}"
                )

    def validate_for_export(self, target: str = "surveyjs") -> None:
        if self.pages:
            self._validate_page_expressions_for_export(target)
        self.validate()

    def lint(self, level: str = "basic") -> list[LintWarning]:
        if level not in {"basic", "strict"}:
            raise ValueError("lint level must be either 'basic' or 'strict'.")
        warnings: list[LintWarning] = []
        if not self.pages and not self.blocks:
            warnings.append(
                LintWarning(
                    code="EMPTY_QUESTIONNAIRE",
                    severity="warning",
                    message="Questionnaire has no pages or blocks.",
                )
            )
            return warnings
        if self.pages:
            graph = _build_navigation_graph(self.pages)
            for index, page in enumerate(self.pages):
                # Content and terminal pages render `body` instead of questions,
                # so having no items is what they are for — only an ordinary
                # question page with nothing on it is empty.
                if not page.items and (page.kind is None or not page.body):
                    warnings.append(
                        LintWarning(
                            code="EMPTY_PAGE",
                            severity="error" if level == "strict" else "warning",
                            message=f"Page '{page.name}' has no items.",
                            location=page.name,
                        )
                    )
                implicit_next = _default_successor(self.pages, index)
                if page.default_next is not None and page.default_next == implicit_next:
                    warnings.append(
                        LintWarning(
                            code="REDUNDANT_NAVIGATION",
                            severity="warning",
                            message=(
                                f"Page '{page.name}' has redundant default_next='{page.default_next}' "
                                "(same as implicit order)."
                            ),
                            location=page.name,
                        )
                    )
                if index < len(self.pages) - 1 and not graph[page.name]:
                    warnings.append(
                        LintWarning(
                            code="MISSING_NAVIGATION",
                            severity="warning",
                            message=f"Page '{page.name}' has no outgoing navigation edges.",
                            location=page.name,
                        )
                    )
        # Codebook and logic consistency. These are warnings at every level: they
        # describe a questionnaire that compiles and runs but collects the wrong
        # thing, which is worth saying even to someone who did not ask for strict.
        warnings.extend(_condition_value_warnings(self))
        warnings.extend(_contradictory_visibility_warnings(self))
        warnings.extend(_codebook_warnings(self))
        if level == "strict":
            warnings.extend(_strict_question_warnings(self.all_questions()))
            if self.variables is not None:
                used = {
                    var.name
                    for question in self.all_questions()
                    for var in _question_variables(question)
                }
                for name in sorted(set(self.variables) - used):
                    warnings.append(
                        LintWarning(
                            code="UNUSED_VARIABLE",
                            severity="warning",
                            message=f"Variable '{name}' is registered but not used in questionnaire.",
                            location=name,
                        )
                    )
        return warnings


def _question_variables(question: Question):
    return question.var if isinstance(question.var, list) else [question.var]


class _ConditionRef(NamedTuple):
    """One visibility/branching condition, with everything needed to report it."""

    holder: Any
    condition: Any
    field: str
    location: str
    question: Question | None


def _holder_conditions(holder, location: str, question: Question | None):
    """Yield the show_if/hide_if conditions carried by a single object."""

    for name in ("show_if", "hide_if"):
        condition = getattr(holder, name, None)
        if condition is not None:
            yield _ConditionRef(holder, condition, name, location, question)


def _item_conditions(item, parent: str):
    if isinstance(item, Block):
        location = f"Block in {parent}"
        yield from _holder_conditions(item, location, None)
        for nested in item.items:
            yield from _item_conditions(nested, location)
        return
    # Question
    location = f"Question '{question_fallback_id(item)}' in {parent}"
    yield from _holder_conditions(item, location, item)
    for option in getattr(item, "choices", None) or []:
        yield from _holder_conditions(option, f"Option {option.code!r} of {location}", item)


def _iter_conditions(pages: list[Page], blocks: list):
    """Yield a :class:`_ConditionRef` for every visibility or branching condition
    in the questionnaire, in document order.

    ``question`` is the question a condition belongs to (the question itself, or
    the one owning the option), and ``None`` for page- and block-level
    conditions. ``location`` is the human-readable prefix used in messages.
    """

    for page in pages:
        page_location = f"Page '{page.name}'"
        yield from _holder_conditions(page, page_location, None)
        for condition, _target in page.next_if:
            if condition is not None:
                yield _ConditionRef(page, condition, "next_if", page_location, None)
        for item in page.items:
            yield from _item_conditions(item, f"page '{page.name}'")

    # Blocks attached directly to the questionnaire (blocks mode).
    for item in blocks:
        yield from _item_conditions(item, "questionnaire")


def _strict_question_warnings(questions: list[Question]) -> list[LintWarning]:
    warnings: list[LintWarning] = []
    for question in questions:
        question_id = question_fallback_id(question)
        if question.required and question.show_if is not None:
            warnings.append(
                LintWarning(
                    code="REQUIRED_CONDITIONAL",
                    severity="warning",
                    message=f"Required question '{question_id}' also has conditional visibility.",
                    location=question_id,
                )
            )
        if isinstance(question, NumericInput):
            var = question.var
            if var.scale not in {"interval", "ratio"}:
                warnings.append(
                    LintWarning(
                        code="INCOMPATIBLE_QUESTION_SCALE",
                        severity="error",
                        message=f"NumericInput question '{question_id}' uses non-numeric scale '{var.scale}'.",
                        location=question_id,
                    )
                )
        if isinstance(question, LikertScale):
            var = question.var
            if var.scale != "ordinal":
                warnings.append(
                    LintWarning(
                        code="INCOMPATIBLE_QUESTION_SCALE",
                        severity="error",
                        message=f"LikertScale question '{question_id}' should use ordinal scale, got '{var.scale}'.",
                        location=question_id,
                    )
                )
        if isinstance(question, SingleChoice):
            warnings.extend(_categorical_label_warnings(question_id, [question.var]))
        if isinstance(question, MultiChoice):
            warnings.extend(_categorical_label_warnings(question_id, _question_variables(question)))
    return warnings


def _variable_codes(variable) -> list:
    """Every code a variable legitimately carries: labelled categories + missing."""

    return list(variable.labels) + [
        code for code in variable.missing_values if code not in variable.labels
    ]


def _known(value, codes) -> bool:
    """Membership that tolerates unhashable values — lint must never raise."""

    return any(value == code for code in codes)


def _format_codes(codes) -> str:
    return ", ".join(str(code) for code in codes)


def _survey_variables(survey: Questionnaire) -> dict[str, Any]:
    """Every variable the questionnaire touches, keyed by name."""

    variables: dict[str, Any] = {}
    for question in survey.all_questions():
        for variable in _question_variables(question):
            variables.setdefault(variable.name, variable)
    if survey.variables:
        for name, variable in survey.variables.items():
            variables.setdefault(name, variable)
    return variables


def _option_codes(question: Question) -> list:
    return [option.code for option in getattr(question, "choices", None) or []]


def _single_variable(question: Question):
    """The one variable a question writes into, or None for wide/matrix questions."""

    return None if isinstance(question.var, list) else question.var


def _compared_values(node):
    """Yield ``(variable_name, value)`` for each literal compared to a variable."""

    if not isinstance(node, Expression):
        return
    if node.op in {"=", "!=", "in", "not in"} and isinstance(node.left, VarRef):
        right = node.right
        values = right if isinstance(right, (list, tuple, set)) else [right]
        for value in values:
            if not isinstance(value, (Expression, VarRef)):
                yield node.left.name, value
        return
    yield from _compared_values(node.left)
    yield from _compared_values(node.right)


def _condition_value_warnings(survey: Questionnaire) -> list[LintWarning]:
    """Answer codes used in conditions that no longer exist among the choices.

    The classic survey-authoring mistake: the option list is reworked and the
    rule pointing at it is not. The question then shows to nobody (or to
    everybody) for the whole of fieldwork, silently.
    """

    variables = _survey_variables(survey)
    # Codes contributed by an explicit Option list shadow the variable's labels
    # at runtime, so a condition may legitimately name one of them.
    from_choices: dict[str, list] = {}
    for question in survey.all_questions():
        codes = _option_codes(question)
        if not codes:
            continue
        for variable in _question_variables(question):
            from_choices.setdefault(variable.name, []).extend(codes)

    warnings: list[LintWarning] = []
    for ref in _iter_conditions(survey.pages, survey.blocks):
        for name, value in _compared_values(ref.condition):
            variable = variables.get(name)
            # No codebook, or a genuinely numeric scale: comparing to a number
            # is legitimate and there is nothing to check against.
            if variable is None or not variable.labels:
                continue
            if variable.scale in {"interval", "ratio"}:
                continue
            allowed = _variable_codes(variable) + from_choices.get(name, [])
            if _known(value, allowed):
                continue
            warnings.append(
                LintWarning(
                    code="UNKNOWN_CONDITION_VALUE",
                    severity="warning",
                    message=(
                        f"{ref.location} {ref.field} references value {value}, which is not "
                        f"a defined category of '{name}' ({_format_codes(variable.labels)})"
                    ),
                    location=(
                        question_fallback_id(ref.question)
                        if ref.question is not None
                        else ref.location
                    ),
                )
            )
    return warnings


def _contradictory_visibility_warnings(survey: Questionnaire) -> list[LintWarning]:
    """show_if and hide_if on the same object — in the limit, never shown."""

    fields: dict[int, set[str]] = {}
    seen: dict[int, _ConditionRef] = {}
    for ref in _iter_conditions(survey.pages, survey.blocks):
        fields.setdefault(id(ref.holder), set()).add(ref.field)
        seen.setdefault(id(ref.holder), ref)

    warnings: list[LintWarning] = []
    for key, present in fields.items():
        if not {"show_if", "hide_if"} <= present:
            continue
        ref = seen[key]
        warnings.append(
            LintWarning(
                code="CONTRADICTORY_VISIBILITY",
                severity="warning",
                message=(
                    f"{ref.location} sets both show_if and hide_if; the two are combined, "
                    "so the object may never be shown."
                ),
                location=(
                    question_fallback_id(ref.question) if ref.question is not None else ref.location
                ),
            )
        )
    return warnings


def _codebook_warnings(survey: Questionnaire) -> list[LintWarning]:
    """Consistency between questions, their answer options and their codebook."""

    warnings: list[LintWarning] = []
    for question in survey.all_questions():
        question_id = question_fallback_id(question)
        # Wide MultiChoice and Matrix bind a list of variables; the rules below
        # are all about the single variable a question puts its codes into.
        bound = _single_variable(question)

        # Exclusive codes that match no answer option silently stop being
        # exclusive: "None of these" no longer clears the other answers.
        if isinstance(question, MultiChoice) and question.mode == "array" and bound is not None:
            allowed = _variable_codes(bound) + _option_codes(question)
            unknown = [code for code in question.exclusive if not _known(code, allowed)]
            if allowed and unknown:
                warnings.append(
                    LintWarning(
                        code="EXCLUSIVE_CODE_UNKNOWN",
                        severity="warning",
                        message=(
                            f"MultiChoice question '{question_id}' marks "
                            f"{_format_codes(unknown)} exclusive, which is not among its "
                            f"answer codes ({_format_codes(allowed)})."
                        ),
                        location=question_id,
                    )
                )

        # Option.code must match the codes used in Variable.labels, or the
        # export loses its value labels exactly where they are wanted.
        codes = _option_codes(question)
        if codes and bound is not None and bound.labels:
            known = _variable_codes(bound)
            unlabelled = [code for code in codes if not _known(code, known)]
            if unlabelled:
                warnings.append(
                    LintWarning(
                        code="OPTION_CODE_WITHOUT_LABEL",
                        severity="warning",
                        message=(
                            f"Question '{question_id}' offers option code(s) "
                            f"{_format_codes(unlabelled)} that variable "
                            f"'{bound.name}' has no value label for "
                            f"({_format_codes(known)})."
                        ),
                        location=question_id,
                    )
                )

        if isinstance(question, LikertScale) and bound is not None and bound.labels:
            labelled = [code for code in bound.labels if code not in bound.missing_values]
            if labelled and question.points != len(labelled):
                warnings.append(
                    LintWarning(
                        code="LIKERT_POINTS_LABEL_MISMATCH",
                        severity="warning",
                        message=(
                            f"LikertScale question '{question_id}' has {question.points} points "
                            f"but variable '{bound.name}' labels {len(labelled)} of them; "
                            "the unlabelled codes arrive with no text."
                        ),
                        location=question_id,
                    )
                )

    for name, variable in _survey_variables(survey).items():
        if not variable.labels:
            continue

        # A missing code absent from the labels is a missing value that never
        # occurs, while the real refusal stays unmarked.
        unknown_missing = [
            code for code in variable.missing_values if not _known(code, variable.labels)
        ]
        if unknown_missing:
            warnings.append(
                LintWarning(
                    code="MISSING_CODE_NOT_IN_LABELS",
                    severity="warning",
                    message=(
                        f"Variable '{name}' declares missing value(s) "
                        f"{_format_codes(unknown_missing)} that are not among its value "
                        f"labels ({_format_codes(variable.labels)})."
                    ),
                    location=name,
                )
            )

        if variable.valid_range is not None:
            outside = [
                code
                for code in variable.labels
                if code not in variable.missing_values
                and _outside_range(code, variable.valid_range)
            ]
            if outside:
                low, high = variable.valid_range
                warnings.append(
                    LintWarning(
                        code="RANGE_LABEL_MISMATCH",
                        severity="warning",
                        message=(
                            f"Variable '{name}' labels value(s) {_format_codes(outside)} that "
                            f"fall outside its valid_range ({low}, {high})."
                        ),
                        location=name,
                    )
                )

    return warnings


def _outside_range(code, valid_range) -> bool:
    low, high = valid_range
    try:
        if low is not None and code < low:
            return True
        if high is not None and code > high:
            return True
    except TypeError:
        # A non-comparable code (a string label key against a numeric range)
        # is a different problem; do not guess about it here.
        return False
    return False


def _categorical_label_warnings(question_id: str, variables) -> list[LintWarning]:
    warnings: list[LintWarning] = []
    for var in variables:
        if var.scale in {"nominal", "ordinal"} and not var.labels:
            warnings.append(
                LintWarning(
                    code="CATEGORICAL_WITHOUT_LABELS",
                    severity="error",
                    message=f"Categorical question '{question_id}' variable '{var.name}' has no labels.",
                    location=question_id,
                )
            )
    return warnings


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "page"


def _page_to_dict(page: Page, question_to_dict_fn) -> dict:
    payload = {
        "name": page.name,
        "title": page.title,
        "elements": [question_to_dict_fn(question) for question in page.flatten_questions()],
    }
    if page.randomize_blocks:
        payload["randomizeBlocks"] = True
    if page.show_if is not None:
        payload["visibleIf"] = (
            page.show_if.to_surveyjs()
            if isinstance(page.show_if, Expression)
            else str(page.show_if)
        )
    if page.kind is not None:
        payload["kind"] = page.kind
    if page.body is not None:
        payload["body"] = page.body
    if page.redirect_url is not None:
        payload["redirectUrl"] = page.redirect_url
    if page.redirect_delay is not None:
        payload["redirectDelay"] = page.redirect_delay
    return payload


def _default_successor(pages: list[Page], index: int) -> str | None:
    if index + 1 >= len(pages):
        return None
    return pages[index + 1].name


def _build_navigation_graph(pages: list[Page]) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {page.name: set() for page in pages}
    for index, page in enumerate(pages):
        for _, target in page.next_if:
            graph[page.name].add(target)
        if page.default_next is not None:
            graph[page.name].add(page.default_next)
        else:
            successor = _default_successor(pages, index)
            if successor is not None:
                graph[page.name].add(successor)
    return graph


def _contains_cycle(graph: dict[str, set[str]]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def dfs(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for nxt in graph[node]:
            if nxt in graph and dfs(nxt):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(dfs(node) for node in graph)


def _iter_targets(page: Page) -> list[str]:
    targets = [target for _, target in page.next_if]
    if page.default_next is not None:
        targets.append(page.default_next)
    return targets


def _validate_targets_exist(pages: list[Page]) -> None:
    known = {page.name for page in pages}
    for page in pages:
        for target in _iter_targets(page):
            if target not in known:
                raise ValueError(f"Unknown target page in navigation: {page.name} -> {target}")


def _validate_reachability(pages: list[Page], graph: dict[str, set[str]]) -> None:
    if not pages:
        return
    start = pages[0].name
    reached: set[str] = set()
    stack = [start]
    while stack:
        node = stack.pop()
        if node in reached:
            continue
        reached.add(node)
        for nxt in graph[node]:
            stack.append(nxt)
    unreachable = [page.name for page in pages if page.name not in reached]
    if unreachable:
        raise ValueError(f"Unreachable pages in navigation graph: {', '.join(unreachable)}")
