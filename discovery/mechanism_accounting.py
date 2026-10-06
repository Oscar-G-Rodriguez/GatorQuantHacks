"""Funded option ledger and auditable quotes for the registered Massive round.

Backtrader drives the session clock in each hypothesis's own runner. This
ledger handles collateral and multi-leg option units explicitly, avoiding the
stock broker's misleading default treatment of option shorts and multipliers.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path

import numpy as np
import pandas as pd

from .io import digest, read_json
from .mechanism_data import CONFIG, backward_quote, settings


class Sources:
    """Frozen request bytes and same-session lookups, never future-filled."""

    def __init__(self, folder):
        self.folder = Path(folder)
        self.source = read_json(self.folder / "source.json")
        self.cfg = settings()
        window = self.source["window"]
        for anchor in self.source["anchors"]:
            if anchor["cohort"] == "ordinary":
                center = pd.Timestamp(anchor["filing_date"])
                offset = pd.Timedelta(days=self.cfg["ordinary_exclusion_calendar_days"])
                anchor["ordinary_history_complete"] = (center-offset >= pd.Timestamp(window["start"])
                                                        and center+offset <= pd.Timestamp(window["end"]))
        if not self.source.get("complete"):
            raise ValueError("Incomplete acquisition cannot become a scientific snapshot")
        if self.source["config_sha256"] != digest(CONFIG):
            raise ValueError("Input configuration changed after acquisition")
        self.rows = {}
        for rid, receipt in self.source["objects"].items():
            p = self.folder / "raw" / f"{rid}.json"
            if digest(p) != receipt["sha256"]:
                raise ValueError("Frozen response changed: " + rid)
            self.rows[rid] = read_json(p)
        self.dates = self.source["sessions"]
        self.index = {d: i for i, d in enumerate(self.dates)}
        self._bars = {}

    def series(self, selection, role):
        rid = selection["bar_objects"].get(role)
        if rid is None:
            return {}
        if rid not in self._bars:
            result = {}
            for row in self.rows[rid]:
                day = pd.Timestamp(row["t"], unit="ms", tz="UTC").tz_convert("America/New_York").strftime("%Y-%m-%d")
                if day in result:
                    raise ValueError("Duplicate option/session in one frozen request")
                result[day] = row
            self._bars[rid] = result
        return self._bars[rid]

    def mark(self, selection, role, day, maximum_age=0):
        if day not in self.index:
            return None
        series = self.series(selection, role)
        i = self.index[day]
        for age in range(maximum_age + 1):
            if i-age < 0:
                break
            candidate = self.dates[i-age]
            row = series.get(candidate)
            if row and row.get("c", 0) > 0:
                return {"price": float(row["c"]), "date": candidate,
                        "age_sessions": age, "volume": float(row.get("v", 0))}
        return None

    def spot(self, selection, day):
        c = self.mark(selection, "atm_call", day)
        p = self.mark(selection, "atm_put", day)
        if c is None or p is None:
            return None
        years = max(0, (pd.Timestamp(selection["expiry"])-pd.Timestamp(day)).days) / 365.25
        value = selection["atm_strike"] * math.exp(-self.cfg["rate"] * years) + c["price"] - p["price"]
        return value if value > 0 and math.isfinite(value) else None

    def prior_volume(self, selection, role, decision_day, count=5):
        i = self.index[decision_day]
        if i < count-1:
            return None
        series = self.series(selection, role)
        rows = [series.get(d) for d in self.dates[i-count+1:i+1]]
        if any(r is None for r in rows):
            return None
        return sum(float(r.get("v", 0)) for r in rows) / count


def construction(shape, otm=.05):
    """Signed standard-contract units; every synthetic leg is explicit."""
    key = str(otm)
    if shape == "synthetic_long":
        return {"atm_call": 1, "atm_put": -1}
    if shape == "covered_call":
        return {"atm_call": 1, "atm_put": -1, "upper_call_"+key: -1}
    if shape == "protective_put":
        return {"atm_call": 1, "atm_put": -1, "lower_put_"+key: 1}
    if shape == "cash_secured_put":
        return {"lower_put_"+key: -1}
    if shape == "cash":
        return {}
    raise ValueError("Unregistered strategy construction")


def quote_set(selection, label, roles, cfg):
    group = selection.get("quotes", {}).get(label)
    if not group or "legs" not in group:
        return None, (group or {}).get("reason", "quote_group_unavailable")
    quotes, times = {}, []
    for role in roles:
        record = group["legs"].get(role)
        if not record or record.get("quote") is None:
            return None, (record or {}).get("reason", "required_leg_quote_missing")
        q, reason = backward_quote([record["quote"]], group["cutoff_ns"], cfg)
        if q is None:
            return None, reason
        quotes[role] = q
        times.append(q["sip_timestamp"])
    if times and max(times)-min(times) > cfg["quote_max_leg_span_seconds"]*10**9:
        return None, "asynchronous_quote_legs"
    return quotes, None


def transaction(positions, quotes, cfg, opening=True, cost_multiplier=1):
    """Cash change in dollars, with bid/ask friction counted exactly once.

    Quantities are CONTRACTS, prices are dollars per underlying share, and
    the standard multiplier is 100. Fees are per contract, not per share.
    """
    cash, costs, details = 0.0, 0.0, []
    for role, signed_units in positions.items():
        quantity = signed_units if opening else -signed_units
        q = quotes[role]
        mid = (q["bid_price"] + q["ask_price"]) / 2
        half = (q["ask_price"] - q["bid_price"]) / 2
        direction = 1 if quantity > 0 else -1
        execution = mid + direction*half*cost_multiplier
        slippage = mid*cfg["adverse_slippage_premium_bps_side"] / 10000 * cost_multiplier
        execution += direction*slippage
        if execution <= 0:
            raise ValueError("Cost stress yields invalid option price")
        fee = abs(quantity)*cfg["commission_per_contract_side"]*cost_multiplier
        leg_cash = -quantity*100*execution-fee
        leg_cost = abs(quantity)*100*(half*cost_multiplier+slippage)+fee
        cash += leg_cash
        costs += leg_cost
        details.append({"role": role, "contracts": quantity, "multiplier": 100,
                        "price_per_share": execution, "mid_per_share": mid,
                        "cash_change": leg_cash, "cost_dollars": leg_cost,
                        "quote_timestamp_ns": q["sip_timestamp"]})
    return cash, costs, details


def reserve(selection, shape, positions):
    if shape == "cash_secured_put":
        role = next(iter(positions))
        return abs(positions[role])*100*selection["legs"][role]["strike_price"]
    # The funded synthetic exposure has strike cash behind its short ATM put.
    return abs(positions["atm_put"])*100*selection["atm_strike"] if positions else 0.0


def performance(nav_rows, initial_capital, cfg):
    """Actual daily NAV metrics; missing NAV never becomes a zero return."""
    frame = pd.DataFrame(nav_rows)
    if frame.empty or frame["nav"].isna().any():
        return {"status": "inconclusive", "reason": "missing_or_empty_nav", "observations": len(frame)}
    values = frame.nav.to_numpy(float)
    previous = np.r_[initial_capital, values[:-1]]
    returns = values/previous-1
    elapsed = frame.elapsed_days.to_numpy(float)
    rf = np.exp(cfg["rate"]*elapsed/365.25)-1
    vol = np.std(returns, ddof=1)*np.sqrt(252) if len(returns) > 1 else None
    excess_vol = np.std(returns-rf, ddof=1) if len(returns) > 1 else 0
    sharpe = float(np.mean(returns-rf)/excess_vol*np.sqrt(252)) if excess_vol > 1e-15 else None
    curve = np.r_[initial_capital, values]
    drawdown = curve/np.maximum.accumulate(curve)-1
    return {"status": "measured", "observations": len(values),
            "annualized_return": float((values[-1]/initial_capital)**(252/len(values))-1),
            "annualized_volatility": float(vol) if vol is not None else None,
            "sharpe": sharpe, "maximum_drawdown": float(drawdown.min()),
            "premium_turnover": float((frame.traded_premium/previous).sum()),
            "reserve_turnover": float((frame.traded_reserve/previous).sum()),
            "total_return": float(values[-1]/initial_capital-1),
            "start": frame.iloc[0].date, "end": frame.iloc[-1].date,
            "stale_mark_days": int((frame.stale_legs > 0).sum())}


@dataclass
class Position:
    anchor: dict
    selection: dict
    quantities: dict
    shape: str
    reserved: float
    entry_date: str
    planned_exit: str | None
    entry_cash: float
    entry_cost: float


class Ledger:
    """Session-by-session funded program, retaining failed exits and marks."""

    def __init__(self, sources, anchors, shape, horizon=5, delay=0, cost_multiplier=1,
                 cohort="event", predicate=None, shape_for=None):
        self.sources, self.cfg = sources, settings()
        self.shape, self.horizon, self.delay = shape, horizon, delay
        self.cost_multiplier, self.cohort = cost_multiplier, cohort
        self.shape_for = shape_for
        self.cash = self.cfg["capital"]
        self.positions, self.nav, self.audit, self.closed = {}, [], [], []
        self.last_date = self.sources.source["window"]["start"]
        self.peak = self.cash
        self.stopped_at = None
        self.entries = {}
        for anchor in anchors:
            if anchor["cohort"] != cohort or (predicate is not None and not predicate(anchor)):
                continue
            variant = anchor["variants"].get(str(delay), {})
            if variant.get("entry_date"):
                self.entries.setdefault(variant["entry_date"], []).append(anchor)
        for items in self.entries.values():
            items.sort(key=lambda a: (a["filing_date"], a["issuer"], a["accession"], a["ticker"]))

    def _mark_value(self, day):
        value, stale, missing = self.cash, 0, 0
        for p in self.positions.values():
            for role, quantity in p.quantities.items():
                mark = self.sources.mark(p.selection, role, day, self.cfg["mark_max_carry_sessions"])
                if mark is None:
                    missing += 1
                else:
                    value += quantity*100*mark["price"]
                    stale += int(mark["age_sessions"] > 0)
        return (None if missing else value), stale, missing

    def step(self, day):
        elapsed = (pd.Timestamp(day)-pd.Timestamp(self.last_date)).days
        self.cash *= math.exp(self.cfg["rate"]*elapsed/365.25)
        self.last_date = day
        traded_premium, traded_reserve = 0.0, 0.0
        prior_nav = self.nav[-1]["nav"] if self.nav else self.cfg["capital"]
        if prior_nav is None:
            prior_nav = self.cfg["capital"]
            integrity_stop = True
        else:
            integrity_stop = False
        index = self.sources.index[day]
        # Entries execute after yesterday's decision, before today's close.
        # No exit/return/closing volume appears in this eligibility branch.
        for a in self.entries.get(day, []):
            reason = "ordinary_category_window_incomplete" if a["cohort"] == "ordinary" and not a.get("ordinary_history_complete", True) else None
            variant = a["variants"][str(self.delay)]
            selection = variant["selected"].get(self.cfg["primary_bucket"])
            if selection is None:
                reason = "primary_bucket_unavailable"
            chosen_shape = self.shape_for(a) if self.shape_for else self.shape
            quantities = construction(chosen_shape, self.cfg["primary_otm"])
            if not quantities:
                continue
            quotes = None
            if reason is None:
                quotes, reason = quote_set(selection, "entry", quantities, self.cfg)
            if reason is None:
                volumes = [self.sources.prior_volume(selection, r, variant["decision_date"]) for r in quantities]
                if any(v is None or v < self.cfg["minimum_prior_five_session_leg_volume"] for v in volumes):
                    reason = "insufficient_complete_prior_leg_volume"
            reserved = reserve(selection, chosen_shape, quantities) if reason is None else 0
            current_reserved = sum(p.reserved for p in self.positions.values())
            if reason is None and (reserved > prior_nav*self.cfg["maximum_name_reserve_fraction"]
                                   or current_reserved+reserved > prior_nav*min(self.cfg["maximum_gross_reserve_fraction"], self.cfg["maximum_unknown_sector_fraction"])):
                reason = "reserve_or_concentration_limit"
            if reason is None and (a["issuer"] in self.positions or self.stopped_at is not None or integrity_stop):
                reason = "issuer_already_open_or_portfolio_stopped"
            if self.horizon == "expiry":
                scheduled = selection.get("quotes", {}).get("expiry", {}) if selection else {}
                exit_day = scheduled.get("date")
                # Expiry/cutoff is known at the decision; an unresolved expiry
                # cannot be silently changed into the last available date.
            else:
                ei = a["filing_session"]+int(self.horizon)
                exit_day = self.sources.dates[ei] if ei < len(self.sources.dates) else None
            if reason is None and exit_day and (exit_day < day or exit_day > selection["expiry"]):
                reason = "registered_exit_before_entry_or_after_expiry"
            if reason:
                self.audit.append({"date": day, "anchor_id": a["anchor_id"], "action": "unfilled_entry", "reason": reason})
                continue
            change, cost, legs = transaction(quantities, quotes, self.cfg, True, self.cost_multiplier)
            if self.cash+change < current_reserved+reserved:
                self.audit.append({"date": day, "anchor_id": a["anchor_id"], "action": "unfilled_entry", "reason": "insufficient_funded_cash"})
                continue
            self.cash += change
            self.positions[a["issuer"]] = Position(a, selection, quantities, chosen_shape, reserved, day, exit_day, change, cost)
            traded_premium += sum(abs(r["contracts"])*100*r["price_per_share"] for r in legs)
            traded_reserve += reserved
            self.audit.append({"date": day, "anchor_id": a["anchor_id"], "action": "entry", "decision_date": variant["decision_date"],
                               "arrival_ns": selection["quotes"]["entry"]["cutoff_ns"], "cash_change": change, "cost": cost,
                               "reserved": reserved, "legs": legs, "historical_clock_verified": False})
        for issuer, p in list(self.positions.items()):
            forced = self.stopped_at is not None and index > self.stopped_at
            if not forced and (p.planned_exit is None or day < p.planned_exit):
                continue
            label = str(self.horizon) if day == p.planned_exit else "retry_"+day
            if label not in p.selection.get("quotes", {}):
                label = next((k for k, v in p.selection.get("quotes", {}).items()
                              if k != "entry" and v.get("date") == day), label)
            quotes, reason = quote_set(p.selection, label, p.quantities, self.cfg)
            if quotes is None:
                self.audit.append({"date": day, "anchor_id": p.anchor["anchor_id"], "action": "unfilled_exit", "reason": reason,
                                   "risk_liquidation": forced})
                continue
            change, cost, legs = transaction(p.quantities, quotes, self.cfg, False, self.cost_multiplier)
            self.cash += change
            traded_premium += sum(abs(r["contracts"])*100*r["price_per_share"] for r in legs)
            traded_reserve += p.reserved
            self.closed.append({"anchor_id": p.anchor["anchor_id"], "event_id": p.anchor["event_id"], "issuer": issuer,
                                "entry_date": p.entry_date, "exit_date": day, "planned_exit_date": p.planned_exit,
                                "net_option_cash_pnl": p.entry_cash+change, "cost_dollars": p.entry_cost+cost,
                                "reserve": p.reserved, "scheduled_exit_filled": day == p.planned_exit,
                                "risk_liquidation": forced})
            self.audit.append({"date": day, "anchor_id": p.anchor["anchor_id"], "action": "exit", "cash_change": change,
                               "cost": cost, "arrival_ns": p.selection["quotes"][label]["cutoff_ns"], "legs": legs,
                               "risk_liquidation": forced})
            del self.positions[issuer]
        value, stale, missing = self._mark_value(day)
        if value is not None:
            self.peak = max(self.peak, value)
            dd = 1-value/self.peak
            if dd >= self.cfg["drawdown_stop"] and self.stopped_at is None:
                self.stopped_at = index
            elif (self.stopped_at is not None and index-self.stopped_at >= self.cfg["reentry_wait_sessions"]
                  and dd < self.cfg["drawdown_reentry"] and stale == 0 and missing == 0):
                self.stopped_at = None
        self.nav.append({"date": day, "nav": value, "cash": self.cash, "elapsed_days": elapsed,
                         "reserved": sum(p.reserved for p in self.positions.values()), "open_positions": len(self.positions),
                         "traded_premium": traded_premium, "traded_reserve": traded_reserve,
                         "stale_legs": stale, "missing_legs": missing})

    def result(self):
        metrics = performance(self.nav, self.cfg["capital"], self.cfg)
        metrics.update(trades=len(self.closed), open_positions_at_cutoff=len(self.positions),
                       unfilled_entries=sum(r["action"] == "unfilled_entry" for r in self.audit),
                       unfilled_exits=sum(r["action"] == "unfilled_exit" for r in self.audit),
                       shape=self.shape, cohort=self.cohort, horizon=self.horizon, delay=self.delay,
                       cost_multiplier=self.cost_multiplier)
        return {"metrics": metrics, "nav": self.nav, "execution_audit": self.audit, "closed_trades": self.closed,
                "unresolved_positions": [{"anchor_id": p.anchor["anchor_id"], "issuer": p.anchor["issuer"],
                                          "entry_date": p.entry_date, "planned_exit_date": p.planned_exit}
                                         for p in self.positions.values()]}
