"""Synthetic checks of buffered joins, paired cohorts and cluster mathematics."""
import unittest

import numpy as np
import pandas as pd

from discovery.connections import cluster_ols, mean_contrast, option_panel, shifted


class ConnectionTests(unittest.TestCase):
    def test_offset_uses_sessions_without_compressing_missing_days(self):
        ds=["2024-01-02","2024-01-03","2024-01-04"]
        f=pd.DataFrame({"ticker":["A","A"],"date":[ds[0],ds[2]],"x":[1.,99.]})
        r=shifted(f,["x"],1,ds)
        self.assertTrue(r.x.isna().all())
        self.assertEqual(shifted(f,["x"],2,ds).x.iloc[1],1.)

    def test_issuer_fit_recovers_known_within_effect(self):
        rng=np.random.default_rng(10)
        x=rng.normal(size=80);z=rng.normal(size=80);issuer=np.repeat(np.arange(8),10)
        f=pd.DataFrame({"issuer":issuer,"x":x,"z":z,"y":2*x-3*z+issuer})
        r=cluster_ols(f,["x","z"],"y","x",{"fixture":1},bootstrap=True)
        self.assertAlmostEqual(r["coefficient"],2.)
        self.assertAlmostEqual(r["ci_low"],2.)
        self.assertEqual(r["valid_bootstrap_draws"],999)

    def test_offset_discards_multiple_end_boundary_join_keys(self):
        ds=["2025-12-26","2025-12-29","2025-12-30","2025-12-31"]
        frame=pd.DataFrame({"ticker":["A"]*4,"date":ds,"x":[1.,2.,3.,4.]})
        result=shifted(frame,["x"],3,ds)
        self.assertEqual(len(result),4)
        self.assertTrue(result.x.iloc[:3].isna().all())
        self.assertEqual(result.x.iloc[3],1.)

    def test_pair_contrast_preserves_issuer_and_not_unpaired_subtraction(self):
        records=[]
        for i in range(8):
            records.extend([{"event_id":str(i),"issuer":str(i),"cohort":"event","value":i+2.},
                            {"event_id":str(i),"issuer":str(i),"cohort":"ordinary","value":float(i)}])
        records.append({"event_id":"unpaired","issuer":"extra","cohort":"event","value":999.})
        r,q=mean_contrast(pd.DataFrame(records),"value",{"fixture":2})
        self.assertEqual(r["pairs"],8)
        self.assertEqual(r["mean_difference"],2.)
        self.assertEqual(r["ci_low"],2.)
        self.assertEqual(len(q),8)

    def test_expiry_and_future_marks_do_not_become_outcomes(self):
        ds=pd.bdate_range("2024-01-02",periods=6).strftime("%Y-%m-%d").tolist()
        def bar(d,price):return {"t":pd.Timestamp(d,tz="America/New_York").value//10**6,"c":price,"v":1}
        sources={"sessions":ds,"bar_objects":{"c":[bar(ds[0],5),bar(ds[3],100)],"p":[bar(ds[0],3),bar(ds[3],100)]},
                 "anchors":[{"anchor_id":"a","event_id":"e","cohort":"event","ticker":"A","issuer":"123",
                            "pre":ds[0],"observations":{},"categories":["cfo_appointment"],"same_filing_categories":[],
                            "selected":{"30":{"expiry":ds[3],"strike":100.,"selection_moneyness":1.,
                                             "bar_objects":{"call":"c","put":"p"},"legs":{"call":{"ticker":"C"},"put":{"ticker":"P"}}}}}]}
        stock=pd.DataFrame({"ticker":[],"date":[]})
        result=option_panel(sources,stock)
        r=result[result.max_age==3].iloc[0]
        self.assertEqual(r.call,5.)
        self.assertEqual(r.call_change_1,0.)
        self.assertEqual(r.missing_3,"development_or_expiry_boundary")

    def test_quote_evidence_survives_absent_trade_marks(self):
        ds=["2024-01-02","2024-01-03"]
        sources={"sessions":ds,"bar_objects":{"c":[],"p":[]},"anchors":[{
            "anchor_id":"a","event_id":"e","cohort":"event","ticker":"A","issuer":"1","pre":ds[0],
            "observations":{},"categories":["cfo_appointment"],"same_filing_categories":[],
            "selected":{"120":{"expiry":"2024-05-01","strike":100.,"selection_moneyness":1.,
                                   "bar_objects":{"call":"c","put":"p"},"legs":{},"quote_cutoff_ns":10000000000,
                                   "pre_quotes":{"call":[{"sip_timestamp":9000000000,"bid_price":2.,"ask_price":3.}],
                                                 "put":[{"sip_timestamp":8000000000,"bid_price":1.,"ask_price":2.}]}}}}]}
        r=option_panel(sources,pd.DataFrame({"ticker":[],"date":[]})).iloc[0]
        self.assertEqual(r.status,"inconclusive")
        self.assertEqual(r.call_quote_mid,2.5)
        self.assertEqual(r.quote_leg_time_difference_seconds,1.)


if __name__=="__main__":unittest.main()
