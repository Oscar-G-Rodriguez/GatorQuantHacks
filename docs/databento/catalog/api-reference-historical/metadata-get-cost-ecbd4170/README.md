# Historical.metadata.get_cost

Estimate USD cost before a download. The documented time-granularity approximation can overestimate short/non-aligned intervals; actual bytes determine billing.

Official route: [Databento documentation](https://databento.com/docs/api-reference-historical/metadata/metadata-get-cost).

Review state: `retrieved`.

## Python parameter inventory

Required: `dataset`, `start`.
Optional: `end`, `symbols`, `schema`, `stype_in`, `limit`.

Read the source for types, defaults, return values, and incompatible combinations.

C++ view: `Historical::MetadataGetCost`. Open the official source with the C++ language selector for exact overloads; Python parameter names above are not a C++ signature.

Implementation route: [task guide](../../../historical/README.md). Return to [catalog](../../README.md).
