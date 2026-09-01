"""
Unit tests for Synthetic Dataset Generator components.
"""

import os
import sys

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import unittest
import yaml
import numpy as np
import pandas as pd

from src.data.failure_taxonomy import FAILURE_TAXONOMY, ALL_ACTIONS
from src.data.safety import evaluate_safety_gate
from src.data.economics import calculate_ev, get_action_cost
from src.data.logging_policy import select_logged_action
from src.data.ground_truth import compute_true_recovery_probability, sample_recovery_outcome
from src.data.generate_synthetic import generate_dataset

class TestDatasetGenerator(unittest.TestCase):

    def test_safety_gate_fraud_hard_decline(self):
        ctx = {"failure_category": "hard_decline", "retry_count_before_event": 0}
        safe_actions, constraints = evaluate_safety_gate(ctx)
        self.assertEqual(safe_actions, ["do_nothing"])
        self.assertIn("HARD_SAFETY_NON_RETRYABLE_HARD_DECLINE", constraints)

    def test_safety_gate_retry_cap(self):
        ctx = {"failure_category": "soft_decline", "retry_count_before_event": 3}
        safe_actions, constraints = evaluate_safety_gate(ctx)
        self.assertEqual(safe_actions, ["do_nothing"])
        self.assertIn("HARD_SAFETY_RETRY_CAP_EXCEEDED", constraints)

    def test_safety_gate_expired_card(self):
        ctx = {"failure_category": "expired_card", "retry_count_before_event": 0}
        safe_actions, _ = evaluate_safety_gate(ctx)
        self.assertNotIn("retry_now", safe_actions)
        self.assertNotIn("retry_later", safe_actions)
        self.assertIn("update_information", safe_actions)

    def test_logging_policy_overlap(self):
        rng = np.random.RandomState(42)
        ctx = {"failure_category": "soft_decline"}
        safe_actions = ["retry_now", "retry_later", "switch_method", "do_nothing"]
        
        actions_chosen = set()
        for _ in range(100):
            action, prob = select_logged_action(ctx, safe_actions, epsilon=0.30, rng=rng)
            actions_chosen.add(action)
            self.assertGreater(prob, 0.0)
            
        self.assertTrue(len(actions_chosen) >= 3, "Logging policy must demonstrate action overlap")

    def test_ground_truth_prob_range(self):
        ctx = {
            "failure_category": "soft_decline",
            "payment_method": "card_credit",
            "issuer_category": "psu_bank",
            "hour": 3,
            "corridor": "domestic_in",
            "amount": 1000.0,
            "retry_count_before_event": 0,
            "historical_success_rate": 0.8
        }
        for a in ALL_ACTIONS:
            p = compute_true_recovery_probability(ctx, a)
            self.assertGreaterEqual(p, 0.001)
            self.assertLessEqual(p, 0.95)

    def test_economic_calculation(self):
        ev = calculate_ev(action="retry_now", p_recovery=0.5, amount=1000.0, context={"retry_count_before_event": 0})
        # EV = 0.5 * 1000 - 2.0 (cost) - 0 (downside) - 1.0 (friction) = 497.0
        self.assertEqual(ev, 497.0)

if __name__ == "__main__":
    unittest.main()
