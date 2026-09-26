"""Excel input/output for SurveyData."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from siamang.data.survey_data import SurveyData
from siamang.io._frames import scalar_frame


class ExcelReader:
    def read(self, path: str | Path, **kwargs) -> SurveyData:
        frame = pd.read_excel(path, **kwargs)
        return SurveyData(frame)


class ExcelWriter:
    def write(self, data: SurveyData, path: str | Path, **kwargs) -> Path:
        from siamang.io.excel_text import to_excel

        output = Path(path)
        # An open answer "=1+1" is text: written as a formula it would run in
        # Excel and read back as no answer at all.
        to_excel(scalar_frame(data.frame), output, index=False, **kwargs)
        return output
