"""Turn collected runtime payloads into one column per Variable (see the Civic Trust study)."""

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
