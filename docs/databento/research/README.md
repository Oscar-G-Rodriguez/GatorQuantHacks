# Databento data contract for a QuantHacks experiment

The root repository rules require a completed economic hypothesis and experiment plan committed before strategy implementation or a backtest. Oscar's explicitly authorized statistical discovery may precede registration; preserve its dates, development boundary and search history as described in the [discovery guide](../../discovery/README.md). Databento documentation does not select the hypothesis, reserve the holdout, validate a signal, or prove sponsor access. Use this file to make either an authorized discovery acquisition or a registered plan auditable. The [Massive-track enrichment check](../../discovery/cross-variable-options.md) records free account metadata and nonzero download estimates without purchasing data.

## Declare inputs and availability

For each source, record dataset, schemas, dated instrument universe, symbology, request interval, fields/units, source clock, downstream availability delay, session calendar, and missing/revision rules. Resolve definitions as of the relevant time; a latest definition must not overwrite the history used by earlier decisions.

A useful normalized research row contains `dataset`, `publisher_id`, dated `instrument_id`, raw symbol, `schema`, source ordinal, the original provider timestamps, an explicit `available_at_utc`, raw/converted price units, quality flags, and source file identity. Add local receipt time for an actual live capture. These internal fields are a proposed adapter contract, not extra Databento fields.

## Common leakage traps

| Trap | Required handling |
| --- | --- |
| Bar timestamp is its start | Wait for interval completion and the registered delivery delay; fill at the next feasible execution time |
| Daily UTC bar is called a settlement | Use the actual settlement statistic or name the trade-bar close accurately |
| OI joined on session date | Restrict to statistics versions received by the decision, including preliminary/final/deletion behavior |
| Latest corporate-action/master record | Preserve the endpoint's historical revisions and actual record availability; event/effective date alone is insufficient |
| Continuous contract rollover | Identify the tradable contracts and price/cost the registered roll; exclude artificial return from a contract switch |
| Parent universe includes spreads | Filter dated instrument classes and retain spread-leg definitions where needed |
| Equal timestamps discarded | Preserve distinct events and source order; deduplicate only through a justified replay/identity policy |
| Cross-market legs joined to nearest observation | Use backward availability joins with explicit quote age; never match a future quote |
| Derived BBO treated as venue orders | Respect dataset granularity; zero/anonymized order/venue fields do not support queue claims |

These controls apply provider facts from the [OHLCV](https://databento.com/docs/schemas-and-data-formats/ohlcv), [statistics](https://databento.com/docs/schemas-and-data-formats/statistics), [symbology](https://databento.com/docs/standards-and-conventions/symbology), and [reference history](https://databento.com/docs/api-reference-reference/corporate-actions/corporate-actions-get-range) specifications to the repository's research requirements.

## Corn, curve, and spread experiments

If the registered hypothesis uses agricultural futures, define the predicted output and horizon first. Use quotes/trades for intraday observations, definitions for units/maturities, and statistics for official OI/settlement inputs. A quote stream can be live while its latest OI observation still describes a prior session.

Distinguish listed spreads from synthetic legs and direct liquidity from implied liquidity. Do not infer simultaneous two-leg execution from two independent closing marks. Convert ticks to cash P&L using verified product units. Match contract definition, execution price, position quantity, fees, and settlement/marking conventions consistently. [Notional example](https://databento.com/docs/examples/instrument-definitions/contract-notional), [CME normalization](https://databento.com/docs/venues-and-datasets/glbx-mdp3).

## Verification that matters

Before a result claim, use small permitted fixtures to test exact conversions, valid negative prices, sentinel handling, temporal symbol reuse, record ties, bar-close availability, revisions/deletions, replay overlap, and book clears. Compare both language implementations on the same records. Validate dataset completeness separately from signal/backtest behavior.

Keep the final holdout unexposed during development. Log every variant and failed attempt in the repository's research records. Costs, delays, capacity, risk limits, and feasible fills belong to the registered experiment and must be tested there. Successful decoding supplies input evidence; it does not demonstrate economic predictability or alpha.
