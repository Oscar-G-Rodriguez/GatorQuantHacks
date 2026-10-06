# Historical retrieval

Historical data is obtained through metadata, symbology, time-series, and batch methods. Use metadata and resolution to construct a precise request, then retain the result for repeated research. The HTTP service uses RPC-style methods under `https://hist.databento.com/v0/`; official clients supply the language-specific wrappers. [Historical API](https://databento.com/docs/api-reference-historical).

## Prepare a request

1. Use `metadata.list_datasets()` and `metadata.list_schemas(dataset=...)` to discover valid inputs.
2. Use `metadata.get_dataset_range(dataset=...)` for account-visible whole-dataset and per-schema bounds. A schema can have less history than its dataset.
3. Use `metadata.get_dataset_condition(...)` for date-level quality. Preserve `available`, `degraded`, `pending`, and `missing` distinctions and modification dates.
4. Resolve symbols for the requested dates and review `partial` and `not_found` results.
5. Query `metadata.get_cost(...)`, `get_billable_size(...)`, or `get_record_count(...)` with the intended filters. Record the estimate and budget before downloading.

These metadata methods are described individually in the catalog. Estimates are not the billed result: the cost endpoint warns about non-10-minute intervals and definition intervals that are not full UTC days. [Cost estimate](https://databento.com/docs/api-reference-historical/metadata/metadata-get-cost).

## Time-series requests

`timeseries.get_range(dataset, start, end, symbols, schema, stype_in, stype_out, limit, path)` is the principal Python request interface. Specify `schema`, both bounds, and symbols explicitly. At review time it accepts up to 2,000 explicit symbols; `None` or `ALL_SYMBOLS` expands to the dataset universe. The default schema is `trades`. The default symbology pair is raw input and numeric instrument output. [Exact contract](https://databento.com/docs/api-reference-historical/timeseries/timeseries-get-range).

The historical request clock is `ts_recv` for schemas that contain it and `ts_event` otherwise. Start is inclusive and end is exclusive. A market event with an earlier `ts_event` can legitimately fall inside a receive-time query. Do not silently discard it or claim the query filtered exchange-event time.

`get_range_async` supplies asynchronous retrieval; concurrency still needs a bounded queue, rate control, separate output paths, and a memory budget. Persist a request manifest and distinguish a complete response from an interruption or a record-limited sample.

## Batch downloads

Prefer batch jobs for large reusable requests. Submit once, retain its job ID, poll for completion, list files, then download those files. Job states include `received`, `queued`, `processing`, `done`, and `expired`. A failed download should resume the known job instead of submitting another paid request. [Submit](https://databento.com/docs/api-reference-historical/batch/batch-submit-job), [job listing](https://databento.com/docs/api-reference-historical/batch/batch-list-jobs), [files](https://databento.com/docs/api-reference-historical/batch/batch-list-files), [download](https://databento.com/docs/api-reference-historical/batch/batch-download).

DBN plus Zstandard is a useful retention format. CSV/JSON batch options include price and timestamp formatting and symbol mapping. `split_symbols` cannot be combined with `ALL_SYMBOLS` or a record limit. `split_duration` and `split_size` partition output files; they do not change your research's event timeline. Keep support files and their symbology alongside the data.

Historical streaming repeats can incur repeated charges. The reviewed billing page describes batch files as downloadable again for 30 days without another charge for the same job. Confirm current account terms and expiration before relying on that window. [Metered pricing](https://databento.com/docs/api-reference-historical/basics/metered-pricing).

## Validate before use

Compare returned instruments, schemas, time bounds, rows, and file identity with the request. Preserve unresolved symbols and degraded dates. Verify that a small integration sample and the full dataset pass different acceptance criteria. HTTP 206 denotes partial symbol resolution; a successful transport response alone does not establish completeness. See [operations](../operations/README.md) for error handling.
