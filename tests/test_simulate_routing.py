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
