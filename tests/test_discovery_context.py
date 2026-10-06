"""Small synthetic checks for filing identity and interaction identifiability."""
import ast
import unittest

import numpy as np
import pandas as pd

from discovery.context import attach_context
from discovery.io import ROOT, STUDIES, read_json
from discovery.methods import handler


class ContextIntegrityTests(unittest.TestCase):
    def test_same_day_other_filing_is_not_a_cotag_and_unknown_is_missing(self):
        p = pd.DataFrame({"date": ["2024-02-05", "2024-02-06", "2024-02-06"],
                          "issuer": ["123", "123", "456"],
                          "event__cfo_appointment": [0., 1., 0.], "event__ceo_departure": [0., 0., 0.]})
        c = {"start": "2024-01-01", "end": "2025-12-31", "categories": ["cfo_appointment", "ceo_departure"],
             "cotag_groups": {"earnings": ["quarterly_earnings"]}}
        lead = {"cik": "123", "accession_number": "first", "filing_date": "2024-02-05", "tertiary_category": "cfo_appointment"}
        other = {**lead, "accession_number": "second", "tertiary_category": "quarterly_earnings"}
        out = attach_context(p, c, [lead, other], [lead])
        self.assertEqual(out.loc[0, "context__earnings"], 0)
        self.assertEqual(out.loc[1, "context__earnings"], 1)
        self.assertEqual(out.loc[1, "cotag__cfo_appointment__earnings"], 0)
        self.assertTrue(pd.isna(out.loc[2, "context__earnings"]))
        out = attach_context(p, c, [lead, {**other, "accession_number": "first"}], [lead])
        self.assertEqual(out.loc[1, "cotag__cfo_appointment__earnings"], 1)

    def test_early_context_is_not_reassigned_to_first_usable_day(self):
        p = pd.DataFrame({"date": ["2024-02-01"], "issuer": ["123"],
                          "event__cfo_appointment": [0.], "event__ceo_departure": [0.]})
        c = {"start": "2024-01-01", "end": "2025-12-31", "categories": ["cfo_appointment", "ceo_departure"],
             "cotag_groups": {"earnings": ["quarterly_earnings"]}}
        source = {"cik": "123", "accession_number": "first", "filing_date": "2024-01-01", "tertiary_category": "quarterly_earnings"}
        self.assertEqual(attach_context(p, c, [source], [source]).loc[0, "context__earnings"], 0)

    def test_rare_candidate_cannot_split_but_supported_threshold_can(self):
        # Loading this pure function separately lets a Windows correctness check
        # avoid importing blocked compiled model libraries. HPC imports all code.
        tree = ast.parse((ROOT / "Hypotheses" / STUDIES["H08"] / "analysis.py").read_text())
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "candidate_split_possible")
        scope = {"np": np}
        exec(compile(ast.Module(body=[function], type_ignores=[]), "synthetic-split-check", "exec"), scope)
        split = scope["candidate_split_possible"]
        self.assertFalse(split(np.r_[np.zeros(100), np.ones(25)], 30))
        self.assertFalse(split(np.r_[np.zeros(100), np.arange(-12, 13)], 30))
        self.assertTrue(split(np.r_[np.zeros(100), np.ones(30)], 30))

    def test_interaction_recovers_known_coefficient_with_issuer_effects(self):
        rng = np.random.default_rng(14)
        c = read_json(ROOT / "config/discovery-pilot.json")
        c.update(horizons=[1], interaction_controls=["past_vol_20"], cotag_groups={}, min_positive=8)
        controls = ["past_return_5", "past_return_20", "past_vol_20", "past_log_volume", "market_past_return_5"]
        dates = pd.bdate_range("2024-01-01", periods=100).strftime("%Y-%m-%d")
        p = pd.DataFrame({"date": np.repeat(dates, 4), "issuer": np.tile(["a", "b", "c", "d"], 100)})
        for control in controls:
            p[control] = rng.normal(size=len(p))
        features = ["event__" + category for category in c["categories"]]
        for feature in features:
            p[feature] = rng.binomial(1, .25, len(p))
        p["sequence_a_before_b"], p["recent_a"] = 0., 0.
        early = p[p.date < dates[40]]
        z = (p.past_vol_20 - early.past_vol_20.mean()) / early.past_vol_20.std()
        p["return_1"] = .01 * p[features[0]] + .003 * p[features[0]] * z + .02 * p.past_return_5 + p.issuer.map({"a": .1, "b": -.2, "c": .3, "d": -.1})
        p["volatility_1"] = p["return_1"]
        rows, _ = handler("H07")(p, {"controls": controls}, c, {"seed": 1})
        measured = next(r for r in rows if r.get("statistic") == "interaction_coefficient" and r["feature"] == features[0] and r["target"] == "return_1")
        self.assertEqual(measured["status"], "measured")
        self.assertAlmostEqual(measured["interaction_coefficient"], .003, places=10)
        self.assertAlmostEqual(measured["event_main_coefficient"], .01, places=10)


if __name__ == "__main__":
    unittest.main()
