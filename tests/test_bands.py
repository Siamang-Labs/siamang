"""siamang.data.bands — numbers into labeled bands, missing codes kept out."""

from __future__ import annotations

import pandas as pd
import pytest

from siamang.core import Variable, VariableMap
from siamang.data import SurveyData
from siamang.data.bands import band_labels, bands


def _data() -> SurveyData:
    variables = VariableMap()
    variables.add(Variable("age", "ratio", label="Age", missing_values=(999,)))
    frame = pd.DataFrame({"age": [17, 18, 29.9, 30, 64, 65, 99, 999, None, "n/a"], "w": [1.0] * 10})
    return SurveyData(frame=frame, variables=variables)


def test_each_band_takes_its_lower_bound_and_stops_before_the_next():
    out = bands(_data(), "age", bins=[18, 30, 65, 100], into="age_band")
    codes = out.data.frame["age_band"]
    # 17 is below the first band, 999 a missing code, then a blank and a text.
    assert codes.tolist()[:7] == [pd.NA, 1, 1, 2, 2, 3, 3]
    assert codes.iloc[7:].isna().all()
    variable = out.data.variables["age_band"]
    assert variable.scale == "ordinal" and variable.label == "Age (bands)"
    assert variable.labels == {1: "18 to under 30", 2: "30 to under 65", 3: "65 to under 100"}
    # The source column is left exactly as it was, 999 included.
    assert out.data.frame["age"].tolist()[7] == 999


def test_the_stats_count_every_band_and_everything_left_out():
    stats = bands(_data(), "age", bins=[18, 30, 65, 100], into="age_band").stats
    assert stats["Variable"] == "age → age_band"
    assert stats["Bands"] == "18 to under 30: 2; 30 to under 65: 2; 65 to under 100: 2"
    assert stats["Outside the bands"] == 1  # the 17
    assert (stats["Missing codes"], stats["Blank"], stats["Not numbers"]) == (1, 1, 1)
    weighted = bands(_data().with_weight("w"), "age", bins=[18, 100], into="b").stats
    assert weighted["Weight"] == "unweighted (the weight 'w' is not applied)"


def test_a_missing_code_inside_the_bands_stays_out_of_them():
    """Without the codebook, 999 would be the oldest respondent in the file."""

    out = bands(_data(), "age", bins=[0, 500, 1000], into="b")
    assert pd.isna(out.data.frame["b"].iloc[7])
    assert out.stats["Bands"] == "0 to under 500: 7; 500 to under 1000: 0"


def test_labels_and_closed_upper_bounds_can_be_chosen():
    out = bands(_data(), "age", bins=[18, 30, 65], into="b", labels=["Young", "Older"], right=True)
    assert out.data.variables["b"].labels == {1: "Young", 2: "Older"}
    # Upper bounds included: 30 goes down, 18 stays in the first band.
    assert out.data.frame["b"].tolist()[1:5] == [1, 1, 1, 2]
    assert band_labels([18, 30, 65], right=True) == ["18 to 30", "over 30 to 65"]
    assert band_labels([0.5, 1.5]) == ["0.5 to under 1.5"]


def test_boundaries_that_cannot_make_bands_are_refused():
    with pytest.raises(ValueError, match="at least two"):
        bands(_data(), "age", bins=[18], into="b")
    with pytest.raises(ValueError, match="increase"):
        bands(_data(), "age", bins=[30, 18], into="b")
    with pytest.raises(ValueError, match="numbers"):
        bands(_data(), "age", bins=[18, "old"], into="b")
    with pytest.raises(ValueError, match="3 boundaries make 2 bands, but 1 labels"):
        bands(_data(), "age", bins=[18, 30, 65], into="b", labels=["x"])
    with pytest.raises(KeyError, match="nope"):
        bands(_data(), "nope", bins=[1, 2], into="b")
    with pytest.raises(ValueError, match="a list of numbers"):
        bands(_data(), "age", bins="18, 30", into="b")
    with pytest.raises(ValueError, match="a list of texts"):
        bands(_data(), "age", bins=[18, 30, 65], into="b", labels="young, old")
    with pytest.raises(ValueError, match="new variable"):
        bands(_data(), "age", bins=[18, 30], into="age")
