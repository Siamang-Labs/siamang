"""Load a Questionnaire from a Python file (used by all CLI commands)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


def load_survey_module(path: str | Path) -> ModuleType:
    """Import ``path`` and return the module itself.

    Callers that need more than one attribute (a questionnaire *and* its
    ``options`` dict, say) should use this and read them off the result:
    calling :func:`load_survey` twice executes the user's module twice.
    """

    module_path = Path(path).resolve()
    if not module_path.is_file():
        raise FileNotFoundError(f"No such file: {module_path}")

    spec = importlib.util.spec_from_file_location(f"_siamang_user_{module_path.stem}", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot import {module_path}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_survey(path: str | Path, attribute: str = "survey") -> Any:
    """Import ``path`` and return the named questionnaire object.

    The CLI looks for an attribute named ``survey`` by default. Override via
    ``--attribute``.
    """

    module = load_survey_module(path)
    if not hasattr(module, attribute):
        raise AttributeError(
            f"File {Path(path).resolve()} does not define `{attribute}`. "
            "Either set `survey = sg.Questionnaire(...)` or pass --attribute NAME."
        )
    return getattr(module, attribute)
