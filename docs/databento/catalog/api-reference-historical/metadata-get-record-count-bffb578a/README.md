# Historical.metadata.get_record_count

Estimate the returned record count using the same schema, symbols and bounds as the planned download; validate the actual result separately.

Official route: [Databento documentation](https://databento.com/docs/api-reference-historical/metadata/metadata-get-record-count).

Review state: `retrieved`.

## Python parameter inventory

Required: `dataset`, `start`.
Optional: `end`, `symbols`, `schema`, `stype_in`, `limit`.

Read the source for types, defaults, return values, and incompatible combinations.

C++ view: `Historical::MetadataGetRecordCount`. Open the official source with the C++ language selector for exact overloads; Python parameter names above are not a C++ signature.

Implementation route: [task guide](../../../historical/README.md). Return to [catalog](../../README.md).
