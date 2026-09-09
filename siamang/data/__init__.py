"""Data layer for siamang.

Besides :class:`SurveyData` and the table builders, three modules of plain
pandas helpers cover the cleaning and weighting steps of a survey pipeline:

- :mod:`siamang.data.respondents` — one row per respondent, completion time,
  partials and speeders;
- :mod:`siamang.data.weights` — cell weights, raking, effective sample size;
- :mod:`siamang.data.stats` — tidy frequencies, crosstabs and a chi-square test
  on a bare frame.
"""

from siamang.data import respondents, stats, weights
from siamang.data.survey_data import SurveyData
from siamang.data.tables import BannerTable, SurveyTables

__all__ = ["BannerTable", "SurveyData", "SurveyTables", "respondents", "stats", "weights"]
