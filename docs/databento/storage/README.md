# Retention, replay, and tabular conversion

Retain a permitted raw capture once, then derive the research representation from it. DBN carries metadata and typed event records and works across Python and C++. Parquet is useful for repeated column-oriented research, while CSV/JSON help inspection and interoperability. Preserve raw event order and identity when converting.

## DBN compatibility

Let the official decoder read the metadata version, record length, schema, optional send timestamp, and symbol mapping. Do not write a parser that casts bytes to one current struct and assumes every retained file uses it. The reviewed specification covers versions 1, 2, and 3; version 3 expands statistics quantity and instrument/leg definitions. Text exports can change along with binary schemas. Record the decoder's upgrade policy and original file version. [DBN specification](https://databento.com/docs/standards-and-conventions/databento-binary-encoding).

Use `.dbn.zst` for compressed DBN when the selected client supports it. Zstandard is compression, not another record schema. Inspect the actual file/header and let the appropriate decoder handle it. [Zstandard guide](https://databento.com/docs/standards-and-conventions/working-with-zstandard).

## Python and C++ routes

Python loads a retained file with `db.DBNStore.from_file(path)`, then iterates, replays, or converts it. `to_file` preserves DBN; `to_csv`, `to_json`, `to_parquet`, `to_ndarray`, and `to_df` expose different downstream representations. Consult each method's exact conversion and overwrite options. C++ uses DBN store/file-store APIs and typed records. [Python file read](https://databento.com/docs/api-reference-historical/helpers/dbn-store-from-file), [DBN write](https://databento.com/docs/api-reference-historical/helpers/dbn-store-to-file), [Parquet](https://databento.com/docs/api-reference-historical/helpers/dbn-store-to-parquet).

Select a schema when converting a mixed live file to a table. Preserve full 64-bit values and explicitly choose fixed or decimal prices. A stringified JSON integer must not be parsed through floating point. DataFrame conversion can add mapped symbols, but it cannot supply mappings absent from the source metadata. Chunked iteration is preferable to materializing a high-volume book feed in one DataFrame.

## Suggested artifact contract

Store licensed bytes outside the public repo. A permitted committed manifest should describe:

- dataset, schemas, symbols, stypes, request bounds, query clock, and provider request/job identity;
- SDK/decoder versions, DBN version/upgrade policy, retrieval time, file hashes, sizes, and completion state;
- dated definitions and symbology, quality warnings, record limits, partial/unresolved symbols, and first/last observed timestamps;
- conversion version, source ordinal, price scale, session calendar, filtering, and missing-data policy;
- cost estimate versus actual reported cost, and the account's applicable access/redistribution constraints.

A request-specific file destination plus hash prevents silent replacement. Write partial data to a separate temporary destination and promote it only after validation. Exact timestamp overlap does not justify content deduplication: two legitimate events can have the same timestamp and values. Partition by a documented identity/date policy and reconcile boundaries without losing events.
