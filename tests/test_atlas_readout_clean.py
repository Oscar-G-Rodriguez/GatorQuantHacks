import unittest
import pandas as pd
from discovery.atlas_readout_clean import clean_master


class ReadoutCorrectionTest(unittest.TestCase):
    def test_superseded_category_inference_cannot_survive_delivery(self):
        source = pd.DataFrame({'category': ['category_' + str(i) for i in range(119)],
                               'filings': range(119), 'positive_cells_passing_both_adjustments': [0] * 119,
                               'adjusted_p_min_63': [.001] * 119, 'adjusted_p_min_126': [.002] * 119})
        cleaned = clean_master(source)
        self.assertNotIn('adjusted_p_min_63', cleaned)
        self.assertNotIn('adjusted_p_min_126', cleaned)
        pd.testing.assert_frame_equal(cleaned, source[['category', 'filings', 'positive_cells_passing_both_adjustments']])
        self.assertIn('adjusted_p_min_63', source)


if __name__ == '__main__':
    unittest.main()
