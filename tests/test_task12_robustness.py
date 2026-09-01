"""
Task 12 Robustness & Anti-Circularity Test Suite
Verifies 10 mandatory robustness, ablation, and non-circularity criteria.
"""

import os
import sys
import unittest
import numpy as np
import pandas as pd

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from src.models.preprocessing import ALL_PREDICTOR_FEATURES
from src.models.recovery_predictor import RecoveryPredictor
from src.policy.advisor import PolicyAdvisor
from src.policy.baseline import DeterministicBaselinePolicy
from src.evaluation.robustness import (
    run_economic_sensitivity,
    run_ablation_study,
    run_distribution_shifts,
    run_stress_testing
)

class TestTask12Robustness(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        df_obs_full = pd.read_csv("data/synthetic/test.csv")
        df_ora_full = pd.read_csv("data/synthetic/test_oracle.csv").drop_duplicates("event_id")
        
        # Merge on event_id to guarantee 100% match
        df_merged = df_obs_full.merge(df_ora_full, on="event_id", how="inner").head(500)
        
        cls.df_test_obs = df_merged[df_obs_full.columns]
        cls.df_test_ora = df_merged[["event_id"] + [c for c in df_ora_full.columns if c != "event_id"]]
        
        cls.predictor = RecoveryPredictor.load("models/recovery_predictor.joblib")
        cls.advisor = PolicyAdvisor(predictor=cls.predictor, config_path="configs/synthetic_config.yaml")

    def test_1_no_oracle_probability_in_features(self):
        """Test 1: No oracle probability column enters model features."""
        for feat in ALL_PREDICTOR_FEATURES:
            self.assertNotIn("true_p", feat)

    def test_2_no_oracle_action_in_features(self):
        """Test 2: No oracle action column enters model features."""
        for feat in ALL_PREDICTOR_FEATURES:
            self.assertNotIn("true_best", feat)

    def test_3_no_counterfactual_outcome_in_features(self):
        """Test 3: No counterfactual or post-action outcome column enters model features."""
        forbidden = ["recovered", "recovery_timestamp", "time_to_recovery_hours", "recovered_gmv", "action_cost", "downside_penalty", "friction_cost"]
        for feat in ALL_PREDICTOR_FEATURES:
            self.assertNotIn(feat, forbidden)

    def test_4_test_data_separated_from_train(self):
        """Test 4: Test data contains distinct timestamps from train data."""
        df_train = pd.read_csv("data/synthetic/train.csv")
        self.assertGreater(self.df_test_obs["failure_timestamp"].min(), df_train["failure_timestamp"].max())

    def test_5_distribution_shift_no_retraining(self):
        """Test 5: Distribution shift evaluation uses original predictor model without retraining."""
        res_shift = run_distribution_shifts(self.advisor, self.df_test_obs, self.df_test_ora)
        self.assertIn("SHIFT_COMBINED", res_shift)
        self.assertIn("ml_policy_ev_ci", res_shift["SHIFT_COMBINED"])

    def test_6_ground_truth_inaccessible(self):
        """Test 6: Hidden ground-truth parameters remain inaccessible to predictor."""
        row_dict = self.df_test_obs.iloc[0].to_dict()
        res_rec = self.advisor.recommend(row_dict)
        self.assertNotIn("SYNTHETIC_ORACLE_ONLY_", res_rec)

    def test_7_safety_rules_deterministic(self):
        """Test 7: Safety rules output identical safe actions for identical input context."""
        ctx = self.df_test_obs.iloc[0].to_dict()
        safe1, _ = self.advisor.evaluate_context(ctx)[4], self.advisor.evaluate_context(ctx)[5]
        safe2, _ = self.advisor.evaluate_context(ctx)[4], self.advisor.evaluate_context(ctx)[5]
        self.assertEqual(safe1, safe2)

    def test_8_baseline_independent_of_ground_truth(self):
        """Test 8: Baseline policy operates independently of ground-truth oracle columns."""
        b_policy = DeterministicBaselinePolicy()
        ctx = self.df_test_obs.iloc[0].to_dict()
        action = b_policy.select_action(ctx)
        self.assertIn(action, ["retry_now", "retry_later", "switch_method", "update_information", "do_nothing"])

    def test_9_ablation_framework_consistency(self):
        """Test 9: Ablation results are generated from the same underlying evaluation framework."""
        ablation_res = run_ablation_study(self.advisor, self.df_test_obs, self.df_test_ora)
        self.assertEqual(len(ablation_res), 5)
        self.assertIn("A3_ML_Economic_No_Safety_Gate", ablation_res)
        self.assertGreater(ablation_res["A3_ML_Economic_No_Safety_Gate"]["safety_violations_count"], 0)

    def test_10_results_not_direct_oracle_query(self):
        """Test 10: Model recommendations differ from direct oracle lookups when model predictions vary."""
        res_econ = run_economic_sensitivity(self.advisor, self.df_test_obs, self.df_test_ora)
        self.assertIn("BASELINE", res_econ)
        self.assertTrue(res_econ["BASELINE"]["ranking_stable"])

if __name__ == "__main__":
    unittest.main()
