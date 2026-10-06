# Slow reader behavior

Choose skip versus warn deliberately. Compatible quote/depth subscriptions can skip records by default; complete event history needs gap evidence and a compatible policy. Excess lag can exhaust replay retention.

Official route: [Databento documentation](https://databento.com/docs/api-reference-live/basics/slow-reader-behavior).

Review state: `retrieved`.

Topics in the retained section: Skip, Warn, Data aged out of retention.

Implementation route: [task guide](../../../live/README.md). Return to [catalog](../../README.md).
