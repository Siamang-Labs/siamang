"""siamang.model — the questionnaire as a JSON document.

    >>> from siamang.model import to_document, from_document
    >>> doc = to_document(survey, options)      # Questionnaire (+ options) -> dict
    >>> loaded = from_document(doc)              # dict -> LoadedSurvey
    >>> loaded.survey.validate()
    >>> loaded.survey.compile(**loaded.options)

The document format is what a graphical survey builder stores; the Python
file is what researchers get. See :mod:`siamang.model.document` for the
layout and :func:`validate_document` for the JSON Schema.
"""

from siamang.model.document import (
    OPTION_KEYS,
    QUESTION_TYPES,
    SCHEMA_VERSION,
    DocumentError,
    LoadedSurvey,
    dumps,
    from_document,
    loads,
    to_document,
)
from siamang.model.import_qsf import QsfImportResult, Skipped, import_qsf, import_qsf_file
from siamang.model.importer import ImportResult, import_module
from siamang.model.parse_python import Dropped, StaticImportResult, parse_file, parse_source
from siamang.model.schema import load_schema, migrate, validate_document
from siamang.model.scripts import LIBRARY_SCRIPT_TYPES

__all__ = [
    "DocumentError",
    "ImportResult",
    "LIBRARY_SCRIPT_TYPES",
    "LoadedSurvey",
    "OPTION_KEYS",
    "QUESTION_TYPES",
    "SCHEMA_VERSION",
    "dumps",
    "from_document",
    "import_module",
    "import_qsf",
    "import_qsf_file",
    "QsfImportResult",
    "Skipped",
    "parse_file",
    "parse_source",
    "StaticImportResult",
    "Dropped",
    "load_schema",
    "loads",
    "migrate",
    "to_document",
    "validate_document",
]
