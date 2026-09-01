"""
Policy Sanity & Unit Tests — Task 11
Verifies model predictions, safety enforcement, leakage safeguards, and IPS evaluation logic.
"""

import os
import sys
import unittest
import numpy as np
import pandas as pd

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from src.models.preprocessing import prepare_feature_dataframe, ALL_PREDICTOR_FEATURES
from src.models.recovery_predictor import RecoveryPredictor
from src.policy.advisor import PolicyAdvisor
from src.policy.baseline import DeterministicBaselinePolicy
from src.policy.evaluation import run_policy_evaluation

class TestTask11Policy(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.df_train = pd.read_csv("data/synthetic/train.csv").iloc[:2000]
        cls.df_val = pd.read_csv("data/synthetic/val.csv").iloc[:500]
        cls.df_test_obs = pd.read_csv("data/synthetic/test.csv").iloc[:500]
        cls.df_test_ora = pd.read_csv("data/synthetic/test_oracle.csv").iloc[:500]
        
        cls.predictor = RecoveryPredictor(model_type="hist_gb", calibrate=True)
        cls.predictor.fit(cls.df_train, cls.df_val)
        cls.advisor = PolicyAdvisor(predictor=cls.predictor, config_path="configs/synthetic_config.yaml")

    def test_1_probability_bounds(self):
        """Test 1: All predicted probabilities satisfy 0 <= p <= 1."""
        probs = self.predictor.predict_proba(self.df_test_obs, action="retry_now")
        self.assertTrue(np.all(probs >= 0.0))
        self.assertTrue(np.all(probs <= 1.0))

    def test_2_recommended_action_is_safe(self):
        """Test 2: Recommended action is always in A_safe(X)."""
        ctx = self.df_test_obs.iloc[0].to_dict()
        rec = self.advisor.recommend(ctx)
        safe_list = ctx["safe_actions"].split("|")
        self.assertIn(rec["recommended_action"], safe_list)

    def test_3_safety_gate_cannot_be_bypassed(self):
        """Test 3: Fraud/hard-block cases force do_nothing and cannot be bypassed."""
        ctx = self.df_test_obs.iloc[0].to_dict()
        ctx["failure_category"] = "hard_decline"
        rec = self.advisor.recommend(ctx)
        self.assertEqual(rec["recommended_action"], "do_nothing")
        self.assertIn("HARD_SAFETY_NON_RETRYABLE_HARD_DECLINE", rec["safety_constraints_applied"])

    def test_4_action_changes_prediction(self):
        """Test 4: Changing action changes prediction output."""
        row_df = self.df_test_obs.iloc[:1].copy()
        row_df["failure_category"] = "soft_decline"
        p_now = self.predictor.predict_proba(row_df, action="retry_now")[0]
        p_nothing = self.predictor.predict_proba(row_df, action="do_nothing")[0]
        self.assertNotEqual(p_now, p_nothing)

    def test_5_no_oracle_leakage_in_features(self):
        """Test 5: No oracle column enters model training features."""
        for feat in ALL_PREDICTOR_FEATURES:
            self.assertNotIn("ORACLE", feat)
            self.assertNotIn("true_", feat)

    def test_6_no_post_action_leakage_in_features(self):
        """Test 6: No post-action column enters model training features."""
        forbidden = ["recovered", "recovery_timestamp", "time_to_recovery_hours", "recovered_gmv", "action_cost", "downside_penalty", "friction_cost"]
        for feat in ALL_PREDICTOR_FEATURES:
            self.assertNotIn(feat, forbidden)

    def test_7_preprocessing_no_leakage(self):
        """Test 7: Feature preparation pipeline operates strictly on specified context features."""
        feat_df = prepare_feature_dataframe(self.df_test_obs, action_col="logged_action")
        self.assertEqual(len(feat_df.columns), len(ALL_PREDICTOR_FEATURES))

    def test_8_policy_can_select_do_nothing(self):
        """Test 8: Policy can naturally select do_nothing for non-retryable context."""
        ctx = self.df_test_obs.iloc[0].to_dict()
        ctx["retry_count_before_event"] = 3  # Retry cap exceeded
        rec = self.advisor.recommend(ctx)
        self.assertEqual(rec["recommended_action"], "do_nothing")

    def test_9_policy_evaluates_multiple_safe_actions(self):
        """Test 9: Policy evaluates multiple candidate safe actions rather than only logged action."""
        ctx = self.df_test_obs.iloc[0].to_dict()
        ctx["failure_category"] = "soft_decline"
        rec = self.advisor.recommend(ctx)
        self.assertGreaterEqual(len(rec["alternatives"]), 1)

    def test_10_ips_uses_logging_probability(self):
        """Test 10: IPS evaluation uses logging_probability from dataset."""
        eval_res = run_policy_evaluation(self.advisor, self.df_test_obs, self.df_test_ora)
        self.assertIn("ml_policy_ips_ev_inr", eval_res["off_policy_ips_evaluation"])
        self.assertGreater(eval_res["off_policy_ips_evaluation"]["ml_effective_sample_size"], 0)

if __name__ == "__main__":
    unittest.main()
