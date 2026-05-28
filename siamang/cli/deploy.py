"""`siamang deploy` — deploy a survey to the configured backend+frontend."""

from __future__ import annotations

from typing import Any

from siamang.cli.loader import load_survey
from siamang.config import current, load


def run(
    path: str,
    attribute: str = "survey",
    backend: str | None = None,
    frontend: str | None = None,
    profile: str | None = None,
    config_path: str | None = None,
) -> int:
    cfg = current()
    if config_path is not None:
        cfg = load(config_path)
    if profile is not None:
        cfg = cfg.with_profile(profile)

    backend_name = backend or cfg.default_backend()
    frontend_name = frontend or cfg.default_frontend()

    backend_kwargs: dict[str, Any] = {}
    frontend_kwargs: dict[str, Any] = {}
    if backend_name != "local":
        try:
            backend_kwargs = cfg.backend(backend_name)
        except Exception:
            backend_kwargs = {}
    if frontend_name != "local":
        try:
            frontend_kwargs = cfg.frontend(frontend_name)
        except Exception:
            frontend_kwargs = {}

    survey = load_survey(path, attribute=attribute)
    result = survey.deploy(
        backend=backend_name,
        frontend=frontend_name,
        backend_kwargs=backend_kwargs,
        frontend_kwargs=frontend_kwargs,
    )
    print(f"Deployed: {result.url}")
    print(f"  survey_id: {result.survey_id}")
    print(f"  backend:   {result.backend}")
    print(f"  frontend:  {result.frontend}")
    if result.dashboard:
        print(f"  dashboard: {result.dashboard}")
    return 0
