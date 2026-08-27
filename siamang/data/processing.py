"""Data transformation helpers for SurveyData."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True, slots=True)
class DataProcessing:
    frame: pd.DataFrame

    def recode(self, column: str, mapping: dict[Any, Any]):
        from siamang.data.survey_data import SurveyData

        copy = self.frame.copy()
        copy[column] = copy[column].replace(mapping)
        return SurveyData(copy)
