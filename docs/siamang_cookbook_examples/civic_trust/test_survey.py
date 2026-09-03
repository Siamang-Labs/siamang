"""Smoke tests for the Civic Trust 2026 instrument — run with `pytest`."""

import pytest

from codebook import TRUST_ITEMS, variables
from survey import eligible, options, survey
from siamang.core import validate_options


def test_structure_is_valid():
    survey.validate(strict=True)              # raises on any structural problem
    validate_options(survey, options)         # quota cells match the codebook
    assert not [w for w in survey.lint(level="strict") if w.severity == "error"]


def test_eligibility_gate():
    assert eligible.evaluate({"consent": 1, "age": 34, "region": 2})
    assert not eligible.evaluate({"consent": 1, "age": 17, "region": 2})
    assert not eligible.evaluate({"consent": 2, "age": 40, "region": 1})
    assert not eligible.evaluate({"consent": 1, "age": 40, "region": 99})


def test_simulation_respects_gates():
    data = survey.simulate(n=300, seed=42)
    frame = data.frame
    assert frame.shape == (300, len(variables))
    ineligible = ~((frame["consent"] == 1) & (frame["age"] >= 18) & (frame["region"] != 99))
    # Everyone screened out has NaN on the gated pages
    assert frame.loc[ineligible, "trust_govt"].isna().all()
    # Nobody eligible is missing the trust battery
    assert frame.loc[~ineligible, [v.name for v in TRUST_ITEMS]].notna().all().all()
    assert not [i for i in data.validate() if i.severity == "error"]


@pytest.mark.parametrize("seed", [1, 2])
def test_simulation_is_reproducible(seed):
    a = survey.simulate(n=50, seed=seed).frame
    b = survey.simulate(n=50, seed=seed).frame
    assert a.equals(b)
