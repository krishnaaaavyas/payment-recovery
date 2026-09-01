"""
Task 13A FastAPI REST API Unit Test Suite
Tests /health, /decide, /execute, and /audit/{decision_id} endpoints using starlette/httpx TestClient.
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


class TestTask13API(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        audit_store.clear()

    def test_health_endpoint(self):
        """Test 1: GET /health returns HTTP 200 and status ok."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["service"], "payment-recovery-advisor")

    def test_decide_malformed_input(self):
        """Test 2: POST /decide returns HTTP 422 on missing required amount field."""
        bad_payload = {
            "payment_id": "pay_bad_001",
            "payment_method": "card_credit",
            "failure_code": "TIMED_OUT",
            "failure_category": "network_timeout"
        }
        response = self.client.post("/decide", json=bad_payload)
        self.assertEqual(response.status_code, 422)

    def test_decide_valid_payment_event(self):
        """Test 3: POST /decide returns structured decision response."""
        payload = {
            "payment_id": "pay_valid_123",
            "amount": 3500.0,
            "currency": "INR",
            "payment_method": "card_credit",
            "failure_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
            "failure_category": "network_timeout",
            "retry_count_before_event": 0
        }
        response = self.client.post("/decide", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("decision_id", data)
        self.assertEqual(data["payment_id"], "pay_valid_123")
        self.assertIn(data["action"], ["retry_now", "retry_later", "switch_method", "update_information", "do_nothing"])
        self.assertGreaterEqual(data["recovery_probability"], 0.0)
        self.assertIsInstance(data["expected_value"], float)

    def test_execute_and_audit_flow(self):
        """Test 4 & 5: POST /decide -> POST /execute -> GET /audit/{id} end-to-end integration."""
        # 1. Decide
        payload = {
            "payment_id": "pay_flow_999",
            "amount": 1500.0,
            "currency": "INR",
            "payment_method": "card_credit",
            "failure_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
            "failure_category": "network_timeout",
            "retry_count_before_event": 0
        }
        dec_resp = self.client.post("/decide", json=payload)
        self.assertEqual(dec_resp.status_code, 200)
        dec_data = dec_resp.json()
        dec_id = dec_data["decision_id"]
        act = dec_data["action"]

        # 2. Execute
        exec_payload = {
            "decision_id": dec_id,
            "payment_id": "pay_flow_999",
            "action": act
        }
        exec_resp = self.client.post("/execute", json=exec_payload)
        self.assertIn(exec_resp.status_code, [200, 400])

        # 3. Audit
        audit_resp = self.client.get(f"/audit/{dec_id}")
        self.assertEqual(audit_resp.status_code, 200)
        audit_data = audit_resp.json()
        self.assertEqual(audit_data["decision_id"], dec_id)
        self.assertEqual(audit_data["payment_id"], "pay_flow_999")

    def test_audit_not_found(self):
        """Test 6: GET /audit/{missing_id} returns HTTP 404."""
        response = self.client.get("/audit/dec_non_existent_999")
        self.assertEqual(response.status_code, 404)

if __name__ == "__main__":
    unittest.main()
