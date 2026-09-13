"""Data layer for siamang.

Besides :class:`SurveyData` and the table builders, modules of plain pandas
helpers cover the cleaning, weighting and analysis steps of a survey pipeline:

- :mod:`siamang.data.respondents` — one row per respondent, completion time,
  partials and speeders;
- :mod:`siamang.data.quality` — straightlining, contradictions, duplicate
  answer patterns and failed attention checks;
- :mod:`siamang.data.weights` — cell weights, raking, effective sample size;
- :mod:`siamang.data.stats` — tidy frequencies, crosstabs and a chi-square test
  on a bare frame;
- :mod:`siamang.data.multi` — multiple-choice answers over a base of
  respondents, and the indicator columns everything else needs;
- :mod:`siamang.data.turf` — how many different people a shortlist of options
  reaches together;
- :mod:`siamang.data.choice` — choice sets and the conditional logit fitted on
  them, shared by every best–worst or trade-off method;
- :mod:`siamang.data.maxdiff` — counting scores and utilities for a best–worst
  question;
- :mod:`siamang.data.text_coding` — a frozen codeframe applied to open answers.
"""

from siamang.data import (
    choice,
    maxdiff,
    multi,
    quality,
    respondents,
    stats,
    text_coding,
    turf,
    weights,
)
from siamang.data.survey_data import SurveyData
from siamang.data.tables import BannerTable, SurveyTables

__all__ = [
    "BannerTable",
    "SurveyData",
    "SurveyTables",
    "choice",
    "maxdiff",
    "multi",
    "quality",
    "respondents",
    "stats",
    "text_coding",
    "turf",
    "weights",
]
