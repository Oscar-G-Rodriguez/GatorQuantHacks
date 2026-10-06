# C++ client

Use C++ when event processing, order-book state, or a measured throughput requirement warrants a native component. Keep request configuration and research assumptions shared with Python. A different implementation language must not change the experiment's clock, symbol resolution, price scale, or missing-data policy.

The official [C++ quickstart](https://databento.com/docs/quickstart?historical=cpp&live=cpp) uses CMake 3.24+, OpenSSL 3.0+, libcrypto, and Zstandard. The [SDK repository](https://github.com/databento/databento-cpp) specifies C++17 as the minimum standard. The DBN C library is supplied as a prebuilt component where supported; other platforms may require Rust to build it. Check the chosen release's platform support. Pin a release or commit instead of copying the quickstart's moving `main` reference into a reproducible research build.

## Build integration

Link the imported target `databento::databento`. Record the client ref, compiler, build configuration, DBN library version, and dependency versions. Keep build products out of Git. Configure and build from the component directory using the project's CMake presets or the usual `cmake -S . -B build` and `cmake --build build` pattern. On Windows, account for the chosen generator and configuration when locating an executable.

## Historical and live interfaces

Historical construction uses `databento::Historical::Builder().SetKeyFromEnv().Build()`. Method families become names such as `MetadataGetCost`, `MetadataGetDatasetRange`, `SymbologyResolve`, `TimeseriesGetRange`, and `BatchSubmitJob`. Their positional overloads differ from Python keyword arguments. Open the [C++ historical reference](https://databento.com/docs/api-reference-historical?historical=cpp) for the selected overload rather than translating Python syntax mechanically.

Live access offers `LiveBlocking` and `LiveThreaded`. Builders configure the key and dataset and end in `BuildBlocking()` or `BuildThreaded()`. A subscription specifies symbols, `Schema`, and `SType`; the dataset belongs to the client. `SubscribeWithSnapshot` is the MBO snapshot path. [C++ live reference](https://databento.com/docs/api-reference-live?live=cpp).

For threaded consumption, return `databento::KeepGoing::Continue` from a handler to continue reading. Dispatch with typed checks such as `record.GetIf<databento::TradeMsg>()`, and process symbol mapping, error, and system messages alongside market records. A market-only cast is unsafe on a live stream. Synchronize any state read by another thread, and make ownership of queued data explicit.

## Local replay pattern

This original example shows the processing shape for an already retained, permitted file. Verify its API against the pinned headers before using it; it was not compiled in this documentation task.

```cpp
#include <databento/dbn.hpp>
#include <databento/dbn_store.hpp>
#include <iostream>

int main(int argc, char** argv) {
  if (argc != 2) return 2;
  databento::DbnStore input{argv[1]};
  while (const auto* record = input.NextRecord()) {
    if (const auto* trade = record->GetIf<databento::TradeMsg>()) {
      std::cout << trade->hd.instrument_id << '\n';
    }
  }
}
```

The reviewed [store header](https://github.com/databento/databento-cpp/blob/main/include/databento/dbn_store.hpp) defines the path constructor and `NextRecord`; `DbnFileStore` is a compatibility alias in the current headers. Use the pinned headers for record lifetime. Consume borrowed record views immediately or copy the required data before retaining them across reads.

Depth fields use `levels[i].bid_px`, `levels[i].ask_px`, and corresponding size/count members. Raw prices remain signed fixed-point integers. Keep 64-bit IDs and nanosecond timestamps in integer types. Compare Python and C++ outputs on the same small retained fixture before scaling up.

The reviewed Reference API lists Python, Rust, and HTTP. For a C++ research component, load a documented reference-data artifact prepared by Python or implement the official HTTP contract explicitly; do not invent a `databento::Reference` class.
