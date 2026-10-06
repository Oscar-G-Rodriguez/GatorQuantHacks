"""Synthetic regression cases for the documented empty-comparison repair."""
import unittest

import pandas as pd

from discovery.mechanism_comparisons import paired_trade
from discovery.mechanism_data import settings


def row(cohort="event",shape="covered_call",stock=.03,collateral=.02):
    return dict(anchor_id="a-"+cohort,event_id="a",issuer="A",cohort=cohort,
                filing_date="2024-01-03",filing_session=1,delay=0,bucket="120",otm=.05,
                horizon=5,cost_multiplier=1,status="measured",shape=shape,
                stock_notional_return=stock,collateral_return=collateral)


class EmptyComparisonRepair(unittest.TestCase):
    def test_all_unmeasured_window_without_return_columns_stays_empty(self):
        value=row();value.pop("stock_notional_return");value.pop("collateral_return")
        value["status"]="inconclusive"
        value["reason"]="required_leg_quote_missing"
        frame=pd.DataFrame([value]);before=frame.copy(deep=True)
        for shape in ["covered_call","protective_put"]:
            common,paired=paired_trade(frame,shape,settings())
            self.assertTrue(common.empty);self.assertTrue(paired.empty)
            self.assertIn("increment",common)
            self.assertEqual(common.increment.dtype,float)
        pd.testing.assert_frame_equal(frame,before)

    def test_measured_long_without_matched_shape_stays_empty(self):
        common,paired=paired_trade(pd.DataFrame([row(shape="synthetic_long")]),"covered_call",settings())
        self.assertTrue(common.empty);self.assertTrue(paired.empty)
        self.assertIn("shape_return",common)

    def test_nonempty_comparison_keeps_exact_original_payoffs(self):
        frame=pd.DataFrame([row(),row(shape="synthetic_long",stock=.01),
                            row("ordinary",stock=.02),row("ordinary","synthetic_long",stock=.015)])
        common,paired=paired_trade(frame,"covered_call",settings())
        self.assertEqual(len(common),2);self.assertEqual(len(paired),1)
        self.assertAlmostEqual(common.loc[common.cohort=="event","increment"].iloc[0],.02)
        self.assertAlmostEqual(paired.increment.iloc[0],.015)
        malformed=frame.drop(columns=["stock_notional_return"])
        with self.assertRaises(AttributeError):paired_trade(malformed,"covered_call",settings())


if __name__=="__main__":unittest.main()
