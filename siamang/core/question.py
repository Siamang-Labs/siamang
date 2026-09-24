"""Question abstractions and concrete question types."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from siamang.core.attribute import Attribute
from siamang.core.media import Media
from siamang.core.option import Option
from siamang.core.variable import Variable


@dataclass(frozen=True, slots=True)
class Question:
    """Base question binding a prompt to one variable (or many for matrix)."""

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
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("Question text must not be empty.")
        if self.id is not None and not self.id.strip():
            raise ValueError("Question id must not be empty when provided.")
        if self.name is not None and not self.name.strip():
            raise ValueError("Question name must not be empty when provided.")
        if self.media is not None:
            items = self.media if isinstance(self.media, list) else [self.media]
            for item in items:
                if not isinstance(item, Media):
                    raise TypeError("Question.media must be Media or list[Media].")


@dataclass(frozen=True, slots=True)
class SingleChoice(Question):
    display: str = "radio"
    none_of_above: bool = False
    choices: list[Option] | None = None

    def __post_init__(self) -> None:
        Question.__post_init__(self)
        if self.display not in {"radio", "dropdown", "buttons"}:
            raise ValueError("display must be one of: radio, dropdown, buttons")
        if not isinstance(self.var, Variable):
            raise TypeError("SingleChoice expects var to be a Variable.")
        _validate_choices(self.choices)


@dataclass(frozen=True, slots=True, init=False)
class MultiChoice(Question):
    min_answers: int = 1
    max_answers: int | None = None
    exclusive: list[int] = field(default_factory=list)
    mode: str = "array"
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
    ) -> None:
        if vars is not None:
            if var is not None:
                raise ValueError("Use either 'var' or 'vars' for MultiChoice, not both.")
            var = vars
            mode = "wide"
        if var is None:
            raise TypeError("MultiChoice requires 'var' for array mode or 'vars' for wide mode.")
        object.__setattr__(self, "text", text)
        object.__setattr__(self, "var", var)
        object.__setattr__(self, "required", required)
        object.__setattr__(self, "hint", hint)
        object.__setattr__(self, "show_if", show_if)
        object.__setattr__(self, "hide_if", hide_if)
        object.__setattr__(self, "skip_to", skip_to)
        object.__setattr__(self, "randomize", randomize)
        object.__setattr__(self, "other_specify", other_specify)
        object.__setattr__(self, "tag", tag)
        object.__setattr__(self, "id", id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "media", media)
        object.__setattr__(self, "metadata", dict(metadata or {}))
        object.__setattr__(self, "min_answers", min_answers)
        object.__setattr__(self, "max_answers", max_answers)
        object.__setattr__(self, "exclusive", list(exclusive or []))
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "choices", list(choices) if choices is not None else None)
        self.__post_init__()

    def __post_init__(self) -> None:
        Question.__post_init__(self)
        if self.mode not in {"array", "wide"}:
            raise ValueError("MultiChoice mode must be either 'array' or 'wide'.")
        if self.mode == "array" and not isinstance(self.var, Variable):
            raise TypeError("MultiChoice array mode expects var to be a Variable.")
        if self.mode == "wide" and (not isinstance(self.var, list) or not self.var):
            raise TypeError(
                "MultiChoice wide mode expects vars to be a non-empty list of Variables."
            )
        if self.mode == "wide" and self.var and any(not isinstance(v, Variable) for v in self.var):
            raise TypeError("MultiChoice wide mode vars must contain only Variable instances.")
        if self.min_answers < 0:
            raise ValueError("min_answers must be >= 0")
        if self.max_answers is not None and self.max_answers < self.min_answers:
            raise ValueError("max_answers must be >= min_answers")
        if (
            self.mode == "wide"
            and self.max_answers is not None
            and self.max_answers > len(self.var)
        ):
            raise ValueError("max_answers cannot exceed number of wide-mode variables")
        _validate_choices(self.choices)


@dataclass(frozen=True, slots=True)
class LikertScale(Question):
    """A numbered scale. ``start`` is the first point's value (1 by default;
    0 for an NPS-style 0–10 scale), ``display`` its rendering: numbered
    buttons (``scale``) or stars (``stars``)."""

    points: int = 5
    left_label: str | None = None
    right_label: str | None = None
    na_option: bool | str = False
    start: int = 1
    display: str = "scale"

    def __post_init__(self) -> None:
        Question.__post_init__(self)
        if not isinstance(self.var, Variable):
            raise TypeError("LikertScale expects var to be a Variable.")
        if self.points < 2:
            raise ValueError("points must be >= 2")
        if self.start not in (0, 1):
            raise ValueError("start must be 0 or 1")
        if self.display not in {"scale", "stars"}:
            raise ValueError("display must be one of: scale, stars")

    @property
    def values(self) -> list[int]:
        """The scale's values in order (``start`` … ``start + points - 1``)."""
        return list(range(self.start, self.start + self.points))


