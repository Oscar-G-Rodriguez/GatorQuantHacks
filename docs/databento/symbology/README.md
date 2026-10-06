# Instruments and symbology

A symbol is a query expression, not necessarily a permanent instrument identity. Resolve it for the experiment's actual dates, retain that mapping, and associate each returned record with the applicable mapping interval. Use definitions for contract characteristics and live `SymbolMappingMsg` records for changing subscriptions.

## Select the input type deliberately

| `stype_in` | Typical input | Meaning |
| --- | --- | --- |
| `raw_symbol` | A dated venue ticker/contract symbol | Original source symbol, including its venue naming convention |
| `instrument_id` | A numeric identifier | Requires publisher/dataset and date context |
| `parent` | `ZC.FUT`, `ES.OPT`, an equity options parent | Related instruments; can include spreads or combinations |
| `continuous` | `ZC.c.0`, `ZC.v.0`, `ZC.n.0` | Contract selected by a calendar, prior-day volume, or prior-day open-interest rule |

Continuous ranks are zero-based. Prices are those of the selected tradable contracts and are unadjusted across rolls. Parent support and continuous support vary by dataset. Valid input/output combinations are constrained; do not assume every listed `SType` works in both directions. Equities also differ between Nasdaq and CMS ticker conventions. [Symbology specification](https://databento.com/docs/standards-and-conventions/symbology).

## Historical resolution

Python `Historical.symbology.resolve` takes dataset, symbols, input/output types, inclusive start date, and exclusive end date. Each `result` entry contains intervals with `d0`, `d1`, and output symbol `s`. Inspect `partial`, `not_found`, `message`, and `status`, not just the existence of a result dictionary. Keep a dated join and avoid a global dictionary keyed only by instrument ID. [Resolution contract](https://databento.com/docs/api-reference-historical/symbology/symbology-resolve).

For `ALL_SYMBOLS`, time-series DBN metadata does not provide the usual symbol mappings. Obtain definitions or a supported explicit resolution request; do not promise a `symbol` column simply by enabling tabular mapping. Batch support files also have documented mapping limits. [Dataset symbols tutorial](https://databento.com/docs/examples/symbology/all-dataset-symbols).

## Live mapping

Process symbol mapping messages before emitting a human-readable symbol for a market record. Mappings arrive at session start and when the subscription's mapping changes. Python can maintain a mapping structure; C++ provides symbol-map helpers including `PitSymbolMap`. Preserve mapping intervals and raw subscription symbols. [Live mapping tutorial](https://databento.com/docs/examples/symbology/live-symbol-mapping).

## Futures and options

Filter definitions by `instrument_class` and the relevant underlying/asset metadata. A futures parent can include outright contracts and exchange-listed spreads. Do not assume a one-digit year suffix, infer strike from a string when definitions supply it, or assume all options for a futures product share one root. [Parent example](https://databento.com/docs/examples/symbology/parent-symbology), [futures options chains](https://databento.com/docs/examples/futures/futures-product-options).

For a futures spread, retain its listed instrument identity, leg ratios, sides, and effective definition. A synthetic two-leg portfolio needs its own execution and synchronization rules. A continuous price series crossing a roll must not turn the contract price jump into strategy P&L. Declare the roll rule, determine the actual instruments, and price the rollover with feasible costs and timestamps.
