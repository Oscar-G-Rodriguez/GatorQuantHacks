# Historical.batch.download

Download an existing completed job into a deliberate directory. Resume/retry the known job instead of silently submitting another paid request.

Official route: [Databento documentation](https://databento.com/docs/api-reference-historical/batch/batch-download).

Review state: `retrieved`.

## Python parameter inventory

Required: `job_id`.
Optional: `output_dir`, `filename_to_download`, `keep_zip`.

Read the source for types, defaults, return values, and incompatible combinations.

C++ view: `Historical::BatchDownload`. Open the official source with the C++ language selector for exact overloads; Python parameter names above are not a C++ signature.

Implementation route: [task guide](../../../historical/README.md). Return to [catalog](../../README.md).
