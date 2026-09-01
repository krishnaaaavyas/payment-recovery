"""
Logging Policy Module
Simulates historical merchant action logging policy with epsilon-greedy exploration.
Guarantees positivity/overlap in observed actions.
"""

import numpy as np
from typing import Dict, List, Tuple, Any

def select_logged_action(
    context: Dict[str, Any],
    safe_actions: List[str],
    epsilon: float = 0.30,
    rng: np.random.RandomState = None
) -> Tuple[str, float]:
    """
    Returns (logged_action, logging_probability).
    70% follows a simple standard merchant heuristic.
    30% random uniform selection over safe_actions.
    """
    if rng is None:
        rng = np.random.RandomState()
        
    if not safe_actions:
        return "do_nothing", 1.0
    if len(safe_actions) == 1:
        return safe_actions[0], 1.0
        
    cat = context.get("failure_category", "")
    
    # Simple historical merchant heuristic
    if cat in ["soft_decline", "network_timeout"]:
        heuristic_action = "retry_now" if "retry_now" in safe_actions else safe_actions[0]
    elif cat in ["insufficient_funds", "issuer_unavailable", "bank_unavailable", "velocity_limit"]:
        heuristic_action = "retry_later" if "retry_later" in safe_actions else safe_actions[0]
    elif cat in ["expired_card", "invalid_information"]:
        heuristic_action = "update_information" if "update_information" in safe_actions else safe_actions[0]
    elif cat in ["upi_decline", "upi_timeout"]:
        heuristic_action = "switch_method" if "switch_method" in safe_actions else safe_actions[0]
    else:
        heuristic_action = "do_nothing" if "do_nothing" in safe_actions else safe_actions[0]
        
    # Epsilon-greedy selection
    K = len(safe_actions)
    prob_uniform = epsilon / K
    prob_heuristic = (1.0 - epsilon) + prob_uniform
    
    action_probs = {}
    for a in safe_actions:
        if a == heuristic_action:
            action_probs[a] = prob_heuristic
        else:
            action_probs[a] = prob_uniform
            
    # Normalize probabilities to sum exactly to 1.0
    total_p = sum(action_probs.values())
    p_vec = [action_probs[a] / total_p for a in safe_actions]
    
    chosen_action = rng.choice(safe_actions, p=p_vec)
    chosen_prob = action_probs[chosen_action] / total_p
    
    return chosen_action, round(chosen_prob, 4)
