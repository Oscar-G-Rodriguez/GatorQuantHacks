# Units, timestamps, and record interpretation

The provider exposes a shared normalized format, but venue-specific semantics remain relevant. Put conversions in one boundary module and document the resulting internal units. Keep the original record and fields available for audit. [Normalization rationale](https://databento.com/docs/standards-and-conventions/normalization).

## Prices and identifiers

Raw DBN prices are signed integers scaled by `1e-9`. `INT64_MAX` represents an undefined price. A negative price can be valid for a future or spread; treating every non-positive value as missing corrupts some markets. Use integer or decimal arithmetic when exact tick calculations matter. Converted tabular prices may already be floating-point decimal values.

Instrument identity needs dataset/publisher context and a dated mapping. Numeric `instrument_id` is guaranteed only within a day; some publishers reuse or remap it. Keep order IDs and nanosecond times at full integer precision. JSON may serialize 64-bit fields as strings. Test flag bits with `&`, because several can coexist. `F_LAST=128`, `F_TOB=64`, `F_SNAPSHOT=32`, `F_MBP=16`, `F_BAD_TS_RECV=8`, and `F_MAYBE_BAD_BOOK=4` affect interpretation. [Common fields](https://databento.com/docs/standards-and-conventions/common-fields-enums-types).

## Four clocks

| Field | Meaning | Implementation use |
| --- | --- | --- |
| `ts_event` | Timestamp provided by the source for the event | Interpret according to the dataset; source clocks can be non-monotonic |
| `ts_recv` | Databento capture receipt | Historical index where present; useful availability proxy with stated downstream latency |
| `ts_in_delta` | Signed delta from Databento receipt to publisher send | Publisher send time is `ts_recv - ts_in_delta`; preserve clamping/clock limitations |
| `ts_out` | Optional gateway send timestamp in live data | Separate provider processing/transit from your own arrival time |

Record your application's receipt time separately. It is absent from historical records and cannot be reconstructed merely by renaming `ts_recv`. Nanosecond resolution describes the representation; it does not guarantee that the exchange clock is accurate to a nanosecond. The [timestamping guide](https://databento.com/docs/architecture/timestamping-guide) explains clock accuracy, precision, hardware capture, and dataset exceptions.

Explicitly store UTC and convert to exchange-local time only for session rules and presentation. Dates without time represent UTC midnight. Use explicit bounds to avoid reduced-precision end inference. Check each endpoint: dataset-condition date bounds and some Reference defaults differ from the general time-series convention.

## Actions and sides

`side` depends on `action`: a trade refers to the aggressor; a fill refers to a resting order; add/modify/cancel refer to the resting book side. `N` means unspecified and must not be guessed from the label alone. `T` and `F` observations do not themselves mutate resting orders under normalized MBO semantics; book mutation comes from the appropriate add/modify/cancel/clear records. Use the [order-state tutorial](https://databento.com/docs/examples/order-book/order-tracking) and selected venue rules.

Assign a source ordinal before transformations. Preserve delivered order for equal timestamps within an instrument. Re-sorting on exchange timestamps can change event sequence and produce an impossible intermediate book. Cross-instrument analysis additionally needs a declared ordering and staleness rule; equal nanoseconds do not imply atomic arrival across feeds.
