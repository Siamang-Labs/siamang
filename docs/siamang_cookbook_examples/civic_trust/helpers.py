"""Shared helpers for the Civic Trust study (imported by run_local.py, analysis.py and the notebook)."""

import numpy as np
import pandas as pd

import siamang as sg
from siamang.core import Matrix, MultiChoice
from siamang.core.question import question_output_name


def flatten_responses(frame: pd.DataFrame, survey: sg.Questionnaire) -> pd.DataFrame:
    """Turn collected runtime payloads into one column per Variable.

    The React runtime posts its whole answers store: bookkeeping keys
    (``__options__``, ``__pages__``, ``__errors__``), a ``{row: code}`` dict per
    Matrix, a list of selected variable names per wide MultiChoice and a
    ``{"selected": [...], "otherText": ...}`` dict for questions with other_specify.
    """
    frame = frame.loc[:, ~frame.columns.str.startswith("__")].copy()
    for q in survey.all_questions():
        qid = question_output_name(q)
        if isinstance(q, Matrix) and qid in frame.columns:
            cells = frame.pop(qid)
            for v in q.var:
                frame[v.name] = cells.map(lambda d, n=v.name: d.get(n) if isinstance(d, dict) else np.nan)
        elif isinstance(q, MultiChoice) and q.mode == "wide" and qid in frame.columns:
            picks = frame.pop(qid)
            for v in q.var:
                frame[v.name] = picks.map(lambda s, n=v.name: int(n in s) if isinstance(s, list) else np.nan)
        elif q.other_specify and qid in frame.columns:
            frame[qid] = frame[qid].map(lambda d: d.get("selected") if isinstance(d, dict) else d)
    return frame


def rake(frame: pd.DataFrame, targets: dict[str, dict], max_iter: int = 50,
         tol: float = 1e-6) -> pd.Series:
    """Iterative proportional fitting to several marginal targets. Mean weight = 1."""
    w = pd.Series(1.0, index=frame.index)
    for _ in range(max_iter):
        change = 0.0
        for col, target in targets.items():
            p = pd.Series(target, dtype=float)
            p = p / p.sum()
            current = w.groupby(frame[col]).sum()
            total = current.sum()
            for cat, share in p.items():
                if current.get(cat, 0) > 0:
                    factor = share * total / current[cat]
                    change = max(change, abs(factor - 1))
                    w[frame[col] == cat] *= factor
        if change < tol:
            break
    return w / w.mean()
