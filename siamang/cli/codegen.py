"""`siamang codegen` — write a questionnaire or flow document as Python source."""

from __future__ import annotations

import sys
from pathlib import Path

from siamang.codegen import generate_questionnaire
from siamang.model import DocumentError, loads


def run(
    path: str,
    output: str | None = None,
    *,
    questionnaire: str | None = None,
    format: bool = True,
) -> int:
    try:
        document = loads(Path(path).read_text(encoding="utf-8"))
        if "nodes" in document:
            from siamang.flow import generate_flow

            qdoc = loads(Path(questionnaire).read_text(encoding="utf-8")) if questionnaire else None
            code = generate_flow(document, qdoc, format=format)
        else:
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
