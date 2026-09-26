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
        if suffix == ".parquet":
            import pandas as pd

            from siamang.io.snapshot import _lists_back

            # pandas reads a list stored in Parquet as a numpy array, which no
            # multiple-choice helper takes for a list (Explode failed on "the
            # truth value of an array is ambiguous"): back to lists, as
            # read_snapshot gives them.
            return SurveyData(_lists_back(pd.read_parquet(p, **kwargs)))
        raise ValueError(f"Unsupported file format: {suffix}")
