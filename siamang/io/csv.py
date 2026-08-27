"""CSV input/output for SurveyData."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from siamang.data.survey_data import SurveyData


class CSVReader:
    def read(self, path: str | Path, **kwargs) -> SurveyData:
        frame = pd.read_csv(path, **kwargs)
        return SurveyData(frame)


class CSVWriter:
    def write(self, data: SurveyData, path: str | Path, **kwargs) -> Path:
        output = Path(path)
        data.frame.to_csv(output, index=False, **kwargs)
        return output