@dataclass(frozen=True, slots=True)
class NumericInput(Question):
    display: str = "input"
    unit: str | None = None
    step: int | float = 1

    def __post_init__(self) -> None:
        Question.__post_init__(self)
        if not isinstance(self.var, Variable):
            raise TypeError("NumericInput expects var to be a Variable.")
        if self.display not in {"input", "slider"}:
            raise ValueError("display must be one of: input, slider")
        if self.step <= 0:
            raise ValueError("step must be > 0")


#: What an OpenText answer must look like; the runtime picks the input type
#: and refuses a value that does not match on "Next".
TEXT_FORMATS = ("text", "email", "phone", "url", "date", "time")


@dataclass(frozen=True, slots=True)
class OpenText(Question):
    multiline: bool = False
    max_chars: int | None = None
    placeholder: str | None = None
    format: str = "text"

    def __post_init__(self) -> None:
        Question.__post_init__(self)
        if not isinstance(self.var, Variable):
            raise TypeError("OpenText expects var to be a Variable.")
        if self.max_chars is not None and self.max_chars <= 0:
            raise ValueError("max_chars must be > 0")
        if self.format not in TEXT_FORMATS:
            raise ValueError("format must be one of: " + ", ".join(TEXT_FORMATS))
        if self.multiline and self.format != "text":
            raise ValueError("a multiline answer cannot have a format")


@dataclass(frozen=True, slots=True)
class Matrix(Question):
    var: list[Variable]
    subquestions: list[str] | None = None
    column_labels: list[str] | None = None
    na_option: bool | str = False

    def __post_init__(self) -> None:
        Question.__post_init__(self)
        if not self.var:
            raise ValueError("Matrix requires at least one variable")
        if any(not isinstance(v, Variable) for v in self.var):
            raise TypeError("Matrix var must contain only Variable instances")
        # Statements and variables are matched by position, so a length mismatch
        # records answers under the wrong statement without anything looking wrong.
        if self.subquestions is not None and len(self.subquestions) != len(self.var):
            raise ValueError(
                f"Matrix has {len(self.subquestions)} subquestions but {len(self.var)} "
                "variables; they are matched by position and must be the same length."
            )

    def columns(self) -> list[tuple[Any, str]]:
        """The answer columns as ``(code, header)`` pairs, in display order.

        A cell stores a code of the row variables' codebook, the value a
        condition, a quota and the analysis read — not the column's position.
        Without ``column_labels`` the columns are the first row variable's value
        labels in code order, less the not_applicable code ``na_option`` offers
        in a column of its own. With them, each header's code comes from that
        codebook too: the value label whose text is the header, when every
        header names exactly one label; else the label in the same position,
        when there are as many labels as headers (a 0–10 scale headed ``0`` …
        ``10`` over labels ``No trust`` … ``Complete trust``); else the same
        with the codebook's declared missing codes (a not_applicable, refusal or
        don't know) set apart — a header that names one of them takes its code,
        and the others line up with the rest of the labels; else — the codebook
        says nothing usable — 1, 2, 3 … in column order.
        """

        first = self.var[0]
        labels = dict(getattr(first, "labels", None) or {})
        if self.column_labels is None:
            if self.na_option and na_code(first) is not None:
                # na_option's own column stores it; as a scale column it would
                # be offered twice, the first time in the middle of the scale.
                labels.pop(na_code(first), None)
            try:
                ordered = sorted(labels.items())
            except TypeError:  # codes of mixed types: keep the authored order
                ordered = list(labels.items())
            return [(code, str(label)) for code, label in ordered]
        headers = [str(header) for header in self.column_labels]
        by_text: dict[str, list[Any]] = {}
        for code, label in labels.items():
            by_text.setdefault(str(label), []).append(code)
        if headers and all(len(by_text.get(header, ())) == 1 for header in headers):
            codes = [by_text[header][0] for header in headers]
            if len(set(map(repr, codes))) == len(codes):
                return list(zip(codes, headers, strict=True))
        if len(labels) == len(headers):
            return list(zip(labels, headers, strict=True))
        placed = _columns_beside_missing(headers, labels, first)
        if placed is not None:
            return placed
        return [(index + 1, header) for index, header in enumerate(headers)]


