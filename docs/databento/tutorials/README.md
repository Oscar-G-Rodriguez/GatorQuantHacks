# Worked examples and how to adapt them

The official tutorials show provider workflows and analytical mechanisms. Start from a registered experiment's data requirements, then borrow only the relevant mechanics. Sample dates, symbols, portfolio weights, models, and trading parameters are illustrative. The catalog provides a card for every discovered example and marks unfinished upstream articles.

## Find the relevant family

| Need | Official examples | Check when adapting |
| --- | --- | --- |
| Request/export/large downloads | Historical basics: requesting, programmatic batch, encodings | Explicit universe/bounds, cost, persisted job ID, complete files |
| Bars/indicators/valuation | Custom OHLCV, resampling, VWAP/RSI, EOD, benchmarks, candles | Interval convention, missing bars, completed information, units |
| Combine schemas | Join definitions with trades, options with underlying | Dated instrument identity, backward availability, stale inputs |
| Live capture/control messages | Stream to file, dispatch, mapping, snapshots, latency | Mixed record types, shutdown, gap recovery, local clock |
| Equities | Closing prices, auctions, synthetic NBBO, premarket movers, spreads | Venue coverage, quote rules, session and corporate-action policy |
| Futures | Definitions, product option chains, OI/settlement, publishing times, hours | Instrument classes, quoted units, revised statistics and actual release time |
| Options | Chains, 0DTE, IV, spreads, NBBO sampling, venue volume | Correct underlying, expiry/session, quote age, exercise/model assumptions |
| Order books | Events, resting state, full book, microprice, queue position | Matching algorithm, actual source granularity, event boundary, initialization |
| Reference enrichment | Adjustments, listings/delistings, shares/market cap | Latest versus historical state, effective versus known-at date |
| Analytical/trading examples | Markouts, latency, cointegration, ML, stock screener | Research registration, chronological validation, costs, executable fills |

[Examples index](https://databento.com/docs/examples).

## Reuse a mechanism, then verify the change

For resampling, declare bins, labels, session breaks, and when each output becomes usable. For a markout, distinguish a retrospective target from a signal known before execution. For IV, choose the appropriate model and inputs and record how invalid/illiquid quotes are rejected. For ML, split chronologically before fitting transformations and keep overlapping target horizons out of adjacent training/validation windows as registered.

A statistical tutorial is not a complete trading-system specification. Add actual costs, latency, position/risk rules, selection history, and execution feasibility before interpreting its outputs as an experiment result. Keep tutorial attribution and record what the implementation changes.

Some tutorials have Python code even when the surrounding docs support C++. The C++ view of a language picker is not proof that every analytical example has a native translation. Port the verified mechanism through the typed C++ APIs, then compare outputs with a retained fixture.

Upstream pages about messaging-rate volatility, portfolio optimization, and several corporate-action examples were marked as being written. The catalog preserves that limitation instead of inventing steps. Use finished API/schema documentation to implement independently when the registered experiment needs those features.
