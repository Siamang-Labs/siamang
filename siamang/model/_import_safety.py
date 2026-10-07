"""What the importers bring in from another tool, made safe on the way in.

A Qualtrics, LimeSurvey or SurveyJS file is a third party's: its page texts are
HTML anyone could have written, its end-of-survey address anything. The
importers put a page's body in the document as :mod:`siamang.core.safe_html`
keeps it (saying what was left out) and an address a respondent is sent to
only when it is an http(s) one (:mod:`siamang.core.safe_url`) — so the
document holds what the survey will show, and loads.
"""

from __future__ import annotations

from typing import Any

from siamang.core.safe_html import check_html_length, sanitize_html_report
from siamang.core.safe_url import navigation_url_problem, normalize_url


def imported_html(text: str, where: str, warnings: list[str]) -> str:
    """``text`` as the runtime would show it; a warning (in ``warnings``)
    names what was left out that could have run a script or changed the
    page. HTML longer than a page's body may be is left out whole."""

    try:
        report = sanitize_html_report(text)
        check_html_length(report.html)  # escaping "<" and "&" can lengthen it
    except ValueError as exc:  # longer than safe_html.MAX_HTML_LENGTH
        warnings.append(f"{where}: HTML left out. {str(exc)[:1].upper()}{str(exc)[1:]}.")
        return ""
    messages = report.messages(dangerous_only=True)
    if messages:
        warnings.append(f"{where}: part of the HTML left out. " + " ".join(messages))
    return report.html


def imported_url(value: Any, where: str, warnings: list[str]) -> str | None:
    """``value`` when it is an address a respondent can be sent to, else None
    and a warning in ``warnings``."""

    if value is None or not str(value).strip():
        return None
    text = str(value)
    problem = navigation_url_problem(text)
    if problem:
        warnings.append(f"{where}: the address {text!r} is not imported: {problem}.")
        return None
    return normalize_url(text)
