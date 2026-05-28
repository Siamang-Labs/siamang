"""Excel input/output for SurveyData."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from siamang.data.survey_data import SurveyData


class ExcelReader:
    def read(self, path: str | Path, **kwargs) -> SurveyData:
        frame = pd.read_excel(path, **kwargs)
        return SurveyData(frame)


class ExcelWriter:
    def write(self, data: SurveyData, path: str | Path, **kwargs) -> Path:
        output = Path(path)
        data.frame.to_excel(output, index=False, **kwargs)
        return output
