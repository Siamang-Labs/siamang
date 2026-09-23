"""Questionnaire validation and lint rules.

Covers the hard errors raised by `Questionnaire.validate()`, the findings
returned by `Questionnaire.lint()`, and `validate_options()` — the check that
compiler-level quotas actually match the questionnaire they ship with.
"""

import pytest

from siamang.core import (
    AND,
    Attribute,
    Conjoint,
    ContentPage,
    Expression,
    FinalPage,
    LikertScale,
    Matrix,
    MaxDiff,
    MissingValue,
    MultiChoice,
    OpenText,
    Option,
    Page,
    Questionnaire,
    Quota,
    SingleChoice,
    Variable,
    compare,
    validate_options,
)

AGREE5 = {1: "Strongly disagree", 2: "Disagree", 3: "Neutral", 4: "Agree", 5: "Strongly agree"}


def _news() -> Variable:
    return Variable(
        "news_source",
        "nominal",
        labels={
            1: "Social media",
            2: "News apps",
            3: "TV / radio",
            4: "Friends",
            5: "I avoid news",
        },
    )


def _trust() -> Variable:
    return Variable("trust_news", "ordinal", labels=AGREE5)


def _survey(*items, **page_kwargs) -> Questionnaire:
    """A one-page questionnaire named 'habits' — the location used in messages."""

    return Questionnaire(title="T", pages=[Page("habits", items=list(items), **page_kwargs)])


def _codes(findings) -> list[str]:
    return [finding.code for finding in findings]


# ── V1: quotas ────────────────────────────────────────────────────────────────


def _quota_survey() -> Questionnaire:
    age_group = Variable("age_group", "ordinal", labels={1: "16-29", 2: "30-44", 3: "45+"})
    return _survey(SingleChoice("Age group?", age_group))


def test_valid_quotas_pass():
    validate_options(
        _quota_survey(), {"quota": [Quota("age_group", 1, 400), Quota("age_group", 2, 400)]}
    )  # must not raise


def test_quota_on_unknown_variable_rejected():
    with pytest.raises(ValueError, match="unknown variable: age_grp"):
        validate_options(_quota_survey(), {"quota": [Quota("age_grp", 1, 400)]})


def test_quota_on_undefined_category_rejected():
    with pytest.raises(ValueError, match="not a defined category"):
        validate_options(_quota_survey(), {"quota": [Quota("age_group", 7, 400)]})


def test_quota_with_non_positive_limit_rejected():
    with pytest.raises(ValueError, match="limit must be > 0"):
        validate_options(_quota_survey(), {"quota": [Quota("age_group", 1, 0)]})


def test_duplicate_quota_cell_rejected():
    with pytest.raises(ValueError, match="Duplicate quota"):
        validate_options(
            _quota_survey(), {"quota": [Quota("age_group", 1, 400), Quota("age_group", 1, 200)]}
        )


def test_plural_quotas_key_rejected():
    """The compiler reads options["quota"]; the plural spelling is dropped."""

    with pytest.raises(ValueError, match="the compiler reads 'quota'"):
        validate_options(_quota_survey(), {"quotas": [Quota("age_group", 1, 400)]})


def test_non_quota_entry_rejected():
    with pytest.raises(ValueError, match="must contain Quota objects"):
        validate_options(_quota_survey(), {"quota": [{"variable": "age_group"}]})


@pytest.mark.parametrize("options", [None, {}, {"language": "en"}, {"quota": []}])
def test_options_without_quotas_are_skipped(options):
    validate_options(_quota_survey(), options)  # must not raise


def test_quota_on_unlabelled_variable_is_allowed():
    """An external panel code has no entry in labels; that stays legal."""

    panel = Variable("panel_cell", "nominal")
    survey = _survey(SingleChoice("Cell?", panel))
    validate_options(survey, {"quota": [Quota("panel_cell", "A7", 400)]})  # must not raise


# ── V3: next_if conditions ────────────────────────────────────────────────────


