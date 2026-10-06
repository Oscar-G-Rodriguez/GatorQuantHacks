# Hypothesis 2

This is an independent experiment skeleton, with internal hypothesis ID **H02**. The economic idea is undecided. Complete [Hypothesis.md](Hypothesis.md) and commit that substantive plan before writing hypothesis code or running a backtest. Record the actual registration hash afterward in [Research Log.md](Research%20Log.md). Read the [repository rules](../../README.md) and [shared workflow](../README.md).

## Shared setup

This folder uses the one starter at the repository root: `pyproject.toml`, `uv.lock`, `.python-version`, `.venv`, `webull_bt/`, `examples/`, and `docs/`. Keep this folder for its own plan, log, settings, strategy code, and evidence. See [starter provenance](../../docs/RESEARCH_SOURCES.md) and the [shared root ignore rules](../../.gitignore).

The root [English usage guide](../../docs/USAGE_EN.md) explains the kit. Root `examples/strategies/dual_ma.py` and `portfolio.py` are upstream examples. Root `examples/live/` is also supplied, but paper/live trading is unscored and is not part of setup validation.

The root `examples/backtest/backtest_report_lwc.html` is an upstream illustrative report, **not our results**. The starter does not set explicit trading costs or automatically lock the required holdout; implement and verify those controls after registration before making any result claim.

## Local setup after registration

Run `uv sync --locked` once at the repository root for the shared Python 3.11 environment. Keep shared credentials in root `.env`. After committing the plan, copy `Hypotheses/.env.example` to this folder's `.env` and fill the registered dates, market, parameters, and strategy name. Keep development dates strictly before the holdout and verify the bars returned. Local `.env` files, environments, licensed raw data, caches, and logs stay out of Git; record non-secret settings in the plan and run evidence.

After registration, create this folder's own `backtest.py` adapted from the root Webull example, with strategies under `strategies/` and local analysis code. It must own the registered IS/OOS split, lag/fills, cost accounting, relevant momentum/market/factor baselines, signal ablation, uncertainty, robustness, and readable conclusions. Follow [the backtest evidence contract](../../docs/BACKTEST_EVIDENCE_CONTRACT.md). The root example harness is reference material rather than this hypothesis's final validation.

Implement and document explicit development and final-OOS modes; the expected future commands from the root are `uv run python 'Hypotheses/Hypothesis 2/backtest.py' --phase development` and `--phase final-oos`. The local runner does not exist yet. Keep reports and evidence in `results/<run-id>/`, and preserve earlier attempts. API entitlement and market backtest behavior have not been runtime-verified by this preparation.

## Evidence

Use [the mandatory signal-reading README](../../docs/signal-reading/README.md) while writing and reviewing this hypothesis's code. Register S01–S12 choices first, including the appropriate prediction diagnostic and strength/horizon response. Implement them after registration and link their actual code, checks, and run evidence in `validation_checks.json`; include `signal_diagnostics.csv`. A missing diagnostic remains pending and prevents a supported verdict where required.

Keep all variants, failures, revisions, timing/cost checks, and OOS exposure in the research log and `../EXPERIMENTS.csv`. The readable summary must decide whether the proposed signal adds beyond the registered alternatives: supported incremental signal, explained by known exposure, rejected, or inconclusive. Require both IS-validation and untouched-OOS evidence for the final supported verdict. Freeze selection before final OOS; report separate net IS/OOS metrics, labeled strategy/baseline curves, attribution/ablation/robustness, risk, and capacity in the five-page note.
