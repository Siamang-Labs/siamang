"""`siamang codegen` — write a questionnaire document as Python source."""

from __future__ import annotations

import sys
from pathlib import Path

from siamang.codegen import generate_questionnaire
from siamang.model import DocumentError, loads


def run(path: str, output: str | None = None, *, format: bool = True) -> int:
    try:
        document = loads(Path(path).read_text(encoding="utf-8"))
        code = generate_questionnaire(document, format=format)
    except (OSError, ValueError, DocumentError) as exc:
        print(f"codegen error: {exc}", file=sys.stderr)
        return 2
    if output is None or output == "-":
        sys.stdout.write(code)
    else:
        Path(output).write_text(code, encoding="utf-8")
        print(f"wrote {output}", file=sys.stderr)
    return 0
