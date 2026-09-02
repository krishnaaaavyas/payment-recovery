"""
Safety Gate Module
Evaluates failure context X and returns allowed safe actions A_safe(X) and applied constraint tags.
"""

from typing import Dict, List, Tuple, Any
from src.data.failure_taxonomy import FAILURE_TAXONOMY, ALL_ACTIONS

# Closed vocabulary of failure categories this Safety Gate is specified for.
# Anything outside it is unrecognized and must fail CLOSED (Rule 0).
SUPPORTED_FAILURE_CATEGORIES = frozenset(FAILURE_TAXONOMY.keys())


def _is_valid_retry_count(value: Any) -> bool:
    """
    True only for a well-formed, non-negative, integral attempt count.

    Rejects NaN (which would silently bypass the retry cap because every NaN
    comparison is False), None and strings (which would raise), negatives, and
    non-integral floats. numpy integer/float scalars are accepted when integral,
    since the generator and evaluation frames supply those.
    """
    if isinstance(value, str) or value is None:
        return False
    try:
        as_int = int(value)
    except (TypeError, ValueError, OverflowError):   # None, NaN, +/-inf, non-numeric
        return False
    if as_int < 0:
        return False
    try:
        return bool(as_int == value)         # rejects 3.9; accepts 3.0 and np.int64(3)
    except Exception:
        return False

def evaluate_safety_gate(context: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """
    Returns (safe_actions, constraints_applied).

    Fail-closed contract: an action is permitted only if a rule below explicitly
    permits it for a RECOGNIZED failure category. Any category outside
    SUPPORTED_FAILURE_CATEGORIES — including case variants, whitespace-padded
    values, and novel strings — collapses the action set to ["do_nothing"].

    This is a default-deny gate. Previously it was a deny-list with no terminal
    branch, so an unrecognized category fell through to the full five-action set
    with an empty constraint list (TASK_16A audit, finding C-2).
    """
    cat = context.get("failure_category", "")
    retry_count = context.get("retry_count_before_event", 0)

    constraints_applied = []

    # Rule 0: DEFAULT DENY — unrecognized / malformed failure category.
    # No normalization is attempted on purpose: silently coercing "HARD_DECLINE" or
    # " hard_decline " to a known category would mask an upstream integration fault.
    # The gate blocks; the API layer rejects such values outright with HTTP 422.
    # Non-string values (None, numbers, lists) are unrecognized by definition and must
    # not raise on the membership test - an exception here would be a fail-open path if
    # any caller were to swallow it.
    if not isinstance(cat, str) or cat not in SUPPORTED_FAILURE_CATEGORIES:
        constraints_applied.append("HARD_SAFETY_UNKNOWN_FAILURE_CATEGORY")
        return ["do_nothing"], constraints_applied

    # Rule 1: Non-retryable / Fraud / Hard Decline / Blocked Instrument
    if cat in ["hard_decline", "blocked_instrument", "velocity_limit"]:
        constraints_applied.append(f"HARD_SAFETY_NON_RETRYABLE_{cat.upper()}")
        return ["do_nothing"], constraints_applied
    
    # Rule 2a: DEFAULT DENY - malformed attempt count.
    # Rule 2b below is a numeric comparison, and a malformed value silently defeats it:
    # NaN makes every comparison False so the cap is bypassed entirely, while a str or
    # None raises TypeError. Neither may be allowed to widen the action set, so any
    # value that is not a well-formed non-negative integer fails closed
    # (TASK_16C audit, finding NEW-3).
    if isinstance(retry_count, bool) or not _is_valid_retry_count(retry_count):
        constraints_applied.append("HARD_SAFETY_INVALID_RETRY_COUNT")
        return ["do_nothing"], constraints_applied

    retry_count = int(retry_count)

    # Rule 2b: Retry Count Cap Exceeded (Max 3 retries)
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
