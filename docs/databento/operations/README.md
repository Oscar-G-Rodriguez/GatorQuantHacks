# Errors, limits, latency, and operating behavior

Classify a failure before deciding whether to retry. Preserve request identity, exception type/status, and a redacted message. An empty table, partial response, or broken connection has a different meaning from a successful complete request with no events.

## Historical and Reference HTTP failures

Historical Python exceptions distinguish `BentoClientError` and `BentoServerError`. Check authentication, permission/payment, invalid input, missing data, and rate-limit causes. HTTP 206 indicates partially resolved symbols. Retry transient failures with bounded attempts and backoff, respecting `Retry-After` for 429. Do not loop on invalid keys or insufficient entitlement, and do not silently turn such failures into empty data. [Historical errors](https://databento.com/docs/api-reference-historical/basics/errors), [Reference errors](https://databento.com/docs/api-reference-reference/basics/errors).

Rate limits vary by service and method. At review time the historical page describes 100 concurrent connections per IP, 100 time-series/symbology requests per second, 20 metadata/job-list requests per second, and 20 batch submissions per minute. These are dated reference values, not application concurrency targets. Sharing an IP on a compute cluster can aggregate traffic. Confirm the current limits and use substantially lower controlled concurrency. [Historical limits](https://databento.com/docs/api-reference-historical/basics/rate-limits), [Reference limits](https://databento.com/docs/api-reference-reference/basics/rate-limits).

## Live controls

Live errors/system messages carry codes in addition to text. Handle skipped records, retention exhaustion, subscription resolution, heartbeats, slow-reader warnings, and terminal errors. Record gaps and invalidate dependent state when appropriate. A reconnect is recovery work, not proof that the capture remained continuous. [Live errors](https://databento.com/docs/api-reference-live/basics/errors), [system messages](https://databento.com/docs/api-reference-live/basics/system-messages), [error detection](https://databento.com/docs/api-reference-live/basics/error-detection).

Connection limits and maintenance behavior are account/service-specific. Do not create a new session per symbol. Keep subscriptions within the documented dataset/session rules and preserve maintenance disruptions in capture evidence. [Connection limits](https://databento.com/docs/api-reference-live/basics/connection-limits), [maintenance](https://databento.com/docs/api-reference-live/basics/maintenance-schedule).

## Performance and compute placement

Measure the pipeline in stages: download, decompression/decoding, book update, feature computation, disk write, and model work. Keep callbacks small; batch downstream processing, bound queues, and inspect lag under message bursts. Faster model computation does not correct a skipped or stale source stream.

Provider capture accuracy, gateway processing latency, network transit, and application scheduling are separate quantities. HiPerGator provides research compute; its use does not establish colocated feed latency. Benchmark the actual environment and retained sample. [Performance optimization](https://databento.com/docs/architecture/performance-optimization), [locations/connectivity](https://databento.com/docs/architecture/locations-network-connectivity), [latency tutorial](https://databento.com/docs/examples/basics-live/live-latency).

The architecture pages cover capture/normalization, direct connectivity, cloud interconnects, and NTP service. Use those when a measured system requirement calls for them. A research prototype should first establish a correct bounded ingest/replay path and its actual bottleneck.
