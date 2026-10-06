"""Synthetic integrity checks, not real-data statistical execution."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

from discovery.financing_research import collect_filings,in_study,choose_contract,prior_features,control_match,placebo_map


class ResearchIntegrity(unittest.TestCase):
    def test_same_filing_bundle_keeps_missing_text_and_share_classes(self):
        rows=[{"accession_number":"a","filing_date":"2022-01-03","tertiary_category":"debt_issuance","supporting_text":None},
              {"accession_number":"a","filing_date":"2022-01-03","tertiary_category":"underwriting_agreement","supporting_text":"planned financing"}]
        filings,mapping,excluded=collect_filings([{"cik":"1","object_id":"x"}],{"x":rows+rows},
            {"B":{"cik":"0000000001"},"A":{"cik":"1"}},["2022-01-03","2022-01-04"])
        self.assertEqual(len(filings),1);self.assertEqual(mapping,{"0000000001":"A"})
        self.assertEqual(len(filings[0]["records"]),2);self.assertEqual(filings[0]["availability_session"],1)
        self.assertTrue(in_study(filings[0],{"labels":["debt_issuance","underwriting_agreement"]}))
        self.assertEqual(excluded[0]["reason"],"secondary_universe_share_class")

    def test_same_date_different_accessions_do_not_make_conjunction(self):
        rows=[{"accession_number":a,"filing_date":"2022-01-03","tertiary_category":label}
            for a,label in [("a","debt_issuance"),("b","underwriting_agreement")]]
        filings,_,_=collect_filings([{"cik":"1","object_id":"x"}],{"x":rows},{"A":{"cik":"1"}},["2022-01-04"])
        self.assertEqual(len(filings),2)
        self.assertFalse(any(in_study(f,{"labels":["debt_issuance","underwriting_agreement"]}) for f in filings))

    def test_conflicting_filing_date_and_unknown_identity_fail_visible(self):
        rows=[{"accession_number":"a","filing_date":d,"tertiary_category":"debt_issuance"} for d in ["2022-01-03","2022-01-04"]]
        with self.assertRaises(ValueError):collect_filings([{"cik":"1","object_id":"x"}],{"x":rows},{},["2022-01-04"])
        _,_,excluded=collect_filings([{"cik":"1","object_id":"x"}],{"x":[{"filing_date":"2022-01-03"}]},{},["2022-01-04"])
        self.assertEqual(excluded[0]["reason"],"missing_filing_identity_or_date")

    def test_put_selection_and_unknown_deliverables(self):
        base={"contract_type":"put","shares_per_contract":100,"exercise_style":"american","expiration_date":"2022-05-03","strike_price":95,"ticker":"p"}
        variant={"dte":120,"range":[90,180],"otm":.05}
        self.assertEqual(choose_contract([base],"2022-01-03",100,variant,"protective_put"),base)
        self.assertIsNone(choose_contract([{**base,"shares_per_contract":None}],"2022-01-03",100,variant,"protective_put"))
        self.assertIsNone(choose_contract([{**base,"additional_underlyings":[{}]}],"2022-01-03",100,variant,"protective_put"))
        self.assertIsNone(choose_contract([{**base,"strike_price":80}],"2022-01-03",100,variant,"protective_put"))

    def test_future_tail_changes_cannot_change_past_features_or_match(self):
        dates=pd.bdate_range("2022-01-03",periods=350).strftime("%Y-%m-%d").tolist()
        stock={d:{"c":100+np.sin(i/5)+i/100,"v":10000+i} for i,d in enumerate(dates)}
        spy={d:{"c":400+np.sin(i/9)+i/80,"v":10000} for i,d in enumerate(dates)}
        first=prior_features(stock,spy,dates);changed=copy.deepcopy(stock)
        for d in dates[261:]:changed[d]["c"]*=50
        second=prior_features(changed,spy,dates)
        pd.testing.assert_frame_equal(first.iloc[:261],second.iloc[:261])
        self.assertEqual(control_match(first,260,set()),control_match(second,260,set()))
        del stock[dates[250]]
        self.assertTrue(prior_features(stock,spy,dates).iloc[260].isna().all())

    def test_placebo_map_fixed_before_outcomes(self):
        filings=[{"issuer":"1","filing_date":"2022-01-03","future_return":v} for v in [1,-1]]
        cfg={"seed":123,"timing_placebos":199,"placebo_session_offset_range":[5,63]}
        first=placebo_map(filings,cfg)
        self.assertEqual(first,placebo_map([{**f,"future_return":999} for f in filings],cfg))
        self.assertEqual(len(first),199)
        self.assertTrue(all(5<=m["shifts"][0]["offset"]<=63 for m in first))


if __name__=="__main__":unittest.main()
