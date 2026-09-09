"""siamang.codegen — questionnaire documents to Python source.

    >>> from siamang.codegen import generate_questionnaire
    >>> code = generate_questionnaire(document)      # dict -> str

The output is the file a researcher would have written: ``survey = …`` and,
when needed, ``options = …``. Running :func:`siamang.model.to_document` over
the executed module returns the original document, and generating twice
returns the same bytes.
"""

from siamang.codegen.format import FormatterUnavailable, format_source
from siamang.codegen.questionnaire import CODEGEN_VERSION, DEFAULT_HEADER, generate_questionnaire

__all__ = [
    "CODEGEN_VERSION",
    "DEFAULT_HEADER",
    "FormatterUnavailable",
    "format_source",
    "generate_questionnaire",
]