def _columns_beside_missing(
    headers: list[str], labels: dict[Any, str], variable: Variable
) -> list[tuple[Any, str]] | None:
    """Headers placed on a codebook that also labels missing codes: a header
    naming one missing code's label takes it, and the other headers line up,
    in order, with the labels that are not missing codes — when there are as
    many of each. None when the codebook declares no missing code or does not
    line up."""

    missing = list(getattr(variable, "missing_values", ()) or ())
    if not missing:
        return None
    missing_labels = getattr(variable, "missing_labels", None) or {}
    by_text: dict[str, list[Any]] = {}
    for code in missing:
        text = labels.get(code, missing_labels.get(code))
        if text is not None:
            by_text.setdefault(str(text), []).append(code)
    scale = [code for code in labels if code not in missing]
    rest = [index for index, header in enumerate(headers) if len(by_text.get(header, ())) != 1]
    if len(rest) != len(scale):
        return None
    codes: list[Any] = [
        by_text[header][0] if len(by_text.get(header, ())) == 1 else None for header in headers
    ]
    for index, code in zip(rest, scale, strict=True):
        codes[index] = code
    if len(set(map(repr, codes))) != len(codes):
        return None
    return list(zip(codes, headers, strict=True))


@dataclass(frozen=True, slots=True)
class Ranking(Question):
    max_ranked: int | None = None
    choices: list[Option] | None = None

    def __post_init__(self) -> None:
        Question.__post_init__(self)
        if not isinstance(self.var, Variable):
            raise TypeError("Ranking expects var to be a Variable.")
        if self.max_ranked is not None and self.max_ranked <= 0:
            raise ValueError("max_ranked must be > 0")
        _validate_choices(self.choices)


