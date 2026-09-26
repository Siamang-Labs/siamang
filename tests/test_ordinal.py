"""The ordinal (proportional-odds) logit of the Regression node.

The reference values are quoted from R 4.4: ``MASS::polr`` 7.3-66 and
``ordinal::clm`` 2023.12, on the data sets their documentation uses —
``housing`` (Venables & Ripley's *Modern Applied Statistics with S*, the
satisfaction of 1,681 tenants, as frequencies) and ``wine`` (Randall 1989, the
bitterness of 72 wine tastings) — and from statsmodels 0.15's
``OrderedModel``. ``clm`` maximises to a gradient of 1e-8, as this module does,
so its numbers are matched closely; ``polr`` stops ``optim`` earlier, so its
printed values agree to about 1e-5.
"""

from __future__ import annotations

import json
from itertools import product

import numpy as np
import pandas as pd
import pytest

from siamang.core.variable import MissingValue, Variable, VariableMap
from siamang.data import SurveyData
from siamang.data.models import regression
from siamang.data.ordinal import fit, ordinal_regression

# ─── the reference data ──────────────────────────────────────────────────────

#: MASS::housing: Sat varies fastest, then Infl, Type and Cont (R's expand.grid order).
HOUSING_FREQ = [
    21, 21, 28, 34, 22, 36, 10, 11, 36, 61, 23, 17, 43, 35, 40, 26, 18, 54,
    13, 9, 10, 8, 8, 12, 6, 7, 9, 18, 6, 7, 15, 13, 13, 7, 5, 11,
    14, 19, 37, 17, 23, 40, 3, 5, 23, 78, 46, 43, 48, 45, 86, 15, 25, 62,
    20, 23, 20, 10, 22, 24, 7, 10, 21, 57, 23, 13, 31, 21, 13, 5, 6, 13,
]  # fmt: skip

LEVELS = {1: "Low", 2: "Medium", 3: "High"}
TYPES = {1: "Tower", 2: "Apartment", 3: "Atrium", 4: "Terrace"}


def _housing() -> SurveyData:
    rows = [
        {"Sat": sat, "Infl": infl, "Type": kind, "Cont": cont}
        for cont, kind, infl, sat in product((1, 2), (1, 2, 3, 4), (1, 2, 3), (1, 2, 3))
    ]
    frame = pd.DataFrame(rows).assign(Freq=HOUSING_FREQ)
    variables = VariableMap()
    variables.add_many(
        [
            Variable("Sat", "ordinal", label="Satisfaction", labels=LEVELS),
            Variable("Infl", "nominal", label="Influence", labels=LEVELS),
            Variable("Type", "nominal", label="Type", labels=TYPES),
            Variable("Cont", "nominal", label="Contact", labels={1: "Low", 2: "High"}),
        ]
    )
    return SurveyData(frame=frame, variables=variables)


#: ordinal::wine: nine judges × eight bottles; temperature and skin contact by bottle.
WINE_RATING = [
    2, 3, 3, 4, 4, 4, 5, 5, 1, 2, 1, 3, 2, 3, 5, 4, 2, 3, 3, 2, 5, 5, 4, 4,
    3, 2, 3, 2, 3, 2, 5, 3, 2, 3, 4, 3, 3, 3, 3, 3, 3, 2, 3, 2, 2, 4, 5, 4,
    1, 1, 2, 2, 2, 3, 2, 3, 2, 2, 2, 3, 3, 3, 3, 4, 1, 2, 3, 2, 3, 2, 4, 4,
]  # fmt: skip


def _wine() -> pd.DataFrame:
    warm = [0, 0, 0, 0, 1, 1, 1, 1] * 9
    contact = [0, 0, 1, 1, 0, 0, 1, 1] * 9
    return pd.DataFrame({"rating": WINE_RATING, "warm": warm, "contact": contact})


# ─── the fit ─────────────────────────────────────────────────────────────────


