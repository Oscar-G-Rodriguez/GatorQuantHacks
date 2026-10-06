# Live.subscribe

Add a dataset/schema/symbol subscription before replay startup. Replay start and MBO snapshot conflict; subscriptions use one dataset per session.

Official route: [Databento documentation](https://databento.com/docs/api-reference-live/client/subscribe).

Review state: `retrieved`.

## Python parameter inventory

Required: `dataset`, `schema`.
Optional: `symbols`, `stype_in`, `start`, `snapshot`.

Read the source for types, defaults, return values, and incompatible combinations.

Implementation route: [task guide](../../../live/README.md). Return to [catalog](../../README.md).