@dataclass(frozen=True, slots=True)
class MaxDiff(Question):
    """Best–worst scaling: a few items at a time, the best and the worst of them.

    Asking people to rate twenty things gets twenty ratings that all cluster at
    the top, because nothing forces a choice. MaxDiff shows four at a time and
    asks which is best and which is worst; the trade-off is the measurement.

    The items come from the answer variables' labels, the way a matrix takes its
    columns from ``var[0]`` — each task's answer *is* one of the items — and
    ``choices`` overrides them when a question needs its own labels or media.

    ``var`` holds ``2 * tasks + 1`` variables: best and worst for each task, and
    last the version of the design this respondent was shown. The version is a
    variable rather than bookkeeping because without it the answers cannot be
    read: knowing somebody picked item 7 says nothing until you know what 7 was
    up against.
    """

    var: list[Variable]
    choices: list[Option] | None = None
    per_task: int = 4
    tasks: int = 8
    versions: int = 20
    seed: int | None = None
    best_label: str = "Best"
    worst_label: str = "Worst"
    design: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        Question.__post_init__(self)
        if not isinstance(self.var, list) or not self.var:
            raise TypeError("MaxDiff expects var to be a list of Variables.")
        if any(not isinstance(v, Variable) for v in self.var):
            raise TypeError("MaxDiff var must contain only Variable instances")
        expected = 2 * self.tasks + 1
        if len(self.var) != expected:
            raise ValueError(
                f"MaxDiff with {self.tasks} tasks needs {expected} variables "
                f"(best and worst for each task, then the design version) "
                f"but has {len(self.var)}."
            )
        if self.tasks < 1:
            raise ValueError("MaxDiff needs at least one task.")
        if self.versions < 1:
            raise ValueError("MaxDiff needs at least one version of the design.")
        if self.per_task < 2:
            raise ValueError(
                "A MaxDiff task must show at least two items — one has nothing " "to beat."
            )
        _validate_choices(self.choices)

    @property
    def item_codes(self) -> list[Any]:
        """The pool the design draws from: explicit choices, else the labels."""

        if self.choices:
            return [option.code for option in self.choices]
        return list(self.var[0].labels or {})

    @property
    def version_variable(self) -> Variable:
        """The variable recording which version of the design was shown."""

        return self.var[-1]

    def task_variables(self, task: int) -> tuple[Variable, Variable]:
        """The (best, worst) variables of task ``task``, counting from zero."""

        return self.var[2 * task], self.var[2 * task + 1]

    def resolved_design(self):
        """The stored design, or the one this question's parameters imply.

        Studio freezes the design into the document at Save, so it is visible,
        diffable and carried into the snapshot. Generating it here when it is
        absent means a hand-written questionnaire still works — and gives the
        same design every time, because the seed is the questionnaire's.
        """

        from siamang.design import MaxDiffDesign, maxdiff_design

        if self.design:
            return MaxDiffDesign.from_dict(self.design)
        return maxdiff_design(
            self.item_codes,
            per_task=self.per_task,
            tasks=self.tasks,
            versions=self.versions,
            seed=self.seed if self.seed is not None else self._implied_seed(),
        )

    def _implied_seed(self) -> int:
        """A seed derived from the question, for authors who did not pick one.

        Without it ``seed=None`` would mean a fresh design on every compile: the
        survey a respondent answered and the design the analysis reads it against
        would be different tables, and nothing would say so. Derived from the
        question's own identity and shape, so it is stable across processes and
        machines — and changes when the question does, which is right, because a
        question with different items is a different question.
        """

        from hashlib import blake2b

        material = "|".join(
            str(part)
            for part in (
                self.id or self.name or self.var[0].name,
                self.per_task,
                self.tasks,
                self.versions,
                *self.item_codes,
            )
        )
        return int.from_bytes(blake2b(material.encode("utf-8"), digest_size=4).digest(), "big")


