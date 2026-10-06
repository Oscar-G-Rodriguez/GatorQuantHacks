"""Hand-checkable timing, data-identity and financial-accounting fixtures."""
import unittest
from unittest.mock import patch
import threading

import pandas as pd

from discovery.mechanism_data import (
    backward_quote, checked_url, choose_contracts, event_anchors, phase_window,
    session_calendar, settings, standard_pairs, same_day_bar,
    ApiCache,
)


class PreparationIntegrity(unittest.TestCase):
    def setUp(self):
        self.cfg = settings()

    def test_provider_cursor_cannot_transmit_key_off_host(self):
        with self.assertRaises(ValueError):
            checked_url("https://example.com/v3?apiKey=secret")
        self.assertEqual(checked_url("https://api.massive.com/v3?apiKey=secret&cursor=x"),
                         "https://api.massive.com/v3?cursor=x")

    def test_final_window_is_denied_without_freeze(self):
        with self.assertRaisesRegex(ValueError, "frozen"):
            phase_window("final-oos", self.cfg)
        self.assertEqual(phase_window("development", self.cfg)["as_of"], "2025-12-31")

    def test_actual_holiday_and_early_close(self):
        dates, clock = session_calendar({"start": "2024-11-27", "end": "2025-01-10", "as_of": "2025-01-10"})
        self.assertNotIn("2025-01-09", dates)
        close = pd.Timestamp(clock["2024-11-29"]["close_ns"], tz="UTC").tz_convert("America/New_York")
        self.assertEqual(close.hour, 13)

    def test_future_or_stale_quotes_cannot_fill_earlier_order(self):
        cutoff = 100 * 10**9
        q = {"sip_timestamp": cutoff+1, "bid_price": 2, "ask_price": 2.1, "bid_size": 3, "ask_size": 3}
        self.assertIsNone(backward_quote([q], cutoff, self.cfg)[0])
        q["sip_timestamp"] = cutoff-61*10**9
        self.assertIsNone(backward_quote([q], cutoff, self.cfg)[0])
        q["sip_timestamp"] = cutoff-2*10**9
        self.assertIsNotNone(backward_quote([q], cutoff, self.cfg)[0])

    def test_crossed_and_thin_quotes_are_rejected(self):
        q = {"sip_timestamp": 100, "bid_price": 3, "ask_price": 2, "bid_size": 1, "ask_size": 1}
        self.assertEqual(backward_quote([q], 100, self.cfg)[1], "nonpositive_or_crossed_quote")
        q.update(bid_price=2, ask_price=2.1, ask_size=0)
        self.assertEqual(backward_quote([q], 100, self.cfg)[1], "insufficient_displayed_size")

    def test_contract_multiplier_and_deliverables_are_not_guessed(self):
        base = {"expiration_date": "2024-05-17", "strike_price": 100, "exercise_style": "american"}
        call = {**base, "ticker": "CALL", "contract_type": "call", "shares_per_contract": 100}
        put = {**base, "ticker": "PUT", "contract_type": "put", "shares_per_contract": 100}
        self.assertEqual(len(standard_pairs([call, put], "2024-01-03")), 1)
        changed = {**put, "shares_per_contract": None}
        self.assertEqual(standard_pairs([call, changed], "2024-01-03"), {})
        changed = {**put, "additional_underlyings": [{"amount": 1}]}
        self.assertEqual(standard_pairs([call, changed], "2024-01-03"), {})

    def test_future_bar_changes_do_not_change_chain_selection(self):
        rows = []
        for expiry in ["2024-02-02", "2024-05-03"]:
            for strike in [90, 95, 100, 105, 110]:
                for side in ["call", "put"]:
                    rows.append({"ticker": f"{expiry}-{strike}-{side}", "contract_type": side,
                                 "shares_per_contract": 100, "exercise_style": "american",
                                 "strike_price": strike, "expiration_date": expiry})
        day = int(pd.Timestamp("2024-01-03", tz="America/New_York").timestamp()*1000)
        future = int(pd.Timestamp("2024-01-04", tz="America/New_York").timestamp()*1000)
        paths = {r["ticker"]: [{"c": 3, "t": day}, {"c": 999, "t": future}] for r in rows}
        def marks(ticker):
            return same_day_bar(paths[ticker], "2024-01-03")
        first = choose_contracts(rows, "2024-01-03", self.cfg, marks)
        for path in paths.values():
            path[1]["c"] = -123456
        second = choose_contracts(rows, "2024-01-03", self.cfg, marks)
        self.assertEqual(first, second)
        self.assertIn("120", first[0])

    def test_end_of_phase_does_not_compress_missing_dates(self):
        dates = ["2024-01-02", "2024-01-03", "2024-01-04"]
        row = {"tickers": ["ABC"], "cik": 1, "accession_number": "a",
               "filing_date": "2024-01-04", "tertiary_category": "ceo_departure"}
        anchors, reasons = event_anchors([row], ["ABC"], dates, self.cfg,
                                         {"start": dates[0], "end": dates[-1]})
        self.assertEqual(anchors, [])
        self.assertTrue(any(r["reason"] == "anchor_or_entry_outside_phase" for r in reasons))

    def test_different_same_day_accessions_remain_distinct(self):
        dates = [d.strftime("%Y-%m-%d") for d in pd.bdate_range("2024-01-01", "2024-02-01")]
        base = {"tickers": ["ABC"], "cik": 1, "filing_date": "2024-01-10", "tertiary_category": "ceo_departure"}
        anchors, _ = event_anchors([{**base, "accession_number": "a"}, {**base, "accession_number": "b"}],
                                   ["ABC"], dates, self.cfg, {"start": dates[0], "end": dates[-1]})
        self.assertEqual(len({a["event_id"] for a in anchors}), 2)

    def test_transient_windows_receipt_lock_is_retried_without_losing_attempt(self):
        cache = object.__new__(ApiCache)
        from pathlib import Path
        cache.lock, cache.attempt = threading.RLock(), Path("fixture")
        cache.started, cache.prior_count, cache.cap = "fixture", 0, 5
        cache.receipts = [{"http_status": 200, "label": "fixture"}]
        with patch("discovery.mechanism_data.write_json", side_effect=[PermissionError(), None]) as write:
            with patch("discovery.mechanism_data.time.sleep"):
                cache.save_receipts()
        self.assertEqual(write.call_count, 2)
        self.assertEqual(write.call_args.args[1]["requests"], cache.receipts)


if __name__ == "__main__":
    unittest.main()
