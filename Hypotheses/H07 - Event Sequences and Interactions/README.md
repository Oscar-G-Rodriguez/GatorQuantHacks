# H07 — Event sequences and interactions

**Stage:** exploratory implementation, unregistered; first HiPerGator development run completed, with all six configured sequence comparisons inconclusive. See the [research log and returned evidence](Research%20Log.md). Created October 3, 2026, from the nine-idea discussion in chat `private project chat`. This folder now owns `analysis.py`; the original proposals below remain broader than the first implemented methods.

The question is whether event A followed by event B supplies information beyond A alone or B alone, and whether elapsed time or repetition changes that response. This preserves the interacting-disclosures idea without selecting a particular pair. A possible mechanism is that a later disclosure resolves or deepens uncertainty created by an earlier one; that explanation remains to be developed from evidence.

## What counts as a sequence

Define the issuer, ordered availability timestamps, eligible category definitions and whether both disclosures concern the same underlying development. Several tags on one filing are a co-occurrence, not automatically a sequence. Same-day records with unknown order cannot establish A-before-B. Symbol changes/share classes need issuer-level identity handling.

A recent-A flag must be computed from information available before B; do not label an observation using a future B and present that label as known earlier. Distinguish retrospective occurrence sequences from availability-safe sequences. Supporting excerpts can inform a documented event distinction, but later reading-based selection and label corrections remain part of discovery history.

## Proposed calculations

1. Inventory independent A-only, B-only, A-then-B, B-then-A and comparable ordinary observations. Count by issuer, date and development period before fitting a model. Verify sparse/missing mappings through the existing coverage route.
2. Propose a bounded elapsed-time grid and novelty/repetition definition. Retain every inspected pair, window and definition; a search over combinations is still a search.
3. Compare matched response distributions for the individual events and ordered combinations, using the same target/horizon and comparable cohorts.
4. Fit an interpretable interaction model where appropriate:

\[
Y=\alpha+\beta_A A_{\mathrm{recent}}+\beta_B B+\gamma(A_{\mathrm{recent}}B)+\theta^\top Z+\varepsilon.
\]

Here, \(B\) identifies the current event, \(A_{\mathrm{recent}}\) a prior eligible A, and \(Z\) the selected controls. The coefficient \(\gamma\) measures a departure from this model's additive relationship; it does not establish causation.

5. Compare additive and interaction predictions in later development periods through H08. Check reverse order, nearby elapsed times, issuer concentration and appropriate mechanism-irrelevant controls through H11.

## Expected evidence and interpretation

The future output would include a sequence-count matrix, elapsed-time response curves, group contrasts, interaction estimates with uncertainty, paired prediction changes and definition/mapping exclusions.

A sufficiently supported, repeatable interaction could motivate a specific ordered-event hypothesis. An effect explained by B alone, double-counting one development, invalid ordering or a single issuer would count against it. Missing combinations remain missing rather than zero-effect observations. More compute cannot supply absent sequences.

## HiPerGator and open choices

Pair/window comparisons, chronological fits and grouped resampling can run as independent batches. Begin with supported category pairs and controlled search breadth instead of assuming all combinations deserve equal computational effort.

Event pair, novelty definition, ordering clock, sequence window, universe, target, controls, development dates, uncertainty and practical criterion remain open. Follow the [shared discovery boundaries](../README.md#shared-discovery-boundaries).

## Reading route

- [H06: matched events](../H06%20-%20Matched%20Event%20Responses/README.md), [H08: prediction](../H08%20-%20Incremental%20Prediction/README.md) and [H11: uncertainty](../H11%20-%20Robustness%20and%20Uncertainty/README.md).
- [Massive track](../../../Massive%20Track/README.md), including timing, category and starter limitations; [coverage preparation](../../docs/massive/README.md).
- [Signal-reading requirements](../../docs/signal-reading/README.md), particularly S01, S04, S06 and S08–S09; this is proposed method coverage only.

## Current implementation and execution

[analysis.py](analysis.py) implements this folder's first calculations. [The shared run guide](../../docs/discovery/README.md) identifies exactly what is implemented, open extensions, data/timing assumptions and the three-stage task graph. Author code and download history on the PC, then transfer the completed package to Blue and execute actual studies through scheduled HiPerGator jobs. [Research Log.md](Research%20Log.md) preserves preparation and subsequent runs; the shared experiment ledger records attempted comparisons after results are returned.

From the project root in a scheduled allocation, run `python "Hypotheses/H07 - Event Sequences and Interactions/analysis.py" --run <frozen-run-directory>`. The coordinated runner is the preferred way to run all nine; H11 requires the core attempt receipts. No strategy registration, backtest or confirmed signal is asserted.


[Cross-variable follow-up](../../docs/discovery/cross-variable-options.md) specifies the October 3 extensions, actual preparation/access evidence and remaining inference/options limits. Read it before using the new configuration; the original v3 run retains its frozen code and outputs.