@dataclass(frozen=True, slots=True)
class Conjoint(Question):
    """Choice-based conjoint: whole products, side by side, pick one.

    Asking how important price is gets an answer everybody gives the same way.
    Showing three products that differ in price *and* in everything else, and
    asking which one they would buy, makes the respondent spend something to
    get something — and what they gave up is the measurement.

    ``var`` holds one variable per task, recording which alternative was chosen,
    plus one last for the version of the design shown. One per task rather than
    one per attribute: the answer *is* the choice, and which levels that choice
    carried is in the design.

    ``none_label`` adds a "none of these" alternative. It is off by default,
    because it changes what the question measures — with it, shares are of the
    market including people who buy nothing, and without it they are shares of
    those who buy something.
    """

    var: list[Variable]
    attributes: list[Attribute] = field(default_factory=list)
    alternatives: int = 3
    tasks: int = 10
    versions: int = 20
    seed: int | None = None
    none_label: str | None = None
    design: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        Question.__post_init__(self)
        if not isinstance(self.var, list) or not self.var:
            raise TypeError("Conjoint expects var to be a list of Variables.")
        if any(not isinstance(v, Variable) for v in self.var):
            raise TypeError("Conjoint var must contain only Variable instances")
        expected = self.tasks + 1
        if len(self.var) != expected:
            raise ValueError(
                f"Conjoint with {self.tasks} tasks needs {expected} variables (one per task, "
                f"then the design version) but has {len(self.var)}."
            )
        if self.tasks < 1:
            raise ValueError("Conjoint needs at least one task.")
        if self.versions < 1:
            raise ValueError("Conjoint needs at least one version of the design.")
        if self.alternatives < 2:
            raise ValueError("A choice task needs at least two alternatives to choose between.")
        if any(not isinstance(a, Attribute) for a in self.attributes):
            raise TypeError("Conjoint attributes must be Attribute instances.")
        names = [a.name for a in self.attributes]
        if len(set(names)) != len(names):
            raise ValueError("Conjoint attributes must have distinct names.")

    @property
    def version_variable(self) -> Variable:
        return self.var[-1]

    def task_variable(self, task: int) -> Variable:
        """The variable recording which alternative was chosen in ``task``."""

        return self.var[task]

    def profile_labels(self, profile: Sequence[Any]) -> list[str]:
        """A profile as the lines a respondent reads, attribute by attribute."""

        return [
            attribute.label_of(value)
            for attribute, value in zip(self.attributes, profile, strict=True)
        ]

    def resolved_design(self):
        """The stored design, or the one this question's parameters imply."""

        from siamang.design import CbcDesign, cbc_design

        if self.design:
            return CbcDesign.from_dict(self.design)
        if len(self.attributes) < 2:
            raise ValueError(
                f"Conjoint {self.id or self.var[0].name!r} needs at least two attributes "
                "to trade off against each other."
            )
        return cbc_design(
            [attribute.name for attribute in self.attributes],
            [attribute.codes for attribute in self.attributes],
            alternatives=self.alternatives,
            tasks=self.tasks,
            versions=self.versions,
            seed=self.seed if self.seed is not None else self._implied_seed(),
        )

    def _implied_seed(self) -> int:
        """As MaxDiff: an unset seed must not mean a different design each time."""

        from hashlib import blake2b

        material = "|".join(
            str(part)
            for part in (
                self.id or self.name or self.var[0].name,
                self.alternatives,
                self.tasks,
                self.versions,
                *(f"{a.name}:{','.join(map(str, a.codes))}" for a in self.attributes),
            )
        )
        return int.from_bytes(blake2b(material.encode("utf-8"), digest_size=4).digest(), "big")


def _validate_choices(choices: list[Option] | None) -> None:
    if choices is None:
        return
    if not isinstance(choices, list):
        raise TypeError("choices must be a list of Option instances.")
    if not choices:
        raise ValueError("choices must not be an empty list.")
    seen: set[Any] = set()
    for choice in choices:
        if not isinstance(choice, Option):
            raise TypeError("All entries in choices must be Option instances.")
        if choice.code in seen:
            raise ValueError(f"Duplicate option code in choices: {choice.code!r}.")
        seen.add(choice.code)


def question_variable_names(question: Question) -> list[str]:
    variables = question.var if isinstance(question.var, list) else [question.var]
    return [variable.name for variable in variables]


def question_fallback_id(question: Question) -> str:
    if question.id is not None:
        return question.id
    if question.name is not None:
        return question.name
    if isinstance(question, Matrix):
        return "matrix_" + question.var[0].name
    if isinstance(question, MultiChoice) and question.mode == "wide":
        return "multi_" + question.var[0].name
    if isinstance(question, MaxDiff):
        return "maxdiff_" + question.var[0].name
    if isinstance(question, Conjoint):
        return "conjoint_" + question.var[0].name
    return question_variable_names(question)[0]


