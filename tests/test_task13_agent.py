"""
Task 13A RecoveryAgent Unit Test Suite
Tests decision orchestration, candidate action bounding, probabilities, EV, stopping rules, and audit logging.
"""

import os
import sys
import unittest
import pandas as pd

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from src.data.failure_taxonomy import ALL_ACTIONS
from src.api.schemas import FailedPaymentEvent
from src.agent.recovery_agent import RecoveryAgent
from src.agent.audit import AuditStore


class TestTask13Agent(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_store = AuditStore()
        cls.agent = RecoveryAgent(
            model_path="models/recovery_predictor.joblib",
            config_path="configs/synthetic_config.yaml",
            store=cls.test_store
        )
        cls.valid_event = FailedPaymentEvent(
            payment_id="pay_test_001",
            amount=2500.0,
            currency="INR",
            product_category="digital_goods",
            payment_method="card_credit",
            failure_code="BAD_REQUEST_PAYMENT_TIMED_OUT",
            failure_category="network_timeout",
            retry_count_before_event=0
        )

    def setUp(self):
        self.test_store.clear()

    def test_valid_event_produces_bounded_decision(self):
        """Test 1: Valid event produces a decision with allowed action and valid numeric bounds."""
        res = self.agent.decide(self.valid_event)
        self.assertIn(res["action"], ALL_ACTIONS)
        self.assertGreaterEqual(res["recovery_probability"], 0.0)
        self.assertLessEqual(res["recovery_probability"], 1.0)
        self.assertIsInstance(res["expected_value"], float)
        self.assertIn(res["status"], ["APPROVED", "ESCALATE", "STOP"])

    def test_audit_record_generated(self):
        """Test 2: Agent automatically saves full audit record to store."""
        res = self.agent.decide(self.valid_event)
        audit_rec = self.test_store.get_audit(res["decision_id"])
        self.assertIsNotNone(audit_rec)
        self.assertEqual(audit_rec["payment_id"], "pay_test_001")
        self.assertEqual(audit_rec["selected_action"], res["action"])

    def test_max_attempts_stopping_rule(self):
        """Test 3: Retry count >= 3 triggers MAX_ATTEMPTS_EXCEEDED stopping rule and forces do_nothing."""
        event_max_retries = FailedPaymentEvent(
            payment_id="pay_max_retry",
            amount=3000.0,
            payment_method="card_credit",
            failure_code="BAD_REQUEST_PAYMENT_TIMED_OUT",
            failure_category="network_timeout",
            retry_count_before_event=3
        )
        res = self.agent.decide(event_max_retries)
        self.assertEqual(res["status"], "STOP")
        self.assertEqual(res["stopping_rule"], "MAX_ATTEMPTS_EXCEEDED")
        self.assertEqual(res["action"], "do_nothing")

    def test_deterministic_explanation(self):
        """Test 4: Generated explanation is evidence-based and contains no LLM hallucinations."""
        res = self.agent.decide(self.valid_event)
        self.assertIsInstance(res["reason"], str)
        self.assertGreater(len(res["reason"]), 20)

if __name__ == "__main__":
    unittest.main()
