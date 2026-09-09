"""JSON Schema validation and versioning of questionnaire documents."""

from __future__ import annotations

import json
from functools import cache
from importlib import resources
from typing import Any

from siamang.model.document import SCHEMA_VERSION, DocumentError

_SUPPORTED_VERSIONS = (SCHEMA_VERSION,)


@cache
def load_schema(version: str = SCHEMA_VERSION) -> dict[str, Any]:
    """The JSON Schema (draft 2020-12) for documents of ``version``."""

    if version not in _SUPPORTED_VERSIONS:
        raise DocumentError(f"No schema for document version {version!r}.")
    path = resources.files("siamang.schemas").joinpath(f"questionnaire-{version}.json")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_document(document: Any) -> None:
    """Check ``document`` against the JSON Schema of its ``schema_version``.

    Raises :class:`DocumentError` naming the first offending location, e.g.
    ``pages/2/items/0/points: 1 is less than the minimum of 2``. Structural
    rules the schema cannot express (a question naming an unknown variable,
    duplicate ids) are checked by :func:`siamang.model.from_document` and
    ``Questionnaire.validate()``.
    """

    try:
        import jsonschema
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise DocumentError("jsonschema is required to validate documents.") from exc

    if not isinstance(document, dict):
        raise DocumentError(f"Document must be an object, got {type(document).__name__}.")
    version = document.get("schema_version")
    if version not in _SUPPORTED_VERSIONS:
        raise DocumentError(
            f"Unsupported schema_version {version!r}; this engine reads "
            + ", ".join(_SUPPORTED_VERSIONS)
            + "."
        )
    validator = jsonschema.Draft202012Validator(load_schema(version))
    errors = sorted(validator.iter_errors(document), key=lambda error: list(error.absolute_path))
    if not errors:
        return
    error = jsonschema.exceptions.best_match(errors)
    location = "/".join(str(part) for part in error.absolute_path) or "document"
    raise DocumentError(f"{location}: {error.message}")


def migrate(document: dict[str, Any]) -> dict[str, Any]:
    """Bring a document written by an older engine up to :data:`SCHEMA_VERSION`.

    There is a single version so far; the function exists so callers can
    already route every document they load through it.
    """

    version = document.get("schema_version")
    if version == SCHEMA_VERSION:
        return document
    raise DocumentError(f"Cannot migrate a document of schema_version {version!r}.")
