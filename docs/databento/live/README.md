# Live subscriptions and replay

Treat a live session as a mixed record stream with a declared start, subscriptions, control messages, capture path, and recovery policy. Databento distributes market data; connecting this client does not place a trade. Keep this repository's rule against launching the starter's live order example.

## Python consumption modes

For callbacks: construct `db.Live`, subscribe, add callbacks/output streams, call `start()`, then wait with `block_for_close()` or the appropriate asynchronous close method. For synchronous or asynchronous iteration: iterate after subscribing and allow the iterator to manage starting. Calling `start()` first is incompatible with iterator consumption. A Python client instance starts once. [Start](https://databento.com/docs/api-reference-live/client/start), [iteration](https://databento.com/docs/api-reference-live/client/iter), [async iteration](https://databento.com/docs/api-reference-live/client/aiter).

An original callback pattern, for a separately approved entitled subscription, is:

```python
import databento as db

def capture_session(dataset, symbols, schema, output_path, seconds):
    """Capture a bounded session for later replay; analysis reads the saved file."""
    session = db.Live(slow_reader_behavior="warn")
    session.subscribe(dataset=dataset, symbols=symbols,
                      schema=schema, stype_in="raw_symbol")
    session.add_stream(output_path)
    session.start()
    session.block_for_close(timeout=seconds)
```

Check output-stream types and shutdown semantics against the pinned package. `block_for_close(timeout=...)` terminates on timeout and guarantees a closed session when it returns. Validate file completion before promoting it to the retained dataset. [Output stream](https://databento.com/docs/api-reference-live/client/add-stream), [close wait](https://databento.com/docs/api-reference-live/client/block-for-close).

## Subscription constraints

One session uses one dataset and can have multiple schemas/subscriptions. Python `subscribe` returns a subscription ID that can be matched with gateway acknowledgments. There is no unsubscribe method; closing the session ends subscriptions. Replay `start` must be supplied before starting and must be within the documented 24-hour window; `0` requests all available replay. `snapshot=True` is for MBO and conflicts with a replay start. [Subscribe](https://databento.com/docs/api-reference-live/client/subscribe).

Live replay normally filters on `ts_event`; BBO/CBBO replay uses `ts_recv`. This differs from historical request indexing. Preserve the actual clock when bridging historical and live segments. Detect the transition out of replay before treating records as current observations. [Replay mechanics](https://databento.com/docs/api-reference-live/basics/intraday-replay).

## Recovery and processing

Process `SymbolMappingMsg`, `SystemMsg`, and `ErrorMsg` explicitly. Check subscription acknowledgment and errors rather than assuming that a successfully opened socket means every symbol is active. Store local arrival time, lag, last processed position, and capture completeness.

Natural refresh suits a current stateless quote view. Replay suits uninterrupted event history. MBO snapshots suit rebuilding current book state. Replay can repeat the last timestamp; preserve its record count per schema/instrument, as the official recovery procedure requires, rather than deduplicating every identical timestamp. See [recovery](https://databento.com/docs/api-reference-live/basics/recovering-after-a-disconnection).

Set slow-reader behavior deliberately. At review time `skip` is the default for compatible quote/depth schemas and can discard records while catching up. `warn` retains the stream but can accumulate lag; retention exhaustion can become fatal. A skipped stream cannot supply complete event history. [Slow reader behavior](https://databento.com/docs/api-reference-live/basics/slow-reader-behavior).

C++ uses blocking/threaded clients, typed record dispatch, and different shutdown interfaces. Use [the C++ guide](../cpp/README.md) and its selected overloads. Do not copy Python lifecycle methods into C++ code.
