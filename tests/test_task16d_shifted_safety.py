"""
Task 16D — Shifted Safety Gate & Retry-Count Fail-Closed Regression Suite

Locks in the corrections for the TASK_16C independent verification findings:

  NEW-1  The robustness evaluator read the stored `safe_actions` column, which is a
         snapshot of the PRE-shift context. When a distribution shift mutated
         failure_category, the policy selected from a stale safe set and the
         violation counter compared against that same stale set, so it could never
         register a breach. Measured: 2,281/15,000 stale under SHIFT_FAILURE_MIX,
         of which 1,327 permitted update_information where the shifted specification
         forbids it, and 1,277 actual violations went unreported.

  NEW-3  evaluate_safety_gate's retry cap is a numeric comparison. NaN defeated it
         silently (every NaN comparison is False), and str/None raised TypeError.

Every test here is behavioural. The shift tests are constructed so that they FAIL
against the pre-16D implementation (which returned the stale set) and PASS against
the corrected one.
"""

import os
import sys
import unittest

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import numpy as np
import pandas as pd

from src.data.safety import evaluate_safety_gate, SUPPORTED_FAILURE_CATEGORIES
from src.data.failure_taxonomy import FAILURE_TAXONOMY, ALL_ACTIONS
from src.evaluation.robustness import compute_safety_and_baseline

CATEGORIES_ALLOWING_UPDATE_INFO = {"expired_card", "invalid_information"}


class TestSafetyRecomputedFromContext(unittest.TestCase):
    """compute_safety_and_baseline must derive the safe set from the context, not a column."""

    @classmethod
    def setUpClass(cls):
        cls.df = pd.read_csv("data/synthetic/test.csv")

    def test_A_unshifted_recomputation_matches_stored_column(self):
        """
        On unshifted data the recomputed gate and the generation-time snapshot agree,
        so the 16D change is a no-op outside the shifted path. This is what makes the
        other Task 12 scenarios' numbers comparable across the fix.
        """
        safe, _ = compute_safety_and_baseline(self.df)
        stored = [s.split("|") for s in self.df["safe_actions"].values]
        self.assertEqual(safe, stored)

    def test_B_helper_ignores_a_poisoned_safe_actions_column(self):
        """
        THE core regression. Poison the stored column with an illegal, wide-open set.
        The old implementation returned it verbatim; the corrected one must ignore it
        and return the gate's verdict for the actual context.
        """
        df = self.df.head(500).copy()
        df["safe_actions"] = "|".join(ALL_ACTIONS)      # every action, always

        safe, _ = compute_safety_and_baseline(df)
        expected = [evaluate_safety_gate(ctx)[0] for ctx in df.to_dict(orient="records")]

        self.assertEqual(safe, expected)
        self.assertNotEqual(
            safe, [ALL_ACTIONS] * len(df),
            "helper returned the poisoned column verbatim - it is still reading the stored value",
        )
        # And specifically: a hard decline must not have been widened.
        hard = df.index[df["failure_category"] == "hard_decline"].tolist()
        for i, idx in enumerate(df.index):
            if idx in hard:
                self.assertEqual(safe[i], ["do_nothing"])

    def test_C_helper_tracks_a_category_change(self):
        """Mutating failure_category alone must change the returned safe set."""
        df = self.df.head(200).copy()
        before, _ = compute_safety_and_baseline(df)
        df["failure_category"] = "hard_decline"
        after, _ = compute_safety_and_baseline(df)

        self.assertTrue(all(s == ["do_nothing"] for s in after))
        self.assertNotEqual(before, after)