def test_housing_with_frequency_weights_matches_polr_and_clm():
    """polr(Sat ~ Infl + Type + Cont, weights = Freq, data = housing): R's
    ordinal::clm gives the estimates to the digits quoted, MASS::polr prints
    InflMedium 0.5663937 (SE 0.1046528), InflHigh 1.2888191 (0.1271561),
    TypeApartment −0.5723501 (0.1192380), TypeAtrium −0.3661866 (0.1551733),
    TypeTerrace −1.0910149 (0.1514860), ContHigh 0.3602841 (0.0955358),
    Low|Medium −0.4961353 (0.1248472), Medium|High 0.6907083 (0.1254719),
    residual deviance 3479.149 and AIC 3495.149. The thresholds-only model
    has logLik −1824.43881052."""

    result = regression(
        _housing().frame, "Sat", ["Infl", "Type", "Cont"], kind="ordinal", weight="Freq",
        variables=_housing().variables,
    )  # fmt: skip
    table = result.table
    assert list(table["term"]) == [
        "Infl = Medium",
        "Infl = High",
        "Type = Apartment",
        "Type = Atrium",
        "Type = Terrace",
        "Cont = High",
        "Low|Medium",
        "Medium|High",
    ]
    assert list(table["type"]) == ["coefficient"] * 6 + ["threshold"] * 2
    clm = [
        0.566393737902,
        1.288819110364,
        -0.572350002038,
        -0.366186370687,
        -1.091014658963,
        0.360284004567,
        -0.496135138189,
        0.690708259254,
    ]
    clm_se = [
        0.1046527813639,
        0.1271561445676,
        0.1192380085964,
        0.1551733320186,
        0.1514860185608,
        0.0955357950023,
        0.1248472428773,
        0.1254719378494,
    ]
    assert list(table["estimate"]) == pytest.approx(clm, abs=1e-6)
    assert list(table["std_error"]) == pytest.approx(clm_se, abs=1e-7)
    polr = [0.5663937, 1.2888191, -0.5723501, -0.3661866, -1.0910149, 0.3602841]
    assert list(table["estimate"][:6]) == pytest.approx(polr, abs=1e-6)
    # z and p: clm prints 5.41212 (6.2282e-08), 10.13572, −4.80006 (1.5862e-06), …
    assert table["statistic"][0] == pytest.approx(5.41212, abs=1e-5)
    assert table["p_value"][0] == pytest.approx(6.2282e-08, rel=1e-4)
    assert table["p_value"][3] == pytest.approx(0.01828214, rel=1e-6)
    # exp(confint.default(polr)): InflMedium 1.4351624 – 2.1630287, TypeTerrace
    # 0.2495934 – 0.4519843.
    assert table["odds_ratio"][0] == pytest.approx(np.exp(0.566393737902))
    assert table["odds_ratio_lower"][0] == pytest.approx(1.4351624, abs=1e-6)
    assert table["odds_ratio_upper"][0] == pytest.approx(2.1630287, abs=1e-6)
    assert table["odds_ratio_lower"][4] == pytest.approx(0.2495934, abs=1e-6)
    assert table["odds_ratio_upper"][4] == pytest.approx(0.4519843, abs=1e-6)
    assert table["odds_ratio"][6] is None and table["odds_ratio_upper"][7] is None
    stats = result.stats
    assert stats["model"] == "ordinal logit (proportional odds)"
    assert stats["order"] == "Low < Medium < High" and stats["categories"] == 3
    assert stats["log_likelihood"] == pytest.approx(-1739.57464953, abs=1e-6)
    assert stats["aic"] == pytest.approx(3495.149299, abs=1e-5)
    assert stats["pseudo_r_squared"] == pytest.approx(1 - 1739.57464953 / 1824.43881052)
    assert stats["lr_chi_square"] == pytest.approx(2 * (1824.43881052 - 1739.57464953))
    assert stats["lr_df"] == 6 and stats["lr_p"] == 5.136e-34
    assert stats["n"] == 72 and stats["converged"] == 1
    assert stats["weight"] == "Freq"
    # Frequencies: the standard errors count 1,681 tenants, not 72 rows.
    assert stats["weights"] == (
        "frequencies: they sum to 1,681.0 over 72 respondents, and the standard errors "
        "count 1,681.0"
    )
    assert "MASS::polr" in stats["coefficients"]
    assert json.dumps(stats)  # a stat is plain JSON for a tile


