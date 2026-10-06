# Historical.timeseries.get_range_async

Use asynchronous historical retrieval with bounded concurrency and distinct artifact paths. Its clock, symbol, cost and completeness rules match the synchronous request.

Official route: [Databento documentation](https://databento.com/docs/api-reference-historical/timeseries/timeseries-get-range-async).

Review state: `retrieved`.

## Python parameter inventory

Required: `dataset`, `start`.
Optional: `end`, `symbols`, `schema`, `stype_in`, `stype_out`, `limit`, `path`.

Read the source for types, defaults, return values, and incompatible combinations.

Implementation route: [task guide](../../../historical/README.md). Return to [catalog](../../README.md).