def test_next_if_condition_referencing_unknown_variable_rejected():
    gone = Variable("gone", "nominal", labels={1: "a"})
    pages = [
        Page("a", items=[SingleChoice("News?", _news())], next_if=[(gone.eq(1), "b")]),
        Page("b", items=[SingleChoice("Trust?", _trust())]),
    ]
    with pytest.raises(ValueError, match="next_if references unknown variables: gone"):
        Questionnaire(title="T", pages=pages).validate()


def test_valid_next_if_condition_passes():
    news = _news()
    pages = [
        Page("a", items=[SingleChoice("News?", news)], next_if=[(news.eq(1), "b")]),
        Page("b", items=[SingleChoice("Trust?", _trust())]),
    ]
    Questionnaire(title="T", pages=pages).validate()  # must not raise


# ── V5: question identity in messages ─────────────────────────────────────────


def test_condition_error_names_the_question_not_a_placeholder():
    """Questions are normally declared without id=/name=; the message must still
    identify them by their variable rather than by '?'."""

    question = SingleChoice("Trust?", _trust(), show_if=compare("nope", "=", 1))
    survey = _survey(SingleChoice("News?", _news()), question)
    with pytest.raises(ValueError) as excinfo:
        survey.validate()
    assert "Question 'trust_news'" in str(excinfo.value)
    assert "'?'" not in str(excinfo.value)


# ── V12: raw expressions report why ───────────────────────────────────────────


def test_raw_expression_reports_its_reason():
    question = SingleChoice("Trust?", _trust(), show_if=Expression.raw("{news_source} > 1"))
    with pytest.raises(ValueError, match="Raw string expressions cannot be validated safely"):
        _survey(SingleChoice("News?", _news()), question).validate()


# ── V8: matrix statements match variables ─────────────────────────────────────


def _matrix_vars(n: int) -> list[Variable]:
    return [Variable(f"item{i}", "ordinal", labels={1: "Never", 2: "Always"}) for i in range(n)]


def test_matrix_subquestion_count_must_match_variables():
    with pytest.raises(ValueError, match="matched by position"):
        Matrix("How often?", var=_matrix_vars(3), subquestions=["a", "b"])


def test_matrix_accepts_matching_subquestions_and_none():
    Matrix("How often?", var=_matrix_vars(3), subquestions=["a", "b", "c"])  # must not raise
    Matrix("How often?", var=_matrix_vars(3))  # must not raise


# ── V2: answer codes used in conditions ───────────────────────────────────────


def test_condition_on_removed_answer_code_is_reported():
    news = _news()
    question = LikertScale("Trust?", _trust(), show_if=news.isin([1, 2, 7]))
    findings = _survey(SingleChoice("News?", news), question).lint()
    assert _codes(findings) == ["UNKNOWN_CONDITION_VALUE"]
    assert findings[0].message == (
        "Question 'trust_news' in page 'habits' show_if references value 7, which is not "
        "a defined category of 'news_source' (1, 2, 3, 4, 5)"
    )
    assert findings[0].severity == "warning"


def test_condition_on_existing_answer_codes_is_quiet():
    news = _news()
    question = LikertScale("Trust?", _trust(), show_if=news.isin([1, 2, 3]))
    assert _survey(SingleChoice("News?", news), question).lint() == []


def test_condition_on_numeric_variable_is_quiet():
    """A ratio variable is compared against numbers, not against categories."""

    age = Variable("age", "ratio", label="Age", labels={1: "coded"})
    news = _news()
    question = SingleChoice("News?", news, show_if=age.eq(40))
    assert _survey(SingleChoice("Age?", age), question).lint() == []


def test_condition_reaches_into_composed_expressions():
    news = _news()
    trust = _trust()
    question = SingleChoice("Q?", trust, show_if=AND(news.eq(1), trust.eq(9)))
    findings = _survey(SingleChoice("News?", news), question).lint()
    assert _codes(findings) == ["UNKNOWN_CONDITION_VALUE"]
    assert "'trust_news'" in findings[0].message


