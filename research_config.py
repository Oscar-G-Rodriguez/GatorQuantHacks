"""Select a hypothesis's local settings without duplicating the starter."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from pathlib import Path

from dotenv import dotenv_values, load_dotenv


def configure_backtest(project_root: Path, argv: Sequence[str] | None = None) -> None:
    """Load shared credentials and optionally select one hypothesis experiment.

    Root .env supplies shared credentials. A selected hypothesis's .env supplies
    its research settings, and its strategy and report remain inside that folder.
    Without --hypothesis, retain the upstream examples/backtest/.env interface.
    """
    parser = argparse.ArgumentParser(description="Run the shared Webull backtest.")
    parser.add_argument("--hypothesis", metavar="FOLDER", help="Folder name under Hypotheses, e.g. 'Hypothesis 1'.")
    args = parser.parse_args(argv)
    project_root = project_root.resolve()

    if args.hypothesis is None:
        load_dotenv(project_root / ".env")
        load_dotenv(project_root / "examples/backtest/.env")
        return

    hypotheses_root = (project_root / "Hypotheses").resolve()
    folder = (hypotheses_root / args.hypothesis).resolve()
    if folder.parent != hypotheses_root or not folder.is_dir():
        parser.error("--hypothesis must name an existing direct folder under Hypotheses")
    config = folder / ".env"
    if not config.is_file() or not config.resolve().is_relative_to(folder):
        parser.error(f"missing local settings: copy {hypotheses_root / '.env.example'} to {config} after registration")

    load_dotenv(project_root / ".env")
    load_dotenv(config, override=True)
    settings = dotenv_values(config)
    module_name = (settings.get("WEBULL_STRATEGY") or "").strip()
    if not module_name.isidentifier():
        parser.error("set WEBULL_STRATEGY to a strategy filename without .py in the hypothesis .env")
    strategy = (folder / "strategies" / f"{module_name}.py").resolve()
    if not strategy.is_file() or not strategy.is_relative_to(folder / "strategies"):
        parser.error(f"missing hypothesis strategy: {strategy}; complete and commit the plan before implementing it")

    output = (settings.get("WEBULL_VISUALIZE_OUTPUT") or "results/backtest_report.html").strip()
    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = folder / output_path
    output_path = output_path.resolve()
    if not output_path.is_relative_to(folder) or output_path.suffix.lower() != ".html":
        parser.error("WEBULL_VISUALIZE_OUTPUT must name an HTML report inside the selected hypothesis folder")

    # Explicit paths avoid loading another hypothesis's same-named strategy or
    # overwriting another experiment's report through the upstream defaults.
    os.environ["WEBULL_STRATEGY"] = str(strategy)
    os.environ["WEBULL_VISUALIZE_OUTPUT"] = str(output_path)
