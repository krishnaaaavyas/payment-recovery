"""
Economics Module
Models action costs C(a), downside penalties D(a), and friction costs F(a).
"""

from typing import Dict, Any, List

DEFAULT_DIRECT_COSTS = {
    "retry_now": 2.00,
    "retry_later": 3.00,
    "switch_method": 5.00,
    "update_information": 7.00,
    "do_nothing": 0.00
}

DEFAULT_FRICTION_COSTS = {
    "retry_now": 1.00,
    "retry_later": 2.00,
    "switch_method": 10.00,
    "update_information": 20.00,
    "do_nothing": 0.00
}

def get_action_cost(action: str, config_econ: Dict[str, Any] = None) -> float:
    costs = (config_econ or {}).get("direct_costs", DEFAULT_DIRECT_COSTS)
    return float(costs.get(action, 0.0))

def get_friction_cost(action: str, config_econ: Dict[str, Any] = None) -> float:
    frictions = (config_econ or {}).get("friction_costs", DEFAULT_FRICTION_COSTS)
    return float(frictions.get(action, 0.0))

def get_downside_penalty(context: Dict[str, Any], action: str, config_econ: Dict[str, Any] = None) -> float:
    penalty = 0.0
    retry_count = context.get("retry_count_before_event", 0)
    cat = context.get("failure_category", "")
    
    penalties_cfg = (config_econ or {}).get("downside_penalties", {})
    excessive_penalty = float(penalties_cfg.get("retry_excessive", 15.00))
    misaligned_penalty = float(penalties_cfg.get("misaligned_action", 5.00))
    
    # Penalty for repeated retries
    if retry_count >= 2 and action in ["retry_now", "retry_later"]:
        penalty += excessive_penalty
        
    # Penalty for prompting info update on non-info technical failures
    if action == "update_information" and cat not in ["expired_card", "invalid_information"]:
        penalty += misaligned_penalty
        
    return penalty

def calculate_ev(
    action: str,
    p_recovery: float,
    amount: float,
    context: Dict[str, Any],
    config_econ: Dict[str, Any] = None
) -> float:
    """
    EV(a | X) = P(recovery | X, a) * V - C(a) - D(a) - F(a)
    """
    c = get_action_cost(action, config_econ)
    f = get_friction_cost(action, config_econ)
    d = get_downside_penalty(context, action, config_econ)
    
    ev = (p_recovery * amount) - c - d - f
    return round(ev, 4)
