"""Interactive Result charts: every kind of ``visualize.result_chart`` as Vega-Lite.

The charts of an analysis's result (:mod:`siamang.reporting.result_charts`,
:mod:`siamang.reporting.method_charts`) say what they draw as a Vega-Lite 6
spec, as the charts of the data do (``tests/test_interactive_charts.py``). Each
spec is held to the same: valid against the Vega-Lite 6.4.3 JSON Schema, its
numbers the ones the picture was drawn from — read back from the artists
matplotlib drew, or from the analysis's own result where the analysis draws its
picture itself — no respondent's row, and drawn by the vendored libraries in
headless Chromium without an error, a warning or a request to anywhere.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
import pandas as pd
import pytest

matplotlib.use("Agg")

from jsonschema import Draft7Validator  # noqa: E402
from jsonschema.exceptions import best_match  # noqa: E402

import siamang as sg  # noqa: E402
from siamang.core.variable import Variable, VariableMap  # noqa: E402
from siamang.data import (  # noqa: E402
    SurveyData,
    correspondence,
    drivers,
    factor,
    paired,
    pricing,
    text_coding,
    turf,
)
from siamang.reporting import Report, vega  # noqa: E402
from siamang.reporting import result_charts as rc  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SCHEMA = FIXTURES / "vega-lite-v6.4.3.schema.json"
N = 300


# ─── the results ─────────────────────────────────────────────────────────────


def _survey(weighted: bool = False) -> SurveyData:
    """300 respondents: a region, an age, an income, three items on one scale,
    a 0–10 recommendation, three yes/no awareness questions — and an id no
    spec may carry."""

    rng = np.random.default_rng(5)
    region = rng.choice([1, 2, 3, 4], size=N, p=[0.35, 0.3, 0.2, 0.15])
    latent = rng.normal(size=N)
    items = {
        f"t{i}": np.clip(np.round(3 + 0.3 * i + latent * 0.8 + rng.normal(0, 0.8, N)), 1, 5)
        for i in range(1, 4)
    }
    frame = pd.DataFrame(
        {
            "respondent_id": [f"RID-{index:05d}-SECRET" for index in range(N)],
            "region": region,
            "age": np.round(rng.normal(44, 14, N) + 3 * (region == 2)).clip(18, 90),
            "income": np.round(rng.lognormal(10.5, 0.5, N), -2),
            "recommend": np.clip(np.round(rng.normal(7.2, 2.2, N)), 0, 10),
            "aware_a": (rng.random(N) < 0.7).astype(int),
            "aware_b": (rng.random(N) < 0.45).astype(int),
            "aware_c": (rng.random(N) < 0.25).astype(int),
            "w": rng.uniform(0.5, 1.8, N).round(3),
            **items,
        }
    )
    scale = {1: "Disagree strongly", 2: "Disagree", 3: "Neither", 4: "Agree", 5: "Agree strongly"}
    variables = VariableMap()
    variables.add_many(
        [
            Variable("respondent_id", "nominal", label="Respondent"),
            Variable(
                "region",
                "nominal",
                label="Region",
                labels={1: "North", 2: "South", 3: "East", 4: "Capital metropolitan area"},
            ),
            Variable("age", "ratio", label="Age"),
            Variable("income", "ratio", label="Household income"),
            Variable("recommend", "interval", label="Likelihood to recommend"),
            *[
                Variable(name, "nominal", label=label, labels={0: "No", 1: "Yes"})
                for name, label in (
                    ("aware_a", "Aware of Acme"),
                    ("aware_b", "Aware of Globex"),
                    ("aware_c", "Aware of Initech"),
                )
            ],
            Variable("w", "ratio", label="Weight"),
            *[
                Variable(f"t{i}", "interval", label=f"Trust in {name}", labels=scale)
                for i, name in zip(range(1, 4), ["Acme", "Globex", "Initech"], strict=True)
            ],
        ]
    )
    data = SurveyData(frame=frame, variables=variables)
    return data.with_weight("w") if weighted else data


def _choices() -> SurveyData:
    """A MaxDiff and a conjoint answered by 160 respondents (the flow tests'
    questionnaire)."""

    items = {
        1: "Price",
        2: "Quality of the materials",
        3: "Speed of delivery",
        4: "Friendly support",
        5: "Range",
    }
    variables = [
        sg.Variable(f"md_t{task}_{side}", "nominal", label=f"t{task} {side}", labels=items)
        for task in (1, 2, 3)
        for side in ("best", "worst")
    ]
    variables.append(sg.Variable("md_version", "nominal", label="Design version"))
    maxdiff = sg.MaxDiff(
        "Which matters most?", variables, per_task=3, tasks=3, versions=4, seed=2, id="q_md"
    )
    attributes = [
        sg.Attribute(
            "brand", [sg.Option(1, "Acme"), sg.Option(2, "Globex"), sg.Option(3, "Initech")]
        ),
        sg.Attribute("price", [sg.Option(10, "10"), sg.Option(15, "15"), sg.Option(20, "20")]),
    ]
    tasks = [
        sg.Variable(f"cbc_t{t}", "nominal", label=f"Task {t}", labels={1: "1", 2: "2", 3: "3"})
        for t in (1, 2, 3, 4)
    ]
    tasks.append(sg.Variable("cbc_version", "nominal", label="Design version"))
    conjoint = sg.Conjoint(
        "Which would you buy?",
        tasks,
        attributes=attributes,
        alternatives=3,
        tasks=4,
        versions=6,
        seed=7,
        id="q_cbc",
    )
    survey = sg.Questionnaire(title="Choices", pages=[sg.Page(name="p", items=[maxdiff, conjoint])])
    # Answers drawn from known utilities plus Gumbel noise, as the tests of
    # the two models draw them (a simulated walk of the questionnaire is slow).
    worth = {1: 0.4, 2: 0.9, 3: 0.0, 4: -0.3, 5: -0.8}
    parts = {(0, 1): 0.0, (0, 2): 0.5, (0, 3): -0.3, (1, 10): 0.0, (1, 15): -0.6, (1, 20): -1.4}
    md, cbc = maxdiff.resolved_design(), conjoint.resolved_design()
    rng = np.random.default_rng(4)
    rows = []
    for _ in range(160):
        row: dict[str, Any] = {}
        version = int(rng.integers(len(md.versions)))
        row["md_version"] = version
        for task in range(maxdiff.tasks):
            shown = list(md.task(version, task))
            best = shown[int(np.argmax([worth[c] for c in shown] + rng.gumbel(size=len(shown))))]
            rest = [c for c in shown if c != best]
            worst = rest[int(np.argmin([worth[c] for c in rest] + rng.gumbel(size=len(rest))))]
            best_var, worst_var = maxdiff.task_variables(task)
            row[best_var.name], row[worst_var.name] = best, worst
        version = int(rng.integers(len(cbc.versions)))
        row["cbc_version"] = version
        for task in range(conjoint.tasks):
            profiles = cbc.task(version, task)
            utility = [sum(parts[(i, code)] for i, code in enumerate(p)) for p in profiles]
            choice = int(np.argmax(utility + rng.gumbel(size=len(utility)))) + 1
            row[conjoint.task_variable(task).name] = choice
        rows.append(row)
    return SurveyData(frame=pd.DataFrame(rows), variables=survey.variables, questionnaire=survey)


def _themes() -> Any:
    variables = VariableMap()
    variables.add(Variable("why", "nominal", label="Why did you choose us?", dtype="str"))
    answers = ["slow", "slow", "dear", "dear", "dear", "kind", "kind", "slow", "other", ""] * 3
    data = SurveyData(frame=pd.DataFrame({"why": answers}), variables=variables)
    frame = text_coding.parse(
        {
            "schema_version": "1.0",
            "variable": "why",
            "themes": [
                {"code": 1, "label": "Charging takes too long at the public stations"},
                {"code": 2, "label": "Price"},
                {"code": 3, "label": "Friendly staff"},
            ],
            "assignments": {
                text_coding.fingerprint("slow"): 1,
                text_coding.fingerprint("dear"): 2,
                text_coding.fingerprint("kind"): 3,
            },
            "sentiment": {
                text_coding.fingerprint("slow"): -1,
                text_coding.fingerprint("dear"): 0,
                text_coding.fingerprint("kind"): 1,
            },
        }
    )
    return data.report.themes(frame, sentiment=True)


def _turf_frame() -> pd.DataFrame:
    rng = np.random.default_rng(8)
    chances = {"a": 0.45, "b": 0.35, "c": 0.3, "d": 0.2, "e": 0.12}
    return pd.DataFrame(
        {name: (rng.random(N) < chance).astype(float) for name, chance in chances.items()}
    )


TURF_LABELS = {
    "a": "Flavors: Vanilla",
    "b": "Flavors: Chocolate",
    "c": "Flavors: Strawberry",
    "d": "Flavors: Pistachio",
    "e": "Flavors: Salted caramel",
}


def _drivers_data() -> SurveyData:
    rng = np.random.default_rng(11)
    n = 240
    x = rng.normal(size=(n, 4))
    y = x @ np.array([0.8, 0.4, -0.3, 0.1]) + rng.normal(size=n)
    frame = pd.DataFrame(x, columns=["price", "staff", "queue", "parking"])
    frame["overall"] = y
    frame["w"] = rng.uniform(0.5, 1.5, n)
    variables = VariableMap()
    variables.add_many(
        [
            Variable("price", "interval", label="Price compared with other shops in the area"),
            Variable("staff", "interval", label="Friendliness of the staff"),
            Variable("queue", "interval", label="Waiting time at the tills"),
            Variable("parking", "interval", label="Parking"),
            Variable("overall", "interval", label="Overall satisfaction"),
        ]
    )
    return SurveyData(frame=frame, variables=variables).with_weight("w")


def _smoke() -> SurveyData:
    """R's smoke table (ca::smoke) as respondents: staff group by smoking."""

    smoke = [[4, 2, 3, 2], [4, 3, 7, 4], [25, 10, 12, 4], [18, 24, 33, 13], [10, 6, 7, 2]]
    rows, columns = [], []
    for i, counts in enumerate(smoke, start=1):
        for j, count in enumerate(counts, start=1):
            rows += [i] * count
            columns += [j] * count
    variables = VariableMap()
    variables.add_many(
        [
            Variable("staff", "nominal", label="Staff group", labels={
                1: "Senior managers", 2: "Junior managers", 3: "Senior employees",
                4: "Junior employees", 5: "Secretaries"}),
            Variable("smoking", "ordinal", label="Smoking", labels={
                1: "None", 2: "Light", 3: "Medium", 4: "Heavy"}),
        ]
    )  # fmt: skip
    return SurveyData(frame=pd.DataFrame({"staff": rows, "smoking": columns}), variables=variables)


