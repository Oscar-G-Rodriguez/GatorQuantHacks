"""Small synthetic checks of historical selection and backward alignment."""
import unittest

import pandas as pd

from discovery.options_data import anchors, backward_mark, select_pairs, session_dates


class PreparationTests(unittest.TestCase):
    def test_historical_selection_requires_two_standard_legs(self):
        rows=[]
        for strike in [95,100,105]:
            for leg in ["call","put"]:
                rows.append({"ticker":f"{leg}{strike}","strike_price":strike,"expiration_date":"2024-05-01",
                             "contract_type":leg,"shares_per_contract":100})
        selected,missing=select_pairs(rows,"2024-01-02",101)
        self.assertEqual(selected["120"]["strike"],100)
        self.assertNotIn("120",missing)
        self.assertFalse(select_pairs([{**r,"shares_per_contract":10} for r in rows],"2024-01-02",101)[0])

    def test_future_bar_is_never_backward_mark(self):
        ds=["2024-01-02","2024-01-03","2024-01-04","2024-01-05"]
        def bar(day,px):
            return {"t":pd.Timestamp(day,tz="America/New_York").value//10**6,"c":px,"v":1}
        bars=[bar(ds[0],3),bar(ds[2],99)]
        self.assertEqual(backward_mark(bars,ds[1],ds)["price"],3)
        self.assertEqual(backward_mark(bars,ds[1],ds)["age"],1)
        self.assertIsNone(backward_mark(bars,ds[1],ds,max_age=0))

    def test_prior_control_and_buffer_dates(self):
        ds=pd.bdate_range("2024-01-01",periods=160).strftime("%Y-%m-%d").tolist()
        leads=[{"cik":"123","accession_number":"a","filing_date":ds[110],"tickers":["A"],
                "tertiary_category":"ceo_departure","same_filing_categories":["ceo_departure"]}]
        rows,excluded=anchors(leads,["A"],ds)
        self.assertEqual(len(rows),2)
        e,c=rows
        self.assertEqual(e["pre_session"]-c["pre_session"],84)
        self.assertLess(c["observations"]["5"],e["pre"])
        self.assertEqual(e["observations"]["1"],ds[112])
        self.assertEqual(excluded,[])

    def test_calendar_retains_early_closes_and_exceptional_holidays(self):
        ds=session_dates()
        self.assertNotIn("2025-01-09",ds)
        self.assertIn("2024-11-29",ds)


if __name__=="__main__":
    unittest.main()
