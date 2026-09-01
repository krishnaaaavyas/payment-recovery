"""
Policy Advisor Module
Implements PolicyAdvisor decision engine combining Safety Gate, RecoveryPredictor, and Economics.
Formulates EV-maximizing recommendation with confidence levels.
"""

import os
import sys
import yaml
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from src.data.safety import evaluate_safety_gate
from src.data.economics import calculate_ev, get_action_cost, get_downside_penalty, get_friction_cost
from src.models.recovery_predictor import RecoveryPredictor

class PolicyAdvisor:
    """
    Economic Recovery Advisor for payment failure episodes.
    a* = argmax_{a in A_safe(X)} EV(a | X)
    """

    def __init__(self, predictor: RecoveryPredictor, config_path: str = "configs/synthetic_config.yaml"):
        self.predictor = predictor
        with open(config_path, "r") as f:
            self.cfg = yaml.safe_load(f)
        self.econ_cfg = self.cfg.get("economics", {})

    def evaluate_context(self, context: Dict[str, Any]) -> Tuple[str, float, float, List[Dict[str, Any]], List[str], str]:
        """
        Evaluates a single failure context dict X.
        Returns (recommended_action, expected_p_rec, expected_ev, alternatives_list, safety_constraints, confidence).
        """
        # 1. Safety Gate
        safe_actions, constraints = evaluate_safety_gate(context)
        
        # Format context into single-row DataFrame for predictor
        df_ctx = pd.DataFrame([context])
        
        # 2. Model Predictions for all safe actions
        probs_dict = self.predictor.predict_proba_all_actions(df_ctx, safe_actions)
        
        amount = float(context.get("amount", 1000.0))
        
        # 3. Calculate EV for each safe action
        ev_dict = {}
        prob_dict = {}
        for a in safe_actions:
            p_a = float(probs_dict[a][0])
            ev_a = calculate_ev(action=a, p_recovery=p_a, amount=amount, context=context, config_econ=self.econ_cfg)
            ev_dict[a] = ev_a
            prob_dict[a] = p_a
            
        # Sort actions by EV descending
        sorted_actions = sorted(safe_actions, key=lambda a: ev_dict[a], reverse=True)
        recommended_action = sorted_actions[0]
        rec_ev = ev_dict[recommended_action]
        rec_p = prob_dict[recommended_action]
        
        # Alternatives list
        alternatives = []
        for a in sorted_actions[1:]:
            alternatives.append({
                "action": a,
                "probability": prob_dict[a],
                "expected_value": ev_dict[a],
                "action_cost": get_action_cost(a, self.econ_cfg),
                "friction_cost": get_friction_cost(a, self.econ_cfg)
            })
            
        # Confidence calculation
        if len(sorted_actions) == 1:
            confidence = "high"
        else:
            second_best_ev = ev_dict[sorted_actions[1]]
            ev_margin = rec_ev - second_best_ev
            
            if ev_margin > 50.0 and (rec_p > 0.40 or recommended_action == "do_nothing"):
                confidence = "high"
            elif ev_margin >= 10.0:
                confidence = "medium"
            else:
                confidence = "low"
                
        return recommended_action, rec_p, rec_ev, alternatives, constraints, confidence

    def recommend(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returns structured JSON-serializable recommendation.
        """
        rec_action, rec_p, rec_ev, alternatives, constraints, confidence = self.evaluate_context(context)
        
        return {
            "event_id": context.get("event_id", ""),
            "recommended_action": rec_action,
            "expected_recovery_probability": rec_p,
            "expected_value": rec_ev,
            "confidence": confidence,
            "safety_constraints_applied": constraints,
            "alternatives": alternatives,
            "breakdown": {
                "order_amount": float(context.get("amount", 0.0)),
                "direct_action_cost": get_action_cost(rec_action, self.econ_cfg),
                "downside_penalty": get_downside_penalty(context, rec_action, self.econ_cfg),
                "friction_cost": get_friction_cost(rec_action, self.econ_cfg)
            }
        }