def _brand_grid() -> Any:
    """A brand-image grid with long labels: 32 points to label on one map."""

    rng = np.random.default_rng(3)
    names = [f"Brand {chr(65 + i)} Supermarkets and Groceries" for i in range(12)]
    ticks = [f"Attribute number {j + 1} of the image grid" for j in range(20)]
    where_b, where_a = rng.normal(size=(12, 2)), rng.normal(size=(20, 2))
    rows = []
    for b in range(12):
        chance = 1 / (1 + np.exp(-(0.9 * where_b[b] @ where_a.T - 0.8)))
        for _ in range(60):
            rows.append([b + 1, *(rng.random(20) < chance).astype(int)])
    frame = pd.DataFrame(rows, columns=["brand"] + [f"a{j}" for j in range(20)])
    variables = VariableMap()
    variables.add(
        Variable("brand", "nominal", label="Brand", labels=dict(enumerate(names, start=1)))
    )
    for j, label in enumerate(ticks):
        variables.add(Variable(f"a{j}", "nominal", label=label, labels={0: "No", 1: "Yes"}))
    data = SurveyData(frame=frame, variables=variables)
    return correspondence.analyze(data, "brand", attributes=[f"a{j}" for j in range(20)])


def _prices() -> SurveyData:
    rng = np.random.default_rng(21)
    n = 200
    base = rng.lognormal(np.log(12), 0.35, n)
    frame = pd.DataFrame(
        {
            "tc": np.round(base * 0.45),
            "ch": np.round(base * 0.75),
            "ex": np.round(base * 1.3),
            "te": np.round(base * 1.8),
            "lc": rng.integers(1, 6, n),
            "le": rng.integers(1, 6, n),
            "p8": (rng.random(n) < 0.8).astype(int),
            "p12": (rng.random(n) < 0.55).astype(int),
            "p16": (rng.random(n) < 0.35).astype(int),
            "p20": (rng.random(n) < 0.15).astype(int),
            "w": rng.uniform(0.6, 1.4, n),
        }
    )
    variables = VariableMap()
    variables.add_many(
        [
            Variable("tc", "ratio", label="Too cheap (EUR)"),
            Variable("ch", "ratio", label="A bargain (EUR)"),
            Variable("ex", "ratio", label="Getting expensive (EUR)"),
            Variable("te", "ratio", label="Too expensive (EUR)"),
        ]
    )
    return SurveyData(frame=frame, variables=variables).with_weight("w")