def question_output_name(question: Question) -> str:
    """The runtime's item ``id`` — for most questions, the key the answer is
    stored under.

    For a question that writes exactly one variable, that variable: the column
    the codebook describes, the name a condition, a quota or ``{answer:…}``
    reads. An explicit ``name`` does not override it — ``validate()`` rejects
    a single-variable question whose ``name`` is not its variable's name,
    because the answer would then sit under a key that nothing reading the
    variable looks at. A Matrix, a wide MultiChoice, a MaxDiff or a Conjoint
    writes several variables, so its item id is its ``name`` or else its id —
    the handle a script targets and an error is keyed by — while the runtime
    stores each of its variables under the variable's own name and nothing
    under the item id.

    The author-facing ``id`` is a different thing (``question_fallback_id``):
    the runtime carries it as ``qid`` for design mode and script targets.
    """
    if not isinstance(question.var, list):
        return question.var.name
    if question.name:
        return question.name
    return question_fallback_id(question)


def answer_key_aliases(questions: Iterable[Question]) -> dict[str, str]:
    """Design-time question id → answer key, for the questions where the two
    differ (``question_fallback_id`` vs ``question_output_name``).

    Empty for a survey whose ids are its variable names — the common case, in
    which nothing that names a question needs translating for the runtime.
    """
    aliases: dict[str, str] = {}
    for question in questions:
        design_id = question_fallback_id(question)
        key = question_output_name(question)
        if design_id != key:
            aliases[design_id] = key
    return aliases


# ── Codes the runtime adds to a question's own ───────────────────────────────
#
# "Other (please specify)", a SingleChoice's "None of the above" and the "Not
# applicable" of a scale or a matrix are answers too, and they are stored as
# codes of the question's variable, like every other answer: a column that
# mixes 1, 2, 3 with "__other__" or "na" is a column no analysis can type.

#: What "Other (please specify)" stores unless the question's
#: ``metadata["other_code"]`` names a code. Negative, so it cannot collide with a
#: choice list coded 0, 1, 2 …; the typed text is stored apart, under
#: :func:`other_text_key`.
DEFAULT_OTHER_CODE = -66

#: What a SingleChoice's "None of the above" stores unless the question's
#: ``metadata["none_code"]`` names a code.
DEFAULT_NONE_CODE = -77


def other_code(question: Question) -> Any:
    """The code a question's "Other (please specify)" stores.

    ``metadata["other_code"]`` when the question sets it — which may be the code
    of one of its own choices, and that choice then *is* the Other option: it
    gets the text box, and no extra option is added — else
    :data:`DEFAULT_OTHER_CODE`.
    """

    return (question.metadata or {}).get("other_code", DEFAULT_OTHER_CODE)


def none_code(question: Question) -> Any:
    """The code a SingleChoice's "None of the above" stores:
    ``metadata["none_code"]``, else :data:`DEFAULT_NONE_CODE`."""

    return (question.metadata or {}).get("none_code", DEFAULT_NONE_CODE)


def other_text_key(question: Question) -> str:
    """Where the text typed into "Other (please specify)" is stored:
    ``<variable>_other`` — for a wide MultiChoice, ``<name or id>_other``."""

    return f"{question_output_name(question)}_other"


def na_code(variable: Variable) -> Any | None:
    """The code a "Not applicable" answer stores for ``variable``: the first
    missing value the codebook declares with kind ``not_applicable``, or None
    when it declares none — the runtime then stores the text ``"na"``, as it
    always has, rather than a number the analysis would average in."""

    for missing in variable.missing:
        if missing.kind == "not_applicable":
            return missing.code
    return None


def choice_codes(question: Question) -> list[Any]:
    """The codes a choice question offers: its ``choices``, else its (single)
    variable's value labels. Empty for a wide MultiChoice without choices."""

    choices = getattr(question, "choices", None)
    if choices:
        return [option.code for option in choices]
    if isinstance(question.var, list):
        return []
    return list(question.var.labels or {})


def question_answer_keys(question: Question) -> list[str]:
    """Every key the runtime stores for ``question``: its variables, and the
    "Other (please specify)" text when it offers one."""

    keys = question_variable_names(question)
    if question.other_specify and isinstance(question, SingleChoice | MultiChoice):
        keys.append(other_text_key(question))
    return keys
