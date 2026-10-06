# Choose the schema that supports the question

Discover supported schemas through metadata before requesting a dataset. The same schema name can describe differently normalized source feeds. Schema fields, dataset-specific exceptions, and SDK representation all form the data contract. The catalog includes a field-name inventory for each schema page and links to the full type descriptions.

## Market data families

| Schema | Suitable question | Boundary |
| --- | --- | --- |
| `mbo` | Order lifecycle, book reconstruction, queue research | Inspect native MBO versus `F_MBP`/`F_TOB` normalization; no universal queue/fill guarantee |
| `mbp-10` | Ten-level depth and depth features | Aggregated levels; insufficient for individual-order queue position |
| `mbp-1` | Event-driven venue BBO and trade/book changes | Distinguish event action and one-sided/two-sided updates |
| `tbbo` | Trade-conditioned venue quotes | Quotes are sampled around trade events, not every quote update |
| `bbo-1s`, `bbo-1m` | Regularly sampled venue quotes | Coarser observations lose intervening updates |
| `cmbp-1`, `tcbbo`, `cbbo-1s`, `cbbo-1m` | Consolidated quote equivalents | Check contributing venue fields and dataset-specific meaning |
| `trades` | Executed volume, trade flow, custom bars | Unspecified aggressor and corrections require a policy |
| `ohlcv-1s`, `-1m`, `-1h`, `-1d` | Bar-based research | Start-labelled bars; no print when there was no trade |
| `definition` | Instrument metadata as a time series | Updates and strategy-leg records require dated state |
| `statistics` | Official OI, settlement, cleared volume and other statistics | Session reference time differs from availability |
| `status`, `imbalance` | Trading state or auction observations | Venue status/enums are essential to interpretation |

[Schema overview](https://databento.com/docs/schemas-and-data-formats), [event/trade/time sampling comparison](https://databento.com/docs/faqs/difference-between-mbp-and-tbbo).

## Price-level layouts

Python DataFrame/CSV depth columns are flattened (`bid_px_00`, `ask_sz_00`). Python records and C++ structs have arrays of level structures. Consolidated messages may use publisher-attribution fields instead of order counts. Choose the actual record type before accessing members; similar schema names do not guarantee identical layouts. [MBP-1/CMBP-1](https://databento.com/docs/schemas-and-data-formats/mbp-1), [MBP-10](https://databento.com/docs/schemas-and-data-formats/mbp-10).

## Bars and statistics

OHLCV `ts_event` marks the interval start. Expose a bar only after its interval ends and the required delivery delay passes. Daily bars follow UTC dates and can differ from exchange-session bars and official settlements. Resample with explicit session boundaries and a documented empty-interval policy. [OHLCV contract](https://databento.com/docs/schemas-and-data-formats/ohlcv), [resampling example](https://databento.com/docs/examples/basics-historical/ohlcv-resampling).

Statistics carry `stat_type`, `ts_ref`, `update_action`, and flags. Important types include settlement `3`, cleared volume `6`, and open interest `9`. Retain updates/deletions and preliminary/final distinctions. Join observations by represented session while restricting versions by availability. A missing or inapplicable numeric field can use the integer maximum sentinel. [Statistics contract](https://databento.com/docs/schemas-and-data-formats/statistics), [publishing-time analysis](https://databento.com/docs/examples/futures/statistics-schedule).

Definitions include units, tick increments, expiration, class, and version-specific strategy legs. Never infer a cash multiplier from a generic field without considering the instrument's quoted units. Derive tick value/notional using the official worked approach and audit it for the product. [Definition fields](https://databento.com/docs/schemas-and-data-formats/instrument-definitions), [notional example](https://databento.com/docs/examples/instrument-definitions/contract-notional).
