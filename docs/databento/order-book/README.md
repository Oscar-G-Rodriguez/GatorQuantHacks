# Order state and book reconstruction

Start with the delivered DBN stream and the selected dataset's normalization rules. A full book is state accumulated from a valid initialization and subsequent events. Beginning at an arbitrary delta in the middle of a session does not establish the missing resting orders.

## State transitions

Track resting orders within their publisher/instrument context. Insert adds, apply modifications with the documented priority consequences, reduce/remove cancels, and clear the instrument on a clear action. Trade and fill records describe executions but do not themselves mutate the resting-order map; applying both the observation and its accompanying book change double-counts removal. [Order tracking](https://databento.com/docs/examples/order-book/order-tracking), [order actions](https://databento.com/docs/examples/order-book/order-actions).

Maintain aggregated price levels alongside orders when repeated BBO/depth access matters. Compute features at completed event boundaries, not every transient internal update. Retain the record ordinal and do not reorder equal-time messages. Compare derived quotes with the appropriate provider quote schema on a small fixture to detect action/priority errors. [Limit order book tutorial](https://databento.com/docs/examples/order-book/limit-order-book).

## Snapshots and recovery

Snapshots initialize an instrument with a clear and a sequence of adds in priority order. Snapshot flags identify reconstructed state; snapshot receipt time must not be treated as each order's original arrival. Complete initialization before using a book in a signal. Historical daily snapshots and live requested snapshots differ in when they are supplied. [Snapshot mechanics](https://databento.com/docs/standards-and-conventions/mbo-snapshot), [live snapshot request](https://databento.com/docs/api-reference-live/basics/live-snapshot).

After a gap, mark state unusable, then apply the chosen replay or snapshot recovery. Do not continue a queue feature from an unknown partial state. A warning about bad timestamps and a warning about an unreliable book require different responses: preserve both and document their effect on each feature.

## Feed granularity

`F_TOB` and `F_MBP` can identify book records normalized from coarser upstream data. Such records do not establish individual orders or hidden depth. `mbp-10` is aggregated depth; `EQUS.MINI` has derived aggregated BBO and no venue order counts. Queue-position analysis needs a suitable order-level source and the venue's actual matching algorithm.

CME also has implied liquidity. The reviewed `GLBX.MDP3` guide describes merged real/implied top-of-book through consolidated quote schemas, so a book derived from native MBO and a consolidated quote can represent different liquidity. Historical CME data before the MBO introduction is coarser. [CME dataset guide](https://databento.com/docs/venues-and-datasets/glbx-mdp3).

## Features and fills

Microprice and book imbalance need valid bid/ask prices and sizes, an explicit stale-quote cutoff, and a zero-denominator policy. Queue estimates are conditional on visible orders and matching rules. They do not prove where our hypothetical order would fill. Reproduce the [microprice example](https://databento.com/docs/examples/order-book/microprice) and [queue example](https://databento.com/docs/examples/order-book/queue-position) only within their documented scope; then add the registered execution model and meaningful state-transition fixtures.