PRICE_QUESTIONS = {"too_cheap": "tc", "cheap": "ch", "expensive": "ex", "too_expensive": "te"}


def _results() -> dict[str, Any]:
    """Every kind a Result chart draws, and the forms within a kind, by name."""

    d, w = _survey(), _survey(weighted=True)
    two = SurveyData(frame=d.frame[d.frame["region"] <= 2], variables=d.variables)
    items = [f"t{i}" for i in range(1, 4)]
    choices = _choices()
    products = {"Cheap Acme": {"brand": 1, "price": 10}, "Dear Globex": {"brand": 2, "price": 20}}
    pca = w.analysis.pca(items)
    fa = factor.analyze(d, [*items, "age", "recommend"], criterion="parallel", hide_below=0.3)
    clusters = d.cluster(items, k=3)
    frame = d.frame.assign(buy=(d.frame["t1"] >= 4).astype(int))
    buy = SurveyData(frame=frame, variables=d.variables)
    ols = w.analysis.regression("recommend", ["age", "t1", "region"])
    logit = buy.analysis.regression("buy", ["age", "recommend"])
    ordinal = d.analysis.regression("t1", ["age", "recommend"], kind="ordinal")
    search = turf.turf(_turf_frame(), list(TURF_LABELS), max_size=4, labels=TURF_LABELS)
    fixed = turf.evaluate(
        _turf_frame(), ["a", "b", "c"], items=list(TURF_LABELS), labels=TURF_LABELS
    )
    key = drivers.analyze(_drivers_data(), "overall", ["price", "staff", "queue", "parking"])
    prices = _prices()
    themes = _themes()
    return {
        "means": rc.chart(w.report.means("age", by="region")),
        "means_letters": rc.chart(
            d.report.means("age", by="region", method="anova", posthoc="tukey")
        ),
        "means_sd": rc.chart(d.report.means("income", by="region"), kind="means_sd"),
        "descriptives": rc.chart(d.report.descriptives(items, by="region"), palette="theme"),
        "descriptives_panels": rc.chart(d.report.descriptives(["income", "age"])),
        "ttest": rc.chart(two.report.ttest("age", by="region")),
        "ttest_one": rc.chart(d.report.ttest("age", kind="one_sample", mu=45)),
        "paired": rc.chart(paired.compare(d, items).table),
        "mcnemar": rc.chart(paired.compare(d, ["aware_a", "aware_b"], test="mcnemar").table),
        "cochran": rc.chart(paired.cochran(w, ["aware_a", "aware_b", "aware_c"]).table),
        "proportion": rc.chart(w.analysis.proportion_ci("region", 2, weighted=True)),
        "nps": rc.chart(d.report.nps("recommend")),
        "turf_reach": rc.chart([search, {"Weight": "w"}]),
        "turf_items": rc.chart(fixed),
        "maxdiff_utilities": rc.chart(choices.report.maxdiff("q_md")),
        "maxdiff_scores": rc.chart(choices.report.maxdiff("q_md"), kind="scores"),
        "maxdiff_shares": rc.chart(choices.report.maxdiff("q_md"), kind="shares"),
        "conjoint_importance": rc.chart(choices.report.conjoint("q_cbc")),
        "conjoint_partworths": rc.chart(choices.report.conjoint("q_cbc"), kind="partworths"),
        "shares": rc.chart(choices.report.conjoint_shares("q_cbc", products)),
        "scree": rc.chart([pca.variance, pca.stats]),
        "loadings": rc.chart(pca.loadings, palette="theme"),
        "factor_scree": rc.chart(fa.variance),
        "factor_loadings": rc.chart(fa.loadings),
        "profile": rc.chart([clusters.centroids, clusters.stats]),
        "coefficients": rc.chart(ols),
        "odds_ratios": rc.chart(logit),
        "ordinal": rc.chart(ordinal),
        "correlations": rc.chart(
            w.report.correlation_matrix([*items, "age", "income"], method="pearson")
        ),
        "themes": rc.chart(themes),
        "sentiment": rc.chart(themes, kind="sentiment"),
        "drivers": rc.chart([key.table, key.stats]),
        "map": rc.chart(correspondence.analyze(_smoke(), "staff", column="smoking").rows),
        "map_crowded": rc.chart(_brand_grid().table, figsize=(6, 4.5)),
        "van_westendorp": rc.chart(pricing.van_westendorp(prices, **PRICE_QUESTIONS)),
        "van_westendorp_nms": rc.chart(
            pricing.van_westendorp(
                prices, **PRICE_QUESTIONS, likelihood_cheap="lc", likelihood_expensive="le"
            ).table
        ),
        "gabor_granger": rc.chart(
            pricing.gabor_granger(prices, ["p8", "p12", "p16", "p20"], prices=[8, 12, 16, 20]).table
        ),
    }


@pytest.fixture(scope="module")
def charts() -> dict[str, Any]:
    import matplotlib.pyplot as plt

    matplotlib.rcParams["figure.max_open_warning"] = 0  # every chart is kept to be read
    made = _results()
    yield made
    plt.close("all")


@pytest.fixture(scope="module")
def specs(charts) -> dict[str, dict[str, Any]]:
    return {name: chart.vega_lite() for name, chart in charts.items()}


@pytest.fixture(scope="module")
def validator() -> Draft7Validator:
    return Draft7Validator(json.loads(SCHEMA.read_text("utf-8")))


