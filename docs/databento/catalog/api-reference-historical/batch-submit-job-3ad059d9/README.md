# Historical.batch.submit_job

Create one persistent batch request, then save its ID and poll/download that job. Symbol splitting cannot combine with ALL_SYMBOLS or a record limit.

Official route: [Databento documentation](https://databento.com/docs/api-reference-historical/batch/batch-submit-job).

Review state: `retrieved`.

## Python parameter inventory

Required: `dataset`, `symbols`, `schema`, `start`.
Optional: `end`, `encoding`, `compression`, `pretty_px`, `pretty_ts`, `map_symbols`, `split_symbols`, `split_duration`, `split_size`, `delivery`, `stype_in`, `stype_out`, `limit`.

Read the source for types, defaults, return values, and incompatible combinations.

C++ view: `Historical::BatchSubmitJob`. Open the official source with the C++ language selector for exact overloads; Python parameter names above are not a C++ signature.

Implementation route: [task guide](../../../historical/README.md). Return to [catalog](../../README.md).
