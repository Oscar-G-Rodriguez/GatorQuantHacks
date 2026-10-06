"""Offline checks for shared setup and experiment separation; no market tests."""

from __future__ import annotations

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research_config import configure_backtest


class HypothesisConfigurationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        (self.root / "Hypotheses").mkdir()
        (self.root / ".env").write_text("WEBULL_APP_KEY=shared_fixture_key\nWEBULL_SYMBOLS=BASE\n", encoding="utf-8")
        environment = patch.dict(os.environ, {}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)

    def prepare(self, name: str, settings: str = "") -> Path:
        folder = self.root / "Hypotheses" / name
        (folder / "strategies").mkdir(parents=True)
        (folder / "strategies/strategy.py").write_text("# Fixture path only; never executed.\n", encoding="utf-8")
        (folder / ".env").write_text("WEBULL_STRATEGY=strategy\nWEBULL_SYMBOLS=LOCAL\n" + settings, encoding="utf-8")
        return folder

    def assert_rejected(self, args: list[str]) -> None:
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            configure_backtest(self.root, args)
        self.assertEqual(error.exception.code, 2)

    def test_shared_credentials_and_local_settings(self) -> None:
        folder = self.prepare("Hypothesis 1", "WEBULL_FROMDATE=2020-01-01T00:00:00Z\n")
        configure_backtest(self.root, ["--hypothesis", folder.name])
        self.assertEqual(os.environ["WEBULL_APP_KEY"], "shared_fixture_key")
        self.assertEqual(os.environ["WEBULL_SYMBOLS"], "LOCAL")
        self.assertEqual(os.environ["WEBULL_FROMDATE"], "2020-01-01T00:00:00Z")
        self.assertEqual(Path(os.environ["WEBULL_STRATEGY"]), folder / "strategies/strategy.py")
        self.assertEqual(Path(os.environ["WEBULL_VISUALIZE_OUTPUT"]), folder / "results/backtest_report.html")

    def test_identical_strategy_names_resolve_to_selected_folder(self) -> None:
        first = self.prepare("Hypothesis 1")
        second = self.prepare("Hypothesis 2")
        configure_backtest(self.root, ["--hypothesis", first.name])
        self.assertEqual(Path(os.environ["WEBULL_STRATEGY"]), first / "strategies/strategy.py")
        configure_backtest(self.root, ["--hypothesis", second.name])
        self.assertEqual(Path(os.environ["WEBULL_STRATEGY"]), second / "strategies/strategy.py")
        self.assertEqual(Path(os.environ["WEBULL_VISUALIZE_OUTPUT"]), second / "results/backtest_report.html")

    def test_missing_strategy_does_not_fall_back_to_example(self) -> None:
        folder = self.prepare("Hypothesis 1")
        (folder / "strategies/strategy.py").unlink()
        self.assert_rejected(["--hypothesis", folder.name])

    def test_missing_settings_are_rejected(self) -> None:
        folder = self.prepare("Hypothesis 1")
        (folder / ".env").unlink()
        self.assert_rejected(["--hypothesis", folder.name])

    def test_folder_outside_hypotheses_is_rejected(self) -> None:
        self.assert_rejected(["--hypothesis", ".."])

    def test_output_cannot_overwrite_another_hypothesis(self) -> None:
        folder = self.prepare("Hypothesis 1", "WEBULL_VISUALIZE_OUTPUT=../Hypothesis 2/results/report.html\n")
        self.assert_rejected(["--hypothesis", folder.name])

    def test_relative_custom_output_stays_with_selected_hypothesis(self) -> None:
        folder = self.prepare("Hypothesis 1", "WEBULL_VISUALIZE_OUTPUT=results/costs-doubled.html\n")
        configure_backtest(self.root, ["--hypothesis", folder.name])
        self.assertEqual(Path(os.environ["WEBULL_VISUALIZE_OUTPUT"]), folder / "results/costs-doubled.html")

    def test_original_example_settings_remain_supported(self) -> None:
        example = self.root / "examples/backtest"
        example.mkdir(parents=True)
        (example / ".env").write_text("WEBULL_STRATEGY=dual_ma\n", encoding="utf-8")
        configure_backtest(self.root, [])
        self.assertEqual(os.environ["WEBULL_APP_KEY"], "shared_fixture_key")
        self.assertEqual(os.environ["WEBULL_STRATEGY"], "dual_ma")


if __name__ == "__main__":
    unittest.main()
