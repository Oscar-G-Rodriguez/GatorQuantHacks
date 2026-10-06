"""Offline Backtrader session driver; funded option accounting remains explicit.

Adapted from the root Webull example's Cerebro/feed/own-strategy organization.
The constant session feed is a clock, not a simulated market price. Broker P&L
is never reported: each hypothesis's ledger supplies every actual NAV mark.
"""
import backtrader as bt
import pandas as pd


class FundedStrategy(bt.Strategy):
    params = (("ledger", None),)

    def next(self):
        day = self.data.datetime.date(0).isoformat()
        self.p.ledger.step(day)


def replay(strategy_class, ledger, dates):
    frame = pd.DataFrame({"open":1., "high":1., "low":1., "close":1., "volume":0.}, index=pd.to_datetime(dates))
    engine = bt.Cerebro(stdstats=False)
    engine.adddata(bt.feeds.PandasData(dataname=frame))
    engine.addstrategy(strategy_class, ledger=ledger)
    engine.run(runonce=False, preload=True)
    return ledger.result()
