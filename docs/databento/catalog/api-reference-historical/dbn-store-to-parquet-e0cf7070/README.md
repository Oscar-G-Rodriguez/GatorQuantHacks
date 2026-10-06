# DBNStore.to_parquet

Create a derived research artifact with explicit schema, fixed/float price choice, timestamps and overwrite mode. Preserve raw DBN identity.

Official route: [Databento documentation](https://databento.com/docs/api-reference-historical/helpers/dbn-store-to-parquet).

Review state: `retrieved`.

## Python parameter inventory

Required: `path`.
Optional: `price_type`, `pretty_ts`, `map_symbols`, `schema`, `mode`, `kwargs`.

Read the source for types, defaults, return values, and incompatible combinations.

Implementation route: [task guide](../../../historical/README.md). Return to [catalog](../../README.md).
