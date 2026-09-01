"""
Baseline Policy Module
Implements competent deterministic decline-code baseline policy.
"""

from typing import Dict, List, Any
from src.data.safety import evaluate_safety_gate

class DeterministicBaselinePolicy:
    """
    Deterministic rules baseline based on failure-code semantics.
    Respects hard safety gate.
    """

    def select_action(self, context: Dict[str, Any]) -> str:
        safe_actions, _ = evaluate_safety_gate(context)
        
        if "do_nothing" in safe_actions and len(safe_actions) == 1:
            return "do_nothing"
            
        cat = context.get("failure_category", "")
        
        if cat in ["expired_card", "invalid_information"]:
            return "update_information" if "update_information" in safe_actions else safe_actions[0]
        elif cat in ["upi_decline"]:
            return "switch_method" if "switch_method" in safe_actions else safe_actions[0]
        elif cat in ["insufficient_funds", "issuer_unavailable", "bank_unavailable", "velocity_limit"]:
            return "retry_later" if "retry_later" in safe_actions else safe_actions[0]
        elif cat in ["soft_decline", "network_timeout", "authentication_failure", "upi_timeout"]:
            return "retry_now" if "retry_now" in safe_actions else safe_actions[0]
        else:
            return "do_nothing" if "do_nothing" in safe_actions else safe_actions[0]
