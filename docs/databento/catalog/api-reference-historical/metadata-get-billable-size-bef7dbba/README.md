# Historical.metadata.get_billable_size

Estimate uncompressed billable size for the intended request. Compressed storage size is a different quantity.

Official route: [Databento documentation](https://databento.com/docs/api-reference-historical/metadata/metadata-get-billable-size).

Review state: `retrieved`.

## Python parameter inventory

Required: `dataset`, `start`.
Optional: `end`, `symbols`, `schema`, `stype_in`, `limit`.

Read the source for types, defaults, return values, and incompatible combinations.

C++ view: `Historical::MetadataGetBillableSize`. Open the official source with the C++ language selector for exact overloads; Python parameter names above are not a C++ signature.

Implementation route: [task guide](../../../historical/README.md). Return to [catalog](../../README.md).
