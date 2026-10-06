# Historical.timeseries.get_range

Download explicit symbols/schema over an inclusive-start, exclusive-end interval. Historical filtering uses receipt time where present, otherwise event time. Persist before analysis.

Official route: [Databento documentation](https://databento.com/docs/api-reference-historical/timeseries/timeseries-get-range).

Review state: `retrieved`.

## Python parameter inventory

Required: `dataset`, `start`.
Optional: `end`, `symbols`, `schema`, `stype_in`, `stype_out`, `limit`, `path`.

Read the source for types, defaults, return values, and incompatible combinations.

C++ view: `Historical::TimeseriesGetRange`. Open the official source with the C++ language selector for exact overloads; Python parameter names above are not a C++ signature.

Implementation route: [task guide](../../../historical/README.md). Return to [catalog](../../README.md).
