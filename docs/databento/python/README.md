# Python client

Use Python for data inspection, reference-data joins, research orchestration, and column-oriented analysis. Databento exposes `Historical`, `Live`, and `Reference` clients. Create the appropriate client at the provider boundary and pass validated request configuration into it. Do not create clients inside every feature calculation.

The reviewed quickstart specifies Python 3.10+ for historical/live access but contains an older reference-specific Python requirement. Use the selected package release's actual metadata to determine compatibility. QuantHacks currently declares Python 3.11 and uses `uv`; preserve that environment unless a reviewed dependency change requires otherwise. [Official quickstart](https://databento.com/docs/quickstart).

## Dependencies and credentials

Add `databento` through the repository's shared dependency manager from the repository root and commit the root manifest and lockfile together. A command pattern is `uv add databento`; synchronize with `uv sync --locked` afterward. All hypotheses use the root Python 3.11 environment; do not create dependency files or environments inside hypothesis folders. Shared setup is preparation, while hypothesis-specific implementation still requires its completed registration commit. Record the resolved package version in run evidence. This guide does not prescribe an unverified latest version.

Provide `DATABENTO_API_KEY` through the process environment or the existing ignored local configuration. `db.Historical()`, `db.Live()`, and `db.Reference()` can read it. Do not print it or include it in manifests. If a constructor receives an explicit key, that value overrides the environment fallback. [Historical authentication](https://databento.com/docs/api-reference-historical/basics/authentication), [live constructor](https://databento.com/docs/api-reference-live/client/live), [reference constructor](https://databento.com/docs/api-reference-reference/client/reference).

## A bounded request pattern

The following is an original pattern for a configured, previously approved small request. Replace the configuration with dated, resolved inputs. Calling it can consume historical-data credits.

```python
from pathlib import Path
import databento as db

def retain_trades(request: dict, destination: Path) -> Path:
    """Persist one approved interval before downstream analysis reads it."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    db.Historical().timeseries.get_range(
        dataset=request["dataset"],
        schema="trades",
        symbols=request["symbols"],
        stype_in=request["stype_in"],
        start=request["start_utc"],
        end=request["end_utc"],
        path=destination,
    )
    return destination
```

`timeseries.get_range` returns a `DBNStore` and completes after the download. Its `path` option allows persistence without making a DataFrame the primary artifact. [Request contract](https://databento.com/docs/api-reference-historical/timeseries/timeseries-get-range).

## Records and DataFrames

Raw record iteration preserves DBN event structure. Use it for stateful order books and precise event handling. `DBNStore.to_df()` is convenient for research; make conversion choices explicit. It defaults to floating-point prices and timezone-aware timestamps, with an index of `ts_recv` when present, otherwise `ts_event`. `price_type="fixed"` retains integer price units. `count` returns batches through an iterator instead of one large DataFrame. Mixed-schema stores require a selected schema for tabular conversion. [DataFrame conversion](https://databento.com/docs/api-reference-historical/helpers/dbn-store-to-df).

Raw MBP records expose `record.levels[0].bid_px`; DataFrame/CSV columns use `bid_px_00`. Never apply the fixed-price scale again to a DataFrame already converted to decimal prices. [MBP-1 layout](https://databento.com/docs/schemas-and-data-formats/mbp-1).

Use the [live guide](../live/README.md) for callbacks, iteration, and asynchronous shutdown. Calling `start()` before iterating a Python `Live` client is an error; choose one consumption interface. Keep callbacks short and move expensive analysis to a separate bounded processing stage.
