"""Reading a MaxDiff: choice sets, counting scores and conditional-logit utilities."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import siamang as sg
from siamang.data import SurveyData
from siamang.data import maxdiff as md
from siamang.data.choice import ChoiceSets, mnl

ITEMS = {1: "Price", 2: "Quality", 3: "Speed", 4: "Support", 5: "Range", 6: "Brand"}
TRUE = {1: 2.0, 2: 1.4, 3: 0.8, 4: 0.2, 5: -0.6, 6: 0.0}


def _question(tasks: int = 8, per_task: int = 4, versions: int = 10, seed: int = 9) -> sg.MaxDiff:
    variables = []
    for task in range(1, tasks + 1):
        for side in ("best", "worst"):
            variables.append(
                sg.Variable(
                    f"md_t{task}_{side}", "nominal", label=f"task {task} {side}", labels=ITEMS
                )
            )
    variables.append(sg.Variable("md_version", "nominal", label="Design version"))
    return sg.MaxDiff(
        "Which matters most?",
        variables,
        per_task=per_task,
        tasks=tasks,
        versions=versions,
        seed=seed,
        id="q_md",
    )


def _survey(question: sg.MaxDiff) -> sg.Questionnaire:
    return sg.Questionnaire(title="MD", pages=[sg.Page(name="p", items=[question])])


def _fieldwork(question: sg.MaxDiff, n: int = 400, seed: int = 11) -> SurveyData:
    """Respondents who actually prefer what TRUE says they prefer.

    Answers are drawn from the utilities plus Gumbel noise — the model the
    conditional logit assumes — so recovering TRUE is a fair test of the
    estimator rather than of the data-generating trick.
    """

    survey = _survey(question)
    design = question.resolved_design()
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n):
        version = int(rng.integers(len(design.versions)))
        row: dict[str, object] = {"md_version": version}
        for task in range(question.tasks):
            shown = list(design.task(version, task))
            drawn = np.array([TRUE[c] for c in shown]) + rng.gumbel(size=len(shown))
            best = shown[int(np.argmax(drawn))]
            rest = [c for c in shown if c != best]
            again = np.array([TRUE[c] for c in rest]) + rng.gumbel(size=len(rest))
            worst = rest[int(np.argmin(again))]
            best_var, worst_var = question.task_variables(task)
            row[best_var.name] = best
            row[worst_var.name] = worst
        rows.append(row)
    return SurveyData(frame=pd.DataFrame(rows), variables=survey.variables, questionnaire=survey)


# ─── the estimator ───────────────────────────────────────────────────────────


def test_the_conditional_logit_recovers_utilities_it_was_never_told():
    """The test the whole module stands on. An estimator that has not been shown
    to recover known parameters is a number with nothing behind it."""

    rng = np.random.default_rng(7)
    truth = np.array([1.6, 1.0, 0.4, 0.0, -0.7, -1.4])
    reference = len(truth) - 1
    rows, chosen, group = [], [], []
    for set_id in range(2400):
        shown = rng.choice(len(truth), size=3, replace=False)
        pick = int(np.argmax(truth[shown] + rng.gumbel(size=3)))
        for position, item in enumerate(shown):
            row = np.zeros(len(truth) - 1)
            if item != reference:
                row[item] = 1.0
            rows.append(row)
            chosen.append(position == pick)
            group.append(set_id)
    result = mnl(
        ChoiceSets(
            design=np.array(rows),
            chosen=np.array(chosen),
            group=np.array(group),
            names=[f"item{i}" for i in range(len(truth) - 1)],
        )
    )
    fitted = np.r_[result.coefficients, 0.0]
    centered = truth - truth[reference]
    assert result.stats["converged"]
    assert np.corrcoef(centered, fitted)[0, 1] > 0.99
    assert np.abs(centered - fitted).max() < 0.25


def test_choice_sets_must_be_well_formed():
    design = np.eye(3)[:, :2]
    with pytest.raises(ValueError, match="exactly one chosen"):
        ChoiceSets(
            design=design,
            chosen=np.array([True, True, False]),
            group=np.zeros(3, dtype=int),
            names=["a", "b"],
        )
    with pytest.raises(ValueError, match="non-decreasing"):
        ChoiceSets(
            design=design,
            chosen=np.array([True, False, False]),
            group=np.array([1, 0, 0]),
            names=["a", "b"],
        )
    with pytest.raises(ValueError, match="no choice sets"):
        ChoiceSets(
            design=np.empty((0, 2)),
            chosen=np.empty(0, dtype=bool),
            group=np.empty(0, dtype=int),
            names=["a", "b"],
        )


# ─── reading the answers ─────────────────────────────────────────────────────


def test_both_halves_of_the_answer_become_choices():
    """The worst pick is a choice of the least preferred, so it enters with the
    sign flipped instead of being thrown away."""

    question = _question(tasks=2, per_task=4, versions=2)
    data = _fieldwork(question, n=5)
    sets = md.choice_sets(data, "q_md")
    # Two sets per task: the whole task, then what was left after the best.
    assert sets.n_sets == 5 * 2 * 2
    assert list(sets.sizes[:2]) == [4, 3]
    first, second = sets.design[:4], sets.design[4:7]
    assert first.max() == 1.0 and second.min() == -1.0


def test_answers_that_contradict_the_design_are_counted_not_used():
    """An item picked that its task never showed means the design changed after
    fieldwork. Using it would put a preference where there was no comparison."""

    question = _question(tasks=3, per_task=3, versions=2)
    data = _fieldwork(question, n=20)
    frame = data.frame.copy()
    best, worst = question.task_variables(0)
    frame.loc[frame.index[0], best.name] = 999  # never in any task
    frame.loc[frame.index[1], worst.name] = None  # walked away mid-question
    frame.loc[frame.index[2], worst.name] = frame.loc[frame.index[2], best.name]
    frame.loc[frame.index[3], "md_version"] = None  # no version: unreadable
    read = md.answers(data.with_frame(frame), "q_md")
    assert read.reasons["not in the task"] == 1
    assert read.reasons["not answered"] == 1
    assert read.reasons["same item twice"] == 1
    assert read.reasons["no version"] == 3  # all of that respondent's tasks
    assert read.respondents == 19


def test_a_code_that_came_back_as_text_still_matches_the_design():
    """A CSV round trip brings codes back as strings and a float column as 3.0.
    Comparing them naively looks exactly like a respondent choosing something
    they were never offered."""

    question = _question(tasks=2, per_task=3, versions=2)
    data = _fieldwork(question, n=10)
    as_text = data.frame.astype({c: "object" for c in data.frame.columns}).map(
        lambda v: str(v) if pd.notna(v) else v
    )
    read = md.answers(data.with_frame(as_text), "q_md")
    assert read.dropped == 0
    assert len(read.frame) == 10 * 2


def test_the_question_is_found_by_name_or_told_what_exists():
    question = _question(tasks=2, per_task=3, versions=2)
    data = _fieldwork(question, n=3)
    assert md.question_of(data, "q_md") is question
    with pytest.raises(KeyError, match="q_md"):
        md.question_of(data, "nope")
    bare = SurveyData(frame=data.frame)
    with pytest.raises(ValueError, match="no questionnaire attached"):
        md.question_of(bare, "q_md")


# ─── the two numbers ─────────────────────────────────────────────────────────


def test_counting_and_utilities_both_recover_the_true_order():
    question = _question()
    data = _fieldwork(question)

    counts = md.counts(data, "q_md")
    assert list(counts["label"]) == [
        ITEMS[i] for i, _ in sorted(TRUE.items(), key=lambda kv: -kv[1])
    ]
    assert counts["score"].between(-1, 1).all()
    assert counts.iloc[0]["best"] > counts.iloc[0]["worst"]

    result = md.utilities(data, "q_md")
    assert result.stats["converged"]
    estimate = dict(zip(result.table["term"], result.table["estimate"], strict=True))
    fitted = np.array([estimate[ITEMS[code]] for code in sorted(ITEMS)])
    truth = np.array([TRUE[code] for code in sorted(ITEMS)])
    assert np.corrcoef(truth, fitted)[0, 1] > 0.98
    # Shares are the utilities in units people read, and they are a distribution.
    assert result.table["share"].sum() == pytest.approx(100.0, abs=0.5)
    assert result.stats["respondents"] == 400


def test_every_respondent_gets_a_score_without_a_hierarchical_model():
    """Coarse, because one respondent sees each item a handful of times — but
    real, and they carry into a crosstab or a cluster like any variable."""

    question = _question(tasks=6, per_task=3, versions=4)
    data = _fieldwork(question, n=30)
    scores = md.respondent_scores(data, "q_md")
    assert set(scores.columns) == {"respondent", "item", "label", "score"}
    assert scores["respondent"].nunique() == 30
    assert scores["score"].between(-1, 1).all()
    # The average of the individual scores is the population score.
    mean = scores.groupby("label")["score"].mean().sort_values(ascending=False)
    assert mean.index[0] == "Price"


def test_the_table_carries_its_base_and_says_how_it_was_estimated():
    question = _question(tasks=6, per_task=3, versions=4)
    data = _fieldwork(question, n=60)
    table = data.report.maxdiff("q_md")
    frame = table.to_frame()
    assert list(frame.columns) == ["Item", "Shown", "Best", "Worst", "Score", "Utility", "Share %"]
    assert frame.iloc[0]["Item"] == "Price"
    assert table.stats["Base"] == "60 respondents"
    assert "conditional logit" in table.stats["Method"]
    assert table.stats["Reference"] in ITEMS.values()

    counts_only = data.report.maxdiff("q_md", method="counts").to_frame()
    assert "Utility" not in counts_only.columns


def test_weights_change_the_answer_and_are_taken_from_the_data():
    question = _question(tasks=6, per_task=3, versions=4)
    data = _fieldwork(question, n=120)
    frame = data.frame.assign(w=1.0)
    frame.loc[frame.index[:60], "w"] = 5.0
    weighted = md.counts(data.with_frame(frame), "q_md", weight="w")
    unweighted = md.counts(data, "q_md")
    assert weighted["shown"].sum() > unweighted["shown"].sum()
    with pytest.raises(KeyError, match="not found"):
        md.counts(data, "q_md", weight="nope")


def test_weighted_choice_sets_fit_the_weighted_estimate_by_hand():
    """Two alternatives, one parameter: the MLE is the log of the weighted odds.

    A is picked in sets weighing 1 and 3, B in two sets weighing 1: unweighted
    that is 2 : 2 and β = 0; weighted it is 4 : 2 and β = log 2. The weights
    are rescaled to Kish's effective number of sets, (1+3+1+1)² / (1+9+1+1) =
    3, so the information is 3 · p(1 − p) at p = 2/3 and the standard error
    √1.5 — neither the raw sample's (√(9/8)) nor that of six sets (√0.75).
    """

    design = np.array([[1.0], [0.0]] * 4)
    chosen = np.array([True, False, True, False, False, True, False, True])
    group = np.repeat(np.arange(4), 2)

    def fit(weight):
        return mnl(
            ChoiceSets(design=design, chosen=chosen, group=group, names=["A"], weight=weight)
        )

    plain = fit(None)
    assert plain.coefficients[0] == pytest.approx(0.0, abs=1e-6)
    assert plain.table["std_error"][0] == pytest.approx(1.0, abs=1e-4)
    assert "effective_sets" not in plain.stats

    weighted = fit(np.array([1.0, 3.0, 1.0, 1.0]))
    assert weighted.coefficients[0] == pytest.approx(np.log(2.0), abs=1e-4)
    assert weighted.table["std_error"][0] == pytest.approx(np.sqrt(1.5), abs=1e-3)
    assert weighted.table["share"].tolist() == [66.7, 33.3]
    assert weighted.stats["effective_sets"] == 3.0

    # Equal weights of any size are no weights at all.
    same = fit(np.full(4, 7.0))
    assert same.coefficients[0] == pytest.approx(0.0, abs=1e-6)
    assert same.table["std_error"][0] == pytest.approx(1.0, abs=1e-4)
    with pytest.raises(ValueError, match="weight of zero"):
        fit(np.zeros(4))


def test_the_utilities_carry_the_weight_the_counts_do():
    """The data's weight reached Shown, Best, Worst and the Score but not the
    model, so the Score and Utility columns of one table described two
    different samples. Integer weights are frequency weights: a respondent of
    weight 3 must read exactly like three respondents of weight 1, to the model
    as to the counts."""

    question = _question(tasks=6, per_task=3, versions=4)
    data = _fieldwork(question, n=80)
    w = np.where(np.arange(80) % 4 == 0, 3.0, 1.0)
    weighted = data.with_frame(data.frame.assign(w=w)).with_weight("w")
    expanded = data.with_frame(
        data.frame.loc[data.frame.index.repeat(w.astype(int))].reset_index(drop=True)
    )

    fitted = md.utilities(weighted, "q_md")
    frequency = md.utilities(expanded, "q_md")
    plain = md.utilities(data, "q_md")
    assert np.allclose(fitted.coefficients, frequency.coefficients, atol=2e-3)
    assert not np.allclose(fitted.coefficients, plain.coefficients, atol=2e-3)
    assert fitted.stats["weight"] == "w" and "weight" not in plain.stats
    # The same weight named explicitly is the same fit.
    explicit = md.utilities(data.with_frame(data.frame.assign(w=w)), "q_md", weight="w")
    assert np.allclose(explicit.coefficients, fitted.coefficients)

    # Standard errors are those of the effective base, not of the 120 rows the
    # expanded file pretends to have: larger by √(Σw² / Σw) over the sets.
    sets = md.choice_sets(weighted, "q_md")
    ratio = np.sqrt((sets.weight**2).sum() / sets.weight.sum())
    assert np.allclose(
        fitted.table["std_error"][:-1], frequency.table["std_error"][:-1] * ratio, rtol=1e-2
    )

    table = weighted.report.maxdiff("q_md")
    frame = table.to_frame().set_index("Item")
    by_hand = expanded.report.maxdiff("q_md").to_frame().set_index("Item")
    for column in ("Shown", "Best", "Worst", "Score", "Utility", "Share %"):
        assert np.allclose(frame[column], by_hand.loc[frame.index, column], atol=2e-3), column
    assert table.stats["Weight"] == "w"
    assert table.stats["Base"] == "80 respondents (120 weighted)"
    assert "Weight" not in data.report.maxdiff("q_md").stats


def test_the_data_has_to_carry_the_questions_variables():
    question = _question(tasks=2, per_task=3, versions=2)
    data = _fieldwork(question, n=5)
    without = data.with_frame(data.frame.drop(columns=["md_version"]))
    with pytest.raises(KeyError, match="md_version"):
        md.answers(without, "q_md")


# ─── the export that lets somebody run HB themselves ─────────────────────────


def test_the_exported_file_says_the_same_thing_the_engine_does(tmp_path):
    """The only check available for the export, and it is a strong one: fit the
    same model on the file as an outside tool would, and see whether it finds
    the same preferences. A mis-coded worst task or a flipped sign fails here,
    and nothing else would catch it — there is no R to run the script in."""

    from siamang.io.choice import write_maxdiff_choices

    question = _question()
    data = _fieldwork(question, n=300)
    path = write_maxdiff_choices(data, "q_md", tmp_path / "md")
    frame = pd.read_csv(path)

    columns = [c for c in frame.columns if c.startswith("x")]
    chosen = np.zeros(len(frame), dtype=bool)
    for _, block in frame.groupby("ques"):
        chosen[block.index[int(block.iloc[0]["y"]) - 1]] = True
    from_file = mnl(
        ChoiceSets(
            design=frame[columns].to_numpy(float),
            chosen=chosen,
            group=frame["ques"].to_numpy(),
            names=columns,
        )
    )
    internal = md.utilities(data, "q_md")
    estimate = dict(zip(internal.table["term"], internal.table["estimate"], strict=True))
    ours = np.array([estimate[ITEMS[code]] for code in question.item_codes])
    theirs = np.r_[from_file.coefficients, 0.0]
    assert np.corrcoef(ours, theirs)[0, 1] > 0.999
    assert list(np.argsort(-ours)) == list(np.argsort(-theirs))


def test_the_exported_shape_is_the_one_the_r_packages_require(tmp_path):
    """Every task the same number of alternatives — bayesm needs that, which is
    why the export uses the paired coding and the engine's own estimate does
    not."""

    from siamang.io.choice import write_maxdiff_choices

    question = _question(tasks=3, per_task=4, versions=3)
    data = _fieldwork(question, n=8)
    path = write_maxdiff_choices(data, "q_md", tmp_path / "md")
    frame = pd.read_csv(path)

    sizes = frame.groupby("ques").size().unique()
    assert list(sizes) == [4]
    # y carries the chosen alternative on the first row of each task, zero after.
    first_rows = frame.groupby("ques").head(1)
    assert (first_rows["y"] >= 1).all() and (first_rows["y"] <= 4).all()
    assert (frame.groupby("ques")["y"].apply(lambda s: (s != 0).sum()) == 1).all()
    # Two tasks per answered task: the best pick, then the same items negated.
    assert frame["ques"].nunique() == 8 * 3 * 2
    assert frame[[c for c in frame.columns if c.startswith("x")]].to_numpy().min() == -1.0


def test_the_dictionary_describes_exactly_the_columns_in_the_file(tmp_path):
    """A dictionary that has drifted from its data is worse than none: it is
    read instead of the file."""

    import json

    from siamang.io.choice import write_maxdiff_choices

    question = _question(tasks=2, per_task=3, versions=2)
    data = _fieldwork(question, n=5)
    path = write_maxdiff_choices(data, "q_md", tmp_path / "md")
    frame = pd.read_csv(path)
    dictionary = json.loads(path.with_name("md.dictionary.json").read_text(encoding="utf-8"))

    assert set(dictionary["columns"]) == set(frame.columns)
    # The reference item has no column of its own and the note says which it is.
    assert dictionary["reference"] in dictionary["items"]
    assert dictionary["reference"] in dictionary["note"]
    assert len(dictionary["items"]) == len([c for c in frame.columns if c.startswith("x")]) + 1
    assert path.with_name("md.hb.R").read_text(encoding="utf-8").startswith("# Hierarchical Bayes")
