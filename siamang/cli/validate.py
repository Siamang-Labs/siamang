"""`siamang validate` — run questionnaire validation and lint."""

from __future__ import annotations

from siamang.cli.loader import load_survey


def run(path: str, attribute: str = "survey", strict: bool = False) -> int:
    survey = load_survey(path, attribute=attribute)
    try:
        survey.validate(strict=strict)
    except ValueError as exc:
        print(f"validation error: {exc}")
        return 2

    warnings = survey.lint()
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
