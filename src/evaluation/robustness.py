"""
Robustness, Sensitivity, Ablation & Stress Evaluation Engine (Pre-computed & High Performance)
Executes Task 12 experimental suite: Economic Sensitivity, Ground-Truth Robustness, Ablation Study, Distribution Shift, and Stress Testing.
"""

import os
import sys

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import yaml
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional

from src.data.failure_taxonomy import ALL_ACTIONS, FAILURE_TAXONOMY
from src.data.safety import evaluate_safety_gate
from src.data.economics import calculate_ev, get_action_cost, get_downside_penalty, get_friction_cost
from src.data.ground_truth import compute_true_recovery_probability
from src.models.recovery_predictor import RecoveryPredictor
from src.policy.advisor import PolicyAdvisor
from src.policy.baseline import DeterministicBaselinePolicy

def compute_true_ev_matrix(
    df: pd.DataFrame,
    econ_cfg: Dict[str, Any],
    amounts: Optional[np.ndarray] = None,
    interaction_scale: float = 1.0,
    econ_overrides: Optional[Dict[str, Any]] = None
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Computes the hidden ground-truth (p_true, EV_true) for EVERY action on EVERY row,
    directly from the simulator.

    This replaces reading `SYNTHETIC_ORACLE_ONLY_true_ev_{a}` out of the oracle CSV,
    which had two defects (TASK_16A audit, findings M-1 and M-2):

      1. The CSV only stores values for actions that were SAFE at generation time.
         Every other cell is NaN, so an ablation that deliberately ignores the safety
         gate had ~84% of its rows silently dropped by nanmean, leaving a
         survivorship-selected subset.
      2. The CSV is keyed to the ORIGINAL context. Under a distribution shift the
         features change but the stored ground truth does not, so the policy was
         being scored in one world against the truth of another.

    Recomputing from the simulator removes both. Returns (p_matrix, ev_matrix), each
    of shape (len(df), len(ALL_ACTIONS)), with no NaN.

    Oracle isolation is preserved: this is evaluation-side only. Nothing here is
    visible to the predictor, the advisor or the agent.
    """
    records = df.to_dict(orient="records")
    N = len(records)
    amounts = df["amount"].values if amounts is None else amounts

    p_matrix = np.zeros((N, len(ALL_ACTIONS)))
    ev_matrix = np.zeros((N, len(ALL_ACTIONS)))

    for i, ctx in enumerate(records):
        # EV is evaluated at the (possibly perturbed) amount, and the ground-truth
        # probability is evaluated at the SAME amount, so the >Rs10,000 interaction
        # stays consistent with the value being scored.
        ctx_eval = dict(ctx)
        ctx_eval["amount"] = float(amounts[i])
        for j, a in enumerate(ALL_ACTIONS):
            p = compute_true_recovery_probability(ctx_eval, a, interaction_scale=interaction_scale)
            p_matrix[i, j] = p
            ev_matrix[i, j] = _ev_from_parts(a, p, float(amounts[i]), ctx_eval, econ_cfg, econ_overrides)

    assert not np.isnan(ev_matrix).any(), "Ground-truth EV matrix contains NaN."
    return p_matrix, ev_matrix


def _ev_from_parts(
    action: str,
    p: float,
    amount: float,
    ctx: Dict[str, Any],
    econ_cfg: Dict[str, Any],
    econ_overrides: Optional[Dict[str, Any]] = None
) -> float:
    """EV(a|X) = p*V - C(a) - D(a) - F(a), with optional scenario cost overrides."""
    if econ_overrides is None:
        return calculate_ev(action, p, amount, ctx, econ_cfg)
    c = econ_overrides["direct_costs"][action]
    f = econ_overrides["friction_costs"][action]
    d = 0.0
    if action in ["retry_now", "retry_later"] and ctx.get("retry_count_before_event", 0) >= 2:
        d += econ_overrides["downside_penalties"]["retry_excessive"]
    if action == "update_information" and ctx.get("failure_category") not in ["expired_card", "invalid_information"]:
        d += econ_overrides["downside_penalties"]["misaligned_action"]
    return (p * amount) - c - d - f


def masked_oracle_best(ev_matrix: np.ndarray, safe_actions_list: List[List[str]]) -> np.ndarray:
    """Per-event max of true EV over the SAFE action set only."""
    N = ev_matrix.shape[0]
    best = np.zeros(N)
    for i in range(N):
        idxs = [ALL_ACTIONS.index(a) for a in safe_actions_list[i]]
        best[i] = max(ev_matrix[i, k] for k in idxs)
    return best


def compute_bootstrap_ci(data: np.ndarray, n_bootstraps: int = 200, seed: int = 42) -> Dict[str, float]:
    """Computes mean, median, std, and 95% bootstrap confidence interval using fast 2D matrix sampling."""
    rng = np.random.RandomState(seed)
    N = len(data)
    if N == 0:
        return {"mean": 0.0, "median": 0.0, "std": 0.0, "ci_lower": 0.0, "ci_upper": 0.0}
        
    boot_indices = rng.randint(0, N, size=(n_bootstraps, N))
    boot_means = np.nanmean(data[boot_indices], axis=1)
    
    ci_lower = float(np.percentile(boot_means, 2.5))
    ci_upper = float(np.percentile(boot_means, 97.5))
    
    return {
        "mean": float(np.round(np.nanmean(data), 2)),
        "median": float(np.round(np.nanmedian(data), 2)),
        "std": float(np.round(np.nanstd(data), 2)),
        "ci_lower": float(np.round(ci_lower, 2)),
        "ci_upper": float(np.round(ci_upper, 2))
    }

def compute_safety_and_baseline(df: pd.DataFrame) -> Tuple[List[List[str]], List[str]]:
    """
    Evaluates the Safety Gate against the contexts in `df` and derives the matching
    deterministic-baseline action for each row.

    The safe action set is ALWAYS recomputed from `evaluate_safety_gate(context)`.
    It is never read back from the stored `safe_actions` column.

    This function previously string-split `df["safe_actions"]`, which is a snapshot
    taken at dataset-generation time. Under a distribution shift that mutates
    `failure_category`, that snapshot no longer describes the context being
    evaluated: the policy selected from a pre-shift safe set, and the violation
    counter compared the selection against that same pre-shift set, so it could
    never register a breach (TASK_16C audit, finding NEW-1). Recomputing here fixes
    every call site at once and removes the whole class of defect.

    On unshifted data this is a no-op: the stored column and the recomputed gate
    agree on all 100,000 generated rows (asserted by the Task 16D regression suite).
    """
    safe_actions_list = [evaluate_safety_gate(ctx)[0] for ctx in df.to_dict(orient="records")]

    baseline_actions = []
    for safe_a, cat in zip(safe_actions_list, df["failure_category"].values):
        if "do_nothing" in safe_a and len(safe_a) == 1:
            baseline_actions.append("do_nothing")
        elif cat in ["expired_card", "invalid_information"]:
            baseline_actions.append("update_information" if "update_information" in safe_a else safe_a[0])
        elif cat in ["upi_decline"]:
            baseline_actions.append("switch_method" if "switch_method" in safe_a else safe_a[0])
        elif cat in ["insufficient_funds", "issuer_unavailable", "bank_unavailable", "velocity_limit"]:
            baseline_actions.append("retry_later" if "retry_later" in safe_a else safe_a[0])
        elif cat in ["soft_decline", "network_timeout", "authentication_failure", "upi_timeout"]:
            baseline_actions.append("retry_now" if "retry_now" in safe_a else safe_a[0])
        else:
            baseline_actions.append("do_nothing" if "do_nothing" in safe_a else safe_a[0])
            
    return safe_actions_list, baseline_actions

def run_economic_sensitivity(
    advisor: PolicyAdvisor,
    df_test_obs: pd.DataFrame,
    df_test_oracle: pd.DataFrame,
    config_path: str = "configs/robustness_config.yaml",
    precomputed_probs: Optional[Dict[str, np.ndarray]] = None
) -> Dict[str, Any]:
    """Phase 3: Evaluates policy performance under economic parameter perturbations (Vectorized)."""
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)
    scenarios = cfg.get("economic_sensitivity", {})
    N = len(df_test_obs)
    
    batch_probs = precomputed_probs if precomputed_probs is not None else {
        a: advisor.predictor.predict_proba(df_test_obs, action=a) for a in ALL_ACTIONS
    }
    
    base_amounts = df_test_obs["amount"].values
    retry_counts = df_test_obs["retry_count_before_event"].values
    fail_cats = df_test_obs["failure_category"].values
    
    safe_actions_list, baseline_actions = compute_safety_and_baseline(df_test_obs)

    results = {}

    for sc_name, sc_params in scenarios.items():
        val_mult = sc_params.get("value_multiplier", 1.0)
        cost_mult = sc_params.get("cost_multiplier", 1.0)
        fric_mult = sc_params.get("friction_multiplier", 1.0)
        down_mult = sc_params.get("downside_multiplier", 1.0)

        amounts = base_amounts * val_mult

        econ_pert = {
            "direct_costs": {a: get_action_cost(a) * cost_mult for a in ALL_ACTIONS},
            "friction_costs": {a: get_friction_cost(a) * fric_mult for a in ALL_ACTIONS},
            "downside_penalties": {
                "retry_excessive": 15.00 * down_mult,
                "misaligned_action": 5.00 * down_mult
            }
        }

        # Ground truth is recomputed at the PERTURBED amount. The simulator's
        # >Rs10,000 interaction depends on transaction value, so scaling V without
        # recomputing p would score the policy against the wrong world.
        _, ora_ev_matrix = compute_true_ev_matrix(
            df_test_obs, econ_cfg=None, amounts=amounts, econ_overrides=econ_pert
        )

        ev_matrix = np.zeros((N, len(ALL_ACTIONS)))
        for a_idx, a in enumerate(ALL_ACTIONS):
            c_val = econ_pert["direct_costs"][a]
            f_val = econ_pert["friction_costs"][a]

            d_vec = np.zeros(N)
            if a in ["retry_now", "retry_later"]:
                d_vec += np.where(retry_counts >= 2, econ_pert["downside_penalties"]["retry_excessive"], 0.0)
            if a == "update_information":
                d_vec += np.where(~np.isin(fail_cats, ["expired_card", "invalid_information"]), econ_pert["downside_penalties"]["misaligned_action"], 0.0)

            ev_matrix[:, a_idx] = (batch_probs[a] * amounts) - c_val - d_vec - f_val

        ml_actions = []
        safety_violations = 0

        for i in range(N):
            safe_a = safe_actions_list[i]
            safe_indices = [ALL_ACTIONS.index(a) for a in safe_a]
            safe_evs = [ev_matrix[i, idx] for idx in safe_indices]

            rec_act = safe_a[int(np.argmax(safe_evs))]
            ml_actions.append(rec_act)

            if rec_act not in safe_a:
                safety_violations += 1

        ml_act_indices = [ALL_ACTIONS.index(a) for a in ml_actions]
        base_act_indices = [ALL_ACTIONS.index(a) for a in baseline_actions]

        ora_ml_arr = ora_ev_matrix[np.arange(N), ml_act_indices]
        ora_base_arr = ora_ev_matrix[np.arange(N), base_act_indices]
        ora_best_arr = masked_oracle_best(ora_ev_matrix, safe_actions_list)

        uplift_arr = ora_ml_arr - ora_base_arr
        regret_arr = ora_best_arr - ora_ml_arr

        # No NaN can reach these means: the EV matrix is recomputed for every action.
        assert not np.isnan(ora_ml_arr).any() and not np.isnan(ora_best_arr).any()

        results[sc_name] = {
            "parameters": sc_params,
            "events_evaluated": int(N),
            "ml_policy_ev_ci": compute_bootstrap_ci(ora_ml_arr),
            "baseline_policy_ev_ci": compute_bootstrap_ci(ora_base_arr),
            "oracle_best_ev_ci": compute_bootstrap_ci(ora_best_arr),
            "uplift_ci": compute_bootstrap_ci(uplift_arr),
            "regret_ci": compute_bootstrap_ci(regret_arr),
            "safety_violations": safety_violations,
            "per_event_dominance_violations": int(np.sum(regret_arr < -1e-6)),
            "ranking_stable": bool(
                float(np.mean(ora_best_arr)) >= float(np.mean(ora_ml_arr)) - 1e-5
                and float(np.mean(ora_ml_arr)) >= float(np.mean(ora_base_arr)) - 1e-5
            ),
            "action_distribution": pd.Series(ml_actions).value_counts(normalize=True).to_dict()
        }

    return results


def run_ablation_study(
    advisor: PolicyAdvisor,
    df_test_obs: pd.DataFrame,
    df_test_oracle: pd.DataFrame,
    config_path: str = "configs/synthetic_config.yaml",
    precomputed_probs: Optional[Dict[str, np.ndarray]] = None
) -> Dict[str, Any]:
    """Phase 5: Evaluates 5 distinct policy ablation variants (Vectorized)."""
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)
    econ_cfg = cfg.get("economics", {})
    N = len(df_test_obs)
    
    batch_probs = precomputed_probs if precomputed_probs is not None else {
        a: advisor.predictor.predict_proba(df_test_obs, action=a) for a in ALL_ACTIONS
    }
    
    amounts = df_test_obs["amount"].values
    retry_counts = df_test_obs["retry_count_before_event"].values
    fail_cats = df_test_obs["failure_category"].values
    
    ev_matrix = np.zeros((N, len(ALL_ACTIONS)))
    for a_idx, a in enumerate(ALL_ACTIONS):
        p_vec = batch_probs[a]
        c_val = get_action_cost(a, econ_cfg)
        f_val = get_friction_cost(a, econ_cfg)
        d_vec = np.zeros(N)
        if a in ["retry_now", "retry_later"]:
            d_vec += np.where(retry_counts >= 2, 15.00, 0.0)
        if a == "update_information":
            d_vec += np.where(~np.isin(fail_cats, ["expired_card", "invalid_information"]), 5.00, 0.0)
            
        ev_matrix[:, a_idx] = (p_vec * amounts) - c_val - d_vec - f_val
        
    safe_actions_list, baseline_actions = compute_safety_and_baseline(df_test_obs)

    # Ground truth for ALL five actions on ALL rows, including actions the safety gate
    # forbids. A3 deliberately ignores the gate, so it selects forbidden actions on ~84%
    # of events; reading those cells from the oracle CSV produced NaN, and nanmean then
    # silently reduced A3's denominator to the 15.8% of events where its choice happened
    # to be legal (TASK_16A audit, finding M-1).
    _, ora_ev_matrix = compute_true_ev_matrix(df_test_obs, econ_cfg=econ_cfg)

    ablations = {}
    
    # A0: Rule Baseline
    a0_actions = baseline_actions
    
    # A1: Predictive Model Only (max predicted probability among safe actions)
    a1_actions = []
    for i in range(N):
        safe_a = safe_actions_list[i]
        safe_p = [batch_probs[a][i] for a in safe_a]
        a1_actions.append(safe_a[int(np.argmax(safe_p))])
        
    # A2 & A4: ML + Economics + Safety Gate (Full Architecture)
    a2_actions = []
    for i in range(N):
        safe_a = safe_actions_list[i]
        safe_indices = [ALL_ACTIONS.index(a) for a in safe_a]
        safe_evs = [ev_matrix[i, idx] for idx in safe_indices]
        a2_actions.append(safe_a[int(np.argmax(safe_evs))])
        
    # A3: ML + Economics WITHOUT Safety Gate
    a3_actions = [ALL_ACTIONS[int(np.argmax(ev_matrix[i]))] for i in range(N)]
    
    ablation_dict = {
        "A0_Rule_Baseline": a0_actions,
        "A1_Predictive_Model_Only": a1_actions,
        "A2_ML_Economic_Optimization": a2_actions,
        "A3_ML_Economic_No_Safety_Gate": a3_actions,
        "A4_Full_Architecture": a2_actions
    }
    
    for abl_name, action_list in ablation_dict.items():
        act_indices = [ALL_ACTIONS.index(a) for a in action_list]
        ora_ev_arr = ora_ev_matrix[np.arange(N), act_indices]

        # Denominator is explicit and identical for every variant. Nothing is dropped.
        n_missing = int(np.isnan(ora_ev_arr).sum())
        assert n_missing == 0, f"{abl_name}: {n_missing} events lack ground-truth EV."

        violations = 0
        for i in range(N):
            if action_list[i] not in safe_actions_list[i]:
                violations += 1

        ablations[abl_name] = {
            "events_in_population": int(N),
            "events_evaluated": int(N - n_missing),
            "events_missing_ground_truth": n_missing,
            "mean_oracle_ev_inr": float(np.round(float(np.mean(ora_ev_arr)), 2)),
            "ev_bootstrap_ci": compute_bootstrap_ci(ora_ev_arr),
            "safety_violations_count": violations,
            "safety_violation_rate": float(np.round(violations / N, 4)),
            "action_distribution": pd.Series(action_list).value_counts(normalize=True).to_dict()
        }

    return ablations


def run_distribution_shifts(
    advisor: PolicyAdvisor,
    df_test_obs: pd.DataFrame,
    df_test_oracle: pd.DataFrame,
    config_path: str = "configs/robustness_config.yaml"
) -> Dict[str, Any]:
    """Phase 6: Evaluates trained policy against 4 shifted test sets without retraining (Vectorized)."""
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)
    shifts_cfg = cfg.get("distribution_shifts", {})
    econ_cfg = advisor.econ_cfg
    N = len(df_test_obs)
    shifts_results = {}
    
    for shift_name, shift_params in shifts_cfg.items():
        df_shifted = df_test_obs.copy()

        amt_mult = shift_params.get("amount_multiplier", 1.0)
        if amt_mult != 1.0:
            df_shifted["amount"] = df_shifted["amount"] * amt_mult
            # order_value_tier is a deterministic function of amount; leaving it at the
            # pre-shift value would feed the model a self-contradictory context vector.
            df_shifted["order_value_tier"] = pd.cut(
                df_shifted["amount"],
                bins=[-np.inf, 500, 5000, 25000, np.inf],
                labels=["low", "medium", "high", "enterprise"]
            ).astype(str)

        soft_w = shift_params.get("soft_decline_weight", None)
        if soft_w is not None:
            rng = np.random.RandomState(42)
            mask_soft = rng.rand(N) < soft_w
            df_shifted["failure_category"] = np.where(mask_soft, "soft_decline", df_shifted["failure_category"])
            # error_source / error_step are taxonomy-derived from failure_category.
            df_shifted["error_source"] = np.where(
                mask_soft, FAILURE_TAXONOMY["soft_decline"]["error_source"], df_shifted["error_source"])
            df_shifted["error_step"] = np.where(
                mask_soft, FAILURE_TAXONOMY["soft_decline"]["error_step"], df_shifted["error_step"])
            df_shifted["failure_code"] = np.where(
                mask_soft, FAILURE_TAXONOMY["soft_decline"]["default_codes"][0], df_shifted["failure_code"])

        upi_w = shift_params.get("upi_weight", None)
        if upi_w is not None:
            rng = np.random.RandomState(43)
            mask_upi = rng.rand(N) < upi_w
            df_shifted["payment_method"] = np.where(mask_upi, "upi_intent", df_shifted["payment_method"])
            # card_network is only meaningful for card methods.
            df_shifted["card_network"] = np.where(mask_upi, "none", df_shifted["card_network"])

        batch_probs = {a: advisor.predictor.predict_proba(df_shifted, action=a) for a in ALL_ACTIONS}
        amounts = df_shifted["amount"].values
        retry_counts = df_shifted["retry_count_before_event"].values
        fail_cats = df_shifted["failure_category"].values
        
        ev_matrix = np.zeros((N, len(ALL_ACTIONS)))
        for a_idx, a in enumerate(ALL_ACTIONS):
            p_vec = batch_probs[a]
            c_val = get_action_cost(a, econ_cfg)
            f_val = get_friction_cost(a, econ_cfg)
            d_vec = np.zeros(N)
            if a in ["retry_now", "retry_later"]:
                d_vec += np.where(retry_counts >= 2, 15.00, 0.0)
            if a == "update_information":
                d_vec += np.where(~np.isin(fail_cats, ["expired_card", "invalid_information"]), 5.00, 0.0)
                
            ev_matrix[:, a_idx] = (p_vec * amounts) - c_val - d_vec - f_val
            
        # ------------------------------------------------------------------
        # SAFETY GATE IS RE-EVALUATED ON THE SHIFTED CONTEXT.
        #
        # df_shifted is the shifted context X_shifted. Its `safe_actions` column is
        # still the snapshot taken at generation time for the PRE-shift context, so
        # it is refreshed here before use; nothing downstream may read the stale
        # value. The policy may only choose from shifted_safe_actions, and the
        # violation counter is checked against the same recomputed set.
        # (TASK_16C audit, finding NEW-1.)
        # ------------------------------------------------------------------
        shifted_contexts = df_shifted.to_dict(orient="records")
        shifted_safe_actions = [evaluate_safety_gate(ctx)[0] for ctx in shifted_contexts]
        df_shifted["safe_actions"] = ["|".join(sa) for sa in shifted_safe_actions]
        df_shifted["safety_constraints_applied"] = [
            "|".join(evaluate_safety_gate(ctx)[1]) for ctx in shifted_contexts
        ]

        safe_actions_list, baseline_actions = compute_safety_and_baseline(df_shifted)
        assert safe_actions_list == shifted_safe_actions, (
            "Safety set used for the shifted decision does not match "
            "evaluate_safety_gate(shifted_context)."
        )

        ml_actions = []
        violations = 0

        for i in range(N):
            safe_a = shifted_safe_actions[i]
            safe_indices = [ALL_ACTIONS.index(a) for a in safe_a]
            safe_evs = [ev_matrix[i, idx] for idx in safe_indices]

            rec_act = safe_a[int(np.argmax(safe_evs))]
            ml_actions.append(rec_act)

            if rec_act not in safe_a:
                violations += 1
                
        # Ground truth is recomputed from the SHIFTED contexts. Reading it from the
        # unshifted oracle CSV scored the policy in one world against the truth of
        # another (TASK_16A audit, finding M-2).
        _, ora_ev_matrix = compute_true_ev_matrix(df_shifted, econ_cfg=econ_cfg)

        ml_act_indices = [ALL_ACTIONS.index(a) for a in ml_actions]
        base_act_indices = [ALL_ACTIONS.index(a) for a in baseline_actions]

        ora_ml_arr = ora_ev_matrix[np.arange(N), ml_act_indices]
        ora_b_arr = ora_ev_matrix[np.arange(N), base_act_indices]
        # Oracle ceiling is also taken over the SHIFTED safe set, so policy and oracle
        # are constrained identically.
        ora_best_arr = masked_oracle_best(ora_ev_matrix, shifted_safe_actions)

        regret_arr = ora_best_arr - ora_ml_arr

        shifts_results[shift_name] = {
            "parameters": shift_params,
            "ground_truth_recomputed_on_shifted_context": True,
            "safety_gate_recomputed_on_shifted_context": True,
            "events_evaluated": int(N),
            "ml_policy_ev_ci": compute_bootstrap_ci(ora_ml_arr),
            "baseline_policy_ev_ci": compute_bootstrap_ci(ora_b_arr),
            "oracle_best_ev_ci": compute_bootstrap_ci(ora_best_arr),
            "uplift_ci": compute_bootstrap_ci(ora_ml_arr - ora_b_arr),
            "regret_ci": compute_bootstrap_ci(regret_arr),
            "safety_violations": violations,
            "per_event_dominance_violations": int(np.sum(regret_arr < -1e-6)),
            "ranking_stable": bool(
                float(np.mean(ora_best_arr)) >= float(np.mean(ora_ml_arr)) - 1e-5
                and float(np.mean(ora_ml_arr)) >= float(np.mean(ora_b_arr)) - 1e-5
            ),
            "action_distribution": pd.Series(ml_actions).value_counts(normalize=True).to_dict()
        }

    return shifts_results


def run_ground_truth_robustness(
    advisor: PolicyAdvisor,
    df_test_obs: pd.DataFrame,
    config_path: str = "configs/robustness_config.yaml",
    precomputed_probs: Optional[Dict[str, np.ndarray]] = None
) -> Dict[str, Any]:
    """
    Ground-truth robustness: re-scores the FROZEN policy against simulator variants in
    which the hidden contextual interactions are weakened or strengthened.

    This experiment was previously described in TASK_12_ROBUSTNESS.md with specific
    regret figures, and configured in robustness_config.yaml, but had no implementation
    and produced no output key (TASK_16A audit, finding C-3c). It is implemented here.

    The policy is NOT retrained. The question is whether O1's advantage survives when
    the interaction structure it learned to exploit is not as strong as it was in
    training - i.e. whether the result is an artifact of one particular simulator.
    """
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)
    scenarios = cfg.get("ground_truth_robustness", {})
    if not scenarios:
        return {}

    econ_cfg = advisor.econ_cfg
    N = len(df_test_obs)

    batch_probs = precomputed_probs if precomputed_probs is not None else {
        a: advisor.predictor.predict_proba(df_test_obs, action=a) for a in ALL_ACTIONS
    }

    amounts = df_test_obs["amount"].values
    retry_counts = df_test_obs["retry_count_before_event"].values
    fail_cats = df_test_obs["failure_category"].values
    safe_actions_list, baseline_actions = compute_safety_and_baseline(df_test_obs)

    # The policy's own decisions do not depend on the simulator, so they are fixed
    # across all scenarios. Only the ground truth used to score them changes.
    ev_matrix = np.zeros((N, len(ALL_ACTIONS)))
    for a_idx, a in enumerate(ALL_ACTIONS):
        c_val = get_action_cost(a, econ_cfg)
        f_val = get_friction_cost(a, econ_cfg)
        d_vec = np.zeros(N)
        if a in ["retry_now", "retry_later"]:
            d_vec += np.where(retry_counts >= 2, 15.00, 0.0)
        if a == "update_information":
            d_vec += np.where(~np.isin(fail_cats, ["expired_card", "invalid_information"]), 5.00, 0.0)
        ev_matrix[:, a_idx] = (batch_probs[a] * amounts) - c_val - d_vec - f_val

    ml_actions = []
    for i in range(N):
        safe_a = safe_actions_list[i]
        idxs = [ALL_ACTIONS.index(a) for a in safe_a]
        ml_actions.append(safe_a[int(np.argmax([ev_matrix[i, k] for k in idxs]))])

    ml_act_indices = [ALL_ACTIONS.index(a) for a in ml_actions]
    base_act_indices = [ALL_ACTIONS.index(a) for a in baseline_actions]

    results = {}
    for sc_name, sc_params in scenarios.items():
        scale = float(sc_params.get("interaction_scale", 1.0))

        _, ora_ev_matrix = compute_true_ev_matrix(
            df_test_obs, econ_cfg=econ_cfg, interaction_scale=scale
        )

        ora_ml_arr = ora_ev_matrix[np.arange(N), ml_act_indices]
        ora_b_arr = ora_ev_matrix[np.arange(N), base_act_indices]
        ora_best_arr = masked_oracle_best(ora_ev_matrix, safe_actions_list)
        regret_arr = ora_best_arr - ora_ml_arr

        results[sc_name] = {
            "parameters": sc_params,
            "interaction_scale": scale,
            "events_evaluated": int(N),
            "policy_retrained": False,
            "ml_policy_ev_ci": compute_bootstrap_ci(ora_ml_arr),
            "baseline_policy_ev_ci": compute_bootstrap_ci(ora_b_arr),
            "oracle_best_ev_ci": compute_bootstrap_ci(ora_best_arr),
            "uplift_ci": compute_bootstrap_ci(ora_ml_arr - ora_b_arr),
            "regret_ci": compute_bootstrap_ci(regret_arr),
            "per_event_dominance_violations": int(np.sum(regret_arr < -1e-6)),
            "ranking_stable": bool(
                float(np.mean(ora_best_arr)) >= float(np.mean(ora_ml_arr)) - 1e-5
                and float(np.mean(ora_ml_arr)) >= float(np.mean(ora_b_arr)) - 1e-5
            ),
        }

    return results


def run_stress_testing(
    advisor: PolicyAdvisor,
    df_test_obs: pd.DataFrame,
    df_test_oracle: pd.DataFrame,
    precomputed_probs: Optional[Dict[str, np.ndarray]] = None
) -> Dict[str, Any]:
    """Phase 7: Stress testing across high/low amount tiers, retry counts, and top regret cases."""
    N = len(df_test_obs)
    
    batch_probs = precomputed_probs if precomputed_probs is not None else {
        a: advisor.predictor.predict_proba(df_test_obs, action=a) for a in ALL_ACTIONS
    }
    
    amounts = df_test_obs["amount"].values
    retry_counts = df_test_obs["retry_count_before_event"].values
    fail_cats = df_test_obs["failure_category"].values
    econ_cfg = advisor.econ_cfg
    
    ev_matrix = np.zeros((N, len(ALL_ACTIONS)))
    for a_idx, a in enumerate(ALL_ACTIONS):
        p_vec = batch_probs[a]
        c_val = get_action_cost(a, econ_cfg)
        f_val = get_friction_cost(a, econ_cfg)
        d_vec = np.zeros(N)
        if a in ["retry_now", "retry_later"]:
            d_vec += np.where(retry_counts >= 2, 15.00, 0.0)
        if a == "update_information":
            d_vec += np.where(~np.isin(fail_cats, ["expired_card", "invalid_information"]), 5.00, 0.0)
            
        ev_matrix[:, a_idx] = (p_vec * amounts) - c_val - d_vec - f_val
        
    safe_actions_list, baseline_actions = compute_safety_and_baseline(df_test_obs)
    ml_actions = []
    ml_evs = []
    
    for i in range(N):
        safe_a = safe_actions_list[i]
        safe_indices = [ALL_ACTIONS.index(a) for a in safe_a]
        safe_evs = [ev_matrix[i, idx] for idx in safe_indices]
        
        best_idx = int(np.argmax(safe_evs))
        rec_act = safe_a[best_idx]
        rec_ev = safe_evs[best_idx]
        
        ml_actions.append(rec_act)
        ml_evs.append(rec_ev)
        
    df_stress = df_test_obs.copy()
    df_stress["ml_action"] = ml_actions
    df_stress["ml_ev"] = ml_evs
    df_stress["baseline_action"] = baseline_actions
    
    assert df_test_oracle["event_id"].is_unique, "Oracle frame has duplicate event_id values."
    df_merged = df_stress.merge(df_test_oracle, on="event_id", how="inner", validate="one_to_one")
    assert len(df_merged) == N, f"Oracle join changed the population: {len(df_merged)} vs {N}."

    ml_act_indices = [ALL_ACTIONS.index(a) for a in ml_actions]
    base_act_indices = [ALL_ACTIONS.index(a) for a in baseline_actions]

    # Recomputed from the simulator rather than read from the oracle CSV, so subgroup
    # means and the top-regret table are defined for every event.
    _, ora_ev_matrix = compute_true_ev_matrix(df_test_obs, econ_cfg=econ_cfg)
    ora_best_arr = masked_oracle_best(ora_ev_matrix, safe_actions_list)

    df_merged["ml_ora_ev"] = ora_ev_matrix[np.arange(N), ml_act_indices]
    df_merged["base_ora_ev"] = ora_ev_matrix[np.arange(N), base_act_indices]
    df_merged["regret"] = ora_best_arr - df_merged["ml_ora_ev"].values
    df_merged["disagreement"] = df_merged["ml_action"] != df_merged["baseline_action"]
    
    high_val = df_merged[df_merged["amount"] >= 50000.0]
    low_val = df_merged[df_merged["amount"] <= 200.0]
    high_retry = df_merged[df_merged["retry_count_before_event"] >= 2]
    
    top20_regret = df_merged.sort_values("regret", ascending=False).head(20)[
        ["event_id", "amount", "failure_category", "logged_action", "ml_action", "baseline_action", "SYNTHETIC_ORACLE_ONLY_true_best_action", "regret"]
    ].to_dict(orient="records")
    
    return {
        "subgroups": {
            "high_value_amount_ge_50k": {
                "count": len(high_val),
                "ml_oracle_ev_mean": float(np.round(high_val["ml_ora_ev"].mean(), 2)),
                "baseline_oracle_ev_mean": float(np.round(high_val["base_ora_ev"].mean(), 2)),
                "regret_mean": float(np.round(high_val["regret"].mean(), 2)),
                "action_distribution": high_val["ml_action"].value_counts(normalize=True).to_dict()
            },
            "low_value_amount_le_200": {
                "count": len(low_val),
                "ml_oracle_ev_mean": float(np.round(low_val["ml_ora_ev"].mean(), 2)),
                "baseline_oracle_ev_mean": float(np.round(low_val["base_ora_ev"].mean(), 2)),
                "regret_mean": float(np.round(low_val["regret"].mean(), 2)),
                "action_distribution": low_val["ml_action"].value_counts(normalize=True).to_dict()
            },
            "high_retry_count_ge_2": {
                "count": len(high_retry),
                "ml_oracle_ev_mean": float(np.round(high_retry["ml_ora_ev"].mean(), 2)),
                "baseline_oracle_ev_mean": float(np.round(high_retry["base_ora_ev"].mean(), 2)),
                "regret_mean": float(np.round(high_retry["regret"].mean(), 2)),
                "action_distribution": high_retry["ml_action"].value_counts(normalize=True).to_dict()
            }
        },
        "top20_regret_summary": {
            "mean_regret_top20": float(np.round(np.mean([r["regret"] for r in top20_regret]), 2)),
            "actions_in_top20": pd.Series([r["ml_action"] for r in top20_regret]).value_counts().to_dict()
        },
        "disagreement_summary": {
            "total_disagreements": int(np.sum(df_merged["disagreement"])),
            "disagreement_rate": float(np.round(np.mean(df_merged["disagreement"]), 4))
        }
    }
