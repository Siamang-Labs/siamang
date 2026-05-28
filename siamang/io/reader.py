"""Simple file reader router."""

from __future__ import annotations

from pathlib import Path

from siamang.data.survey_data import SurveyData
from siamang.io.csv import CSVReader
from siamang.io.excel import ExcelReader
from siamang.io.spss import SPSSReader
from siamang.io.stata import StataReader


class SurveyDataReader:
    def read(self, path: str | Path, **kwargs) -> SurveyData:
        p = Path(path)
        suffix = p.suffix.lower()
        if suffix == ".csv":
            return CSVReader().read(p, **kwargs)
        if suffix in {".xlsx", ".xls"}:
            return ExcelReader().read(p, **kwargs)
        if suffix == ".sav":
            return SPSSReader().read(p, **kwargs)
        if suffix == ".dta":
            return StataReader().read(p, **kwargs)
        raise ValueError(f"Unsupported file format: {suffix}")