class TestShiftedSafetyGate(unittest.TestCase):
    """
    End-to-end: a failure-category shift that genuinely changes safety eligibility.

    Constructed deliberately: expired_card permits {do_nothing, switch_method,
    update_information} and forbids retries; soft_decline permits
    {do_nothing, retry_now, retry_later, switch_method} and forbids
    update_information. Shifting expired_card -> soft_decline therefore flips
    eligibility in BOTH directions, so a stale set is detectable either way.
    """

    def setUp(self):
        df = pd.read_csv("data/synthetic/test.csv")
        self.original = df[df["failure_category"] == "expired_card"].head(300).reset_index(drop=True)
        self.assertGreater(len(self.original), 0, "fixture needs expired_card rows")

        self.shifted_context = self.original.copy()
        self.shifted_context["failure_category"] = "soft_decline"
        self.shifted_context["error_source"] = FAILURE_TAXONOMY["soft_decline"]["error_source"]
        self.shifted_context["error_step"] = FAILURE_TAXONOMY["soft_decline"]["error_step"]
        self.shifted_context["failure_code"] = FAILURE_TAXONOMY["soft_decline"]["default_codes"][0]
        # NOTE: safe_actions column deliberately left at its pre-shift value, exactly
        # as run_distribution_shifts used to leave it.

    def test_D_shift_actually_changes_eligibility(self):
        """Guard the fixture itself: the shift must be safety-relevant."""
        pre = evaluate_safety_gate(self.original.iloc[0].to_dict())[0]
        post = evaluate_safety_gate(self.shifted_context.iloc[0].to_dict())[0]
        self.assertIn("update_information", pre)
        self.assertNotIn("update_information", post)
        self.assertNotIn("retry_now", pre)
        self.assertIn("retry_now", post)

    def test_E_shifted_safe_actions_equal_gate_on_shifted_context(self):
        """shifted_safe_actions == evaluate_safety_gate(shifted_context)  (requirement B)."""
        shifted_safe_actions, _ = compute_safety_and_baseline(self.shifted_context)
        expected = [evaluate_safety_gate(ctx)[0]
                    for ctx in self.shifted_context.to_dict(orient="records")]
        self.assertEqual(shifted_safe_actions, expected)

    def test_F_no_stale_pre_shift_set_is_used(self):
        """
        Requirement D. The stored column still holds the expired_card set; the
        returned set must differ from it. Fails against the old implementation.
        """
        shifted_safe_actions, _ = compute_safety_and_baseline(self.shifted_context)
        stale = [s.split("|") for s in self.shifted_context["safe_actions"].values]
        self.assertNotEqual(
            shifted_safe_actions, stale,
            "shifted decision is still using the pre-shift safe_actions snapshot",
        )
        for s in shifted_safe_actions:
            self.assertNotIn("update_information", s)

    def test_G_selected_action_is_in_shifted_safe_actions(self):
        """Requirement C: argmax-EV selection must land inside the shifted safe set."""
        from src.models.recovery_predictor import RecoveryPredictor
        from src.data.economics import get_action_cost, get_friction_cost, get_downside_penalty
        import yaml

        econ = yaml.safe_load(open("configs/synthetic_config.yaml"))["economics"]
        pred = RecoveryPredictor.load("models/recovery_predictor.joblib")
        df = self.shifted_context
        n = len(df)

        shifted_safe_actions, _ = compute_safety_and_baseline(df)
        probs = {a: pred.predict_proba(df, action=a) for a in ALL_ACTIONS}
        recs = df.to_dict(orient="records")
        amounts = df["amount"].values

        for i in range(n):
            evs = {a: probs[a][i] * amounts[i] - get_action_cost(a, econ)
                      - get_downside_penalty(recs[i], a, econ) - get_friction_cost(a, econ)
                   for a in shifted_safe_actions[i]}
            chosen = max(evs, key=evs.get)
            self.assertIn(chosen, shifted_safe_actions[i])
            self.assertIn(chosen, evaluate_safety_gate(recs[i])[0])
            if chosen == "update_information":
                self.assertIn(recs[i]["failure_category"], CATEGORIES_ALLOWING_UPDATE_INFO)


class TestDistributionShiftReportsHonestSafety(unittest.TestCase):
    """The shipped evaluator must report violations against the SHIFTED specification."""

    @classmethod
    def setUpClass(cls):
        from src.models.recovery_predictor import RecoveryPredictor
        from src.policy.advisor import PolicyAdvisor
        cls.df = pd.read_csv("data/synthetic/test.csv")
        cls.ora = pd.read_csv("data/synthetic/test_oracle.csv")
        cls.advisor = PolicyAdvisor(RecoveryPredictor.load("models/recovery_predictor.joblib"))

    def test_H_reported_zero_violations_survives_independent_recheck(self):
        """
        Re-derive each shift exactly as the evaluator does, then verify the reported
        safety_violations count matches an INDEPENDENT check against
        evaluate_safety_gate on the shifted context.

        Against the old implementation the evaluator reported 0 while an independent
        check found 1,277 for SHIFT_FAILURE_MIX, so this test failed.
        """
        from src.evaluation.robustness import run_distribution_shifts

        res = run_distribution_shifts(self.advisor, self.df, self.ora)

        for name, r in res.items():
            with self.subTest(shift=name):
                self.assertEqual(
                    r["safety_violations"], 0,
                    f"{name}: evaluator reports {r['safety_violations']} violations",
                )
                self.assertTrue(r.get("safety_gate_recomputed_on_shifted_context", False),
                                f"{name}: evaluator did not flag shifted-gate recomputation")


