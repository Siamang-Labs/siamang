"""simulate() follows the questionnaire's navigation: screen-outs, next_if,
default_next and skip_to shape the synthetic data the way the runtime would."""

from __future__ import annotations

import siamang as sg
from siamang.core.page import DisqualificationPage, FinalPage


def _survey() -> sg.Questionnaire:
    age = sg.Variable("age", scale="ratio", label="Age", valid_range=(10, 30))
    owns = sg.Variable("owns", scale="nominal", label="Owns", labels={1: "Yes", 0: "No"})
    brand = sg.Variable("brand", scale="nominal", label="Brand", labels={1: "A", 2: "B"})
    why = sg.Variable("why", scale="nominal", label="Why not")
    sat = sg.Variable("sat", scale="ordinal", label="Sat", labels={1: "Low", 2: "High"})
    pages = [
        sg.Page(
            name="screener",
            items=[sg.NumericInput("How old are you?", var=age, id="q_age")],
            next_if=[(sg.compare("age", "<", 18), "too_young")],
            default_next="ownership",
        ),
        DisqualificationPage("too_young", title="Sorry", body="<p>18+</p>"),
        sg.Page(
            name="ownership",
            items=[
                sg.SingleChoice(
                    "Do you own one?",
                    var=owns,
                    id="q_owns",
                    choices=[sg.Option(1, "Yes"), sg.Option(0, "No")],
                )
            ],
            next_if=[(sg.compare("owns", "=", 0), "why_not")],
            default_next="which",
        ),
        sg.Page(
            name="which",
            items=[
                sg.SingleChoice(
                    "Which?",
                    var=brand,
                    id="q_brand",
                    choices=[sg.Option(1, "A"), sg.Option(2, "B")],
                    skip_to="thanks",
                )
            ],
        ),
        sg.Page(name="why_not", items=[sg.OpenText("Why not?", var=why, id="q_why")]),
        sg.Page(
            name="rating",
            items=[
                sg.SingleChoice(
                    "Sat?", var=sat, id="q_sat", choices=[sg.Option(1, "Low"), sg.Option(2, "High")]
                )
            ],
        ),
        FinalPage("thanks", title="Thanks", body="<p>Done</p>"),
    ]
    return sg.Questionnaire(title="Routing", pages=pages, variables=[age, owns, brand, why, sat])


def test_simulate_follows_screen_outs_branches_and_skips():
    survey = _survey()
    frame = survey.simulate(n=400, seed=11).frame
    assert len(frame) == 400
    young = frame[frame["age"] < 18]
    adult = frame[frame["age"] >= 18]
    assert len(young) > 20 and len(adult) > 20
    # Screened out: nothing after the screener is answered.
    assert young[["owns", "brand", "why", "sat"]].isna().all().all()
    # The branch splits the sample: owners name a brand, non-owners say why not.
    owners = adult[adult["owns"] == 1]
    non_owners = adult[adult["owns"] == 0]
    assert owners["brand"].notna().all() and owners["why"].isna().all()
    assert non_owners["why"].notna().all() and non_owners["brand"].isna().all()
    # skip_to on the brand question jumps straight to the end: owners never rate.
    assert owners["sat"].isna().all()
    # Non-owners go on from why_not to the rating page in sequence.
    assert non_owners["sat"].notna().all()


def test_simulate_without_routing_walks_every_page():
    from siamang.local_simulator import simulate_from_pages

    survey = _survey()
    frame = simulate_from_pages(survey.pages, n=50, seed=3, routing=False)
    # Every question page is answered regardless of the branch (the legacy behavior).
    assert (
        frame["brand"].notna().all() and frame["why"].notna().all() and frame["sat"].notna().all()
    )


# ─── the rest of the logic: blocks, options, scripts, quotas ─────────────────


def _yes_no(name: str) -> sg.Variable:
    return sg.Variable(name, scale="nominal", label=name, labels={1: "Yes", 0: "No"})


