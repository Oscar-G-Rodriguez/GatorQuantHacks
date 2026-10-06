# Databento Binary Encoding

Apply these conventions consistently at the provider adapter boundary. Preserve original values and metadata, check the selected dataset’s exceptions, and compare Python/C++ interpretation on the same retained fixture.

Official route: [Databento documentation](https://databento.com/docs/standards-and-conventions/databento-binary-encoding).

Review state: `retrieved`.

## Field inventory

`version`, `length`, `dataset`, `schema`, `start`, `end`, `limit`, `stype_in`, `stype_out`, `ts_out`, `symbol_cstr_len`, `schema_definition_length`, `schema_definition`, `symbols_length`, `symbols`, `partial_length`, `partial`, `not_found_length`, `not_found`, `mappings_length`, `mappings`, `raw_symbol`, `interval_length`, `intervals`, `start_date`, `end_date`, `symbol`, `rtype`, `publisher_id`, `instrument_id`, `ts_event`.

Implementation route: [task guide](../../../conventions/README.md). Return to [catalog](../../README.md).