def test_explicit_option_codes_satisfy_a_condition():
    """choices shadow the variable's labels at runtime, so a rule may name them.

    The extra code still earns an OPTION_CODE_WITHOUT_LABEL — that is the right
    complaint about it — but the condition itself is not the problem.
    """

    panel = Variable("panel", "nominal", labels={1: "One"})
    news = _news()
    question = SingleChoice("News?", news, show_if=panel.eq(2))
    asked = SingleChoice("Panel?", panel, choices=[Option(1, "One"), Option(2, "Two")])
    assert "UNKNOWN_CONDITION_VALUE" not in _codes(_survey(asked, question).lint())


# ── V6: exclusive codes ───────────────────────────────────────────────────────


def test_exclusive_code_absent_from_answers_is_reported():
    manage = Variable("manage", "nominal", labels={1: "Limits", 2: "Meals"})
    findings = _survey(MultiChoice("Manage?", manage, exclusive=[99])).lint()
    assert _codes(findings) == ["EXCLUSIVE_CODE_UNKNOWN"]


def test_exclusive_code_present_in_answers_is_quiet():
    manage = Variable("manage", "nominal", labels={1: "Limits", 2: "Meals", 99: "None of these"})
    assert _survey(MultiChoice("Manage?", manage, exclusive=[99])).lint() == []


# ── V7: option codes vs value labels ──────────────────────────────────────────


def test_option_code_without_a_value_label_is_reported():
    gender = Variable("gender", "nominal", labels={1: "Woman", 2: "Man"})
    question = SingleChoice("Gender?", gender, choices=[Option(1, "Woman"), Option(9, "Other")])
    findings = _survey(question).lint()
    assert _codes(findings) == ["OPTION_CODE_WITHOUT_LABEL"]


def test_option_codes_matching_labels_are_quiet():
    gender = Variable("gender", "nominal", labels={1: "Woman", 2: "Man"})
    question = SingleChoice("Gender?", gender, choices=[Option(1, "W"), Option(2, "M")])
    assert _survey(question).lint() == []


# ── V9: likert points vs labels ───────────────────────────────────────────────


def test_likert_points_beyond_the_labels_are_reported():
    findings = _survey(LikertScale("Trust?", _trust(), points=7)).lint()
    assert _codes(findings) == ["LIKERT_POINTS_LABEL_MISMATCH"]


def test_likert_points_matching_the_labels_are_quiet():
    assert _survey(LikertScale("Trust?", _trust(), points=5)).lint() == []


def test_likert_ignores_missing_codes_when_counting_labels():
    scale = Variable(
        "scale",
        "ordinal",
        labels={**AGREE5, 99: "Prefer not to say"},
        missing=(MissingValue(99, "Prefer not to say", kind="refusal"),),
    )
    assert _survey(LikertScale("Trust?", scale, points=5)).lint() == []


# ── V10: missing codes vs value labels ────────────────────────────────────────


def test_missing_code_absent_from_labels_is_reported():
    gender = Variable(
        "gender",
        "nominal",
        labels={1: "Woman", 2: "Man"},
        missing=(MissingValue(98, "Refused", kind="refusal"),),
    )
    findings = _survey(SingleChoice("Gender?", gender)).lint()
    assert _codes(findings) == ["MISSING_CODE_NOT_IN_LABELS"]


def test_missing_code_present_in_labels_is_quiet():
    gender = Variable(
        "gender",
        "nominal",
        labels={1: "Woman", 2: "Man", 99: "Prefer not to say"},
        missing=(MissingValue(99, "Prefer not to say", kind="refusal"),),
    )
    assert _survey(SingleChoice("Gender?", gender)).lint() == []


# ── V11: show_if together with hide_if ────────────────────────────────────────


def test_show_if_and_hide_if_on_one_question_is_reported():
    news = _news()
    question = SingleChoice("Trust?", _trust(), show_if=news.eq(1), hide_if=news.eq(2))
    findings = _survey(SingleChoice("News?", news), question).lint()
    assert _codes(findings) == ["CONTRADICTORY_VISIBILITY"]


def test_sibling_objects_each_carrying_one_condition_are_quiet():
    """Two blocks on one page share a location string; they must not be merged."""

    news = _news()
    shown = SingleChoice("A?", Variable("a", "nominal", labels={1: "x"}), show_if=news.eq(1))
    hidden = SingleChoice("B?", Variable("b", "nominal", labels={1: "x"}), hide_if=news.eq(2))
    assert _survey(SingleChoice("News?", news), shown, hidden).lint() == []


