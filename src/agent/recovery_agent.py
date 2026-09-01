"""
Bounded Recovery Decision Agent Module
Orchestrates Input Validation, Safety Gate, RecoveryPredictor, Economic Valuation, PolicyAdvisor,
Stopping Rules, Explanation Generation, and Audit Record creation.
"""

import uuid
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional

from src.data.failure_taxonomy import ALL_ACTIONS
from src.data.safety import evaluate_safety_gate
from src.data.economics import calculate_ev
from src.models.recovery_predictor import RecoveryPredictor
from src.policy.advisor import PolicyAdvisor
from src.agent.audit import audit_store
from src.api.schemas import FailedPaymentEvent


class RecoveryAgent:
    """Bounded economic recovery decision agent."""

    def __init__(
        self,
        advisor: Optional[PolicyAdvisor] = None,
        model_path: str = "models/recovery_predictor.joblib",
        config_path: str = "configs/synthetic_config.yaml",
        store=audit_store
    ):
        if advisor is not None:
            self.advisor = advisor
        else:
            predictor = RecoveryPredictor.load(model_path)
            self.advisor = PolicyAdvisor(predictor=predictor, config_path=config_path)
            
        self.store = store

    def generate_explanation(
        self,
        action: str,
        probability: float,
        ev: float,
        safe_actions: list,
        status: str,
        stopping_rule: Optional[str]
    ) -> str:
        """Generates a deterministic, evidence-based decision explanation string."""
        if status == "STOP":
            if stopping_rule == "MAX_ATTEMPTS_EXCEEDED":
                return (
                    f"Action forced to 'do_nothing' because retry attempt cap (>= 3 attempts) was reached. "
                    f"Safety Gate restricts further retries to prevent customer friction and gateway penalties."
                )
            elif stopping_rule == "NON_POSITIVE_EV":
                return (
                    f"Action forced to 'do_nothing' because candidate recovery actions yielded non-positive "
                    f"Expected Economic Value (EV = INR {ev:.2f}) under the synthetic economic valuation model."
                )
            elif stopping_rule == "UNSAFE_ACTION":
                return (
                    f"Action forced to 'do_nothing' because candidate action '{action}' violated "
                    f"Safety Gate compliance constraints."
                )
            else:
                return f"Decision stopped under rule '{stopping_rule}'."

        elif status == "ESCALATE":
            return (
                f"Action '{action}' recommended with estimated recovery probability P={probability:.4f} "
                f"and expected value EV=INR {ev:.2f}, but status set to ESCALATE due to low model confidence."
            )

        else:  # APPROVED
            safe_str = ", ".join(safe_actions)
            return (
                f"'{action}' was selected because its estimated recovery probability (P={probability:.4f}) "
                f"and net Expected Economic Value (EV=INR {ev:.2f}) maximize economic return among safe "
                f"candidate interventions [{safe_str}] under synthetic environment evaluation."
            )

    def decide(self, event: FailedPaymentEvent) -> Dict[str, Any]:
        """
        Orchestrates full decision lifecycle for a failed payment event episode.
        Returns decision dictionary matching RecoveryDecisionResponse schema.
        """
        ctx = event.model_dump()
        decision_id = f"dec_{uuid.uuid4().hex[:8]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        
        # 1. Evaluate Safety Gate
        safe_actions, safety_rule_desc = evaluate_safety_gate(ctx)
        
        # 2. Invoke PolicyAdvisor decision layer
        rec_act, prob, rec_ev, alternatives, constraints, conf = self.advisor.evaluate_context(ctx)
        
        # Build complete prob_dict and ev_dict for ALL_ACTIONS for audit logging
        df_ctx = pd.DataFrame([ctx])
        probs_all = self.advisor.predictor.predict_proba_all_actions(df_ctx, ALL_ACTIONS)
        amount = float(ctx.get("amount", 1000.0))
        
        prob_dict = {}
        ev_dict = {}
        for a in ALL_ACTIONS:
            p_a = float(probs_all[a][0])
            ev_a = calculate_ev(action=a, p_recovery=p_a, amount=amount, context=ctx, config_econ=self.advisor.econ_cfg)
            prob_dict[a] = p_a
            ev_dict[a] = ev_a
        
        # 3. Apply Stopping Rules & Status Determination
        status = "APPROVED"
        stopping_rule = None
        
        # Stopping Rule 1: Max attempt cap exceeded
        if ctx.get("retry_count_before_event", 0) >= 3:
            status = "STOP"
            stopping_rule = "MAX_ATTEMPTS_EXCEEDED"
            rec_act = "do_nothing"
            rec_ev = ev_dict.get("do_nothing", 0.0)
            prob = prob_dict.get("do_nothing", 0.0)

        # Stopping Rule 2: Unsafe action selected
        elif rec_act not in safe_actions:
            status = "STOP"
            stopping_rule = "UNSAFE_ACTION"
            rec_act = "do_nothing"
            rec_ev = ev_dict.get("do_nothing", 0.0)
            prob = prob_dict.get("do_nothing", 0.0)

        # Stopping Rule 3: Non-positive EV for non-do_nothing action
        elif rec_ev <= 0.0 and rec_act != "do_nothing":
            status = "STOP"
            stopping_rule = "NON_POSITIVE_EV"
            rec_act = "do_nothing"
            rec_ev = ev_dict.get("do_nothing", 0.0)
            prob = prob_dict.get("do_nothing", 0.0)

        # Escalation Rule: Low confidence
        elif conf == "low":
            status = "ESCALATE"
            stopping_rule = "LOW_CONFIDENCE"

        # 4. Generate Deterministic Explanation
        reason = self.generate_explanation(
            action=rec_act,
            probability=prob,
            ev=rec_ev,
            safe_actions=safe_actions,
            status=status,
            stopping_rule=stopping_rule
        )

        execution_available = (status == "APPROVED")

        safety_rule_str = ", ".join(safety_rule_desc) if isinstance(safety_rule_desc, list) else str(safety_rule_desc)

        # 5. Create Decision Response Dict
        decision_response = {
            "decision_id": decision_id,
            "payment_id": event.payment_id,
            "action": rec_act,
            "confidence": conf,
            "recovery_probability": float(np.round(prob, 4)),
            "expected_value": float(np.round(rec_ev, 2)),
            "safe": True if status != "STOP" or stopping_rule == "MAX_ATTEMPTS_EXCEEDED" else False,
            "safety_rule": safety_rule_str,
            "reason": reason,
            "status": status,
            "stopping_rule": stopping_rule,
            "timestamp": now_iso,
            "execution_available": execution_available
        }

        # 6. Save Complete Audit Record
        audit_record = {
            "decision_id": decision_id,
            "timestamp": now_iso,
            "payment_id": event.payment_id,
            "input_context": ctx,
            "candidate_actions": ALL_ACTIONS,
            "safe_actions": safe_actions,
            "predicted_probabilities": {a: float(np.round(p, 4)) for a, p in prob_dict.items()},
            "expected_values": {a: float(np.round(v, 2)) for a, v in ev_dict.items()},
            "selected_action": rec_act,
            "confidence": conf,
            "recovery_probability": float(np.round(prob, 4)),
            "expected_value": float(np.round(rec_ev, 2)),
            "safe": True if status != "STOP" or stopping_rule == "MAX_ATTEMPTS_EXCEEDED" else False,
            "safety_rule": safety_rule_str,
            "reason": reason,
            "status": status,
            "stopping_rule": stopping_rule,
            "execution_status": "pending"
        }
        self.store.save_audit(decision_id, audit_record)

        return decision_response
