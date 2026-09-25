"""One call for every file a flow's Export file step can write.

The format follows the extension, as it always has for the snapshot formats
(:data:`~siamang.io.snapshot.SNAPSHOT_FORMATS`: the data plus its
``<stem>.dictionary.json``), and two more:

``.R``
    the R bundle — ``<stem>.csv``, ``<stem>.dictionary.json`` and the
    ``<stem>.R`` script that reads them into a data frame with factors and
    ``NA`` for the missing codes (:class:`~siamang.io.r.RScriptWriter`);
``.json``
    the codebook alone, as the data dictionary
    (:class:`~siamang.io.dictionary.DictionaryWriter`) — for a reader who has
    the data already, or for a documentation appendix.

Every file lands beside the path given, so a path under a flow's ``outputs/``
keeps all of them there.
"""

from __future__ import annotations

from pathlib import Path

from siamang.data.survey_data import SurveyData
from siamang.io.dictionary import DictionaryWriter
from siamang.io.r import RScriptWriter
from siamang.io.snapshot import SNAPSHOT_FORMATS, write_snapshot

__all__ = ["EXPORT_FORMATS", "export_file"]

#: File suffixes :func:`export_file` writes.
EXPORT_FORMATS = (*SNAPSHOT_FORMATS, ".r", ".json")


def export_file(data: SurveyData, path: str | Path) -> Path:
    """Write ``data`` in the format ``path``'s extension names; return ``path``."""

    target = Path(path)
    suffix = target.suffix.lower()
    if suffix == ".r":
        return RScriptWriter().write(data, target)
    if suffix == ".json":
        if not data.variables:
            raise ValueError(
                "This data has no codebook, so there is no dictionary to write. Load it "
                "with its questionnaire or its dictionary, or export a data format instead."
            )
        return DictionaryWriter().write(data.variables, target)
    if suffix in SNAPSHOT_FORMATS:
        return write_snapshot(data, target)
    raise ValueError(
        f"Unsupported export format {suffix or '(no extension)'!r}; expected one of "
        + ", ".join(".R" if item == ".r" else item for item in EXPORT_FORMATS)
        + "."
    )
