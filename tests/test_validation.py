"""Questionnaire validation and lint rules.

Covers the hard errors raised by `Questionnaire.validate()`, the findings
returned by `Questionnaire.lint()`, and `validate_options()` — the check that
compiler-level quotas actually match the questionnaire they ship with.
"""

import pytest

from siamang.core import (
    AND,
    ContentPage,
    Expression,
    FinalPage,
    LikertScale,
    Matrix,
    MissingValue,
    MultiChoice,
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