# ── V13: value labels vs valid_range ──────────────────────────────────────────


def test_value_label_outside_valid_range_is_reported():
    mood = Variable("mood", "ordinal", labels={1: "Low", 2: "Mid", 3: "High"}, valid_range=(1, 2))
    findings = _survey(SingleChoice("Mood?", mood)).lint()
    assert _codes(findings) == ["RANGE_LABEL_MISMATCH"]


def test_value_labels_inside_valid_range_are_quiet():
    mood = Variable("mood", "ordinal", labels={1: "Low", 2: "Mid"}, valid_range=(1, 2))
    assert _survey(SingleChoice("Mood?", mood)).lint() == []


def test_missing_codes_may_sit_outside_valid_range():
    """A refusal code is deliberately outside the substantive range."""

    mood = Variable(
        "mood",
        "ordinal",
        labels={1: "Low", 2: "Mid", 99: "Refused"},
        valid_range=(1, 2),
        missing=(MissingValue(99, "Refused", kind="refusal"),),
    )
    assert _survey(SingleChoice("Mood?", mood)).lint() == []


# ── EMPTY_PAGE understands page kinds ─────────────────────────────────────────


def test_content_and_terminal_pages_are_not_empty_pages():
    """They render `body` instead of questions — that is what they are for."""

    survey = Questionnaire(
        title="T",
        pages=[
            ContentPage("intro", body="<p>Welcome</p>"),
            Page("q", items=[SingleChoice("News?", _news())]),
            FinalPage("thanks", body="<p>Bye</p>"),
        ],
    )
    assert survey.lint() == []
    survey.validate(strict=True)  # must not raise


def test_a_page_with_neither_items_nor_body_is_still_empty():
    survey = Questionnaire(
        title="T",
        pages=[Page("blank"), Page("q", items=[SingleChoice("News?", _news())])],
    )
    assert "EMPTY_PAGE" in _codes(survey.lint())


# ── Piping ────────────────────────────────────────────────────────────────────


def test_lint_flags_piped_text_that_names_unknown_or_later_variables():
    name = Variable("name", "nominal", label="Name")
    color = Variable("color", "nominal", labels={1: "Red", 2: "Blue"})
    first = Page("first", items=[OpenText("Your name?", var=name)])
    second = Page(
        "second",
        title="Thanks, {answer:name}",
        items=[
            SingleChoice(
                "{answer:name}, favorite color?",
                var=color,
                choices=[Option(1, "Red"), Option(2, "Blue")],
                hint="You said {label:color} — before answering this, that is a forward reference",
            ),
            OpenText("Why {label:color}? And {answer:nickname}?", var=Variable("why", "nominal")),
        ],
    )
    findings = Questionnaire(title="T", pages=[first, second]).lint()
    codes = _codes(findings)
    assert "PIPE_UNKNOWN_VARIABLE" in codes and "PIPE_FORWARD_REFERENCE" in codes
    unknown = [f for f in findings if f.code == "PIPE_UNKNOWN_VARIABLE"]
    assert len(unknown) == 1 and "{answer:nickname}" in unknown[0].message
    forward = [f for f in findings if f.code == "PIPE_FORWARD_REFERENCE"]
    # The hint pipes color before color is answered; the next question may use it.
    assert len(forward) == 1 and "{label:color}" in forward[0].message
    # A page title piping an earlier answer is fine.
    assert all("{answer:name}" not in f.message for f in findings)


# ─── MaxDiff ─────────────────────────────────────────────────────────────────


def _maxdiff_variables(tasks: int, labels=None):
    items = labels if labels is not None else {1: "A", 2: "B", 3: "C", 4: "D"}
    variables = [
        Variable(f"md_t{t}_{side}", "nominal", labels=items)
        for t in range(1, tasks + 1)
        for side in ("best", "worst")
    ]
    variables.append(Variable("md_version", "nominal"))
    return variables


