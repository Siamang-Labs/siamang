"""`siamang validate` — run questionnaire validation and lint."""

from __future__ import annotations

from siamang.cli.loader import load_survey_module
from siamang.core.quota import validate_options


def run(path: str, attribute: str = "survey", strict: bool = False) -> int:
    module = load_survey_module(path)
    if not hasattr(module, attribute):
        raise AttributeError(
            f"File {path} does not define `{attribute}`. "
            "Either set `survey = sg.Questionnaire(...)` or pass --attribute NAME."
        )
    survey = getattr(module, attribute)
    # A questionnaire module may also export a module-level `options` dict
    # (language, completion_text, quota=[Quota(...)], …). Quotas live there
    # rather than on the questionnaire, so nothing else ever checks them.
    options = getattr(module, "options", None)
    try:
        survey.validate(strict=strict)
        validate_options(survey, options)
    except ValueError as exc:
        print(f"validation error: {exc}")
        return 2

    warnings = survey.lint(level="strict" if strict else "basic")
    if not warnings:
        print("OK — no warnings.")
        return 0

    exit_code = 0
    for w in warnings:
        severity = getattr(w, "severity", "warning")
        code = getattr(w, "code", "")
        message = getattr(w, "message", str(w))
        location = getattr(w, "location", "") or ""
        prefix = f"[{severity}]" + (f" [{code}]" if code else "")
        suffix = f" ({location})" if location else ""
        print(f"{prefix} {message}{suffix}")
        if severity == "error":
            exit_code = 1
    return exit_code
