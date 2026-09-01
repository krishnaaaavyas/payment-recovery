"""
Task 13A SimulatedRecoveryExecutor Unit Test Suite
Tests safety enforcement, rejection of unsafe/unknown/stopped actions, and simulation execution mapping.
"""

import os
import sys
import unittest

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from src.agent.executor import SimulatedRecoveryExecutor
from src.agent.audit import AuditStore


class TestTask13Executor(unittest.TestCase):

    def setUp(self):
        self.store = AuditStore()
        self.executor = SimulatedRecoveryExecutor(store=self.store)
        
        # Save a mock APPROVED audit record
        self.approved_dec_id = "dec_approved_123"
        self.store.save_audit(self.approved_dec_id, {
            "decision_id": self.approved_dec_id,
            "payment_id": "pay_test_999",
            "selected_action": "retry_now",
            "safe_actions": ["retry_now", "retry_later", "do_nothing"],
            "status": "APPROVED",
            "stopping_rule": None
        })

        # Save a mock STOPPED audit record
        self.stopped_dec_id = "dec_stopped_123"
        self.store.save_audit(self.stopped_dec_id, {
            "decision_id": self.stopped_dec_id,
            "payment_id": "pay_test_888",
            "selected_action": "do_nothing",
            "safe_actions": ["do_nothing"],
            "status": "STOP",
            "stopping_rule": "MAX_ATTEMPTS_EXCEEDED"
        })

        # Save a mock ESCALATED audit record
        self.escalated_dec_id = "dec_escalated_123"
        self.store.save_audit(self.escalated_dec_id, {
            "decision_id": self.escalated_dec_id,
            "payment_id": "pay_test_777",
            "selected_action": "retry_later",
            "safe_actions": ["retry_later", "do_nothing"],
            "status": "ESCALATE",
            "stopping_rule": "LOW_CONFIDENCE"
        })

    def test_valid_approved_action_executes(self):
        """Test 1: Valid approved action executes cleanly in simulation."""
        success, res = self.executor.execute(self.approved_dec_id, "pay_test_999", "retry_now")
        self.assertTrue(success)
        self.assertEqual(res["status"], "executed")
        self.assertIn("dispatched", res["message"])

    def test_unknown_action_rejected(self):
        """Test 2: Requesting an action different from approved action is rejected."""
        success, res = self.executor.execute(self.approved_dec_id, "pay_test_999", "switch_method")
        self.assertFalse(success)
        self.assertEqual(res["status"], "rejected")

    def test_stopped_decision_rejected(self):
        """Test 3: Stopped decision is rejected by executor."""
        success, res = self.executor.execute(self.stopped_dec_id, "pay_test_888", "do_nothing")
        self.assertFalse(success)
        self.assertEqual(res["status"], "stopped")

    def test_escalated_decision_rejected(self):
        """Test 4: Escalated decision is rejected by executor."""
        success, res = self.executor.execute(self.escalated_dec_id, "pay_test_777", "retry_later")
        self.assertFalse(success)
        self.assertEqual(res["status"], "escalated")

    def test_missing_decision_id_rejected(self):
        """Test 5: Non-existent decision ID is rejected."""
        success, res = self.executor.execute("dec_fake_999", "pay_fake", "retry_now")
        self.assertFalse(success)
        self.assertEqual(res["status"], "rejected")

if __name__ == "__main__":
    unittest.main()
