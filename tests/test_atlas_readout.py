"""Artificial report cohorts, including global/event contrast mismatches."""
import unittest
import numpy as np
import pandas as pd
from discovery.atlas_readout import summarize


class ReadoutTests(unittest.TestCase):
    def test_all_categories_rows_and_same_cohort_interpretation(self):
        master=pd.DataFrame({'category':['a','b']+['empty'+str(i) for i in range(117)],'description':['synthetic']*119})
        rows=[];inference=[]
        for pattern,family in [('tag:a','tag'),('tag:b','tag'),(None,None)]:
            for year in [2023,2024,2025]:
                key=str(pattern)+str(year);positive=pattern=='tag:a'
                rows.append({'comparison_id':key,'pattern':pattern,'family':family,'kind':'return','horizon':5,'lag':0,
                    'group':'labels','baseline':None,'year':year,'status':'measured','event_improvement':1 if pattern is None or positive else -1,
                    'mse_improvement':-1 if pattern is None else np.nan})
                for block in [63,126]:inference.append({'comparison_id':key,'block_sessions':block,'romano_wolf_p':.01,
                    'pointwise_lower':.1,'pointwise_upper':2,'inference_status':'approximate_exploratory','finite_resamples':9999,'missing_resamples':0})
        output,joined,broad,annual=summarize(master,pd.DataFrame(rows),pd.DataFrame(inference))
        self.assertEqual(len(output),119);self.assertEqual(len(joined),9);self.assertEqual(len(broad),3)
        a=output.set_index('category').loc['a'];self.assertEqual(a.measured_conditional_forecast_cells,3)
        self.assertEqual(a.positive_cells_passing_both_adjustments,3)
        self.assertEqual(annual.all_three_years_positive.sum(),1)
        self.assertEqual(annual.all_three_years_positive_passing_both_adjustments.sum(),1)
        self.assertFalse(annual.set_index('pattern').loc['global'].all_three_years_positive)
        with self.assertRaises(ValueError):summarize(master.iloc[:-1],pd.DataFrame(rows),pd.DataFrame(inference))
        with self.assertRaises(ValueError):summarize(master,pd.DataFrame(rows+[rows[0]]),pd.DataFrame(inference))


if __name__=='__main__':unittest.main()
