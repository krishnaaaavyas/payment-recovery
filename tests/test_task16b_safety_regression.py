"""
Task 16B — Safety Gate, API Validation & Executor Regression Suite

Locks in the corrections for the TASK_16A independent audit findings:

  C-2  Safety Gate failed OPEN on unrecognized failure categories, so a mislabelled
       fraud decline could be approved for a customer-facing intervention.
  M-5  The simulated executor accepted replays and never bound an execution request
       to the payment the decision was issued for.

These tests are written to fail if the fail-closed behaviour is ever relaxed.
"""

import os
import sys
import unittest

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from fastapi.testclient import TestClient

from src.api.app import app
from src.api.schemas import FailedPaymentEvent
from src.agent.audit import AuditStore, audit_store
from src.agent.executor import SimulatedRecoveryExecutor
from src.agent.recovery_agent import RecoveryAgent
from src.data.failure_taxonomy import FAILURE_TAXONOMY, ALL_ACTIONS
from src.data.safety import evaluate_safety_gate, SUPPORTED_FAILURE_CATEGORIES


# Categories where the safety specification explicitly PERMITS update_information.
# Everything else must never receive it.
CATEGORIES_ALLOWING_UPDATE_INFO = {"expired_card", "invalid_information"}

MALFORMED_CATEGORIES = [
    "HARD_DECLINE",
    "Hard_Decline",
    " hard_decline ",
    "hard_decline\n",
    "hard-decline",
    "unknown_category",
    "chargeback_fraud_confirmed",
    "'; DROP TABLE payments;--",
    "",
    "soft_decline ",
    "SOFT_DECLINE",
]


class TestSafetyGateSupportedCategories(unittest.TestCase):
    """Every supported category must behave exactly as the safety specification states."""

    def test_all_taxonomy_categories_are_supported(self):
        self.assertEqual(set(FAILURE_TAXONOMY.keys()), set(SUPPORTED_FAILURE_CATEGORIES))
        self.assertEqual(len(SUPPORTED_FAILURE_CATEGORIES), 13)

    def test_every_supported_category_returns_nonempty_subset_of_action_space(self):
        for cat in sorted(SUPPORTED_FAILURE_CATEGORIES):
            with self.subTest(category=cat):
                safe, _ = evaluate_safety_gate({"failure_category": cat, "retry_count_before_event": 0})
                self.assertGreater(len(safe), 0, f"{cat}: safe action set is empty")
                self.assertTrue(set(safe).issubset(set(ALL_ACTIONS)), f"{cat}: produced an action outside the bounded space")
                self.assertIn("do_nothing", safe, f"{cat}: do_nothing must always remain available")

    def test_non_retryable_categories_collapse_to_do_nothing(self):
        for cat in ["hard_decline", "blocked_instrument", "velocity_limit"]:
            with self.subTest(category=cat):
                safe, rules = evaluate_safety_gate({"failure_category": cat, "retry_count_before_event": 0})
                self.assertEqual(safe, ["do_nothing"])
                self.assertIn(f"HARD_SAFETY_NON_RETRYABLE_{cat.upper()}", rules)

    def test_technical_failures_never_allow_update_information(self):
        technical = [
            "upi_decline", "upi_timeout", "soft_decline", "insufficient_funds",
            "issuer_unavailable", "bank_unavailable", "network_timeout", "authentication_failure",
        ]
        for cat in technical:
            with self.subTest(category=cat):
                safe, rules = evaluate_safety_gate({"failure_category": cat, "retry_count_before_event": 0})
                self.assertNotIn("update_information", safe)
                self.assertIn("EXCLUDE_UPDATE_INFO_ON_TECHNICAL_FAILURES", rules)

    def test_stale_info_categories_exclude_blind_retries(self):
        for cat in ["expired_card", "invalid_information"]:
            with self.subTest(category=cat):
                safe, rules = evaluate_safety_gate({"failure_category": cat, "retry_count_before_event": 0})
                self.assertNotIn("retry_now", safe)
                self.assertNotIn("retry_later", safe)
                self.assertIn("update_information", safe)
                self.assertIn("RESTRICT_STALE_INFO_ACTIONS", rules)

    def test_retry_cap_collapses_to_do_nothing_for_every_category(self):
        for cat in sorted(SUPPORTED_FAILURE_CATEGORIES):
            with self.subTest(category=cat):
                safe, rules = evaluate_safety_gate({"failure_category": cat, "retry_count_before_event": 3})
                self.assertEqual(safe, ["do_nothing"])

    def test_update_information_only_ever_offered_where_specification_allows(self):
        """The core anti-fail-open invariant, stated positively."""
        for cat in sorted(SUPPORTED_FAILURE_CATEGORIES):
            safe, _ = evaluate_safety_gate({"failure_category": cat, "retry_count_before_event": 0})
            if "update_information" in safe:
                self.assertIn(
                    cat, CATEGORIES_ALLOWING_UPDATE_INFO,
                    f"{cat}: update_information offered but the safety specification does not allow it",
                )


