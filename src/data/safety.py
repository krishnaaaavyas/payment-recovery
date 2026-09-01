"""
Safety Gate Module
Evaluates failure context X and returns allowed safe actions A_safe(X) and applied constraint tags.
"""

from typing import Dict, List, Tuple, Any
from src.data.failure_taxonomy import ALL_ACTIONS

def evaluate_safety_gate(context: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """
    Returns (safe_actions, constraints_applied).
    Guarantees ML model or policy can NEVER choose an illegal action.
    """
    cat = context.get("failure_category", "")
    retry_count = context.get("retry_count_before_event", 0)
    
    constraints_applied = []
    
    # Rule 1: Non-retryable / Fraud / Hard Decline / Blocked Instrument
    if cat in ["hard_decline", "blocked_instrument", "velocity_limit"]:
        constraints_applied.append(f"HARD_SAFETY_NON_RETRYABLE_{cat.upper()}")
        return ["do_nothing"], constraints_applied
    
    # Rule 2: Retry Count Cap Exceeded (Max 3 retries)
    if retry_count >= 3:
        constraints_applied.append("HARD_SAFETY_RETRY_CAP_EXCEEDED")
        return ["do_nothing"], constraints_applied
    
    # Default: start with all actions
    safe = set(ALL_ACTIONS)
    
    # Rule 3: Expired Card / Invalid Info
    if cat in ["expired_card", "invalid_information"]:
        # Direct retries without updating info or switching method will fail; exclude retry_now & retry_later
        safe.discard("retry_now")
        safe.discard("retry_later")
        constraints_applied.append("RESTRICT_STALE_INFO_ACTIONS")
    
    # Rule 4: UPI / Auth decline - update_information is useless
    if cat in ["upi_decline", "upi_timeout", "soft_decline", "insufficient_funds", "issuer_unavailable", "bank_unavailable", "network_timeout", "authentication_failure"]:
        safe.discard("update_information")
        constraints_applied.append("EXCLUDE_UPDATE_INFO_ON_TECHNICAL_FAILURES")
        
    safe_list = sorted(list(safe))
    if not safe_list:
        safe_list = ["do_nothing"]
        
    return safe_list, constraints_applied