def test_wine_unweighted_matches_clm_polr_and_statsmodels():
    """clm(rating ~ temp + contact, data = wine): tempwarm 2.5031020 (SE
    0.5286801), contactyes 1.5277977 (0.4766226), thresholds −1.3443834,
    1.2508088, 3.4668869, 5.0064042, logLik −86.49192337. statsmodels'
    OrderedModel (BFGS to a gradient of 1e-10): 2.503102007, 1.527797658;
    thresholds −1.344383411, 1.250808798, 3.466886926, 5.006404204;
    llf −86.49192336564909. polr prints 2.503073 and 1.527786: its optim stops
    at a relative tolerance of 1e-8 in the deviance."""

    result = regression(_wine(), "rating", ["warm", "contact"], kind="ordinal")
    table = result.table
    assert list(table["term"]) == ["warm", "contact", "1|2", "2|3", "3|4", "4|5"]
    statsmodels = [2.503102007, 1.527797658, -1.344383411, 1.250808798, 3.466886926, 5.006404204]
    assert list(table["estimate"]) == pytest.approx(statsmodels, abs=2e-6)
    assert list(table["std_error"][:2]) == pytest.approx([0.5286801, 0.4766226], abs=1e-6)
    assert list(table["p_value"][:2]) == pytest.approx([2.1946e-06, 0.0013484], rel=1e-4)
    assert list(table["estimate"][:2]) == pytest.approx([2.503073, 1.527786], abs=1e-4)  # polr
    assert result.stats["log_likelihood"] == pytest.approx(-86.49192336564909, abs=1e-8)
    assert result.stats["aic"] == pytest.approx(184.9838467, abs=1e-6)
    assert result.stats["order"] == "1 < 2 < 3 < 4 < 5"
    assert "weight" not in result.stats and "weights" not in result.stats


def test_the_sign_follows_polr_higher_answers_for_a_positive_coefficient():
    """A predictor that moves the respondents up the scale has a positive
    coefficient (logit P(y ≤ j) = θⱼ − xβ); texts that write θⱼ + xβ would
    print it negative."""

    rng = np.random.default_rng(3)
    x = rng.normal(size=400)
    latent = 1.2 * x + rng.logistic(size=400)
    y = np.digitize(latent, [-1.0, 0.0, 1.0]) + 1
    result = ordinal_regression(pd.DataFrame({"y": y, "x": x}), "y", ["x"])
    assert result.table["estimate"][0] > 0.9 and result.table["odds_ratio"][0] > 2.4
    thresholds = result.table["estimate"][1:].to_numpy()
    assert np.all(np.diff(thresholds) > 0)
    assert list(thresholds) == pytest.approx([-1.0, 0.0, 1.0], abs=0.35)


def test_the_array_fit_scaled_predictors_and_equal_weights():
    """A predictor in thousands converges as one in units (the fit centres and
    scales before BFGS and answers in the original units), and weights of 2
    are two copies of each respondent."""

    frame = _wine()
    base = fit(frame[["warm", "contact"]].to_numpy(), frame["rating"].to_numpy() - 1)
    scaled = fit(frame[["warm", "contact"]].to_numpy() * [1000, 1], frame["rating"] - 1)
    assert scaled.converged
    assert scaled.coefficients[0] * 1000 == pytest.approx(base.coefficients[0], abs=1e-6)
    assert list(scaled.thresholds) == pytest.approx(list(base.thresholds), abs=1e-6)
    doubled = fit(frame[["warm", "contact"]].to_numpy(), frame["rating"] - 1, np.full(72, 2.0))
    copies = fit(
        np.vstack([frame[["warm", "contact"]].to_numpy()] * 2),
        np.concatenate([frame["rating"].to_numpy() - 1] * 2),
    )
    assert list(doubled.coefficients) == pytest.approx(list(copies.coefficients), abs=1e-7)
    assert doubled.covariance == pytest.approx(copies.covariance, rel=1e-6)
    assert doubled.covariance == pytest.approx(base.covariance / 2, rel=1e-6)