def _choice(name: str, text: str, **kwargs) -> sg.SingleChoice:
    yes_no = [sg.Option(1, "Yes"), sg.Option(0, "No")]
    return sg.SingleChoice(text, var=_yes_no(name), id=f"q_{name}", choices=yes_no, **kwargs)


def test_a_hidden_block_leaves_its_questions_unanswered():
    """Block conditions were never read: page.flatten_questions() answered
    every question inside a hidden block, nested ones included."""

    owns = _choice("owns", "Own one?")
    pages = [
        sg.Page(name="p1", items=[owns]),
        sg.Page(
            name="p2",
            items=[
                _choice("always", "Always asked"),
                sg.Block(
                    title="Owners",
                    show_if=sg.compare("owns", "=", 1),
                    items=[
                        _choice("likes", "Like it?"),
                        sg.Block(
                            title="Fans",
                            hide_if=sg.compare("likes", "=", 0),
                            items=[_choice("recommends", "Recommend it?")],
                        ),
                    ],
                ),
            ],
        ),
    ]
    frame = sg.Questionnaire(title="B", pages=pages).simulate(n=300, seed=4).frame
    owners, others = frame[frame["owns"] == 1], frame[frame["owns"] == 0]
    assert len(owners) > 50 and len(others) > 50
    assert frame["always"].notna().all()
    assert owners["likes"].notna().all() and others["likes"].isna().all()
    # The nested block: hidden for non-owners (its parent is) and for owners who
    # said no, shown to the rest.
    assert others["recommends"].isna().all()
    assert owners.loc[owners["likes"] == 0, "recommends"].isna().all()
    assert owners.loc[owners["likes"] == 1, "recommends"].notna().all()


def test_an_option_hidden_by_its_condition_is_never_chosen():
    age = sg.Variable("age", scale="ratio", label="Age", valid_range=(10, 30))
    drink = sg.Variable("drink", scale="nominal", label="Drink", labels={1: "Tea", 2: "Beer"})
    kids = sg.Variable("kids", scale="nominal", label="Kids")
    pages = [
        sg.Page(name="p1", items=[sg.NumericInput("Age?", var=age, id="q_age")]),
        sg.Page(
            name="p2",
            items=[
                sg.SingleChoice(
                    "Drink?",
                    var=drink,
                    id="q_drink",
                    choices=[sg.Option(1, "Tea"), sg.Option(2, "Beer", show_if=age.ge(18))],
                ),
                sg.MultiChoice(
                    "Which apply?",
                    var=sg.Variable("which", scale="nominal", label="Which"),
                    id="q_which",
                    choices=[
                        sg.Option(1, "School"),
                        sg.Option(2, "Work", hide_if=age.lt(18)),
                        sg.Option(3, "Pension", show_if=age.ge(99)),
                    ],
                    max_answers=3,
                ),
                # Every option hidden for the under-18s: nothing can be chosen.
                sg.SingleChoice(
                    "Kids?",
                    var=kids,
                    id="q_kids",
                    choices=[sg.Option(1, "Yes", show_if=age.ge(18))],
                ),
            ],
        ),
    ]
    frame = sg.Questionnaire(title="O", pages=pages).simulate(n=400, seed=2).frame
    minors, adults = frame[frame["age"] < 18], frame[frame["age"] >= 18]
    assert len(minors) > 50 and len(adults) > 50
    assert set(minors["drink"]) == {1} and set(adults["drink"]) == {1, 2}
    assert all(2 not in picked and 3 not in picked for picked in minors["which"])
    assert any(2 in picked for picked in adults["which"])
    assert all(3 not in picked for picked in frame["which"])  # nobody is 99
    assert minors["kids"].isna().all() and (adults["kids"] == 1).all()