class TestSafetyGateFailsClosed(unittest.TestCase):
    """Unknown or malformed categories must never widen the action set."""

    def test_unknown_categories_collapse_to_do_nothing(self):
        for cat in MALFORMED_CATEGORIES:
            with self.subTest(category=repr(cat)):
                safe, rules = evaluate_safety_gate({"failure_category": cat, "retry_count_before_event": 0})
                self.assertEqual(
                    safe, ["do_nothing"],
                    f"{cat!r} did not fail closed; got {safe}",
                )
                self.assertIn("HARD_SAFETY_UNKNOWN_FAILURE_CATEGORY", rules)

    def test_unknown_category_never_yields_update_information(self):
        for cat in MALFORMED_CATEGORIES:
            with self.subTest(category=repr(cat)):
                safe, _ = evaluate_safety_gate({"failure_category": cat, "retry_count_before_event": 0})
                self.assertNotIn("update_information", safe)

    def test_missing_category_key_fails_closed(self):
        safe, rules = evaluate_safety_gate({"retry_count_before_event": 0})
        self.assertEqual(safe, ["do_nothing"])
        self.assertIn("HARD_SAFETY_UNKNOWN_FAILURE_CATEGORY", rules)

    def test_non_string_category_fails_closed(self):
        for bad in [None, 123, 4.5, True, ["hard_decline"]]:
            with self.subTest(value=repr(bad)):
                safe, rules = evaluate_safety_gate({"failure_category": bad, "retry_count_before_event": 0})
                self.assertEqual(safe, ["do_nothing"])
                self.assertIn("HARD_SAFETY_UNKNOWN_FAILURE_CATEGORY", rules)


class TestAgentLevelSafetyIndependentOfAPI(unittest.TestCase):
    """
    Requirement: the domain layer must stay fail-closed even if API validation is
    bypassed. These call RecoveryAgent.decide() directly, constructing the event
    object without going through HTTP request validation.
    """

    @classmethod
    def setUpClass(cls):
        cls.store = AuditStore()
        cls.agent = RecoveryAgent(
            model_path="models/recovery_predictor.joblib",
            config_path="configs/synthetic_config.yaml",
            store=cls.store,
        )

    def setUp(self):
        self.store.clear()

    def _event(self, **overrides):
        base = dict(
            payment_id="pay_safety_probe",
            amount=50000.0,
            payment_method="card_credit",
            failure_code="CARD_STOLEN",
            failure_category="hard_decline",
            retry_count_before_event=0,
        )
        base.update(overrides)
        return FailedPaymentEvent(**base)

    def test_agent_blocks_unknown_category_even_when_validation_bypassed(self):
        for cat in ["HARD_DECLINE", " hard_decline ", "unknown_category"]:
            with self.subTest(category=repr(cat)):
                event = self._event()
                # Bypass Pydantic validation the way a mis-wired internal caller would.
                object.__setattr__(event, "failure_category", cat)
                decision = self.agent.decide(event)
                self.assertEqual(
                    decision["action"], "do_nothing",
                    f"{cat!r} produced action {decision['action']}",
                )
                self.assertNotEqual(decision["action"], "update_information")
                self.assertIn("HARD_SAFETY_UNKNOWN_FAILURE_CATEGORY", decision["safety_rule"])

    def test_agent_still_serves_valid_categories(self):
        decision = self.agent.decide(self._event(
            failure_category="network_timeout",
            failure_code="GATEWAY_TIMEOUT",
            amount=8000.0,
        ))
        self.assertIn(decision["action"], ALL_ACTIONS)
        self.assertIn(decision["status"], ["APPROVED", "ESCALATE", "STOP"])
        self.assertNotEqual(decision["action"], "update_information")

    def test_agent_hard_decline_still_blocked(self):
        decision = self.agent.decide(self._event())
        self.assertEqual(decision["action"], "do_nothing")


