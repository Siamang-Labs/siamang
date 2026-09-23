"""A questionnaire that uses every field the document format carries (test fixture)."""

from datetime import datetime

from siamang.core import (
    AND,
    NOT,
    Attribute,
    Block,
    Conjoint,
    ContentPage,
    DisqualificationPage,
    FinalPage,
    LikertScale,
    Matrix,
    MaxDiff,
    Media,
    MissingValue,
    MultiChoice,
    NumericInput,
    OpenText,
    Option,
    Page,
    Questionnaire,
    Quota,
    Ranking,
    RedirectPage,
    Script,
    SingleChoice,
    Variable,
    VariableMap,
)
from siamang.frontend import UIConfig


def build():
    consent = Variable("consent", "nominal", label="Consent", labels={1: "Yes", 2: "No"})
    age = Variable("age", "ratio", label="Age", valid_range=(16, None), dtype="int", role="input")
    region = Variable(
        "region",
        "nominal",
        label="Region",
        labels={"north": "North", "south": "South", "99": "Elsewhere"},
        description="Where the respondent lives",
        construct="geography",
        source="screener",
    )
    gender = Variable(
        "gender",
        "nominal",
        label="Gender",
        labels={1: "Woman", 2: "Man", 3: "Other", 99: "Refused"},
        missing=(MissingValue(99, "Refused", kind="refusal"),),
    )
    trust = Variable(
        "trust",
        "ordinal",
        label="Trust",
        labels={1: "None", 2: "Some", 3: "Full", 9: "Don't know"},
        missing_values=(9,),
        missing_labels={9: "Don't know"},
    )
    owns_a = Variable("owns_a", "nominal", label="Owns A", labels={0: "No", 1: "Yes"})
    owns_b = Variable("owns_b", "nominal", label="Owns B", labels={0: "No", 1: "Yes"})
    m1 = Variable("m1", "ordinal", label="Statement 1", labels={1: "Low", 2: "High"})
    m2 = Variable("m2", "ordinal", label="Statement 2", labels={1: "Low", 2: "High"})
    rank = Variable("rank", "nominal", label="Ranking", labels={1: "A", 2: "B", 3: "C"})
    score = Variable("score", "interval", label="Score", valid_range=(0, 10))
    comment = Variable("comment", "nominal", label="Comment")
    md_items = {1: "Price", 2: "Quality", 3: "Speed", 4: "Support", 5: "Range"}
    md = [
        Variable(f"md_t{t}_{side}", "nominal", label=f"MaxDiff task {t}: {side}", labels=md_items)
        for t in (1, 2)
        for side in ("best", "worst")
    ]
    md.append(Variable("md_version", "nominal", label="MaxDiff design version"))
    cbc_attributes = [
        Attribute(
            "brand",
            [Option(1, "Acme"), Option(2, "Globex"), Option(3, "Initech")],
            label="Brand",
        ),
        Attribute("price", [Option(10, "10"), Option(15, "15"), Option(20, "20")], label="Price"),
        Attribute("warranty", [Option(1, "1 year"), Option(2, "2 years")], label="Warranty"),
    ]
    cbc = [
        Variable(
            f"cbc_t{t}",
            "nominal",
            label=f"Conjoint task {t}",
            labels={1: "Concept 1", 2: "Concept 2", 3: "Concept 3"},
        )
        for t in (1, 2)
    ]
    cbc.append(Variable("cbc_version", "nominal", label="Conjoint design version"))
    unused = Variable("unused", "nominal", label="Registered but not asked")

    registry = VariableMap()
    registry.add_many(
        [consent, age, region, gender, trust, owns_a, owns_b, m1, m2, rank, score, comment, unused]
    )
    registry.add_many(md)
    registry.add_many(cbc)

    survey = Questionnaire(
        title="Kitchen sink",
        deadline=datetime(2026, 12, 31, 23, 59, 0),
        variables=registry,
        scripts=[
            Script.randomize_options("q_region", seed="abc"),
            Script.randomize_pages(),
            Script.timed_question("q_trust", seconds=45),
            Script.validate_fields_match("q_score", "q_score", message="Must match."),
            Script.validate_fields_match("q_score", "q_score"),
            Script(
                name="log_it",
                trigger="onAnswer",
                target="q_age",
                code="console.log(answers);",
                context={"level": "debug"},
                sandbox=False,
            ),
            Script(code="answers.__ready__ = true;"),
        ],
        pages=[
            ContentPage("intro", body="<p>Hi</p>", title="Welcome"),
            Page(
                "consent_page",
                title="Consent",
                items=[
                    SingleChoice(
                        "Do you agree?",
                        consent,
                        required=True,
                        display="buttons",
                        id="q_consent",
                        media=Media("https://x/logo.png", alt="Logo"),
                    )
                ],
                next_if=[(consent.eq(2), "out")],
                # Without this everyone lands on "out": the disqualification page
                # is simply the next one in document order, and an implicit next
                # does not step over a terminal page.
                default_next="about",
            ),
            DisqualificationPage("out", body="<p>Bye</p>", redirect_url="https://x/out"),
            Page(
                "about",
                title="About you",
                items=[
                    NumericInput(
                        "Age?",
                        age,
                        required=True,
                        unit="years",
                        step=1,
                        hint="Whole years",
                        tag=["screener", "demo"],
                        metadata={"group": "demo", "weight": 1.5},
                        id="q_age",
                    ),
                    SingleChoice(
                        "Region?",
                        region,
                        display="dropdown",
                        randomize=True,
                        other_specify=True,
                        id="q_region",
                        choices=[
                            Option("north", "North"),
                            Option("south", "South", hide_if=age.lt(18)),
                            Option(
                                "99",
                                "Elsewhere",
                                show_if="{age} >= 18",
                                media=Media("https://x/map.jpg", caption="Map"),
                            ),
                        ],
                    ),
                    SingleChoice(
                        "Gender?",
                        gender,
                        none_of_above=True,
                        show_if=age.ge(18),
                        hide_if="{consent} == 2",
                        skip_to="wrap",
                        id="q_gender",
                        name="gender",
                    ),
                ],
                default_next="devices",
            ),
            Page(
                "devices",
                title="Devices",
                randomize_blocks=True,
                show_if=AND(age.ge(18), NOT(region.eq("south"))),
                items=[
                    Block(
                        title="Ownership",
                        randomize=True,
                        show_if=AND(consent.eq(1), NOT(region.isin({"99", "south"}))),
                        items=[
                            MultiChoice("Own?", vars=[owns_a, owns_b], id="q_own", max_answers=2),
                            Block(
                                items=[
                                    LikertScale(
                                        "Trust?",
                                        trust,
                                        points=3,
                                        left_label="None",
                                        right_label="Full",
                                        na_option="Don't know",
                                        id="q_trust",
                                        media=[Media("https://x/a.mp4"), Media("https://x/b.mp3")],
                                    )
                                ],
                                hide_if=owns_a.eq(0),
                            ),
                        ],
                    ),
                    Matrix(
                        "Statements",
                        var=[m1, m2],
                        subquestions=["First", "Second"],
                        column_labels=["Low", "High"],
                        na_option=True,
                        id="q_matrix",
                    ),
                ],
            ),
            Page(
                "wrap",
                items=[
                    Ranking(
                        "Rank",
                        rank,
                        max_ranked=2,
                        id="q_rank",
                        choices=[Option(1, "A"), Option(2, "B"), Option(3, "C")],
                    ),
                    MaxDiff(
                        "Which matters most, and least?",
                        md,
                        per_task=3,
                        tasks=2,
                        versions=4,
                        seed=11,
                        id="q_maxdiff",
                    ),
                    Conjoint(
                        "Which would you buy?",
                        cbc,
                        attributes=cbc_attributes,
                        alternatives=3,
                        tasks=2,
                        versions=3,
                        seed=13,
                        id="q_conjoint",
                    ),
                    NumericInput("Score", score, display="slider", step=0.5, id="q_score"),
                    OpenText(
                        "Comment",
                        comment,
                        multiline=True,
                        max_chars=200,
                        placeholder="Optional",
                        id="q_comment",
                    ),
                ],
            ),
            RedirectPage(
                "go", redirect_url="https://x/done", redirect_delay=3, show_if=score.gt(5)
            ),
            FinalPage("thanks", title="Thanks", body="<p>Done</p>"),
        ],
    )
    options = {
        "language": "de",
        "description": "Everything at once",
        "completion_text": "Danke",
        "show_progress": False,
        "allow_back": False,
        "one_question_per_page": True,
        "max_responses": 500,
        "metadata": {"wave": 1, "tags": ["a", "b"], "nested": {"k": None}},
        "quota": [Quota("gender", 1, 100), Quota("region", "north", 50)],
        "ui": UIConfig(
            primary_color="#123456",
            institution_name="Lab",
            font_pair="mixed",
            estimated_minutes=7,
            access_codes=["a1", "b2"],
            show_title=False,
            custom_css=".x{}",
        ),
    }
    return survey, options


survey, options = build()
