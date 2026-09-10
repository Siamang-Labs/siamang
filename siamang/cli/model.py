"""`siamang model` — convert and check questionnaire documents."""

from __future__ import annotations

import sys
from pathlib import Path

from siamang.core.quota import validate_options
from siamang.model import (
    DocumentError,
    dumps,
    from_document,
    import_lss_file,
    import_module,
    import_qsf_file,
    loads,
    parse_file,
    validate_document,
)


def run_import(
    path: str, attribute: str = "survey", output: str | None = None, static: bool = False
) -> int:
    """``siamang model import questionnaire.py [-o questionnaire.json] [--static]``.

    ``--static`` reads the file without executing it (``parse_python``):
    the declarative subset is imported, anything else is listed as skipped.
    A ``.qsf`` file (Qualtrics export) or an ``.lss`` file (LimeSurvey
    structure export) is converted; what the format cannot hold is listed as
    skipped."""

    try:
        if path.lower().endswith((".qsf", ".lss")):
            converted = (
                import_lss_file(path) if path.lower().endswith(".lss") else import_qsf_file(path)
            )
            for skipped in converted.skipped:
                print(f"[skipped] {skipped}", file=sys.stderr)
            result = converted
        elif static:
            static_result = parse_file(path, attribute=attribute)
            for dropped in static_result.dropped:
                print(f"[skipped] {dropped}", file=sys.stderr)
            result = static_result
        else:
            result = import_module(path, attribute=attribute)
    except DocumentError as exc:
        print(f"import error: {exc}", file=sys.stderr)
        return 2
    for warning in result.warnings:
        print(f"[warning] {warning}", file=sys.stderr)
    text = dumps(result.document)
    if output is None or output == "-":
        sys.stdout.write(text)
    else:
        Path(output).write_text(text, encoding="utf-8")
        print(f"wrote {output}", file=sys.stderr)
    return 0


def run_check(path: str, strict: bool = False) -> int:
    """``siamang model check questionnaire.json`` — schema, structure, validate, lint."""

    try:
        document = loads(Path(path).read_text(encoding="utf-8"))
        validate_document(document)
        loaded = from_document(document)
        loaded.survey.validate(strict=strict)
        validate_options(loaded.survey, loaded.options)
    except (OSError, ValueError) as exc:
        print(f"validation error: {exc}")
        return 2

    warnings = loaded.survey.lint(level="strict" if strict else "basic")
    if not warnings:
        print("OK — no warnings.")
        return 0
    exit_code = 0
    for warning in warnings:
        prefix = f"[{warning.severity}]" + (f" [{warning.code}]" if warning.code else "")
        suffix = f" ({warning.location})" if warning.location else ""
        print(f"{prefix} {warning.message}{suffix}")
        if warning.severity == "error":
            exit_code = 1
    return exit_code