class TestAPISchemaValidation(unittest.TestCase):
    """Unsupported enum values must be rejected with HTTP 422, not scored silently."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        audit_store.clear()

    def _payload(self, **overrides):
        base = {
            "payment_id": "pay_schema_probe",
            "amount": 5000.0,
            "payment_method": "card_credit",
            "failure_code": "GATEWAY_TIMEOUT",
            "failure_category": "network_timeout",
            "retry_count_before_event": 0,
        }
        base.update(overrides)
        return base

    def test_valid_payload_accepted(self):
        r = self.client.post("/decide", json=self._payload())
        self.assertEqual(r.status_code, 200, r.text)

    def test_malformed_failure_category_rejected_422(self):
        for cat in MALFORMED_CATEGORIES:
            with self.subTest(category=repr(cat)):
                r = self.client.post("/decide", json=self._payload(failure_category=cat))
                self.assertEqual(r.status_code, 422, f"{cat!r} was accepted: {r.text[:200]}")

    def test_unknown_payment_method_rejected_422(self):
        r = self.client.post("/decide", json=self._payload(payment_method="crypto_wallet"))
        self.assertEqual(r.status_code, 422)

    def test_unknown_corridor_rejected_422(self):
        r = self.client.post("/decide", json=self._payload(corridor="domestic"))
        self.assertEqual(r.status_code, 422)

    def test_unknown_failure_code_rejected_422(self):
        r = self.client.post("/decide", json=self._payload(failure_code="TOTALLY_MADE_UP"))
        self.assertEqual(r.status_code, 422)

    def test_schema_defaults_are_recognized_by_the_fitted_encoder(self):
        """
        A request that relies on schema defaults must be scored on a fully recognized
        feature vector.

        The invariant checked is the one that actually matters: each categorical
        column's one-hot block must be non-zero after transformation. OneHotEncoder is
        configured with handle_unknown="ignore", so an out-of-vocabulary value is not
        an error - it becomes an all-zero block and the request is scored on a silently
        degraded vector. Asserting on the encoder rather than on string equality also
        avoids a false positive on is_subscription, where the API's int 0/1 and the
        training data's bool False/True are distinct strings but the same category.
        """
        import numpy as np
        import pandas as pd
        from src.models.recovery_predictor import RecoveryPredictor
        from src.models.preprocessing import prepare_feature_dataframe, CATEGORICAL_FEATURES

        predictor = RecoveryPredictor.load("models/recovery_predictor.joblib")
        event = FailedPaymentEvent(**self._payload())
        ctx = event.model_dump()

        df_ctx = prepare_feature_dataframe(
            pd.DataFrame([{**ctx, "action": "retry_now"}]), action_col="action"
        )

        cat_encoder = predictor.pipeline.named_transformers_["cat"]
        cat_cols = CATEGORICAL_FEATURES + ["action"]
        encoded = cat_encoder.transform(df_ctx[cat_cols])

        offset = 0
        for col, cats in zip(cat_cols, cat_encoder.categories_):
            width = len(cats)
            block = np.asarray(encoded)[0, offset:offset + width]
            offset += width
            with self.subTest(field=col):
                self.assertEqual(
                    block.sum(), 1.0,
                    f"value {ctx.get(col, 'retry_now')!r} for '{col}' was not recognized by the "
                    f"fitted encoder (all-zero one-hot block); known categories: {list(cats)[:6]}",
                )

    def test_defaulted_enum_fields_serialize_as_plain_strings(self):
        """
        Regression: without validate_default=True, Pydantic skips validation of unset
        fields, so use_enum_values never runs on them and a defaulted field leaks an
        Enum member ("CurrencyEnum.INR") into the feature vector and the audit record.
        """
        ctx = FailedPaymentEvent(**self._payload()).model_dump()
        for field in ["currency", "product_category", "order_value_tier", "issuer_category",
                      "card_network", "error_source", "error_step", "corridor",
                      "merchant_segment", "merchant_category", "payment_method", "failure_category"]:
            with self.subTest(field=field):
                self.assertIs(type(ctx[field]), str, f"'{field}' is {type(ctx[field]).__name__}, not a plain str")
                self.assertNotIn("Enum", str(ctx[field]))

    def test_every_supported_category_accepted_by_api(self):
        for cat in sorted(SUPPORTED_FAILURE_CATEGORIES):
            code = FAILURE_TAXONOMY[cat]["default_codes"][0]
            with self.subTest(category=cat):
                r = self.client.post("/decide", json=self._payload(failure_category=cat, failure_code=code))
                self.assertEqual(r.status_code, 200, f"{cat} rejected: {r.text[:200]}")
                data = r.json()
                if data["action"] == "update_information":
                    self.assertIn(cat, CATEGORIES_ALLOWING_UPDATE_INFO,
                                  f"{cat}: API returned update_information but the specification forbids it")


class TestExecutorBindingAndReplay(unittest.TestCase):
    """Executor must bind to the decision's payment and authorise a single execution."""

    def setUp(self):
        self.store = AuditStore()
        self.executor = SimulatedRecoveryExecutor(store=self.store)
        self.decision_id = "dec_bind_001"
        self.store.save_audit(self.decision_id, {
            "decision_id": self.decision_id,
            "payment_id": "pay_owner_123",
            "selected_action": "retry_now",
            "safe_actions": ["retry_now", "retry_later", "do_nothing"],
            "status": "APPROVED",
            "stopping_rule": None,
            "execution_status": "pending",
        })

    def test_mismatched_payment_id_rejected(self):
        ok, res = self.executor.execute(self.decision_id, "pay_SOMEONE_ELSE", "retry_now")
        self.assertFalse(ok)
        self.assertEqual(res["status"], "rejected")
        self.assertIn("does not match", res["message"])
        # And the decision must remain executable by its rightful owner.
        self.assertEqual(self.store.get_audit(self.decision_id)["execution_status"], "pending")

    def test_matching_payment_id_executes(self):
        ok, res = self.executor.execute(self.decision_id, "pay_owner_123", "retry_now")
        self.assertTrue(ok)
        self.assertEqual(res["status"], "executed")

    def test_replay_rejected(self):
        ok1, _ = self.executor.execute(self.decision_id, "pay_owner_123", "retry_now")
        self.assertTrue(ok1)
        for attempt in range(2, 5):
            ok, res = self.executor.execute(self.decision_id, "pay_owner_123", "retry_now")
            with self.subTest(attempt=attempt):
                self.assertFalse(ok, f"replay attempt {attempt} was permitted")
                self.assertEqual(res["status"], "rejected")
                self.assertIn("already been", res["message"])

    def test_replay_rejected_via_api(self):
        client = TestClient(app)
        audit_store.clear()
        payload = {
            "payment_id": "pay_replay_probe",
            "amount": 20000.0,
            "payment_method": "card_credit",
            "failure_code": "GATEWAY_TIMEOUT",
            "failure_category": "network_timeout",
            "retry_count_before_event": 0,
        }
        dec = client.post("/decide", json=payload)
        self.assertEqual(dec.status_code, 200, dec.text)
        d = dec.json()
        if not d["execution_available"]:
            self.skipTest("decision was not APPROVED; replay path not applicable")

        body = {"decision_id": d["decision_id"], "payment_id": "pay_replay_probe", "action": d["action"]}
        first = client.post("/execute", json=body)
        self.assertEqual(first.status_code, 200, first.text)
        second = client.post("/execute", json=body)
        self.assertEqual(second.status_code, 400, "replay through the API was permitted")

    def test_spoofed_payment_id_rejected_via_api(self):
        client = TestClient(app)
        audit_store.clear()
        payload = {
            "payment_id": "pay_owner_api",
            "amount": 20000.0,
            "payment_method": "card_credit",
            "failure_code": "GATEWAY_TIMEOUT",
            "failure_category": "network_timeout",
            "retry_count_before_event": 0,
        }
        d = client.post("/decide", json=payload).json()
        r = client.post("/execute", json={
            "decision_id": d["decision_id"],
            "payment_id": "pay_attacker",
            "action": d["action"],
        })
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