def test_maxdiff_pairs_variables_with_tasks():
    """Best and worst per task plus the version: get the count wrong and answers
    land under the wrong task without anything looking amiss."""

    variables = _maxdiff_variables(3)
    assert MaxDiff("Q?", variables, tasks=3).tasks == 3
    with pytest.raises(ValueError, match="needs 5 variables"):
        MaxDiff("Q?", variables, tasks=2)
    with pytest.raises(TypeError, match="list of Variables"):
        MaxDiff("Q?", Variable("x", "nominal"), tasks=0)


def test_maxdiff_refuses_a_task_nobody_can_answer():
    with pytest.raises(ValueError, match="nothing to beat"):
        MaxDiff("Q?", _maxdiff_variables(2), tasks=2, per_task=1)
    with pytest.raises(ValueError, match="at least one version"):
        MaxDiff("Q?", _maxdiff_variables(2), tasks=2, versions=0)


def test_maxdiff_finds_its_items_and_its_variables():
    question = MaxDiff("Q?", _maxdiff_variables(2), tasks=2, per_task=3)
    assert question.item_codes == [1, 2, 3, 4]
    assert question.version_variable.name == "md_version"
    best, worst = question.task_variables(1)
    assert (best.name, worst.name) == ("md_t2_best", "md_t2_worst")
    # Explicit choices override the labels, the way Ranking's do.
    with_choices = MaxDiff(
        "Q?",
        _maxdiff_variables(2),
        tasks=2,
        per_task=2,
        choices=[Option(7, "Seven"), Option(8, "Eight"), Option(9, "Nine")],
    )
    assert with_choices.item_codes == [7, 8, 9]


def test_maxdiff_generates_its_design_when_none_was_frozen():
    """A hand-written questionnaire still works, and still gives the same design
    every time, because the seed is the questionnaire's."""

    question = MaxDiff("Q?", _maxdiff_variables(2), tasks=2, per_task=3, versions=2, seed=5)
    design = question.resolved_design()
    assert design.to_dict() == question.resolved_design().to_dict()
    assert len(design.versions) == 2
    stored = MaxDiff(
        "Q?", _maxdiff_variables(2), tasks=2, per_task=3, versions=2, design=design.to_dict()
    )
    assert stored.resolved_design().to_dict() == design.to_dict()


def test_maxdiff_lint_names_what_cannot_be_estimated():
    def survey(**kwargs):
        tasks = kwargs.pop("tasks", 2)
        question = MaxDiff("Q?", _maxdiff_variables(tasks), tasks=tasks, id="q_md", **kwargs)
        return Questionnaire(title="M", pages=[Page(name="p", items=[question])])

    assert survey(per_task=3, versions=3).lint("strict") == []
    # Showing every item in every task is a complete design: nothing is learned
    # from which items met, which is the entire mechanism.
    codes = [w.code for w in survey(per_task=4, versions=3).lint("strict")]
    assert codes == ["MAXDIFF_COMPLETE_DESIGN"]
    codes = [w.code for w in survey(per_task=3, versions=1).lint("strict")]
    assert codes == ["MAXDIFF_SINGLE_VERSION"]


def test_a_maxdiff_without_a_seed_still_gives_one_design():
    """`seed=None` must not mean a fresh design on every compile: the survey a
    respondent answered and the design the analysis reads it against would be
    different tables, and nothing would say so."""

    def question(qid: str = "q_md", per_task: int = 3) -> MaxDiff:
        return MaxDiff("Q?", _maxdiff_variables(2), tasks=2, per_task=per_task, versions=3, id=qid)

    first = question().resolved_design().to_dict()
    assert first == question().resolved_design().to_dict()
    # It follows the question, so a different question — or the same one with
    # different tasks — gets its own design rather than borrowing this one.
    assert first != question("q_other").resolved_design().to_dict()
    assert first != question(per_task=2).resolved_design().to_dict()


# ─── Conjoint ────────────────────────────────────────────────────────────────


