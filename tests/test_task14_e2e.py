"""
Task 14 End-to-End System Validation Test Suite
Rigorously validates the complete O1 pipeline:
Event Ingestion -> Input Validation -> Safety Gate -> RecoveryPredictor -> Economic Valuation ->
PolicyAdvisor -> RecoveryAgent -> API Layer -> Simulated Executor -> Audit Trail.
"""

import os
import sys
import unittest
from fastapi.testclient import TestClient

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from src.api.app import app
from src.agent.audit import audit_store
from src.data.failure_taxonomy import ALL_ACTIONS


class TestTask14E2EValidation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        audit_store.clear()

    def test_e2e_case1_approved_decision_flow(self):
        """Case 1: Normal Approved Decision lifecycle (Decide -> Execute -> Audit)."""
        payload = {
            "payment_id": "pay_e2e_001",
            "amount": 2500.0,
            "currency": "INR",
            "payment_method": "card_credit",
            "failure_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
            "failure_category": "network_timeout",
            "retry_count_before_event": 0
        }
        
        # 1. Decide
        dec_resp = self.client.post("/decide", json=payload)
        self.assertEqual(dec_resp.status_code, 200)
        dec_data = dec_resp.json()
        
        dec_id = dec_data["decision_id"]
        action = dec_data["action"]
        self.assertIn(action, ALL_ACTIONS)
        self.assertGreaterEqual(dec_data["recovery_probability"], 0.0)
        self.assertLessEqual(dec_data["recovery_probability"], 1.0)
        self.assertIsInstance(dec_data["expected_value"], float)
        self.assertEqual(dec_data["status"], "APPROVED")
        self.assertTrue(dec_data["execution_available"])

        # 2. Execute
        exec_payload = {
            "decision_id": dec_id,
            "payment_id": "pay_e2e_001",
            "action": action
        }
        exec_resp = self.client.post("/execute", json=exec_payload)
        self.assertEqual(exec_resp.status_code, 200)
        exec_data = exec_resp.json()
        self.assertIn(exec_data["status"], ["executed", "scheduled", "stopped"])

        # 3. Audit
        audit_resp = self.client.get(f"/audit/{dec_id}")
        self.assertEqual(audit_resp.status_code, 200)
        audit_data = audit_resp.json()
        self.assertEqual(audit_data["decision_id"], dec_id)
        self.assertEqual(audit_data["selected_action"], action)
        self.assertEqual(audit_data["execution_status"], exec_data["status"])

    def test_e2e_case2_max_attempts_stop_condition(self):
        """Case 2: Retry count >= 3 forces STOP condition and blocks execution."""
        payload = {
            "payment_id": "pay_e2e_max_attempts",
            "amount": 3500.0,
            "payment_method": "card_credit",
            "failure_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
            "failure_category": "network_timeout",
            "retry_count_before_event": 3
        }
        dec_resp = self.client.post("/decide", json=payload)
        self.assertEqual(dec_resp.status_code, 200)
        dec_data = dec_resp.json()

        self.assertEqual(dec_data["status"], "STOP")
        self.assertEqual(dec_data["stopping_rule"], "MAX_ATTEMPTS_EXCEEDED")
        self.assertEqual(dec_data["action"], "do_nothing")
        self.assertFalse(dec_data["execution_available"])

        # Attempt execution on stopped decision must be rejected (HTTP 400)
        exec_payload = {
            "decision_id": dec_data["decision_id"],
            "payment_id": "pay_e2e_max_attempts",
            "action": "do_nothing"
        }
        exec_resp = self.client.post("/execute", json=exec_payload)
        self.assertEqual(exec_resp.status_code, 400)

    def test_e2e_case3_safety_gate_blocking(self):
        """Case 3: Safety Gate excludes update_information on technical failures."""
        payload = {
            "payment_id": "pay_e2e_tech_fail",
            "amount": 1200.0,
            "payment_method": "upi_intent",
            "failure_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
            "failure_category": "network_timeout",
            "retry_count_before_event": 0
        }
        dec_resp = self.client.post("/decide", json=payload)
        self.assertEqual(dec_resp.status_code, 200)
        dec_data = dec_resp.json()

        # Action selected must not be update_information
        self.assertNotEqual(dec_data["action"], "update_information")
        self.assertIn("EXCLUDE_UPDATE_INFO_ON_TECHNICAL_FAILURES", dec_data["safety_rule"])

    def test_e2e_case4_executor_security_controls(self):
        """Case 4: Executor independently rejects unknown, unsafe, or unapproved actions."""
        # 1. Create valid approved decision
        payload = {
            "payment_id": "pay_e2e_sec_test",
            "amount": 1800.0,
            "payment_method": "card_credit",
            "failure_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
            "failure_category": "network_timeout",
            "retry_count_before_event": 0
        }
        dec_resp = self.client.post("/decide", json=payload)
        dec_id = dec_resp.json()["decision_id"]

        # Attempt 1: Execute unknown action string
        exec_unknown = self.client.post("/execute", json={
            "decision_id": dec_id,
            "payment_id": "pay_e2e_sec_test",
            "action": "hack_instant_refund"
        })
        self.assertEqual(exec_unknown.status_code, 400)

        # Attempt 2: Execute action different from approved action
        exec_mismatch = self.client.post("/execute", json={
            "decision_id": dec_id,
            "payment_id": "pay_e2e_sec_test",
            "action": "update_information"
        })
        self.assertEqual(exec_mismatch.status_code, 400)

    def test_e2e_case5_api_validation_error_handling(self):
        """Case 5: API schema validation correctly rejects malformed or invalid payloads (422)."""
        # Missing amount
        resp1 = self.client.post("/decide", json={"payment_id": "bad1"})
        self.assertEqual(resp1.status_code, 422)

        # Invalid non-existent decision audit lookup (404)
        resp2 = self.client.get("/audit/dec_fake_999999")
        self.assertEqual(resp2.status_code, 404)

    def test_e2e_case6_anti_leakage_assertion(self):
        """Case 6: Confirms zero oracle fields exist in decision response or audit record."""
        payload = {
            "payment_id": "pay_e2e_leakage_check",
            "amount": 2000.0,
            "payment_method": "card_credit",
            "failure_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
            "failure_category": "network_timeout"
        }
        dec_resp = self.client.post("/decide", json=payload)
        dec_data = dec_resp.json()
        
        # Verify no oracle fields exist in API response
        for key in dec_data.keys():
            self.assertNotIn("oracle", key.lower())
            self.assertNotIn("true_recovery", key.lower())

        # Verify no oracle fields exist in Audit record input_context
        audit_resp = self.client.get(f"/audit/{dec_data['decision_id']}")
        audit_data = audit_resp.json()
        ctx_keys = audit_data["input_context"].keys()
        for k in ctx_keys:
            self.assertNotIn("oracle", k.lower())
            self.assertNotIn("recovered", k.lower())

if __name__ == "__main__":
    unittest.main()
