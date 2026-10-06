# H10 — Feature redundancy

**Stage:** exploratory implementation, unregistered; first HiPerGator development run completed. See the [research log and returned evidence](Research%20Log.md). Created October 3, 2026, from the nine-idea discussion in chat `private project chat`. This folder now owns `analysis.py`; the original proposals below remain broader than the first implemented methods.

The question is which inputs describe substantially overlapping information, and which groups contribute something different. This is a supporting discovery study for the other folders. It can help reduce a large endpoint catalog to meaningful information families; a distinct feature cluster is not itself a prediction or trading edge.

## Features and coverage

Start with field-level feature definitions, units, clocks and lineage. Several endpoints may expose the same underlying observation, and one endpoint may support several different features. Shared routes, alternative aggregations and snapshots must not be counted as independent information sources merely because their names differ.

Comparable dates and missingness matter. Two fields may correlate only because their coverage starts/stops together, because issuer scales differ, or because both have been filled with stale values. Separate time-series and cross-sectional comparisons, record usable pair counts and avoid pooling incompatible units without an explicit transformation.

## Proposed calculations

1. Inventory each feature's source, formula, cadence, availability clock, missingness, variation and relationship to other derived inputs.
2. Calculate Pearson/Spearman matrices on appropriate cohorts with pairwise sample counts. Examine whether relationships remain after sensible training-fitted normalization or removal of common structure.
3. Build hierarchical information clusters and propose interpretable representatives. Thresholds and representative selection remain recorded discovery choices.
4. Use principal components or another justified low-dimensional representation to describe common variation. Explained variance measures input structure, not predictive value; fit transformations inside training data if they feed H08.
5. Compare whole groups and substitutes through H08 by adding/removing or replacing them in otherwise comparable prediction models. Correlated proxies can mask the importance of an individually removed feature.
6. Revisit clusters across chronological development periods and delayed availability. Check that a representative retains the usable history and clock of the proposed group.

## Expected evidence and interpretation

The future output would be a feature-lineage inventory, correlation/coverage heatmap, cluster map, representative table and group-level incremental prediction comparisons. No clusters or dimensionality estimates exist yet.

Stable groups can simplify later exploration and keep the search count honest. A representative may be selected for clearer meaning, earlier availability or better coverage rather than the highest selected score. Low pairwise correlation does not prove conditional novelty; a high correlation does not prove two inputs are interchangeable for every target.

H10 should report redundancy alongside candidate rankings. It should not receive an invented return forecast or a final supported-signal verdict merely to make its output resemble the other folders.

## HiPerGator and open choices

Large matrix calculations, repeated clustering and family-level prediction comparisons can use parallel batches or suitable numerical libraries. The expensive useful step is checking whether group differences affect later prediction, not simply drawing the largest possible heatmap.

Feature families, compatible cohort, transforms, similarity measure, clustering/representative rule, dimensionality, validation target and computational representation remain open. Follow the [shared discovery boundaries](../README.md#shared-discovery-boundaries).

## Reading route

- [Correlated features and permutation-importance limitations](https://scikit-learn.org/stable/auto_examples/inspection/plot_permutation_importance_multicollinear.html).
- [H08: prediction](../H08%20-%20Incremental%20Prediction/README.md) and [H11: uncertainty](../H11%20-%20Robustness%20and%20Uncertainty/README.md).
- [Signal-reading requirements](../../docs/signal-reading/README.md), especially S03 and S06–S08; this is a conceptual route only.

## Current implementation and execution

[analysis.py](analysis.py) implements this folder's first calculations. [The shared run guide](../../docs/discovery/README.md) identifies exactly what is implemented, open extensions, data/timing assumptions and the three-stage task graph. Author code and download history on the PC, then transfer the completed package to Blue and execute actual studies through scheduled HiPerGator jobs. [Research Log.md](Research%20Log.md) preserves preparation and subsequent runs; the shared experiment ledger records attempted comparisons after results are returned.

From the project root in a scheduled allocation, run `python "Hypotheses/H10 - Feature Redundancy/analysis.py" --run <frozen-run-directory>`. The coordinated runner is the preferred way to run all nine; H11 requires the core attempt receipts. No strategy registration, backtest or confirmed signal is asserted.


[Cross-variable follow-up](../../docs/discovery/cross-variable-options.md) specifies the October 3 extensions, actual preparation/access evidence and remaining inference/options limits. Read it before using the new configuration; the original v3 run retains its frozen code and outputs.