def _conjoint_attributes() -> list[Attribute]:
    return [
        Attribute("brand", [Option(1, "Acme"), Option(2, "Globex"), Option(3, "Initech")]),
        Attribute("price", [Option(10, "10"), Option(15, "15"), Option(20, "20")]),
        Attribute("warranty", [Option(1, "1 year"), Option(2, "2 years")]),
    ]


def _conjoint_variables(tasks: int) -> list[Variable]:
    variables = [
        Variable(f"cbc_t{t}", "nominal", labels={1: "1", 2: "2", 3: "3"})
        for t in range(1, tasks + 1)
    ]
    variables.append(Variable("cbc_version", "nominal"))
    return variables


def test_a_conjoint_writes_one_variable_per_task_plus_the_version():
    """Lighter than a MaxDiff, because the answer *is* the choice: which levels
    it carried lives in the design, not in another column."""

    question = Conjoint("Q?", _conjoint_variables(4), attributes=_conjoint_attributes(), tasks=4)
    assert question.task_variable(0).name == "cbc_t1"
    assert question.version_variable.name == "cbc_version"
    with pytest.raises(ValueError, match="needs 4 variables"):
        Conjoint("Q?", _conjoint_variables(4), attributes=_conjoint_attributes(), tasks=3)


def test_a_conjoint_refuses_what_cannot_be_a_trade_off():
    with pytest.raises(ValueError, match="at least two alternatives"):
        Conjoint(
            "Q?", _conjoint_variables(2), attributes=_conjoint_attributes(), tasks=2, alternatives=1
        )
    with pytest.raises(ValueError, match="distinct names"):
        Conjoint(
            "Q?",
            _conjoint_variables(2),
            attributes=[_conjoint_attributes()[0], _conjoint_attributes()[0]],
            tasks=2,
        )
    with pytest.raises(ValueError, match="at least two attributes"):
        Conjoint("Q?", _conjoint_variables(2), attributes=[], tasks=2).resolved_design()


def test_an_attribute_is_a_dimension_with_levels_not_an_option():
    """`Option` is a code and a label; a product is a row of them, which is why
    `Attribute` exists rather than `Option` growing a field."""

    attribute = Attribute("price", [Option(10, "£10"), Option(20, "£20")], label="Price")
    assert attribute.codes == [10, 20]
    assert attribute.label_of(20) == "£20"
    assert attribute.to_dict()["levels"][0] == {"code": 10, "label": "£10"}
    with pytest.raises(ValueError, match="plain identifier"):
        Attribute("unit price", [Option(1, "a"), Option(2, "b")])
    with pytest.raises(ValueError, match="at least two levels"):
        Attribute("price", [Option(1, "only")])
    with pytest.raises(ValueError, match="two levels with code"):
        Attribute("price", [Option(1, "a"), Option(1, "b")])


def test_a_conjoint_profile_reads_as_the_lines_a_respondent_sees():
    question = Conjoint(
        "Q?", _conjoint_variables(2), attributes=_conjoint_attributes(), tasks=2, seed=1
    )
    profile = question.resolved_design().task(0, 0)[0]
    assert question.profile_labels(profile) == [
        question.attributes[i].label_of(profile[i]) for i in range(3)
    ]


def test_a_conjoint_without_a_seed_still_gives_one_design():
    def question(qid: str = "q_cbc", tasks: int = 4) -> Conjoint:
        return Conjoint(
            "Q?", _conjoint_variables(tasks), attributes=_conjoint_attributes(), tasks=tasks, id=qid
        )

    first = question().resolved_design().to_dict()
    assert first == question().resolved_design().to_dict()
    assert first != question("q_other").resolved_design().to_dict()


def test_conjoint_lint_catches_a_design_nobody_could_fit():
    """The failure that costs money: it is only discovered when fieldwork is
    over and the model will not converge. The design generator already knows."""

    def survey(tasks: int, versions: int) -> Questionnaire:
        question = Conjoint(
            "Q?",
            _conjoint_variables(tasks),
            attributes=_conjoint_attributes(),
            tasks=tasks,
            versions=versions,
            id="q_cbc",
        )
        return Questionnaire(title="C", pages=[Page(name="p", items=[question])])

    assert survey(8, 3).lint("strict") == []
    [single] = survey(8, 1).lint("strict")
    assert single.code == "CONJOINT_SINGLE_VERSION"
    codes = [w.code for w in survey(1, 1).lint("strict")]
    assert "CONJOINT_NOT_ESTIMABLE" in codes
    # Versions pool: the same single task in three versions is estimable.
    assert "CONJOINT_NOT_ESTIMABLE" not in [w.code for w in survey(1, 3).lint("strict")]


