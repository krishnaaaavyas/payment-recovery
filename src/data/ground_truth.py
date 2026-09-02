"""
Ground Truth Recovery Engine
Implements hidden non-linear recovery probability function P(recovery | X, action).
Includes non-obvious contextual interactions that a simple rules baseline cannot access.
"""

import numpy as np
from scipy.special import expit  # Sigmoid function
from typing import Dict, Any, Tuple

def compute_true_recovery_probability(
    context: Dict[str, Any],
    action: str,
    interaction_scale: float = 1.0
) -> float:
    """
    Computes hidden ground-truth p_true = P(recovery | X, action) using a logit model.

    interaction_scale multiplies the five HIDDEN CONTEXTUAL INTERACTION terms
    (PSU night maintenance, cross-border corridor, UPI peak-hour, high-amount
    friction, stale-info alignment) while leaving the base action logit, the
    failure-category effect, retry decay and the customer-history signal untouched.

    scale = 1.0 reproduces the environment the dataset was generated under and is
    the default, so ordinary callers are unaffected. Other values are used only by
    the Task 12 ground-truth robustness experiment, which asks whether the policy's
    advantage depends on the strength of the interactions it was trained to exploit.
    """
    cat = context.get("failure_category", "")
    payment_method = context.get("payment_method", "")
    issuer_cat = context.get("issuer_category", "")
    hour = context.get("hour", 12)
    corridor = context.get("corridor", "domestic_in")
    amount = context.get("amount", 1000.0)
    retry_count = context.get("retry_count_before_event", 0)
    hist_success_rate = context.get("historical_success_rate", 0.70)
    
    # 1. Base action logit
    base_logits = {
        "retry_now": -0.5,
        "retry_later": -0.2,
        "switch_method": 0.1,
        "update_information": 0.2,
        "do_nothing": -6.0  # do_nothing practically never recovers on its own (~0.2% random organic success)
    }
    logit = base_logits.get(action, -1.0)
    
    # 2. Failure category base effect
    cat_effects = {
        "hard_decline": -5.0,
        "blocked_instrument": -5.0,
        "velocity_limit": -3.0,
        "expired_card": -2.0,
        "invalid_information": -1.5,
        "soft_decline": 0.8,
        "insufficient_funds": -0.5,
        "issuer_unavailable": 0.5,
        "bank_unavailable": 0.4,
        "network_timeout": 0.9,
        "authentication_failure": 0.0,
        "upi_timeout": 0.7,
        "upi_decline": -0.3
    }
    logit += cat_effects.get(cat, 0.0)

    # Interaction terms accumulate separately so they can be scaled as a group.
    interaction_logit = 0.0

    # 3. HIDDEN INTERACTION 1: PSU Bank Night Maintenance (23:00 - 04:00)
    # Baseline doesn't know PSU banks perform batch processing at night.
    # retry_now fails miserably; retry_later (next morning) or switch_method succeeds.
    is_night = (hour >= 23 or hour <= 4)
    if issuer_cat == "psu_bank" and is_night:
        if action == "retry_now":
            interaction_logit -= 2.5
        elif action in ["retry_later", "switch_method"]:
            interaction_logit += 1.5
            
    # 4. HIDDEN INTERACTION 2: Cross-Border Card Corridor
    # International payments have high 3DS friction & risk checks.
    if corridor.startswith("cross_border"):
        if action == "retry_now":
            interaction_logit -= 1.2
        elif action in ["switch_method", "update_information"]:
            interaction_logit += 1.0
            
    # 5. HIDDEN INTERACTION 3: UPI Peak-Hour Timeout (18:00 - 21:00)
    # During evening peak hours, NPCI queue fills up. retry_now causes cascade timeout.
    # switch_method (to Card or Netbanking) or retry_later recovers well.
    is_peak = (18 <= hour <= 21)
    if payment_method.startswith("upi") and cat in ["upi_timeout", "network_timeout"] and is_peak:
        if action == "retry_now":
            interaction_logit -= 1.8
        elif action in ["retry_later", "switch_method"]:
            interaction_logit += 1.4
            
    # 6. HIDDEN INTERACTION 4: High Amount (> ₹10,000) Friction & Verification
    # High value payments need explicit user updates or method switch, simple retries fail due to balance/limits.
    if amount > 10000.0:
        if action in ["update_information", "switch_method"]:
            interaction_logit += 0.8
        elif action == "retry_now":
            interaction_logit -= 0.6
            
    # 7. HIDDEN INTERACTION 5: Stale Info alignment
    if cat in ["expired_card", "invalid_information"]:
        if action == "update_information":
            interaction_logit += 3.0
        elif action == "switch_method":
            interaction_logit += 2.0
        else:
            interaction_logit -= 3.0
            
    # Apply the interaction scale as a group (1.0 = the generated environment).
    logit += interaction_scale * interaction_logit

    # 8. Retry Decay: Each previous retry reduces recovery chance
    logit -= 0.4 * retry_count
    
    # 9. Customer History Signal
    logit += 1.2 * (hist_success_rate - 0.5)
    
    # Convert logit to probability
    p_true = float(expit(logit))
    
    # Cap boundaries for realistic noise (never 0.0 or 1.0)
    p_true = max(0.001, min(0.95, p_true))
    return round(p_true, 4)


def sample_recovery_outcome(
    p_true: float,
    action: str,
    amount: float,
    rng: np.random.RandomState = None
) -> Tuple[int, float, float]:
    """
    Samples probabilistic outcome.
    Returns (recovered (0 or 1), time_to_recovery_hours, recovered_gmv).
    """
    if rng is None:
        rng = np.random.RandomState()
        
    recovered = int(rng.binomial(1, p_true))
    
    if recovered == 1:
        recovered_gmv = amount
        # Sample realistic recovery time in hours (within 72h window)
        if action == "retry_now":
            time_hours = rng.exponential(scale=0.2)  # avg 12 mins
        elif action == "retry_later":
            time_hours = rng.uniform(2.0, 24.0)     # 2 to 24 hours
        elif action == "switch_method":
            time_hours = rng.exponential(scale=0.5)  # avg 30 mins
        elif action == "update_information":
            time_hours = rng.uniform(1.0, 48.0)     # customer response time
        else:
            time_hours = rng.uniform(0.1, 72.0)
            
        time_to_recovery_hours = round(min(72.0, max(0.01, float(time_hours))), 2)
    else:
        recovered_gmv = 0.0
        time_to_recovery_hours = -1.0  # Not recovered
        
    return recovered, time_to_recovery_hours, recovered_gmv
