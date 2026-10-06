# H03 — Lag and horizon maps

**Stage:** exploratory implementation, unregistered; first HiPerGator development run completed. See the [research log and returned evidence](Research%20Log.md). Created October 3, 2026, from the nine-idea discussion in chat `private project chat`. This folder now owns `analysis.py`; the original proposals below remain broader than the first implemented methods.

The question is whether a measured input precedes a subsequent response, and how that relationship changes with observation delay and outcome horizon. The purpose is to turn a broad association into a specific candidate about what becomes informative, when and for how long. The direction, instrument and mechanism remain open.

## Candidate interpretation and data

A delayed response might be consistent with gradual incorporation of information; a reversal might suggest a temporary adjustment. These are interpretations to investigate, not established explanations. Shared market movements, overlapping outcomes and misdated availability could produce similar maps.

Possible inputs include past price/volume measurements, disclosure indicators, reported short measurements or historically observable curve features. Select a provider/field and compatible target rather than treating endpoints as interchangeable features. Keep an input's observation, release and vendor-availability times separate. Repeated monthly macro values across daily rows do not create independent daily observations.

## Proposed calculations

1. Define an input available by a decision time and a subsequent outcome: return, realized volatility, downside occurrence or repricing. State units, horizon start and end, and the session calendar.
2. Build a bounded grid of feature ages and outcome horizons. Every inspected grid cell is part of the discovery search. Use the sponsor's required horizons where applicable rather than selecting only an attractive horizon.
3. Estimate Pearson correlation for linear association and Spearman correlation for ordered association. For cross-sectional claims, calculate within eligible dates; for temporal claims, calculate within a defensible time series. Report the aggregation and weighting.
4. Compare against the target's own past behavior and relevant market/sector information through H05. Repeat with later input availability to identify responses that occur too early to motivate a usable signal.
5. Examine chronological development periods and issuer/date contributions, then obtain dependence-aware uncertainty through H11. Horizon overlap and changes in the eligible cohort remain visible.

## Expected evidence and interpretation

The broader output proposal includes a lag-by-horizon heatmap, signed estimates with intervals, cohort counts, period breakdowns and a delay-sensitivity table. The first completed run supplies the implemented association table, with supported correlation uncertainty in H11; additional visualizations and period breakdowns remain proposals. The research log links the actual evidence.

A consistent region of response across neighboring horizons and later development periods could motivate a bounded hypothesis. A single isolated cell, a relationship occurring before input availability, or concentration in one issuer would count against that interpretation. Wide intervals can leave the question unresolved; a small estimate alone does not prove independence.

## HiPerGator and open choices

Independent feature/target/period calculations and resampling batches can run in parallel over the same cached panel. The arithmetic screen may be cheap; repeated uncertainty and sensitivity calculations are the more useful compute workload.

The first engineering configuration is documented in the [discovery guide](../../docs/discovery/README.md). Broader provider/data choices, historically verified availability, a practical effect criterion and a selected economic mechanism remain open. Follow the [shared discovery boundaries](../README.md#shared-discovery-boundaries) before extending measurement. A later candidate needs a specific economic claim before advancing to a strategy/backtest.

## Reading route

- [H05: controlled relationships](../H05%20-%20Controlled%20Relationships/README.md) and [H11: uncertainty](../H11%20-%20Robustness%20and%20Uncertainty/README.md).
- [Signal-reading requirements](../../docs/signal-reading/README.md), especially S03–S04, S08 and S10; this mapping is conceptual, not executed coverage.
- [SciPy Spearman definition and p-value guidance](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.spearmanr.html) and [chronological validation](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html).

## Current implementation and execution

[analysis.py](analysis.py) implements this folder's first calculations. [The shared run guide](../../docs/discovery/README.md) identifies exactly what is implemented, open extensions, data/timing assumptions and the three-stage task graph. Author code and download history on the PC, then transfer the completed package to Blue and execute actual studies through scheduled HiPerGator jobs. [Research Log.md](Research%20Log.md) preserves preparation and subsequent runs; the shared experiment ledger records attempted comparisons after results are returned.

From the project root in a scheduled allocation, run `python "Hypotheses/H03 - Lag and Horizon Maps/analysis.py" --run <frozen-run-directory>`. The coordinated runner is the preferred way to run all nine; H11 requires the core attempt receipts. No strategy registration, backtest or confirmed signal is asserted.
