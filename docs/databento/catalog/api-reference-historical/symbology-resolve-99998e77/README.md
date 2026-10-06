# Historical.symbology.resolve

Resolve dated input symbols into output symbols. Preserve each mapping interval and inspect partial/unresolved lists; never assume a timeless instrument-ID map.

Official route: [Databento documentation](https://databento.com/docs/api-reference-historical/symbology/symbology-resolve).

Review state: `retrieved`.

## Python parameter inventory

Required: `dataset`, `symbols`, `stype_in`, `stype_out`, `start_date`.
Optional: `end_date`.

Read the source for types, defaults, return values, and incompatible combinations.

C++ view: `Historical::SymbologyResolve`. Open the official source with the C++ language selector for exact overloads; Python parameter names above are not a C++ signature.

Implementation route: [task guide](../../../historical/README.md). Return to [catalog](../../README.md).
