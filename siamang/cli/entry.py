"""argparse-based dispatcher for the `siamang` CLI."""

from __future__ import annotations

import argparse
from collections.abc import Sequence


def _add_validate(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("validate", help="Validate a questionnaire file.")
    parser.add_argument("path", help="Path to a Python file exposing `survey`.")
    parser.add_argument(
        "--attribute", default="survey", help="Object name to import (default: survey)."
    )
    parser.add_argument(
        "--strict", action="store_true", help="Treat strict lint errors as failures."
    )


def _add_preview(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("preview", help="Serve the questionnaire locally.")
    parser.add_argument("path")
    parser.add_argument("--attribute", default="survey")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--open", action="store_true", dest="open_browser")
    parser.add_argument("--db", default="survey.db")


def _add_deploy(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("deploy", help="Deploy the questionnaire.")
    parser.add_argument("path")
    parser.add_argument("--attribute", default="survey")
    parser.add_argument("--backend")
    parser.add_argument("--frontend")
    parser.add_argument("--profile")
    parser.add_argument("--config")


def _add_init(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("init", help="Create or update ~/.siamang.toml.")
    parser.add_argument("--path", default="~/.siamang.toml")
    parser.add_argument("--non-interactive", action="store_true")


def _add_model(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "model", help="Convert between questionnaire Python files and JSON documents."
    )
    sub = parser.add_subparsers(dest="model_command", required=True)
    importer = sub.add_parser("import", help="Write the questionnaire of a Python file as JSON.")
    importer.add_argument("path", help="Path to a Python file exposing `survey` (and `options`).")
    importer.add_argument("--attribute", default="survey")
    importer.add_argument("-o", "--output", help="Output file (default: stdout).")
    checker = sub.add_parser("check", help="Validate a JSON questionnaire document.")
    checker.add_argument("path", help="Path to a questionnaire.json document.")
    checker.add_argument("--strict", action="store_true", help="Treat strict lint errors as failures.")


def _add_codegen(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "codegen", help="Generate questionnaire.py from a JSON questionnaire document."
    )
    parser.add_argument("path", help="Path to a questionnaire.json document.")
    parser.add_argument("-o", "--output", help="Output file (default: stdout).")
    parser.add_argument(
        "--no-format", action="store_true", help="Skip the ruff format pass over the output."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="siamang", description="siamang command-line interface")
    sub = parser.add_subparsers(dest="command", required=True)
    _add_validate(sub)
    _add_preview(sub)
    _add_deploy(sub)
    _add_init(sub)
    _add_model(sub)
    _add_codegen(sub)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command = args.command

    if command == "validate":
        from siamang.cli.validate import run as run_validate

        return run_validate(args.path, attribute=args.attribute, strict=args.strict)
    if command == "preview":
        from siamang.cli.preview import run as run_preview

        return run_preview(
            args.path,
            attribute=args.attribute,
            port=args.port,
            open_browser=args.open_browser,
            db_path=args.db,
        )
    if command == "deploy":
        from siamang.cli.deploy import run as run_deploy

        return run_deploy(
            args.path,
            attribute=args.attribute,
            backend=args.backend,
            frontend=args.frontend,
            profile=args.profile,
            config_path=args.config,
        )
    if command == "init":
        from siamang.cli.init import run as run_init

        return run_init(path=args.path, non_interactive=args.non_interactive)
    if command == "model":
        from siamang.cli.model import run_check, run_import

        if args.model_command == "import":
            return run_import(args.path, attribute=args.attribute, output=args.output)
        return run_check(args.path, strict=args.strict)
    if command == "codegen":
        from siamang.cli.codegen import run as run_codegen

        return run_codegen(args.path, output=args.output, format=not args.no_format)

    parser.error(f"Unknown command: {command}")
    return 2
