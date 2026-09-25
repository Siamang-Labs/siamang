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
    Conjoint,
    LikertScale,
    Matrix,
    MaxDiff,
    MultiChoice,
    NumericInput,
    Question,
    SingleChoice,
    answer_key_aliases,
    choice_codes,
    na_code,
    none_code,
    other_code,
    other_text_key,
    question_answer_keys,
    question_fallback_id,
    question_output_name,
)
from siamang.core.script import (
    _PAGE_SCOPED_TRIGGERS,
    _QUESTION_SCOPED_TRIGGERS,
    _VALID_TRIGGERS,
)
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
                # A target may be the author's id or the answer key — the
                # compiler hands the runtime whichever it matches on.
                all_q_ids = {question_output_name(q) for q in self.all_questions()}
                all_q_ids |= {question_fallback_id(q) for q in self.all_questions()}
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
        # After the variable check: two questions bound to one variable share
        # a key too, and 'Duplicate variable' is the message that names why.
        self._validate_answer_keys()
        self._validate_added_codes()
        self._validate_aliased_ids()
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

    def _validate_answer_keys(self) -> None:
        """The runtime stores each answer under the question's output name
        (``question_output_name``: the variable for a single-variable question,
        the ``name`` or id for a matrix or a wide MultiChoice) and resolves a
        ``skip_to`` or a script target against it. A single-variable question's
        ``name``, when given, must be its variable — a different one would put
        the answer where no condition, quota or piping on the variable looks.
        Two questions may not share a key, and no question may carry as its id
        the key of another — the runtime could not tell which of the two was
        meant."""

        for question in self.all_questions():
            if isinstance(question.var, list) or not question.name:
                continue
            if question.name != question.var.name:
                raise ValueError(
                    f"Question '{question_fallback_id(question)}' has name "
                    f"'{question.name}' but writes variable '{question.var.name}'; a "
                    f"single-variable question's answer is stored under its variable, "
                    f"so its name, when given, must be '{question.var.name}'."
                )
        owner_by_key: dict[str, str] = {}
        for question in self.all_questions():
            question_id = question_fallback_id(question)
            key = question_output_name(question)
            if key in owner_by_key:
                raise ValueError(
                    f"Duplicate answer key in questionnaire: questions "
                    f"'{owner_by_key[key]}' and '{question_id}' both store their answer "
                    f"under '{key}'."
                )
            owner_by_key[key] = question_id
        for question in self.all_questions():
            question_id = question_fallback_id(question)
            owner = owner_by_key.get(question_id)
            if owner is not None and owner != question_id:
                raise ValueError(
                    f"Question '{question_id}' has the id under which question "
                    f"'{owner}' stores its answer; an id may not be another question's "
                    f"variable or output name."
                )

    def _validate_added_codes(self) -> None:
        """The codes the runtime stores for "Other (please specify)" and a
        SingleChoice's "None of the above" (``other_code`` / ``none_code``), and
        the key the Other text goes to (``other_text_key``).

        A code must be a number or a string. "None of the above" must not share
        a code with a choice or with Other — the data could not tell them
        apart. Other may name one of its question's choices in
        ``metadata["other_code"]`` (that choice becomes the Other option), but
        the *default* code on a question whose choices already use it is a
        clash nobody asked for. And the text key must not be a variable or an
        answer key of any question: the runtime would overwrite that answer."""

        taken: dict[str, str] = {}
        for question in self.all_questions():
            question_id = question_fallback_id(question)
            for name in question_variable_names_of(question):
                taken.setdefault(name, question_id)
            taken.setdefault(question_output_name(question), question_id)
        for question in self.all_questions():
            if not isinstance(question, SingleChoice | MultiChoice):
                continue
            question_id = question_fallback_id(question)
            codes = choice_codes(question)
            metadata = question.metadata or {}
            other = other_code(question) if question.other_specify else None
            if question.other_specify:
                _require_code(other, f"Question '{question_id}' metadata other_code")
                if "other_code" not in metadata and any(_same(other, c) for c in codes):
                    raise ValueError(
                        f"Question '{question_id}' offers “Other (please specify)”, stored as "
                        f"{other!r} by default, but one of its choices already has that code. "
                        "Set metadata other_code to the code Other should store (it may be "
                        "the code of a choice that is the Other option)."
                    )
                key = other_text_key(question)
                owner = taken.get(key)
                if owner is not None:
                    raise ValueError(
                        f"Question '{question_id}' stores its “Other (please specify)” text "
                        f"under '{key}', which question '{owner}' already stores an answer "
                        "under."
                    )
                taken[key] = question_id
            if isinstance(question, SingleChoice) and question.none_of_above:
                none = none_code(question)
                _require_code(none, f"Question '{question_id}' metadata none_code")
                if any(_same(none, c) for c in codes) or (other is not None and _same(none, other)):
                    raise ValueError(
                        f"Question '{question_id}' stores “None of the above” as {none!r}, "
                        "which is already the code of one of its answers. Set metadata "
                        "none_code to a code of its own."
                    )

    def _validate_aliased_ids(self) -> None:
        """A question whose id is not its answer key (``answer_key_aliases``)
        is still named by its id — a script's target, ``answers["<id>"]`` in
        a custom script's code, which the compiler rewrites to the key — so the
        id must not also be a name the answers hold something else under: a
        variable any question stores (its own rows included), the key of an
        "Other (please specify)" text, a variable a script assigns
        (``Script.assign_condition``, or a custom script's
        ``answers.<name> = …`` of a variable the codebook declares and no
        question collects), or the runtime's own ``__`` keys.
        ``answers["<id>"]`` could then mean either, and the rewrite takes the
        question's; ingest keying an old runtime's answers by id would move the
        other value into the question's column. An id that is its own answer
        key is renamed nowhere and is not concerned; nor is an id that is
        another question's answer key, which ``_validate_answer_keys`` reports.

        A codebook variable that nothing writes is not a name the answers hold
        anything under — the runtime captures no embedded data — and is free:
        the old Builder left one behind whenever a question's variable was
        renamed (id ``q2``, variable ``comment``, codebook entry ``q2`` kept),
        and those documents stay valid."""

        questions = self.all_questions()
        stored: dict[str, tuple[str, str]] = {}
        for question in questions:
            question_id = question_fallback_id(question)
            for name in question_variable_names_of(question):
                stored.setdefault(name, (question_id, "a variable {} stores an answer under"))
            if question.other_specify and isinstance(question, SingleChoice | MultiChoice):
                stored.setdefault(
                    other_text_key(question),
                    (question_id, "the key {} stores its “Other (please specify)” text under"),
                )
        assigned: dict[str, str] = {}
        for script in self.scripts:
            arm = getattr(script, "assigns", None)
            if arm:
                assigned.setdefault(arm, f"the variable script '{script.name}' assigns")
        declared = set(self.variables.keys()) if self.variables is not None else set()
        aliases = answer_key_aliases(questions)
        codebook_only = [
            name
            for name in aliases
            if name in declared and name not in stored and name not in assigned
        ]
        # Codebook entries a script writes: the entry may be what the author
        # meant, or one an older Builder left behind (see below) while the
        # script means the question — so the message offers both ways out.
        codebook_written: set[str] = set()
        if codebook_only:
            # ``siamang.model`` builds on ``siamang.core``: import here.
            from siamang.model.scripts import answer_keys_written

            for index, script in enumerate(self.scripts):
                label = f"script '{script.name}'" if script.name else f"script #{index + 1}"
                for name in answer_keys_written(script, codebook_only):
                    codebook_written.add(name)
                    assigned.setdefault(
                        name,
                        f"a variable the codebook declares, no question collects and {label} "
                        "writes",
                    )
        for question in questions:
            question_id = question_fallback_id(question)
            key = question_output_name(question)
            if question_id == key:
                continue
            if question_id in stored:
                owner, what = stored[question_id]
                taken = what.format(
                    "the question itself" if owner == question_id else f"question '{owner}'"
                )
            elif question_id in assigned:
                taken = assigned[question_id]
            elif question_id.startswith("__"):
                taken = "a name the runtime keeps its own state under (it begins with '__')"
            else:
                continue
            remedy = "give the question another id"
            if question_id in codebook_written:
                remedy += (
                    f", or, if the codebook entry '{question_id}' is left over from renaming "
                    f"this question's variable, delete that entry so that '{question_id}' in "
                    "the script means the question"
                )
            raise ValueError(
                f"Question '{question_id}' stores its answer under '{key}', but "
                f"'{question_id}' is also {taken}. A script that names '{question_id}' "
                f"could mean either; {remedy}."
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
        """``n`` synthetic respondents walking the questionnaire as the runtime
        would move them, with its scripts: the arm of every
        ``Script.assign_condition`` and the page order ``Script.randomize_pages``
        deals. It is :func:`siamang.local_simulator.simulate_survey` without
        quotas, which live in the compiler options — pass them to
        ``simulate_survey`` for their effect. A questionnaire of pages without
        those scripts gets the frame it always got; one of blocks is walked on
        the pages the runtime makes of it, a page per block."""

        from siamang.local_simulator import simulate_survey

        return simulate_survey(self, n=n, seed=seed)

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
        known_vars = self._known_variable_names()
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

    def _known_variable_names(self) -> set[str]:
        """Every name a condition may read: what the questions collect, what the
        codebook declares without a question (embedded data — a panel id, a
        sample cell), and what a script writes before the first page
        (``Script.assign_condition``)."""

        known = {key for question in self.all_questions() for key in question_answer_keys(question)}
        if self.variables is not None:
            known.update(self.variables.keys())
        known.update(self.assigned_variables())
        return known

    def assigned_variables(self) -> list[str]:
        """Variables the scripts write for every respondent, in script order."""

        names: list[str] = []
        for script in self.scripts:
            assigned = getattr(script, "assigns", None)
            if assigned and assigned not in names:
                names.append(assigned)
        return names

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
        warnings.extend(_piping_warnings(self))
        if level == "strict":
            warnings.extend(_strict_question_warnings(self.all_questions()))
            warnings.extend(_na_code_warnings(self))
            warnings.extend(_script_answer_key_warnings(self))
            warnings.extend(_script_target_scope_warnings(self))
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


def question_variable_names_of(question: Question) -> list[str]:
    return [variable.name for variable in _question_variables(question)]


def _require_code(value: Any, where: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        raise ValueError(f"{where} must be a number or a string, not {value!r}.")


def _same(a: Any, b: Any) -> bool:
    """Codes are compared as the runtime compares them: 1 and "1" are one code."""

    return a == b or str(a) == str(b)


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
        if isinstance(question, MaxDiff):
            # The version variable records which design was shown; it is filled
            # by the runtime, so it has no labels to declare and is not a
            # categorical answer in the sense this rule is about.
            warnings.extend(
                _categorical_label_warnings(
                    question_id, question.var[:-1] if question.choices is None else []
                )
            )
            warnings.extend(_maxdiff_warnings(question_id, question))
        if isinstance(question, Conjoint):
            warnings.extend(_conjoint_warnings(question_id, question))
    return warnings


def _script_answer_key_warnings(survey: Questionnaire) -> list[LintWarning]:
    """A custom script that goes on naming a question by an id the runtime
    will not know it by.

    Where a question's id is not its answer key, the compiler translates the
    script's target and the ``answers[…]`` / ``__errors__[…]`` /
    ``__options__[…]`` / ``__timers__[…]`` accesses that name the id, and
    nothing else — it cannot know what ``const q = "q1"`` or ``{q1: 1}`` is
    for. The author can, so each such id is reported, by script, rather than
    the script going dark in the field."""

    aliases = answer_key_aliases(survey.all_questions())
    if not aliases or not survey.scripts:
        return []
    # ``siamang.model`` builds on ``siamang.core``: import here, not at the top.
    from siamang.model.scripts import stale_answer_key_references

    warnings: list[LintWarning] = []
    for index, script in enumerate(survey.scripts):
        name = script.name or f"script #{index + 1}"
        for design_id in stale_answer_key_references(script, aliases):
            key = aliases[design_id]
            warnings.append(
                LintWarning(
                    code="SCRIPT_STALE_QUESTION_ID",
                    severity="warning",
                    message=(
                        f"Script '{name}' still names question '{design_id}' as a string or "
                        f"a bare identifier; its answer is stored under '{key}', and only the "
                        f"answers[…], __errors__[…], __options__[…] and __timers__[…] accesses "
                        f"of '{design_id}' are translated for the runtime. Where the script "
                        f"means the question, write '{key}'."
                    ),
                    location=name,
                )
            )
    return warnings


def _script_target_scope_warnings(survey: Questionnaire) -> list[LintWarning]:
    """A script whose target is the wrong kind of thing for its trigger.

    ``validate()`` accepts any question id, answer key or page name as a
    target. The runtime, though, matches an ``onQuestionShow`` / ``onAnswer``
    target against the question being shown or answered and an
    ``onPageEnter`` / ``onPageExit`` target against the page being entered or
    left — so a question-scoped script aimed at a page, or a page-scoped
    script aimed at a question, validates and is never dispatched. A name that
    is both a page's and a question's is not reported: it does match on its
    trigger's side."""

    if not survey.scripts:
        return []
    questions = survey.all_questions()
    question_names = {question_fallback_id(question) for question in questions}
    question_names |= {question_output_name(question) for question in questions}
    page_names = {page.name for page in (survey.pages or [])}
    warnings: list[LintWarning] = []
    for index, script in enumerate(survey.scripts):
        target = script.target
        if not target:
            continue
        name = script.name or f"script #{index + 1}"
        if (
            script.trigger in _QUESTION_SCOPED_TRIGGERS
            and target in page_names
            and target not in question_names
        ):
            warnings.append(
                LintWarning(
                    code="SCRIPT_TARGET_IS_A_PAGE",
                    severity="warning",
                    message=(
                        f"Script '{name}' runs on {script.trigger} but its target "
                        f"'{target}' is a page, not a question; the runtime dispatches "
                        f"{script.trigger} with the question's key, so the script would "
                        f"never run. Target a question, or use onPageEnter / onPageExit "
                        f"for page '{target}'."
                    ),
                    location=name,
                )
            )
        elif (
            script.trigger in _PAGE_SCOPED_TRIGGERS
            and target in question_names
            and target not in page_names
        ):
            warnings.append(
                LintWarning(
                    code="SCRIPT_TARGET_IS_A_QUESTION",
                    severity="warning",
                    message=(
                        f"Script '{name}' runs on {script.trigger} but its target "
                        f"'{target}' is a question, not a page; the runtime dispatches "
                        f"{script.trigger} with the page's name, so the script would "
                        f"never run. Target the page that holds question '{target}', or "
                        f"use onQuestionShow / onAnswer."
                    ),
                    location=name,
                )
            )
    return warnings


def _conjoint_warnings(question_id: str, question: Conjoint) -> list[LintWarning]:
    """What a conjoint can be configured into that cannot be estimated.

    The last of these is the one that costs money: a design with too few tasks
    for the number of levels cannot be fitted at all, and nobody finds out until
    fieldwork is over and the model will not converge. The design generator
    already knows — it computes the D-error and gets infinity — so the question
    is asked here, before anyone is interviewed.
    """

    warnings: list[LintWarning] = []
    if len(question.attributes) < 2:
        warnings.append(
            LintWarning(
                code="CONJOINT_TOO_FEW_ATTRIBUTES",
                severity="error",
                message=(
                    f"Conjoint '{question_id}' has {len(question.attributes)} attributes; a "
                    "trade-off needs at least two."
                ),
                location=question_id,
            )
        )
        return warnings
    if question.versions == 1:
        warnings.append(
            LintWarning(
                code="CONJOINT_SINGLE_VERSION",
                severity="warning",
                message=(
                    f"Conjoint '{question_id}' has one version of the design, so every "
                    "respondent sees the same products."
                ),
                location=question_id,
            )
        )
    try:
        balance = question.resolved_design().balance
    except ValueError:
        return warnings
    if balance is not None and balance.d_error is None:
        parameters = sum(len(a.levels) - 1 for a in question.attributes)
        warnings.append(
            LintWarning(
                code="CONJOINT_NOT_ESTIMABLE",
                severity="error",
                message=(
                    f"Conjoint '{question_id}' cannot be estimated: "
                    f"{question.tasks} task{'' if question.tasks == 1 else 's'} of "
                    f"{question.alternatives} across {question.versions} "
                    f"version{'' if question.versions == 1 else 's'} cannot pin down "
                    f"{parameters} part-worths. Add tasks, add versions, add alternatives, "
                    "or use fewer levels."
                ),
                location=question_id,
            )
        )
    return warnings


def _maxdiff_warnings(question_id: str, question: MaxDiff) -> list[LintWarning]:
    """What a MaxDiff can be configured into that cannot be estimated.

    A task showing every item is a complete design and teaches nothing about
    which items were preferred *over which*; too few items for the task size
    cannot be shown at all; and a single version means every respondent sees the
    same tasks, which is legal but rarely intended and worth saying once.
    """

    warnings: list[LintWarning] = []
    items = question.item_codes
    if len(items) < 3:
        warnings.append(
            LintWarning(
                code="MAXDIFF_TOO_FEW_ITEMS",
                severity="error",
                message=(
                    f"MaxDiff '{question_id}' has {len(items)} items; it needs at least three "
                    "for a best and a worst to mean anything."
                ),
                location=question_id,
            )
        )
    elif question.per_task >= len(items):
        warnings.append(
            LintWarning(
                code="MAXDIFF_COMPLETE_DESIGN",
                severity="error",
                message=(
                    f"MaxDiff '{question_id}' shows {question.per_task} of {len(items)} items per "
                    "task, so every task shows everything: nothing is learned from which items "
                    "met. Show fewer items per task."
                ),
                location=question_id,
            )
        )
    if question.versions == 1:
        warnings.append(
            LintWarning(
                code="MAXDIFF_SINGLE_VERSION",
                severity="warning",
                message=(
                    f"MaxDiff '{question_id}' has one version of the design, so every respondent "
                    "sees the same tasks. More versions cover more of the item space."
                ),
                location=question_id,
            )
        )
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


def _added_code_warnings(question: Question, question_id: str, bound) -> list[LintWarning]:
    """The codes the runtime adds to a question's own — Other, None of the
    above, Not applicable — should be in its codebook, or they arrive in the
    data with no text (Other, None) or as text in a numeric column (N/A)."""

    warnings: list[LintWarning] = []
    added: list[tuple[str, Any]] = []
    if (
        question.other_specify
        and isinstance(question, SingleChoice | MultiChoice)
        and not isinstance(question.var, list)
    ):
        added.append(("“Other (please specify)”", other_code(question)))
    if isinstance(question, SingleChoice) and question.none_of_above:
        added.append(("“None of the above”", none_code(question)))
    if bound is not None and bound.labels:
        for what, code in added:
            if not _known(code, _variable_codes(bound)):
                warnings.append(
                    LintWarning(
                        code="ADDED_CODE_WITHOUT_LABEL",
                        severity="warning",
                        message=(
                            f"Question '{question_id}' stores {what} as {code!r}, which "
                            f"variable '{bound.name}' has no value label for."
                        ),
                        location=question_id,
                    )
                )
    return warnings


def _na_code_warnings(survey: Questionnaire) -> list[LintWarning]:
    """An N/A answer without a declared ``not_applicable`` code is stored as
    the text "na" — safe, since no mean takes it in, but not a code of the
    variable. Advice for strict lint rather than a defect."""

    warnings: list[LintWarning] = []
    for question in survey.all_questions():
        if not getattr(question, "na_option", False):
            continue
        if not isinstance(question, LikertScale | Matrix):
            continue
        undeclared = [v.name for v in _question_variables(question) if na_code(v) is None]
        if undeclared:
            question_id = question_fallback_id(question)
            warnings.append(
                LintWarning(
                    code="NA_STORED_AS_TEXT",
                    severity="warning",
                    message=(
                        f"Question '{question_id}' offers “Not applicable”, stored as the "
                        f"text 'na' because {', '.join(repr(n) for n in undeclared)} "
                        "declares no missing value of kind not_applicable; declare one "
                        "(and label it) to store its code."
                    ),
                    location=question_id,
                )
            )
    return warnings


def _compared_values(node):
    """Yield ``(variable_name, value)`` for each literal compared to a variable."""

    if not isinstance(node, Expression):
        return
    # `contains` belongs here for the same reason as the rest: a code that no
    # longer exists makes the branch unreachable, and a multiple-choice screener
    # is exactly where nobody notices.
    comparisons = {"=", "!=", "in", "not in", "contains", "not contains"}
    if node.op in comparisons and isinstance(node.left, VarRef):
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


_PIPE_RE = re.compile(r"\{(answer|var|label):([A-Za-z0-9_]+)\}")


def _piping_warnings(survey: Questionnaire) -> list[LintWarning]:
    """Piped text — ``{answer:var}``, ``{label:var}`` in a question's text,
    hint or a page's title / body — must name a variable that exists and is
    answered on an earlier page (or earlier on the same page); otherwise the
    respondent sees the placeholder itself."""

    warnings: list[LintWarning] = []
    known = set(survey.variables.keys()) if survey.variables else set()
    # An assigned arm is written before the first page, so it is never a
    # forward reference — it may be piped anywhere.
    assigned = set(survey.assigned_variables())
    known |= assigned
    seen: set[str] = set(assigned)
    pages = survey.pages or []
    if not pages:
        for question in survey.all_questions():
            known.update(question_answer_keys(question))
        pages_items: list[tuple[str, list[tuple[str, str | None]], list[Question]]] = [
            ("questionnaire", [], survey.all_questions())
        ]
    else:
        for question in survey.all_questions():
            known.update(question_answer_keys(question))
        pages_items = [
            (
                page.name,
                [(page.title or "", "title"), (page.body or "", "body")],
                page.flatten_questions(),
            )
            for page in pages
        ]
    for location, texts, questions in pages_items:
        for text, _what in texts:
            for kind, name in _PIPE_RE.findall(text or ""):
                if name not in known:
                    warnings.append(
                        LintWarning(
                            code="PIPE_UNKNOWN_VARIABLE",
                            severity="warning",
                            message=(
                                f"Page '{location}' pipes {{{kind}:{name}}}, but no variable "
                                f"'{name}' exists; the respondent will see the placeholder."
                            ),
                            location=location,
                        )
                    )
                elif name not in seen:
                    warnings.append(
                        LintWarning(
                            code="PIPE_FORWARD_REFERENCE",
                            severity="warning",
                            message=(
                                f"Page '{location}' pipes {{{kind}:{name}}} before '{name}' is "
                                "answered; it stays empty on this page."
                            ),
                            location=location,
                        )
                    )
        for question in questions:
            question_id = question_fallback_id(question)
            for field_text in (question.text or "", question.hint or ""):
                for kind, name in _PIPE_RE.findall(field_text):
                    if name not in known:
                        warnings.append(
                            LintWarning(
                                code="PIPE_UNKNOWN_VARIABLE",
                                severity="warning",
                                message=(
                                    f"Question '{question_id}' pipes {{{kind}:{name}}}, but no "
                                    f"variable '{name}' exists; the respondent will see the "
                                    "placeholder."
                                ),
                                location=question_id,
                            )
                        )
                    elif name not in seen:
                        warnings.append(
                            LintWarning(
                                code="PIPE_FORWARD_REFERENCE",
                                severity="warning",
                                message=(
                                    f"Question '{question_id}' pipes {{{kind}:{name}}} before "
                                    f"'{name}' is answered; it stays empty there."
                                ),
                                location=question_id,
                            )
                        )
            seen.update(question_answer_keys(question))
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

        warnings.extend(_added_code_warnings(question, question_id, bound))

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
