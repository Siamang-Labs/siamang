"""The checks between a node's parameters, and the conditions they are written in."""

from __future__ import annotations

import pytest

from siamang.flow.registry import RegistryError, condition_holds, spec_from_dict

# ─── conditions and checks ───────────────────────────────────────────────────


def test_a_condition_reads_equal_unequal_set_and_all_of():
    params = {"method": "anova", "posthoc": "none", "test": False, "code": 0, "empty": ""}
    assert condition_holds("method=anova", params)
    assert condition_holds("method!=auto", params)
    assert not condition_holds("method!=anova", params)
    assert condition_holds("method=anova & posthoc=none", params)
    assert not condition_holds("method=anova & posthoc!=none", params)
    assert condition_holds("test=False", params)
    # Set: a code of 0 is set, false and empty are not.
    assert condition_holds("code", params)
    assert not condition_holds("test", params) and not condition_holds("empty", params)
    assert not condition_holds("missing", params)


def test_a_spec_checks_its_checks():
    base = {
        "type": "analyze.x",
        "category": "analyze",
        "title": "X",
        "inputs": {"data": "SurveyData"},
        "outputs": {"stat": "Stat"},
        "params": {
            "a": {"kind": "enum", "values": ["p", "q"], "default": "p"},
            "b": {"kind": "enum", "values": ["r", "s"], "default": "r"},
        },
        "template": [{"when": "a=p & b!=s", "code": "{out.stat} = 1"}],
    }
    spec = spec_from_dict(
        {**base, "checks": [{"when": "a=q", "require": ["b=s"], "message": "q needs s."}]}
    )
    assert spec.checks[0].violated({"a": "q", "b": "r"})
    assert not spec.checks[0].violated({"a": "q", "b": "s"})
    assert not spec.checks[0].violated({"a": "p", "b": "r"})
    assert "checks" not in spec.to_json()  # the palette's schema is unchanged
    with pytest.raises(RegistryError, match="check names unknown param 'c'"):
        spec_from_dict({**base, "checks": [{"when": "c=1", "message": "m"}]})
    with pytest.raises(RegistryError, match="a check needs a 'message'"):
        spec_from_dict({**base, "checks": [{"when": "a=q"}]})
    with pytest.raises(RegistryError, match="error or warning"):
        spec_from_dict({**base, "checks": [{"when": "a=q", "message": "m", "severity": "info"}]})
    with pytest.raises(RegistryError, match="template 'when' names unknown param 'c'"):
        spec_from_dict({**base, "template": [{"when": "a=p & c=1", "code": "x"}]})