# ── Variables no question collects ───────────────────────────────────────────


def _assigned_arm_survey(*, gate: str = "condition", declare: bool = False) -> Questionnaire:
    """An A/B split: the arm is drawn by a script, and a page branches on it."""

    from siamang.core import Script, VariableMap

    news = _news()
    treatment = Page(
        "treatment", items=[SingleChoice("Ad seen?", var=news)], show_if=compare(gate, "=", 2)
    )
    pages = [
        Page(
            "intro",
            items=[SingleChoice("News?", var=Variable("warmup", "nominal", labels={1: "a"}))],
        ),
        treatment,
    ]
    variables = None
    if declare:
        variables = VariableMap()
        variables.add_many([news, pages[0].items[0].var])
        variables.add(Variable("condition", "nominal", labels={1: "Control", 2: "Treatment"}))
    return Questionnaire(
        title="Split",
        pages=pages,
        variables=variables,
        scripts=[Script.assign_condition("condition", [(1, "Control"), (2, "Treatment")])],
    )


def test_a_page_may_branch_on_an_arm_a_script_assigns():
    """`assign_condition` writes the arm before the first page; no question
    collects it, and validate() used to call it unknown — which made the
    one thing the script exists for impossible to publish."""

    survey = _assigned_arm_survey()
    assert survey.assigned_variables() == ["condition"]
    survey.validate()  # must not raise
    survey.validate(strict=True)


def test_a_page_may_branch_on_a_codebook_variable_no_question_collects():
    """Embedded data — a panel id, a sample cell — is declared in the codebook
    and filled from outside the questionnaire."""

    from siamang.core import VariableMap

    news = _news()
    cell = Variable("sample_cell", "nominal", labels={1: "Urban", 2: "Rural"})
    variables = VariableMap()
    variables.add_many([news, cell])
    survey = Questionnaire(
        title="Embedded",
        pages=[
            Page("a", items=[SingleChoice("News?", var=news)]),
            Page("b", items=[OpenText("Why?", var=Variable("why", "nominal"))], show_if=cell.eq(2)),
        ],
        variables=None,
    )
    with pytest.raises(ValueError, match="unknown variables: sample_cell"):
        survey.validate()
    variables.add(Variable("why", "nominal"))
    Questionnaire(title="Embedded", pages=survey.pages, variables=variables).validate()


def test_a_name_nothing_writes_is_still_unknown():
    survey = _assigned_arm_survey(gate="conditon")
    with pytest.raises(ValueError, match="unknown variables: conditon"):
        survey.validate()


def test_an_assigned_arm_is_never_a_forward_reference_when_piped():
    from siamang.core import Script

    news = _news()
    survey = Questionnaire(
        title="Split",
        pages=[
            Page(
                "a",
                title="You are in group {answer:condition}",
                items=[SingleChoice("News?", var=news)],
            )
        ],
        scripts=[Script.assign_condition("condition", [(1, "Control"), (2, "Treatment")])],
    )
    assert not [w for w in survey.lint() if w.code.startswith("PIPE_")]


def test_a_quota_may_balance_an_assigned_arm():
    """`assign_condition(balance=True)` needs a quota cell per arm; the arm is
    no question's variable, so validate_options must know it from the script."""

    survey = _assigned_arm_survey()
    validate_options(survey, {"quota": [Quota("condition", 1, 50), Quota("condition", "2", 50)]})
    with pytest.raises(ValueError, match="not one of its arms"):
        validate_options(survey, {"quota": [Quota("condition", 3, 50)]})
    with pytest.raises(ValueError, match="unknown variable: cond"):
        validate_options(survey, {"quota": [Quota("cond", 1, 50)]})
