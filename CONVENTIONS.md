# Repository conventions

This repository contains independent Python research experiments. The root README and AGENTS.md define research integrity and judging requirements. Repository Markdown is portable project documentation; managed vault source notes and project navigation live outside this Git checkout.

## Runtime and dependencies

- Runtime: Python 3.11, selected by the root `.python-version` (the manifest permits Python >=3.11).
- Runtime/dependency selector: `uv`.
- Dependency manifest and lock: root `pyproject.toml` and `uv.lock`, maintained once.
- Generated environment: root `.venv`, ignored by Git and shared across experiments.
- Synchronization: `uv sync --locked` from the repository root.
- Hypothesis execution: each registered idea implements its own `Hypotheses/<folder>/backtest.py`, adapted from the Webull entry point. Document explicit development and final-OOS modes and run from the root; the expected interface is `uv run python 'Hypotheses/Hypothesis 1/backtest.py' --phase development` and `--phase final-oos`. These local runners do not exist until the plans are registered and implemented.
- Shared credentials: root `.env`, copied from root `.env.example` and excluded from Git.
- Experiment settings: `Hypotheses/<folder>/.env`, copied from the single `Hypotheses/.env.example` template and excluded from Git. Record non-secret settings in committed research evidence.
- Offline setup checks: `uv run python -m unittest discover -s tests -v` from the root.

The starter's libraries are Backtrader, Webull's SDK, python-dotenv, Plotly, and pandas. Preserve the lockfile for reproducibility. A later dependency change must update the manifest and lock together and document why it is needed.

## Structure and changes

Exploratory statistical code may precede a formed or registered hypothesis under [the discovery scope](AGENTS.md#statistical-discovery-before-a-hypothesis). Keep its inputs, development boundaries and run history explicit. The post-registration ownership rules below describe the strategy/backtest implementation and its full evidence package.

Keep common infrastructure once at the repository root: `webull_bt/`, reference `examples/`, `docs/`, and the runtime/dependency files. After the registration commit, create the hypothesis's own `backtest.py`, strategies, and analysis code within its folder. That local implementation owns IS/OOS enforcement, execution/cost assumptions, matched baselines, ablation/factor/uncertainty checks, and readable run-specific output. The root backtest/configuration adapter remains a reference and optional example; it is not the final hypothesis experiment. Follow [BACKTEST_EVIDENCE_CONTRACT.md](docs/BACKTEST_EVIDENCE_CONTRACT.md). Record amendments and runs in `Research Log.md`, and every tested variant in the shared experiment ledger.

Maintain one root `.gitignore`, `.python-version`, `pyproject.toml`, `uv.lock`, and `.venv`. New hypothesis folders contain their plan, log, settings, own backtest/strategy/analysis code, and evidence; do not copy shared libraries or dependency files into them. Adapting the Webull entry point into each local backtest is intentional experiment ownership. The upstream templates under `examples/` serve the original example interface; root and `Hypotheses/` templates serve research setup.

## Verification

The nine exploratory implementations own `analysis.py` in H03–H11 and share `discovery/` utilities. Follow [the discovery guide](docs/discovery/README.md) for local historical downloads, the frozen task graph, Blue transfer, Slurm execution and verified return. Actual statistical runs use HiPerGator under Oscar's current request; local timing/identity unit checks are separate. Numerical discovery dependencies (NumPy, SciPy, scikit-learn and threadpoolctl) are declared and locked once at root.

Read [the required signal-reading methods](docs/signal-reading/README.md) before hypothesis implementation or review. Register S01–S12 choices before strategy/backtest coding, implement the registered diagnostics after the hypothesis commit, and record actual method/code/check/evidence coverage in each run. Select libraries only when the research methods require them; use the single root manifest/lockfile for any dependency change.

Preparation requires file/link checks, archive-entry comparison for moved upstream files, Git-ignore verification, and offline configuration/separation checks. `examples/backtest/main.py` is intentionally adapted for shared setup. English documentation cleanup is recorded in `docs/RESEARCH_SOURCES.md`; other retained starter files preserve upstream bytes. No dependency installation, API call, backtest, or live order is required to validate preparation.

After implementation, choose meaningful tests for information availability, signal/fill lag, chronological split and purge, cost accounting, order/position constraints, and reporting reproducibility. Verify actual behavior rather than mirroring code. Preserve the tested code revision, configuration, data identity, and failed runs. Do not claim execution success from a static review.

H12–H17 adds the root-only Databento client and exchange calendar; read docs/discovery/options-buffered-plan.md before acquisition or methods. New exploration plans were committed before this stage, as Oscar explicitly required. The calendar fixes actual session offsets/early-close quote cutoffs; a provider schema or successful client import does not prove paid historical-data entitlement. Scientific runs remain scheduled on HiPerGator.
