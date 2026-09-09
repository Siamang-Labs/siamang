"""Turn a questionnaire Python module into a document (``siamang model import``)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from siamang.cli.loader import load_survey_module
from siamang.model.document import DocumentError, to_document


@dataclass(frozen=True, slots=True)
class ImportResult:
    document: dict[str, Any]
    warnings: list[str] = field(default_factory=list)


def import_module(path: str | Path, attribute: str = "survey") -> ImportResult:
    """Execute ``path`` and convert its ``survey`` (and ``options``) into a document.

    The module is imported the way ``siamang validate`` imports it, so it must
    be trusted code. Shape changes that keep the compiled survey identical are
    returned as ``warnings``; anything the format cannot hold raises
    :class:`DocumentError`.
    """

    module = load_survey_module(path)
    if not hasattr(module, attribute):
        raise DocumentError(
            f"File {Path(path).resolve()} does not define `{attribute}`. "
            "Either set `survey = sg.Questionnaire(...)` or pass --attribute NAME."
        )
    survey = getattr(module, attribute)
    options = getattr(module, "options", None)
    if options is not None and not isinstance(options, dict):
        raise DocumentError(f"`options` in {path} must be a dict, got {type(options).__name__}.")
    warnings: list[str] = []
    document = to_document(survey, options, on_warning=warnings.append)
    return ImportResult(document=document, warnings=warnings)
