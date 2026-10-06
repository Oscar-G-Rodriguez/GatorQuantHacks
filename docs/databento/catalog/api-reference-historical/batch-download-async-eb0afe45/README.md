# Historical.batch.download_async

Download an existing job asynchronously with bounded concurrency. Retain interrupted/completed states and validate final files before use.

Official route: [Databento documentation](https://databento.com/docs/api-reference-historical/batch/batch-download-async).

Review state: `retrieved`.

## Python parameter inventory

Required: `job_id`.
Optional: `output_dir`, `filename_to_download`, `keep_zip`.

Read the source for types, defaults, return values, and incompatible combinations.

Implementation route: [task guide](../../../historical/README.md). Return to [catalog](../../README.md).
