"""
Dedicated Anti-Circularity Validation Suite
Verifies all 8 critical anti-circularity criteria.
"""

import os
import sys

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import unittest
import numpy as np
import pandas as pd
from src.data.generate_synthetic import generate_dataset
from src.data.validation import run_sanity_tests

class TestAntiCircularity(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Generate a test dataset of 5,000 events
        cls.df_obs, cls.df_oracle = generate_dataset("configs/synthetic_config.yaml", num_events=5000)
        cls.test_results = run_sanity_tests(cls.df_obs, cls.df_oracle)

    def test_criterion_1_and_2_logging_policy_independence(self):
        """Questions 1 & 2: Action assignment is randomized/epsilon-greedy and does not know optimal action."""
        self.assertTrue(self.test_results["test1_action_overlap"]["pass"])
        self.assertTrue(self.test_results["test2_no_deterministic_rule"]["pass"])

    def test_criterion_3_baseline_blindness(self):
        """Question 3: Baseline does NOT have access to hidden recovery function."""
        # Verify baseline EV is substantially lower than Oracle EV
        self.assertTrue(self.test_results["test5_baseline_limited"]["pass"])

    def test_criterion_4_no_oracle_leakage(self):
        """Question 4: ML model receives ZERO oracle variables."""
        self.assertTrue(self.test_results["test9_no_feature_leakage"]["pass"])

    def test_criterion_5_action_overlap_in_context(self):
        """Question 5: Multiple actions observed for similar context segments."""
        self.assertTrue(self.test_results["test1_action_overlap"]["pass"])

    def test_criterion_6_probabilistic_outcomes(self):
        """Question 6: Recovery outcomes are probabilistic, not deterministic 0/1 rule."""
        self.assertTrue(self.test_results["test3_outcome_stochasticity"]["pass"])

    def test_criterion_7_oracle_beats_baseline(self):
        """Question 7: Oracle policy outperforms baseline policy due to hidden contextual interactions."""
        self.assertTrue(self.test_results["test6_oracle_sanity"]["pass"])

    def test_criterion_8_ml_learnability(self):
        """Question 8: Simple ML model can learn interactions from observed actions/outcomes."""
        self.assertTrue(self.test_results["test7_ml_learnability"]["pass"])

if __name__ == "__main__":
    unittest.main()
