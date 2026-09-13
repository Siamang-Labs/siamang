"""CSV input/output for SurveyData."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from siamang.data.survey_data import SurveyData
from siamang.io._frames import scalar_frame


class CSVReader:
    def read(self, path: str | Path, **kwargs) -> SurveyData:
        frame = pd.read_csv(path, **kwargs)
        return SurveyData(frame)


class CSVWriter:
    def write(self, data: SurveyData, path: str | Path, **kwargs) -> Path:
        output = Path(path)
        # `1;3`, the same as SPSS and Stata write, rather than the Python repr
        # of a list — which no other tool reads and which differs from the same
        # project's .sav for no reason a reader could guess.
        scalar_frame(data.frame).to_csv(output, index=False, **kwargs)
        return output
