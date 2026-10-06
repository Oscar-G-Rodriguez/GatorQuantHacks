# backtrader + Webull OpenAPI Data Feed Example

This example implements a historical bar data feed for
[backtrader](https://github.com/mementum/backtrader) using the market data endpoints
of the [Webull OpenAPI](https://developer.webull.com/apis/docs). Its design follows
backtrader's official `feeds/yahoo.py` (`YahooFinanceData`): fetch online data in
`start()`, then deliver it to the strategy one bar at a time in `_load()`.

This is an English translation of the starter kit's technical README, with paths
and imports updated for the current repository layout. For the competition's
research workflow, registration requirements, costs, and holdout rules, start
with the [repository README](../README.md) and
[backtest evidence contract](BACKTEST_EVIDENCE_CONTRACT.md). The examples below
explain the shared library; they are not a completed hypothesis experiment.

When writing hypothesis code, also read [the mandatory signal-reading methods](signal-reading/README.md) and implement the registered S01–S12 coverage after the hypothesis commit.

## Directory structure

```text
GatorQuantHacks/
├── webull_bt/                 # Shared data, trading, and reporting library
│   ├── feed.py                # WebullData, WebullLiveData, and WebullBar
│   ├── broker.py              # WebullBroker: real order placement
│   ├── logging_utils.py       # Shared logging configuration
│   ├── timeutils.py           # Timezone and trading-session helpers
│   ├── visualize.py           # Plotly report generation
│   └── visualize_lwc.py       # Lightweight Charts report generation
├── examples/
│   ├── backtest/
│   │   ├── main.py            # Reference backtest entry point
│   │   └── .env.example       # Example configuration template
│   ├── live/
│   │   ├── main.py            # Simulated-live / real trading entry point
│   │   └── .env.example       # Live configuration template
│   └── strategies/
│       ├── dual_ma.py         # Dual moving average example
│       └── portfolio.py       # Multi-symbol momentum rotation example
├── Hypotheses/                # Independent registered experiments
├── docs/                      # Technical and research documentation
├── .env.example               # Shared research credentials template
├── .python-version            # Shared Python version selector
├── pyproject.toml             # Shared dependency manifest
└── uv.lock                    # Shared dependency lockfile
```

The reference backtest and live scripts have separate configuration files:

- `examples/backtest/main.py` runs a historical backtest using market data
  credentials. It does not require a trading account or place live orders. The
  adapted runner loads root `.env` and its example configuration; its optional
  `--hypothesis` adapter is documented in the repository README.
- `examples/live/main.py` polls for new bars. It can connect to the trading broker
  when `WEBULL_USE_BROKER=1`; `WEBULL_ENV` selects production or sandbox credentials.

Both entry points use the shared `webull_bt/` library. Each hypothesis will own its
backtest and analysis code after its completed plan is committed; see the
[repository conventions](../CONVENTIONS.md).

## Install dependencies

Run from the repository root. The shared runtime uses Python 3.11, with the
manifest allowing Python 3.11 or newer.

```bash
uv sync --locked
# Alternative, inside an activated virtual environment:
pip install -e .
```

The dependencies declared in `pyproject.toml` are `backtrader`,
`webull-openapi-python-sdk`, `python-dotenv`, `plotly`, and `pandas`.
`python-dotenv` loads configuration from `.env` files.

## Configure credentials

For the reference backtest, copy `examples/backtest/.env.example` to
`examples/backtest/.env` and enter your Webull OpenAPI credentials. The application
process is described in Webull's
[Individual Application Process](https://developer.webull.com/apis/docs/authentication/IndividualApplicationAPI.md).
For research experiments, keep shared credentials in root `.env` and experiment
settings in the selected hypothesis's `.env`, as described in the repository README.

Example backtest configuration:

```dotenv
WEBULL_APP_KEY=your_app_key
WEBULL_APP_SECRET=your_app_secret
WEBULL_API_ENDPOINT=api.webull.com

WEBULL_SYMBOLS=AAPL
WEBULL_CATEGORY=US_STOCK
WEBULL_TIMESPAN=M1
WEBULL_COUNT=200
# Optional exact time range (ISO 8601; timezone recommended)
WEBULL_FROMDATE=2026-09-15T09:30:00-04:00
WEBULL_TODATE=2026-09-15T16:00:00-04:00
```

Live configuration belongs in `examples/live/.env`; additional settings are
explained below.

> Credentials are sensitive. The root `.gitignore` excludes `.env` files. Never
> hardcode credentials into source or commit them to Git. The upstream guide notes
> that US stock/ETF data requires the appropriate OpenAPI market data entitlement;
> missing access can result in a 403 response.

## Run the reference examples

The commands below describe the starter interfaces. Follow the repository's
registration rule before any hypothesis-specific code or backtest. The reference
backtest does not itself implement the required cost model or locked holdout;
add those controls in each registered hypothesis's implementation before reporting
research results.

Historical backtest, from the repository root:

```bash
uv run python examples/backtest/main.py
# Or, with the virtual environment activated:
python examples/backtest/main.py
```

Simulated-live example, with `WEBULL_USE_BROKER=0` (no real orders):

```bash
uv run python examples/live/main.py
# Or, with the virtual environment activated:
python examples/live/main.py
```

Paper/live trading is unscored and is not part of research setup or validation.

`WEBULL_FROMDATE` and `WEBULL_TODATE` are optional backtest boundaries in ISO 8601
format, including minute-level times. Include a timezone, for example
`2026-09-15T09:30:00-04:00`. The range is passed to the Webull API as
`start_time`/`end_time`, and backtrader also filters bars locally. Use `M1` for
one-minute bars. Without a date range, the feed requests the most recent
`WEBULL_COUNT` bars.

## Use the feed in your own code

The feed handles data retrieval and delivery. The caller constructs the API client
and supplies credentials. Create a `DataClient`, then pass it to `WebullData`;
`data_client` is required. Multiple feeds can reuse the same client.

```python
import backtrader as bt
from webull.core.client import ApiClient
from webull.data.data_client import DataClient
from webull_bt import WebullData

# Read app_key and app_secret from environment variables.
api_client = ApiClient(app_key, app_secret, "us")
api_client.add_endpoint("us", "api.webull.com")
data_client = DataClient(api_client)

cerebro = bt.Cerebro()
cerebro.adddata(
    WebullData(
        dataname="AAPL",
        data_client=data_client,
        category="US_STOCK",  # See the SDK's Category enum.
        timespan="D",         # See the SDK's Timespan enum.
        count=200,
    )
)
```

## Feed parameters

| Parameter | Default | Description |
| --- | --- | --- |
| `dataname` | — | Security symbol, such as `AAPL`. |
| `data_client` | — | **Required.** An initialized `DataClient`; the caller configures credentials and endpoint. |
| `category` | `US_STOCK` | Security type; use a name from the SDK's `Category` enum. |
| `timespan` | `M1` | Bar interval: `M1/M5/M15/M30/M60/M120/M240/D/W/M/Y`. |
| `count` | `200` | Number of bars requested. The feed documents a maximum of 1,200, or 1,650 for `M1`. |
| `trading_sessions` | `None` | Trading sessions, such as `PRE,RTH,ATH,OVN`. |
| `fromdate` / `todate` | `None` | backtrader's local time-filter boundaries; also used for the API request. |

The reference backtest accepts its date range through `WEBULL_FROMDATE` and
`WEBULL_TODATE`. The feed maps `timespan` to backtrader's `timeframe` and
`compression` automatically.

## Data processing

- The API may return recent bars in reverse chronological order. The feed sorts
  bars in ascending time order before delivering them to backtrader.
- OHLCV fields are parsed from strings into floats. API timestamps, such as
  `2021-12-28T09:00:09.945+0000`, are normalized to UTC and converted to timezone-naive
  UTC datetimes for backtrader.
- The original starter guide describes daily and longer bars as adjusted and
  minute bars as unadjusted, with adjustment determined by Webull. Verify and
  document the adjustment convention of the actual dataset used for research.

## Portfolio strategy: multi-symbol momentum rotation

`examples/strategies/portfolio.py` provides `PortfolioMomentumStrategy`, showing
how to allocate and rebalance capital across a basket. The dual moving average
example in `dual_ma.py` evaluates each symbol independently; the portfolio
example ranks symbols together. Add one `WebullData` feed per symbol to the same
`Cerebro` instance.

The rotation logic is:

1. Rebalance every `rebalance_days` bars.
2. Compute each symbol's return over the previous `lookback` bars as its momentum score.
3. Rank the scores, keep positive scores, and select at most `top_n` symbols.
4. Use `order_target_percent` to assign equal target weights, capped by
   `max_weight`. Close positions in symbols that are no longer selected.
   backtrader calculates the orders needed to reach these targets.

To select the example in `examples/backtest/.env`, use the strategy filename
without `.py`:

```dotenv
WEBULL_STRATEGY=portfolio
WEBULL_SYMBOLS=AAPL,MSFT,GOOG,AMZN
# Optional strategy parameter overrides
WEBULL_STRATEGY_PARAMS=lookback=15,rebalance_days=3,top_n=2,max_weight=0.5
```

Run with the reference backtest command shown above. In a custom script, after
constructing `data_client`:

```python
import backtrader as bt
from webull_bt import WebullData
from examples.strategies.portfolio import PortfolioMomentumStrategy

cerebro = bt.Cerebro()
for symbol in ["AAPL", "MSFT", "GOOG", "AMZN"]:
    cerebro.adddata(
        WebullData(dataname=symbol, data_client=data_client, timespan="D", count=200),
        name=symbol,
    )
cerebro.addstrategy(
    PortfolioMomentumStrategy,
    lookback=20,       # Momentum window in bars
    rebalance_days=5,  # Rebalance interval in bars
    top_n=3,           # Maximum number of symbols held
    max_weight=0.35,   # Maximum weight per symbol
)
cerebro.broker.setcash(100000.0)
cerebro.run()
```

The strategy records `closed_trades` through `notify_trade()`, using the same
trade-detail fields as the dual moving average strategy. It also records
`rebalance_log`, containing each rebalance's rankings and selected symbols. The
reference backtest prints both lists at the end.

## Simulated-live feed: polling

`WebullLiveData` is a live feed driven by polling rather than MQTT streaming. A
background thread requests historical bars at a fixed interval and delivers newly
closed bars to the strategy.

In `examples/live/.env`:

```dotenv
WEBULL_SYMBOLS=AAPL
WEBULL_TIMESPAN=M1
WEBULL_USE_BROKER=0
```

The live entry point does not expose `poll_interval`, `fetch_count`, or `backfill`
through `.env`. Its defaults are defined in `build_live_feed()` in
`examples/live/main.py`. `backfill` is a count of historical bars to load at startup.

Example use in a custom script:

```python
import backtrader as bt
from webull.core.client import ApiClient
from webull.data.data_client import DataClient
from webull_bt import WebullLiveData
from examples.strategies.dual_ma import DualMovingAverageStrategy

api_client = ApiClient(app_key, app_secret, "us")  # Read credentials from the environment.
api_client.add_endpoint("us", "api.webull.com")
data_client = DataClient(api_client)

cerebro = bt.Cerebro()
cerebro.adddata(
    WebullLiveData(
        dataname="AAPL",
        data_client=data_client,
        timespan="M1",
        poll_interval=5,  # Seconds between polls
        fetch_count=20,   # Bars requested per poll
        backfill=20,      # Historical bars loaded at startup; 0 disables backfill
    )
)
cerebro.addstrategy(DualMovingAverageStrategy)
cerebro.run()  # Runs until interrupted or the strategy calls runstop().
```

Key live-feed behavior:

- `islive()` returns `True`, so backtrader disables preload/runonce and processes
  bars as they arrive.
- `_load()` returns `True` when a bar is available and `None` when the queue is
  temporarily empty, meaning retry later rather than stop.
- The feed requests closed bars and enforces strictly increasing delivered
  timestamps, avoiding duplicate or backward-moving bars.
- Choose a polling interval appropriate to the bar interval and API rate limits.
  `fetch_count` must cover the bars that could arrive between polls.

## Trading broker: real order placement

`webull_bt/broker.py` provides `WebullBroker`, mapping backtrader's broker interface
to the Webull trading API. Its design follows backtrader's official
`brokers/ibbroker.py`.

| Component | Purpose |
| --- | --- |
| `WebullOrder(OrderBase)` | Maps order type, direction, and validity into a Webull order request. |
| `WebullCommInfo(CommInfoBase)` | Estimates costs and position value; the broker settles actual commissions. |
| `WebullBroker(BrokerBase)` | Implements buy/sell/cancel, cash/value/position queries, and order-status polling. |

IB uses TWS callbacks for order updates. This Webull implementation uses HTTP
requests and a background thread that polls order details, without a separate
store layer.

### Order type mapping

| backtrader | Webull `order_type` |
| --- | --- |
| `Market` | `MARKET` |
| `Limit` | `LIMIT` |
| `Stop` | `STOP_LOSS` |
| `StopLimit` | `STOP_LOSS_LIMIT` |
| `StopTrail` | `TRAILING_STOP_LOSS` |
| `Close` | `MARKET_ON_CLOSE` |

### Order status mapping

| Webull status | backtrader status |
| --- | --- |
| `SUBMITTED` | `Accepted` |
| `PARTIAL_FILLED` | `Partial` |
| `FILLED` | `Completed` |
| `CANCELLED` | `Cancelled` |
| `FAILED` | `Rejected` |

The broker avoids repeating notifications when neither the status nor filled
quantity has changed.

### Broker configuration

Configure the optional broker in `examples/live/.env`. The order-status polling
interval is set in `build_broker()` in `examples/live/main.py`, rather than `.env`.

```dotenv
# 1 submits real orders; 0 uses backtrader's simulated broker.
WEBULL_USE_BROKER=0
# prod (default) or sandbox selects credentials, endpoint, and account settings.
WEBULL_ENV=prod
WEBULL_TRADE_ENDPOINT=pre-openapi-us-alb.webullbroker.com
WEBULL_ACCOUNT_ID=              # Prefer an explicit account ID.
WEBULL_SANDBOX_ACCOUNT_ID=      # Account ID for the sandbox environment.
WEBULL_TRADING_SESSION=CORE     # CORE / ALL / NIGHT
```

If no account ID is configured for the selected environment, the example chooses
a cash account when available, otherwise the first returned account. Configure
an explicit account ID to control that selection.

Example use in your own code:

```python
import backtrader as bt
from webull.core.client import ApiClient
from webull.trade.trade_client import TradeClient
from webull_bt import WebullBroker

api_client = ApiClient(app_key, app_secret, "us")
api_client.add_endpoint("us", "pre-openapi-us-alb.webullbroker.com")
trade_client = TradeClient(api_client)

cerebro = bt.Cerebro()
cerebro.setbroker(
    WebullBroker(
        trade_client=trade_client,
        account_id="<your_account_id>",  # Query through account_v2.get_account_list().
        trading_session="CORE",
        poll_interval=2,
    )
)
```

> **Real-order warning:** With `WEBULL_USE_BROKER=1`, strategy signals submit orders
> through the trading API. Validate order placement, cancellation, and status
> updates in the appropriate test environment before considering production.
> Trading API access requires separate approval; see Webull's
> [Trading API Application](https://developer.webull.com/apis/docs/authentication/IndividualApplicationAPI.md).
