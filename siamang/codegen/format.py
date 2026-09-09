"""Run ``ruff format`` over generated source, when ruff is installed."""

from __future__ import annotations

import shutil
import subprocess
import sys

from siamang.codegen.emit import LINE_LENGTH


class FormatterUnavailable(RuntimeError):
    """``ruff`` is not installed in this environment."""


def ruff_command() -> list[str] | None:
    """How to invoke ruff here: the ``ruff`` binary, or ``python -m ruff``."""

    binary = shutil.which("ruff")
    if binary:
        return [binary]
    try:
        import ruff  # noqa: F401  (the PyPI package only ships the binary)
    except ImportError:
        return None
    return [sys.executable, "-m", "ruff"]


def format_source(code: str, *, filename: str = "questionnaire.py") -> str:
    """Format ``code`` with ruff's formatter (line length 100, double quotes).

    The generator already lays code out the way ruff does, so this is a
    normalization pass that makes the output byte-for-byte reproducible
    across generator versions. Raises :class:`FormatterUnavailable` when
    ruff cannot be found; callers that can live with unformatted output
    catch it.
    """

    command = ruff_command()
    if command is None:
        raise FormatterUnavailable("ruff is not installed; pip install 'siamang[codegen]'.")
    result = subprocess.run(
        [
            *command,
            "format",
            "--isolated",
            "--line-length",
            str(LINE_LENGTH),
            "--stdin-filename",
            filename,
            "-",
        ],
        input=code,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ruff format failed: {result.stderr.strip()}")
    return result.stdout
