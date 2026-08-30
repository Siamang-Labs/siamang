"""CLI configuration loading: ~/.siamang.toml is honoured by `siamang deploy`
and environment credential overlays apply even without a config file."""

from __future__ import annotations

import textwrap

import pytest

from siamang.config import loader


@pytest.fixture()
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(loader, "_CURRENT", None)
    return tmp_path


def _write_config(home, body: str) -> None:
    path = home / ".siamang.toml"
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    path.chmod(0o600)


def test_load_default_reads_home_config(home):
    _write_config(
        home,
        """
        [defaults]
        backend = "local"
        frontend = "local"

        [profiles.production]
        backend = "supabase"
        """,
    )
    cfg = loader.load()
    assert cfg.default_backend() == "local"
    assert cfg.with_profile("production").default_backend() == "supabase"


def test_env_overlay_applies_without_config_file(home, monkeypatch):
    monkeypatch.setenv("SIAMANG_VERCEL_TOKEN", "tok-123")
    cfg = loader.load()
    assert cfg.frontend("vercel")["token"] == "tok-123"


def test_cli_deploy_uses_home_config_profile(home, tmp_path, monkeypatch):
    _write_config(
        home,
        """
        [defaults]
        backend = "local"
        frontend = "local"

        [profiles.production]
        backend = "local"
        """,
    )
    survey_file = tmp_path / "my_survey.py"
    survey_file.write_text(
        textwrap.dedent(
            """
            import siamang as sg

            age = sg.Variable("age", scale="ratio", label="Age")
            survey = sg.Questionnaire(
                title="T",
                pages=[sg.Page(name="p", items=[sg.NumericInput("Age?", var=age)])],
            )
            """
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    from siamang.cli import deploy as cli_deploy

    # The documented flow: the profile defined in ~/.siamang.toml resolves
    # without --config (0.5.0 raised ConfigError: profile not defined).
    assert cli_deploy.run(str(survey_file), profile="production") == 0