def _main(spec: dict[str, Any]) -> dict[str, Any]:
    """The chart's own view: the first of a spec with notes under it."""

    return spec["vconcat"][0] if len(spec.get("vconcat", [])) == 1 else spec


def _datasets(spec: Any) -> list[list[dict[str, Any]]]:
    """Every inline dataset of ``spec``, wherever it is."""

    found = []
    if isinstance(spec, dict):
        data = spec.get("data")
        if isinstance(data, dict) and isinstance(data.get("values"), list):
            found.append(data["values"])
        for key, value in spec.items():
            if key != "data":
                found += _datasets(value)
    elif isinstance(spec, list):
        for item in spec:
            found += _datasets(item)
    return found


def _rows(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """The chart's own rows: its main view's (first) dataset."""

    return _datasets(_main(spec))[0]


#: The charts drawn as rows of estimates with their intervals, as bars, as
#: stacks of shares and as heatmaps.
DOTS = (
    "means",
    "means_letters",
    "means_sd",
    "descriptives",
    "descriptives_panels",
    "ttest",
    "ttest_one",
    "paired",
    "mcnemar",
    "cochran",
    "maxdiff_utilities",
    "profile",
    "coefficients",
    "odds_ratios",
    "ordinal",
)
BARS = (
    "maxdiff_scores",
    "maxdiff_shares",
    "conjoint_importance",
    "conjoint_partworths",
    "shares",
    "themes",
    "drivers",
)
STACKS = ("nps", "sentiment")
HEATMAPS = ("loadings", "factor_loadings", "correlations")


# ─── the specs ───────────────────────────────────────────────────────────────


def test_every_kind_a_result_chart_draws_has_a_spec(charts, specs):
    assert {chart.drawn for chart in charts.values()} == set(rc.KINDS)
    assert [name for name, spec in specs.items() if spec is None] == []
    assert set(DOTS + BARS + STACKS + HEATMAPS) <= set(charts)


def test_every_spec_is_valid_vega_lite_6(specs, validator):
    for name, spec in specs.items():
        assert spec["$schema"] == vega.SCHEMA, name
        errors = list(validator.iter_errors(spec))
        assert not errors, f"{name}: {best_match(errors).message[:400]}"
        json.dumps(spec, allow_nan=False)
        # Nothing to load: no address but the schema's own name.
        addresses = re.findall(r"https?://[^\s\"']+", json.dumps(spec))
        assert addresses == [vega.SCHEMA], (name, addresses)


def _words(text: str) -> list[str]:
    return re.findall(r"[\w'%.,:×()=+-]+", text)


def test_every_spec_says_what_the_picture_says(charts, specs):
    """The picture's title and weight line, its notes, a description, and a
    tooltip with the base."""

    for name, spec in specs.items():
        chart, drawn = charts[name], charts[name]._drawn
        assert spec["usermeta"]["siamang"]["chart"] == chart.drawn, name
        assert spec["description"] and len(spec["description"]) > 30, name
        title = json.dumps(spec["title"]["text"], ensure_ascii=False)
        heading = (
            chart._fig._suptitle.get_text()
            if chart._suptitle
            else chart._fig.axes[0].get_title(loc="left")
        )
        first = heading.split("\n")[0].split()[:3]
        assert all(word in title for word in first), (name, heading, title)
        subtitle = " ".join(spec["title"].get("subtitle") or [])
        if chart.weight_note:
            assert " ".join(chart.weight_note.split()) in subtitle, name
        # Every note the picture writes under its plot is at the spec's foot.
        notes = [
            " ".join(text._siamang_note.split())
            for ax in chart._fig.axes
            for text in ax.texts
            if getattr(text, "_siamang_note", None)
        ]
        assert all(note in spec["usermeta"]["siamang"]["notes"] for note in notes), name
        # A tooltip says the base wherever the chart has one.
        if drawn.base or name in DOTS:
            assert '"title": "Base"' in json.dumps(spec), name


def test_a_title_given_replaces_the_result_s_own(charts):
    table = _survey().report.means("age", by="region")
    spec = rc.chart(table, title="How old, where").vega_lite()
    assert spec["title"]["text"] == "How old, where"
    key = drivers.analyze(_drivers_data(), "overall", ["price", "staff", "queue", "parking"])
    titled = rc.chart(key, title="What drives it").vega_lite()
    assert titled["title"]["text"] == "What drives it"
    # The analysis's own lines under it, as in its picture.
    assert titled["title"]["subtitle"][-1] == "weighted by 'w'"
    assert titled["title"]["subtitle"][0].startswith("Johnson's relative weights, R² = ")


def test_the_report_theme_s_colors_reach_a_result_chart():
    from siamang.reporting import ReportTheme, chart_theme

    theme = ReportTheme(
        chart_palette=("#123456", "#abcdef", "#ff8800", "#00aa55"),
        chart_text_color="#222244",
        chart_diverging=("#aa0000", "#0000aa"),
    )
    items = [f"t{i}" for i in range(1, 4)]
    means = rc.chart(_survey().report.descriptives(items, by="region"), palette="theme")
    spec = chart_theme.in_report(means, theme).vega_lite()
    colour = _main(spec)["layer"][-2]["encoding"]["fill"]
    assert colour["scale"]["range"] == ["#123456", "#abcdef", "#ff8800", "#00aa55"]
    assert spec["config"]["axis"]["labelColor"] == "#222244"
    nps = rc.chart(_survey().report.nps("recommend"), palette="theme")
    stack = _main(chart_theme.in_report(nps, theme).vega_lite())["layer"][0]
    detractors, _, promoters = stack["encoding"]["color"]["scale"]["range"]
    assert (detractors, promoters) == ("#aa0000", "#0000aa")


# ─── the numbers are the picture's ───────────────────────────────────────────


def _markers(chart: Any) -> list[float]:
    """The x of every point drawn as a marker of the dot rows."""

    found = []
    for ax in chart._fig.axes:
        for line in ax.lines:
            if line.get_marker() == "o" and line.get_linestyle() == "None":
                found += [float(x) for x in line.get_xdata() if x == x]
    return sorted(found)


def _whiskers(chart: Any) -> list[tuple[float, float]]:
    from matplotlib.collections import LineCollection

    found = []
    for ax in chart._fig.axes:
        for collection in ax.collections:
            if isinstance(collection, LineCollection):
                found += [(float(x0), float(x1)) for (x0, _), (x1, _) in collection.get_segments()]
    return sorted(found)


def _spec_rows(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Every row of a spec's own views (a panel each, or one)."""

    main = _main(spec)
    views = main.get("vconcat", [main])
    return [row for view in views for row in view["data"]["values"]]


@pytest.mark.parametrize("name", DOTS)
def test_dots_are_the_points_and_intervals_drawn(charts, specs, name):
    rows = _spec_rows(specs[name])
    estimates = sorted(row["estimate"] for row in rows if row["estimate"] is not None)
    assert estimates == pytest.approx(_markers(charts[name]))
    intervals = sorted(
        (row["lower"], row["upper"])
        for row in rows
        if row["lower"] is not None and row["upper"] is not None
    )
    assert intervals == pytest.approx(_whiskers(charts[name]))
    # Each value written beside its point is the picture's own text.
    drawn = {text.get_text() for ax in charts[name]._fig.axes for text in ax.texts}
    assert {row["label_text"] for row in rows if row["label_text"]} <= drawn


def test_dots_say_their_base_interval_letters_and_scale(specs):
    means = _rows(specs["means"])
    assert [row["base"] for row in means] == [
        "105 respondents",
        "93 respondents",
        "56 respondents",
        "46 respondents",
    ]
    assert all(re.fullmatch(r"\d\d\.\d\d to \d\d\.\d\d", row["interval"]) for row in means)
    tooltip = json.dumps(_main(specs["means"])["layer"])
    assert '"title": "Weighted mean"' in tooltip and "95% confidence interval" in tooltip
    letters = _rows(specs["means_letters"])
    assert all(row["letters"] for row in letters)
    assert all(row["label_text"].endswith(row["letters"]) for row in letters)
    # An odds ratio on a log scale, ticked as numbers are read.
    odds = next(
        layer for layer in _main(specs["odds_ratios"])["layer"] if layer["mark"]["type"] == "point"
    )
    assert odds["encoding"]["x"]["scale"]["type"] == "log"
    assert len(odds["encoding"]["x"]["axis"]["values"]) >= 3
    # A reference: the test value, a utility's zero.
    for name, value in (("ttest_one", 45.0), ("maxdiff_utilities", 0.0)):
        rules = [layer for layer in _main(specs[name])["layer"] if "datum" in json.dumps(layer)]
        assert rules[0]["encoding"]["x"]["datum"] == value
    # The reference utility says so, and has no interval.
    reference = [row for row in _rows(specs["maxdiff_utilities"]) if row["note"]]
    assert [(row["note"], row["interval"]) for row in reference] == [("reference", "none")]


@pytest.mark.parametrize("name", BARS)
def test_bars_are_the_bars_drawn(charts, specs, name):
    ax = charts[name]._fig.axes[0]
    widths = [patch.get_width() for patch in ax.patches]
    rows = _rows(specs[name])
    assert [row["value"] for row in rows] == pytest.approx(widths)
    texts = {text.get_text() for text in ax.texts}
    assert {row["label_text"] for row in rows} <= texts
    from matplotlib.colors import to_hex

    assert [row["colour"] for row in rows] == [
        to_hex(patch.get_facecolor()) for patch in ax.patches
    ]


def test_a_color_that_stands_for_something_has_its_legend(specs):
    worths = _main(specs["conjoint_partworths"])["layer"][0]
    assert worths["encoding"]["color"]["legend"]["title"] == "Attribute"
    assert worths["params"][0]["bind"] == "legend"
    drivers_bars = _main(specs["drivers"])["layer"][0]
    assert drivers_bars["encoding"]["color"]["scale"]["domain"] == [
        "positive beta",
        "negative beta",
    ]
    rows = _rows(specs["drivers"])
    assert {row["group"] for row in rows if row["detail_0"].startswith("-")} == {"negative beta"}


@pytest.mark.parametrize("name", STACKS)
def test_stacks_are_the_segments_drawn(charts, specs, name):
    ax = charts[name]._fig.axes[0]
    drawn = sorted((patch.get_x(), patch.get_width()) for patch in ax.patches)
    rows = _rows(specs[name])
    stacked = sorted((row["start"], row["end"] - row["start"]) for row in rows)
    assert stacked == pytest.approx(drawn)


def test_turf_and_a_proportion_are_their_numbers(charts, specs):
    items = charts["turf_items"]
    widths = [patch.get_width() for patch in items._fig.axes[0].patches]
    rows = _rows(specs["turf_items"])
    reach = [row["value"] for row in rows if row["order"] == 0]
    unique = [row["value"] for row in rows if row["order"] == 1]
    assert reach + unique == pytest.approx(widths)
    total = [
        layer for layer in _main(specs["turf_items"])["layer"] if layer["mark"]["type"] == "rule"
    ]
    line = [line for line in items._fig.axes[0].lines if line.get_label().startswith("All 3")]
    assert total[0]["data"]["values"][0]["value"] == pytest.approx(line[0].get_xdata()[0])
    curve = charts["turf_reach"]._fig.axes[0].lines[0]
    assert [row["reach"] for row in _rows(specs["turf_reach"])] == pytest.approx(
        list(curve.get_ydata())
    )
    # Each size's portfolio in full in its tooltip.
    assert _rows(specs["turf_reach"])[-1]["portfolio"].count(",") == 3
    proportion = charts["proportion"]._fig.axes[0]
    point = next(line for line in proportion.lines if line.get_marker() == "o")
    assert _rows(specs["proportion"])[0]["share"] == pytest.approx(point.get_xdata()[0])


def test_a_scree_plot_is_its_eigenvalues(charts, specs):
    for name in ("scree", "factor_scree"):
        ax = charts[name]._fig.axes[0]
        eigen = next(
            line for line in ax.lines if line.get_linestyle() == "-" and line.get_label()[0] == "_"
        )
        points = _main(specs[name])["layer"][1]["data"]["values"]
        assert [row["value"] for row in points] == pytest.approx(list(eigen.get_ydata()))
        kept = charts[name]._drawn.kept
        assert [row["kept"] for row in points] == [i < kept for i in range(len(points))]
    lines = _main(specs["factor_scree"])["layer"][0]
    assert lines["encoding"]["color"]["scale"]["domain"][2].startswith("Random data")


@pytest.mark.parametrize("name", HEATMAPS)
def test_heatmaps_are_the_image_drawn(charts, specs, name):
    image = charts[name]._fig.axes[0].images[0].get_array()
    cells = np.ma.filled(np.ma.asarray(image, dtype=float), np.nan).ravel().tolist()
    values = [row["value"] for row in _rows(specs[name])]
    assert [None if value != value else pytest.approx(value) for value in cells] == values


def test_a_correlation_matrix_writes_its_marks_and_says_its_p(specs):
    rows = _rows(specs["correlations"])
    diagonal = [row for row in rows if row["row_name"] == row["column_name"]]
    assert {row["cell"] for row in diagonal} == {"—"}
    marked = [row for row in rows if row["cell"].endswith("***")]
    assert marked and {row["detail_0"] for row in marked} == {"< .001"}
    assert '"title": "p"' in json.dumps(specs["correlations"])
    # A factor analysis's blanks are drawn blank, as its picture's.
    blank = [
        layer
        for layer in _main(specs["factor_loadings"])["layer"]
        if "!isValid" in json.dumps(layer)
    ]
    assert blank and blank[0]["mark"]["color"] == "#f4f4f4"


def test_a_map_is_its_points_and_names_them_where_the_picture_did(charts, specs):
    from matplotlib.collections import PathCollection

    for name in ("map", "map_crowded"):
        ax = charts[name]._fig.axes[0]
        rows_xy, columns_xy = (c for c in ax.collections if isinstance(c, PathCollection))
        drawn = np.vstack([rows_xy.get_offsets(), columns_xy.get_offsets()])
        points = _rows(specs[name])
        assert [(point["x"], point["y"]) for point in points] == pytest.approx(
            [tuple(xy) for xy in drawn.tolist()]
        )
    # Named on the map where the picture named them; a crowded map leaves its
    # names to the tooltips and a box that writes them.
    assert specs["map"]["params"][0]["value"] is True
    assert specs["map_crowded"]["params"][0]["value"] is False
    offsets = [(round(point["dx"]), round(point["lx"])) for point in _rows(specs["map"])]
    assert all(dx == lx for dx, lx in offsets)
    # One scale on both axes: the domains follow the container's width.
    x = _main(specs["map"])["layer"][3]["encoding"]["x"]["scale"]["domain"]
    assert all("containerSize()" in end["expr"] for end in x)


def test_price_sensitivity_is_its_curves_and_points(charts, specs):
    ax = charts["van_westendorp"]._fig.axes[0]
    curves = {
        line.get_label(): list(line.get_ydata()) for line in ax.lines if line.get_label()[0] != "_"
    }
    lines = _main(specs["van_westendorp"])["layer"][1]["data"]["values"]
    for name, values in curves.items():
        assert [row["value"] for row in lines if row["curve"] == name] == pytest.approx(values)
    marked = charts["van_westendorp"].result.points
    names = [
        row["name"]
        for layer in _main(specs["van_westendorp"])["layer"]
        if layer["mark"]["type"] == "text"
        for row in layer["data"]["values"]
    ]
    assert sorted(name.split(" ")[0] for name in names) == sorted(marked)
    nms = _main(specs["van_westendorp_nms"])
    assert len(nms["vconcat"]) == 2 and nms["resolve"]["scale"]["x"] == "shared"
    demand_ax, revenue_ax = charts["gabor_granger"]._fig.axes
    rows = _main(specs["gabor_granger"])["vconcat"][0]["data"]["values"]
    [line] = [line for line in demand_ax.lines if line.get_marker() == "o"]
    assert [row["demand"] for row in rows] == pytest.approx(list(line.get_ydata()))
    assert [row["revenue"] for row in rows] == pytest.approx(
        [bar.get_height() for bar in revenue_ax.patches]
    )
    assert [row["best"] for row in rows].count(True) == 1


# ─── nothing but what the chart draws ────────────────────────────────────────


def test_no_respondent_row_reaches_a_spec(charts, specs):
    for name, spec in specs.items():
        text = json.dumps(spec)
        assert "RID-" not in text and "SECRET" not in text, name
        # A row per bar, point, cell, price or portfolio: never one per
        # respondent — a Result chart plots none.
        largest = max(len(values) for values in _datasets(spec))
        assert largest < 200, (name, largest)


def test_a_recording_that_fails_keeps_the_picture(monkeypatch):
    from siamang.reporting import result_specs

    def broken(item: Any) -> Any:
        raise RuntimeError("no record today")

    monkeypatch.setattr(result_specs, "_series", broken)
    with pytest.warns(RuntimeWarning, match="no interactive chart .*no record today"):
        chart = rc.chart(_survey().report.means("age", by="region"))
    assert chart.vega_lite() is None
    assert chart.png()[:8] == b"\x89PNG\r\n\x1a\n"


# ─── the report and the flow ─────────────────────────────────────────────────


def test_an_interactive_report_draws_result_charts(charts, tmp_path):
    report = Report(title="Results")
    names = ["means", "nps", "scree", "map", "van_westendorp"]
    for name in names:
        report.add(charts[name], caption=name)
    html = report.to_html(standalone=True, interactive=True)
    assert html.count('class="siamang-chart"') == len(names)
    assert html.count('<noscript><img src="data:image/png;base64,') == len(names)
    assert html.count('<script data-library="vega-lite">') == 1
    report.save(tmp_path / "r.md", interactive=True)
    written = sorted(path.name for path in tmp_path.glob("r_fig_*.vl.json"))
    assert len(written) == len(names)
    assert json.loads((tmp_path / written[0]).read_text("utf-8")) == charts[names[0]].vega_lite()


def test_a_result_chart_in_a_flow_writes_its_spec_and_publishes_it(tmp_path):
    from siamang.flow import FlowRunner

    nodes = [
        ("src", "source.responses", {"table": "responses"}),
        ("means", "analyze.means", {"y": "age", "by": "region"}),
        ("chart", "visualize.result_chart", {}),
        ("tile", "output.live_tile", {"kind": "chart", "label": "Age"}),
        ("section", "output.report_section", {"heading": "Age"}),
        ("save", "output.save_report", {"title": "T", "path": "outputs/r.md", "interactive": True}),
    ]
    edges = [
        ("src", "data", "means", "data"),
        ("means", "table", "chart", "result"),
        ("chart", "chart", "tile", "input"),
        ("chart", "chart", "section", "items"),
        ("section", "report", "save", "sections"),
    ]
    flow = {
        "schema_version": "1.0",
        "name": "t",
        "nodes": [{"id": i, "type": t, "params": p} for i, t, p in nodes],
        "edges": [
            {"from": {"node": a, "port": ap}, "to": {"node": b, "port": bp}}
            for a, ap, b, bp in edges
        ],
    }
    result = FlowRunner(flow).run(sources={"src": _survey(weighted=True)}, cwd=tmp_path)
    assert result.ok, result
    outputs = sorted(path.name for path in (tmp_path / "outputs").iterdir())
    assert outputs == ["r.html", "r.md", "r_fig_1.png", "r_fig_1.vl.json"]
    tile = next(tile for tile in result.tiles if tile.node == "tile")
    assert tile.spec is not None and tile.spec["usermeta"]["siamang"]["chart"] == "means"
    spec = json.loads((tmp_path / "outputs" / "r_fig_1.vl.json").read_text("utf-8"))
    assert spec == tile.spec


# ─── in a browser ────────────────────────────────────────────────────────────

_HARNESS = r"""
const fs = require("fs");
const [pageFile, outFile, shots] = process.argv.slice(2);
let chromium;
try { ({ chromium } = require("playwright")); }
catch (e) { console.log(JSON.stringify({ skip: "playwright is not installed" })); process.exit(0); }
const drawn = () => {
  const all = document.querySelectorAll(".siamang-chart").length;
  return all > 0 && all === document.querySelectorAll(".siamang-chart-live, .siamang-chart-failed").length;
};
const read = () => Array.from(document.querySelectorAll(".siamang-chart")).map((box) => {
  const svg = box.querySelector(".siamang-chart-view svg");
  const marks = {}, texts = [];
  let over = 0;
  if (svg) {
    svg.querySelectorAll("g.role-mark").forEach((group) => {
      const cls = group.getAttribute("class");
      if (/(^| )notes_/.test(cls)) return;
      const type = cls.split(" ")[0].replace("mark-", "");
      marks[type] = (marks[type] || 0) + group.children.length;
    });
    const edge = svg.getBoundingClientRect();
    svg.querySelectorAll("text").forEach((text) => {
      const r = text.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) return;
      over = Math.max(over, r.bottom - edge.bottom, r.right - edge.right, edge.left - r.left, edge.top - r.top);
    });
    svg.querySelectorAll("g.mark-text.role-mark text").forEach((text) => {
      if (text.textContent.trim()) texts.push(text.textContent.trim());
    });
  }
  return {
    name: box.getAttribute("data-name"),
    live: box.classList.contains("siamang-chart-live"),
    label: svg ? (svg.getAttribute("aria-label") || "") : "",
    width: svg ? svg.getBoundingClientRect().width : 0,
    marks, texts, over,
  };
});
(async () => {
  let browser;
  try {
    const exe = process.env.PLAYWRIGHT_CHROMIUM;
    browser = await chromium.launch(exe ? { executablePath: exe } : {});
  } catch (e) {
    console.log(JSON.stringify({ skip: "no Chromium: " + String(e.message).split("\n")[0] }));
    process.exit(0);
  }
  const logs = [], requests = [];
  try {
    const page = await browser.newPage({ viewport: { width: 900, height: 1000 } });
    page.on("console", (m) => { if (m.type() !== "log") logs.push(m.type() + ": " + m.text()); });
    page.on("pageerror", (e) => logs.push("pageerror: " + e.message));
    page.on("request", (r) => {
      const url = r.url();
      if (!url.startsWith("file:") && !url.startsWith("data:")) requests.push(url);
    });
    await page.goto("file://" + pageFile);
    await page.waitForFunction(drawn, null, { timeout: 90000 });
    const charts = await page.evaluate(read);
    const view = (name) => '.siamang-chart[data-name="' + name + '"] .siamang-chart-view svg';
    const tooltip = async (name, selector, where) => {
      const target = await page.$(view(name) + " " + selector);
      if (!target) return "";
      await target.scrollIntoViewIfNeeded();
      const box = await target.boundingBox();
      const [fx, fy] = where || [0.5, 0.5];
      await page.mouse.move(box.x + box.width * fx, box.y + box.height * fy);
      await page.waitForTimeout(350);
      const text = await page.evaluate(() => {
        const el = document.getElementById("vg-tooltip-element");
        return el && el.classList.contains("visible") ? el.innerText : (el ? el.innerText : "");
      });
      await page.mouse.move(0, 0);
      await page.waitForTimeout(100);
      return text;
    };
    const tooltips = {
      means: await tooltip("means", "g.mark-symbol.role-mark path"),
      van_westendorp: await tooltip("van_westendorp", "g.mark-rect.role-mark path"),
      gabor_granger: await tooltip("gabor_granger", "g.mark-symbol.role-mark path"),
      map: await tooltip("map", "g.mark-symbol.role-mark path"),
      nps: await tooltip("nps", "g.mark-rect.role-mark path"),
    };
    // The legend: a click hides a series, a second shows it again.
    const opacity = (name) => page.evaluate((root) => Array.from(
      document.querySelector(root + " g.mark-symbol.role-mark").children
    ).map((p) => p.getAttribute("opacity") || "1"), view(name));
    let legend = null;
    const entry = await page.$(view("descriptives") + " g.role-legend-symbol path");
    if (entry) {
      await entry.scrollIntoViewIfNeeded();
      const where = await entry.boundingBox();
      const click = () => page.mouse.click(where.x + where.width / 2, where.y + where.height / 2);
      const before = await opacity("descriptives");
      await click();
      await page.waitForTimeout(250);
      const hidden = await opacity("descriptives");
      await click();
      await page.waitForTimeout(250);
      legend = { before, hidden, shown: await opacity("descriptives") };
    }
    // A crowded map's names: off, and written on a tick of the box.
    const names = { before: 0, after: 0 };
    const count = () => page.evaluate((root) => Array.from(
      document.querySelectorAll(root + " g.mark-text.role-mark text")
    ).filter((t) => t.textContent.trim()).length, view("map_crowded"));
    const box = await page.$('.siamang-chart[data-name="map_crowded"] input[type="checkbox"]');
    if (box) {
      names.before = await count();
      await box.click();
      await page.waitForTimeout(300);
      names.after = await count();
      await box.click();
    }
    if (shots) {
      const boxes = await page.$$(".siamang-chart");
      for (let i = 0; i < boxes.length; i++) {
        const name = await boxes[i].getAttribute("data-name");
        await boxes[i].screenshot({ path: shots + "/" + name + ".png" });
      }
    }
    // A phone's width: every chart laid out again, nothing cut.
    await page.setViewportSize({ width: 400, height: 900 });
    await page.reload();
    await page.waitForFunction(drawn, null, { timeout: 90000 });
    const narrow = await page.evaluate(read);
    fs.writeFileSync(outFile, JSON.stringify({ charts, narrow, logs, requests, tooltips, legend, names }));
    console.log(JSON.stringify({ ok: true }));
  } finally {
    await browser.close();
  }
})().catch((e) => { console.log(JSON.stringify({ error: String((e && e.stack) || e) })); });
"""


@pytest.fixture(scope="module")
def drawn(charts, tmp_path_factory) -> dict[str, Any]:
    """Every Result chart drawn in one interactive report, in headless Chromium."""

    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    folder = tmp_path_factory.mktemp("results")
    names = list(charts)
    report = Report(title="Every Result chart")
    for name in names:
        report.add(charts[name], caption=name)
    html = report.to_html(standalone=True, interactive=True)
    for index, name in enumerate(names, start=1):
        html = html.replace(f'data-name="figure-{index}"', f'data-name="{name}"', 1)
    page = folder / "report.html"
    page.write_text(html, encoding="utf-8")
    harness = folder / "harness.js"
    harness.write_text(_HARNESS, encoding="utf-8")
    out = folder / "out.json"
    run = subprocess.run(
        [node, str(harness), str(page), str(out), os.environ.get("SIAMANG_CHART_SHOTS", "")],
        capture_output=True,
        text=True,
        timeout=400,
        env={**os.environ},
    )
    lines = [line for line in run.stdout.splitlines() if line.startswith("{")]
    status = json.loads(lines[-1]) if lines else {"error": run.stderr[-2000:]}
    if "skip" in status:
        pytest.skip(status["skip"])
    assert status.get("ok"), status
    return json.loads(out.read_text("utf-8"))


def test_every_result_chart_is_drawn_without_an_error_or_a_request(drawn, charts):
    assert drawn["logs"] == []
    assert drawn["requests"] == []
    assert [chart["name"] for chart in drawn["charts"]] == list(charts)
    assert [chart["name"] for chart in drawn["charts"] if not chart["live"]] == []
    # Nothing runs past the drawing's edges, at a report's width or a phone's.
    assert [(c["name"], round(c["over"])) for c in drawn["charts"] if c["over"] > 1] == []
    assert [(c["name"], round(c["over"])) for c in drawn["narrow"] if c["over"] > 1] == []
    assert all(0 < c["width"] <= 400 for c in drawn["narrow"])


def _expected_marks(name: str, spec: dict[str, Any]) -> dict[str, int]:
    """The marks a spec should draw, by type: a point per estimate, a bar per
    value, a segment per share, a cell per coefficient, a line per curve."""

    rows = _spec_rows(spec) if name in DOTS else _rows(spec)
    if name in DOTS:
        return {"symbol": sum(1 for row in rows if row["estimate"] is not None)}
    if name in BARS:
        return {"rect": sum(1 for row in rows if row["value"] is not None)}
    if name in STACKS or name == "turf_items":
        return {"rect": len(rows)}
    if name in HEATMAPS:
        blank = 1 if name == "factor_loadings" else 0
        return {"rect": sum(1 for row in rows if row["value"] is not None or blank)}
    if name == "proportion":
        return {"symbol": 1}
    if name == "turf_reach":
        return {"symbol": len(rows), "line": 1}
    if name.endswith("scree"):
        points = _main(spec)["layer"][1]["data"]["values"]
        return {"symbol": len(points), "line": 3 if name == "factor_scree" else 2}
    if name.startswith("map"):
        return {"symbol": len(rows)}
    if name == "van_westendorp":
        return {"line": 4}
    if name == "van_westendorp_nms":
        return {"line": 5}
    if name == "gabor_granger":
        return {"symbol": len(rows), "line": 1}
    raise AssertionError(name)


def test_every_result_chart_draws_the_marks_its_numbers_call_for(drawn, specs):
    by_name = {chart["name"]: chart for chart in drawn["charts"]}
    for name, spec in specs.items():
        marks = by_name[name]["marks"]
        expected = _expected_marks(name, spec)
        assert {mark: marks.get(mark, 0) for mark in expected} == expected, (name, marks)


def test_a_result_chart_reads_aloud_and_its_tooltips_give_value_and_base(drawn):
    labels = {chart["name"]: chart["label"] for chart in drawn["charts"]}
    assert all(len(label) > 30 for label in labels.values()), labels
    assert labels["means"].startswith("Dot chart") and labels["map"].startswith("Perceptual map")
    tips = drawn["tooltips"]
    assert "Weighted mean" in tips["means"] and "95% confidence interval" in tips["means"]
    assert "respondents" in tips["means"]
    # Over Van Westendorp's range: every curve's share at the price pointed at.
    for curve in ("Too cheap", "Not cheap", "Not expensive", "Too expensive", "Price"):
        assert curve in tips["van_westendorp"], tips["van_westendorp"]
    assert "Revenue per respondent" in tips["gabor_granger"]
    assert "Dimension 1" in tips["map"] and "Mass" in tips["map"]
    assert "Share" in tips["nps"] and "300 respondents" in tips["nps"]


def test_a_legend_click_hides_a_series_and_a_crowded_map_names_on_a_tick(drawn, specs):
    legend = drawn["legend"]
    assert legend is not None and set(legend["before"]) == {"1"}
    assert any(float(value) < 0.2 for value in legend["hidden"])
    assert legend["shown"] == legend["before"]
    points = len(_rows(specs["map_crowded"]))
    assert drawn["names"] == {"before": 0, "after": points}