# ─── on survey data ──────────────────────────────────────────────────────────


def _survey(weighted: bool = False) -> SurveyData:
    rng = np.random.default_rng(11)
    n = 300
    trust = rng.integers(1, 6, n).astype(float)
    region = rng.integers(1, 4, n)
    latent = 0.8 * trust + 0.5 * (region == 3) + rng.logistic(size=n)
    satisfaction = np.digitize(latent, [2.0, 3.0, 4.0]) + 2  # 2..5: nobody answers 1
    trust[:7] = 9  # Refused
    satisfaction[7:10] = 8  # Don't know
    frame = pd.DataFrame(
        {
            "satisfaction": satisfaction,
            "trust": trust,
            "region": region,
            "w": np.linspace(0.5, 1.5, n),
        }
    )
    variables = VariableMap()
    variables.add_many(
        [
            Variable(
                "satisfaction",
                "ordinal",
                label="Satisfaction",
                labels={1: "Very low", 2: "Low", 3: "Middle", 4: "High", 5: "Very high",
                        8: "Don't know"},
                missing=(MissingValue(8, "Don't know"),),
            ),
            Variable("trust", "ordinal", label="Trust", missing=(MissingValue(9, "Refused"),)),
            Variable("region", "nominal", label="Region",
                     labels={1: "North", 2: "South", 3: "Capital"}),
        ]
    )  # fmt: skip
    data = SurveyData(frame=frame, variables=variables)
    return data.with_weight("w") if weighted else data


def test_missing_codes_are_left_out_and_named_and_unused_answers_noted():
    data = _survey()
    result = data.analysis.regression("satisfaction", ["trust", "region"], kind="ordinal")
    stats = result.stats
    assert stats["n"] == 290  # 7 Refused and 3 Don't know left out
    assert stats["missing_codes"] == "Satisfaction: 3 (8 = Don't know); Trust: 7 (9 = Refused)"
    assert stats["note"] == "nobody in the model answered Very low, so the model has 4 answers"
    assert stats["order"] == "Low < Middle < High < Very high"
    assert list(result.table["term"]) == [
        "trust",
        "region = South",
        "region = Capital",
        "Low|Middle",
        "Middle|High",
        "High|Very high",
    ]
    assert result.table["estimate"][0] > 0 and "weight" not in stats
    # The same numbers as the fit on the complete rows by hand.
    frame = data.frame
    keep = (frame["trust"] != 9) & (frame["satisfaction"] != 8)
    x = np.column_stack(
        [frame["trust"][keep], frame["region"][keep] == 2, frame["region"][keep] == 3]
    ).astype(float)
    direct = fit(x, frame["satisfaction"][keep].to_numpy() - 2)
    assert list(result.table["estimate"][:3]) == pytest.approx(list(direct.coefficients))


def test_weighted_data_weighs_the_likelihood_and_names_the_weight():
    data = _survey(weighted=True)
    result = data.analysis.regression("satisfaction", ["trust", "region"], kind="ordinal")
    assert result.stats["weight"] == "w"
    # The weights average 1 over everyone, and nearly so over those modelled
    # (294.8 over 290): nothing to say about their sum.
    assert "weights" not in result.stats
    tenfold = data.with_frame(data.frame.assign(w=data.frame["w"] * 10))
    counted = tenfold.analysis.regression("satisfaction", ["trust", "region"], kind="ordinal")
    assert counted.stats["weights"] == (
        "frequencies: they sum to 2,948.5 over 290 respondents, and the standard errors "
        "count 2,948.5"
    )
    assert list(counted.table["estimate"]) == pytest.approx(list(result.table["estimate"]))
    assert list(counted.table["std_error"]) == pytest.approx(
        list(result.table["std_error"] / 10**0.5), rel=1e-6
    )
    plain = _survey().analysis.regression("satisfaction", ["trust", "region"], kind="ordinal")
    assert result.table["estimate"][0] != pytest.approx(plain.table["estimate"][0], abs=1e-6)
    # Equal weights are no weights; a missing weight counts 0.
    ones = data.with_frame(data.frame.assign(w=1.0))
    same = ones.analysis.regression("satisfaction", ["trust", "region"], kind="ordinal")
    assert list(same.table["estimate"]) == pytest.approx(list(plain.table["estimate"]))
    holes = data.with_frame(data.frame.assign(w=[np.nan] * 20 + [1.0] * 280))
    dropped = holes.analysis.regression("satisfaction", ["trust", "region"], kind="ordinal")
    assert dropped.stats["n"] == 290  # counted, weighing nothing
    cut = _survey().with_frame(_survey().frame.iloc[20:])
    alone = cut.analysis.regression("satisfaction", ["trust", "region"], kind="ordinal")
    assert list(dropped.table["estimate"]) == pytest.approx(list(alone.table["estimate"]))