def _arm_survey(**assign) -> sg.Questionnaire:
    pages = [
        sg.Page(name="intro", items=[_choice("owns", "Own one?")]),
        sg.Page(
            name="treated",
            show_if=sg.compare("condition", "=", 2),
            items=[_choice("seen", "Seen the ad?")],
        ),
    ]
    script = sg.Script.assign_condition(
        "condition", [(1, "Control", 2), (2, "Treatment", 1)], **assign
    )
    return sg.Questionnaire(title="A", pages=pages, scripts=[script])


def test_the_assigned_arm_is_drawn_by_its_weights_and_routes():
    """The arm column did not exist, so a page gated on the arm was hidden
    from every simulated respondent."""

    from siamang.local_simulator import simulate_questionnaire, simulate_survey

    survey = _arm_survey()
    frame = simulate_questionnaire(survey, n=900, seed=8)
    assert list(frame.columns) == ["owns", "seen", "condition"]
    counts = frame["condition"].value_counts()
    # Weights 2 : 1 — two thirds control, give or take four binomial SDs (≈ 63).
    assert abs(counts[1] - 600) < 63 and counts[1] + counts[2] == 900
    assert frame.loc[frame["condition"] == 2, "seen"].notna().all()
    assert frame.loc[frame["condition"] == 1, "seen"].isna().all()
    # Deterministic under the seed, and not the same draw under another.
    assert simulate_questionnaire(survey, n=900, seed=8).equals(frame)
    assert not simulate_questionnaire(survey, n=900, seed=9).equals(frame)

    data = simulate_survey(survey, n=50, seed=8)
    assert data.variables["condition"].labels == {1: "Control", 2: "Treatment"}
    assert data.variables["condition"].scale == "nominal"
    assert data.frame.equals(simulate_questionnaire(survey, n=50, seed=8))


def test_a_balanced_assignment_fills_its_quota_cells_in_proportion():
    """balance=True sends each respondent to the arm furthest behind its own
    target — completes over limit — so 60 completes against targets of 40 and
    20 land exactly on 40 and 20, where a free 2 : 1 draw would drift."""

    from siamang.core.quota import Quota
    from siamang.local_simulator import simulate_questionnaire

    survey = _arm_survey(balance=True)
    quotas = [Quota("condition", 1, 40), Quota("condition", 2, 20)]
    frame = simulate_questionnaire(survey, n=60, seed=1, quotas=quotas)
    assert frame["condition"].value_counts().to_dict() == {1: 40, 2: 20}
    # A cell on only one arm cannot balance: the weighted draw stands.
    partial = simulate_questionnaire(survey, n=60, seed=1, quotas=quotas[:1])
    assert partial["condition"].value_counts().sum() == 60


def test_a_full_quota_cell_ends_the_interview_and_only_completes_count():
    """Leaving a page that answered a quota variable, a respondent in a full
    cell ends there, as the runtime's quota_full screen does; a screen-out
    never fills a cell. So exactly ten owners complete, and every owner after
    the tenth complete stops at the first page."""

    from siamang.core.page import DisqualificationPage
    from siamang.core.quota import Quota
    from siamang.local_simulator import simulate_from_pages

    age = sg.Variable("age", scale="ratio", label="Age", valid_range=(10, 30))
    pages = [
        sg.Page(name="screener", items=[_choice("owns", "Own one?")]),
        sg.Page(
            name="age",
            items=[sg.NumericInput("Age?", var=age, id="q_age")],
            next_if=[(sg.compare("age", "<", 18), "out")],
            default_next="main",
        ),
        DisqualificationPage("out", title="Sorry"),
        sg.Page(name="main", items=[_choice("sat", "Satisfied?")]),
    ]
    frame = simulate_from_pages(pages, n=200, seed=6, quotas=[Quota("owns", 1, 10)])
    owners = frame[frame["owns"] == 1]
    completes = owners[owners["sat"].notna()]
    assert len(completes) == 10
    # The tenth complete closes the cell: every owner after it stops at once.
    last = completes.index.max()
    later = owners.loc[owners.index > last]
    assert len(later) > 20 and later["age"].isna().all() and later["sat"].isna().all()
    # Before it, owners who were screened out by age did not use up a place.
    earlier = owners.loc[owners.index <= last]
    assert (earlier["age"] < 18).any() and len(earlier) > 10
    # Non-owners are untouched by the cell, and without quotas nobody stops.
    assert frame.loc[frame["owns"] == 0, "age"].notna().all()
    free = simulate_from_pages(pages, n=200, seed=6)
    assert free["age"].notna().all()