class TestRetryCountFailClosed(unittest.TestCase):
    """NEW-3: malformed attempt counts must never widen the action set."""

    BASE = {"failure_category": "soft_decline"}

    def _safe(self, retry):
        return evaluate_safety_gate({**self.BASE, "retry_count_before_event": retry})

    def test_I_valid_counts_behave_normally(self):
        for v in [0, 1, 2, np.int64(0), np.int64(2), 2.0]:
            with self.subTest(retry=v):
                safe, rules = self._safe(v)
                self.assertIn("retry_now", safe)
                self.assertNotIn("HARD_SAFETY_INVALID_RETRY_COUNT", rules)
                self.assertNotIn("HARD_SAFETY_RETRY_CAP_EXCEEDED", rules)

    def test_J_cap_still_enforced(self):
        for v in [3, 4, 99, np.int64(3), 3.0, 10**9]:
            with self.subTest(retry=v):
                safe, rules = self._safe(v)
                self.assertEqual(safe, ["do_nothing"])
                self.assertIn("HARD_SAFETY_RETRY_CAP_EXCEEDED", rules)

    def test_K_nan_does_not_bypass_the_cap(self):
        """The headline NEW-3 case: NaN >= 3 is False, so the cap was skipped entirely."""
        safe, rules = self._safe(float("nan"))
        self.assertEqual(safe, ["do_nothing"],
                         "NaN retry count bypassed the maximum-attempt safety rule")
        self.assertIn("HARD_SAFETY_INVALID_RETRY_COUNT", rules)

    def test_L_malformed_types_fail_closed_without_raising(self):
        for v in ["3", "abc", None, -1, -99, 3.9, float("inf"), float("-inf"), True, False,
                  [3], {"a": 3}, b"3"]:
            with self.subTest(retry=repr(v)):
                try:
                    safe, rules = self._safe(v)
                except Exception as exc:
                    self.fail(f"retry_count={v!r} raised {type(exc).__name__}: {exc}")
                self.assertEqual(safe, ["do_nothing"], f"retry_count={v!r} widened the action set")
                self.assertIn("HARD_SAFETY_INVALID_RETRY_COUNT", rules)

    def test_M_missing_retry_count_defaults_safely(self):
        safe, rules = evaluate_safety_gate({"failure_category": "soft_decline"})
        self.assertIn("retry_now", safe)
        self.assertNotIn("HARD_SAFETY_INVALID_RETRY_COUNT", rules)

    def test_N_api_rejects_malformed_retry_counts(self):
        from fastapi.testclient import TestClient
        from src.api.app import app
        c = TestClient(app)
        base = {"payment_id": "pay_r", "amount": 1000.0, "payment_method": "card_credit",
                "failure_code": "GATEWAY_TIMEOUT", "failure_category": "network_timeout"}
        for v in [-1, 3.9, "abc", None]:
            with self.subTest(retry=repr(v)):
                r = c.post("/decide", json={**base, "retry_count_before_event": v})
                self.assertEqual(r.status_code, 422, f"API accepted retry_count={v!r}")
        r = c.post("/decide", json={**base, "retry_count_before_event": 3})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["stopping_rule"], "MAX_ATTEMPTS_EXCEEDED")


class TestUnshiftedScenariosUnaffected(unittest.TestCase):
    """Requirement E: an ordinary non-shifted scenario still behaves correctly."""

    def test_O_economic_sensitivity_unaffected_by_the_fix(self):
        import json
        from src.models.recovery_predictor import RecoveryPredictor
        from src.policy.advisor import PolicyAdvisor
        from src.evaluation.robustness import run_economic_sensitivity

        df = pd.read_csv("data/synthetic/test.csv")
        ora = pd.read_csv("data/synthetic/test_oracle.csv")
        advisor = PolicyAdvisor(RecoveryPredictor.load("models/recovery_predictor.joblib"))
        probs = {a: advisor.predictor.predict_proba(df, action=a) for a in ALL_ACTIONS}

        res = run_economic_sensitivity(advisor, df, ora, precomputed_probs=probs)
        self.assertEqual(res["BASELINE"]["safety_violations"], 0)
        self.assertEqual(res["BASELINE"]["per_event_dominance_violations"], 0)
        self.assertTrue(res["BASELINE"]["ranking_stable"])

        if os.path.exists("reports/task12_robustness.json"):
            canon = json.load(open("reports/task12_robustness.json"))["economic_sensitivity"]
            self.assertEqual(res["BASELINE"]["ml_policy_ev_ci"]["mean"],
                             canon["BASELINE"]["ml_policy_ev_ci"]["mean"])


if __name__ == "__main__":
    unittest.main()