def test_what_the_model_cannot_take_is_refused_with_the_reason():
    data = _survey()
    frame = data.frame
    two = data.with_frame(frame.assign(satisfaction=np.where(frame["satisfaction"] > 3, 5, 2)))
    with pytest.raises(ValueError, match="has 2 answers here \\(Low, Very high\\).*use the logit"):
        two.analysis.regression("satisfaction", ["trust"], kind="ordinal")
    many = data.with_frame(frame.assign(score=np.arange(len(frame)) % 30))
    with pytest.raises(ValueError, match="30 different values.*at most 20"):
        many.analysis.regression("score", ["trust"], kind="ordinal")
    words = data.with_frame(frame.assign(satisfaction=["good"] * len(frame)))
    with pytest.raises(ValueError, match="holds text that is not a code"):
        words.analysis.regression("satisfaction", ["trust"], kind="ordinal")
    flat = data.with_frame(frame.assign(constant=4.0))
    with pytest.raises(ValueError, match="constant has the same value for every respondent"):
        flat.analysis.regression("satisfaction", ["trust", "constant"], kind="ordinal")
    twice = data.with_frame(frame.assign(double=frame["trust"] * 2))
    with pytest.raises(ValueError, match="collinear"):
        twice.analysis.regression("satisfaction", ["trust", "double"], kind="ordinal")
    listed = data.with_frame(frame.assign(trust=[[1, 2]] * len(frame)))
    with pytest.raises(TypeError, match="prepare.explode"):
        listed.analysis.regression("satisfaction", ["trust"], kind="ordinal")
    with pytest.raises(ValueError, match="'auto', 'ols', 'logit' or 'ordinal'"):
        data.analysis.regression("satisfaction", ["trust"], kind="probit")


def test_a_separating_predictor_is_warned_not_trusted():
    """Every x = 1 answered 1, every 2 answered 2, every 3 answered 3: the
    likelihood keeps rising as β grows, so there is no estimate to report."""

    x = np.repeat([1.0, 2.0, 3.0], 20)
    z = np.random.default_rng(1).normal(size=60)
    frame = pd.DataFrame({"y": np.repeat([1, 2, 3], 20), "x": x, "z": z})
    result = ordinal_regression(frame, "y", ["x", "z"])
    warning = result.stats["warning"]
    assert warning.startswith("x separates the answers — some answer is predicted")
    assert "z" not in warning.split(" separates")[0]
    assert result.table["estimate"][0] > 10
    # Answers that are merely unusual are not separation.
    y = np.array([1] * 10 + [2] * 10 + [1] * 10 + [2] * 10 + [3] * 20)
    fine = ordinal_regression(frame.assign(y=y), "y", ["x", "z"])
    assert "warning" not in fine.stats and fine.stats["converged"] == 1


def test_the_other_kinds_are_unchanged():
    frame = _wine()
    ols = regression(frame, "rating", ["warm", "contact"], kind="ols")
    assert ols.kind == "ols" and list(ols.table.columns) == [
        "term",
        "estimate",
        "std_error",
        "statistic",
        "p_value",
    ]
    auto = regression(frame, "rating", ["warm", "contact"])
    assert auto.kind == "ols"  # five values: auto never chooses the ordinal model