def test_a_multiple_choice_answer_meets_every_cell_it_names():
    from siamang.core.quota import Quota
    from siamang.local_simulator import simulate_from_pages

    which = sg.Variable("which", scale="nominal", label="Which", labels={1: "A", 2: "B", 3: "C"})
    pages = [
        sg.Page(
            name="p1",
            items=[sg.MultiChoice("Which?", var=which, id="q_which", max_answers=3)],
        ),
        sg.Page(name="p2", items=[_choice("more", "More?")]),
    ]
    frame = simulate_from_pages(pages, n=150, seed=3, quotas=[Quota("which", 2, 15)])
    chose_b = frame[[2 in picked for picked in frame["which"]]]
    assert (chose_b["more"].notna()).sum() == 15
    assert frame.loc[[2 not in picked for picked in frame["which"]], "more"].notna().all()


def test_randomize_pages_deals_each_respondent_an_order():
    """A page gated on an answer from a page the shuffle may put after it is
    shown only to the respondents whose order put the answer first — which is
    what the runtime does, so the simulation shows the hole the design has."""

    from siamang.core.page import FinalPage
    from siamang.local_simulator import _dealt, simulate_from_pages

    pages = [
        sg.Page(name="welcome", items=[_choice("start", "Start?")]),
        sg.Page(name="a", items=[_choice("used", "Used it?")]),
        sg.Page(name="b", show_if=sg.compare("used", "=", 1), items=[_choice("liked", "Liked?")]),
        sg.Page(name="c", items=[_choice("other", "Other?")]),
        FinalPage("thanks", title="Thanks"),
    ]
    scripts = [sg.Script.randomize_pages()]
    frame = simulate_from_pages(pages, n=600, seed=5, scripts=scripts)
    users = frame[frame["used"] == 1]
    shown = users["liked"].notna().mean()
    assert 0.35 < shown < 0.65  # b before a for about half the users
    fixed = simulate_from_pages(pages, n=600, seed=5)
    assert fixed.loc[fixed["used"] == 1, "liked"].notna().all()
    # The first and last page and every terminal page keep their place.
    import random

    random.seed(0)
    for _ in range(20):
        order = [page.name for page in _dealt(pages)]
        assert order[0] == "welcome" and order[-1] == "thanks"
        assert sorted(order[1:4]) == ["a", "b", "c"]


def test_a_shuffled_block_decides_which_skip_is_met_first():
    """skip_to fires on the first answered question in the order shown; a
    block shuffle changes that order, and only that."""

    from siamang.local_simulator import simulate_from_pages

    def pages(randomize: bool) -> list[sg.Page]:
        return [
            sg.Page(
                name="p1",
                items=[
                    sg.Block(
                        title="Pair",
                        randomize=randomize,
                        items=[
                            _choice("x", "X?", skip_to="to_x"),
                            _choice("y", "Y?", skip_to="to_y"),
                        ],
                    )
                ],
            ),
            sg.Page(name="to_y", items=[_choice("ay", "After Y")]),
            sg.Page(name="to_x", items=[_choice("ax", "After X")]),
        ]

    plain = simulate_from_pages(pages(False), n=400, seed=7)
    assert plain["ay"].isna().all() and plain["ax"].notna().all()
    shuffled = simulate_from_pages(pages(True), n=400, seed=7)
    via_y = shuffled["ay"].notna()
    assert 0.35 < via_y.mean() < 0.65
    # Both questions are still answered by everyone: the shuffle moved them.
    assert shuffled[["x", "y"]].notna().all().all()
