"""
Policy Evaluation Engine (High-Performance Vectorized Implementation)
Executes Evaluation A (Model Metrics), Evaluation B (Off-Policy IPS/SNIPS), and Evaluation C (Synthetic Oracle Benchmark).
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

from src.data.failure_taxonomy import ALL_ACTIONS
from src.data.safety import evaluate_safety_gate
from src.data.economics import calculate_ev, get_action_cost, get_downside_penalty, get_friction_cost
from src.policy.advisor import PolicyAdvisor
from src.policy.baseline import DeterministicBaselinePolicy

def bootstrap_snips_ci(
    matches: np.ndarray,
    propensities: np.ndarray,
    rewards: np.ndarray,
    n_bootstraps: int = 2000,
    seed: int = 0
) -> Dict[str, float]:
    """
    Percentile bootstrap confidence interval for the SNIPS estimator.

    Resamples events (not matched events) with replacement, so the uncertainty
    reflects both which events land in the sample and which of them the logging
    policy happened to match.
    """
    N = len(rewards)
    weights = np.where(matches, 1.0 / propensities, 0.0)
    if weights.sum() <= 0:
        return {"point": 0.0, "ci_lower": 0.0, "ci_upper": 0.0, "std_error": 0.0, "n_bootstraps": 0}

    point = float(np.sum(weights * rewards) / np.sum(weights))

    rng = np.random.RandomState(seed)
    draws = []
    for _ in range(n_bootstraps):
        idx = rng.randint(0, N, N)
        w = weights[idx]
        w_sum = w.sum()
        if w_sum > 0:
            draws.append(float(np.sum(w * rewards[idx]) / w_sum))

    arr = np.array(draws)
    return {
        "point": float(np.round(point, 2)),
        "ci_lower": float(np.round(np.percentile(arr, 2.5), 2)),
        "ci_upper": float(np.round(np.percentile(arr, 97.5), 2)),
        "std_error": float(np.round(arr.std(ddof=1), 2)),
        "n_bootstraps": len(draws),
    }


def run_policy_evaluation(
    advisor: PolicyAdvisor,
    df_test_obs: pd.DataFrame,
    df_test_oracle: pd.DataFrame,
    config_path: str = "configs/synthetic_config.yaml"
) -> Dict[str, Any]:
    """
    Runs high-performance vectorized policy evaluation suite on test dataset.
    """
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)
    econ_cfg = cfg.get("economics", {})
    
    baseline_policy = DeterministicBaselinePolicy()
    N = len(df_test_obs)
    
    # 1. Pre-evaluate Safety Gate & Baseline for all rows
    safe_actions_list = []
    safety_violations = 0
    baseline_actions = []
    
    for idx, row in df_test_obs.iterrows():
        safe_a, _ = evaluate_safety_gate(row.to_dict())
        safe_actions_list.append(safe_a)
        b_act = baseline_policy.select_action(row.to_dict())
        baseline_actions.append(b_act)
        
    # 2. Batch predict probabilities for ALL 5 actions across entire test dataset
    batch_probs = {}
    for a in ALL_ACTIONS:
        batch_probs[a] = advisor.predictor.predict_proba(df_test_obs, action=a)
        
    amounts = df_test_obs["amount"].values
    retry_counts = df_test_obs["retry_count_before_event"].values
    fail_cats = df_test_obs["failure_category"].values
    
    # Direct costs, friction costs, downside penalties per action
    action_costs = {a: get_action_cost(a, econ_cfg) for a in ALL_ACTIONS}
    friction_costs = {a: get_friction_cost(a, econ_cfg) for a in ALL_ACTIONS}
    
    excessive_penalty = float(econ_cfg.get("downside_penalties", {}).get("retry_excessive", 15.00))
    misaligned_penalty = float(econ_cfg.get("downside_penalties", {}).get("misaligned_action", 5.00))
    
    # Calculate EV matrices
    ev_matrix = np.zeros((N, len(ALL_ACTIONS)))
    
    for a_idx, a in enumerate(ALL_ACTIONS):
        p_vec = batch_probs[a]
        c_val = action_costs[a]
        f_val = friction_costs[a]
        
        # Calculate downside penalty array
        d_vec = np.zeros(N)
        if a in ["retry_now", "retry_later"]:
            d_vec += np.where(retry_counts >= 2, excessive_penalty, 0.0)
        if a == "update_information":
            d_vec += np.where(~np.isin(fail_cats, ["expired_card", "invalid_information"]), misaligned_penalty, 0.0)
            
        ev_matrix[:, a_idx] = (p_vec * amounts) - c_val - d_vec - f_val
        
    # Select best safe action for each row
    ml_recommended_actions = []
    ml_expected_evs = []
    ml_expected_probs = []
    ml_confidences = []
    
    for i in range(N):
        safe_a = safe_actions_list[i]
        
        # Mask unsafe actions
        safe_indices = [ALL_ACTIONS.index(a) for a in safe_a]
        safe_evs = [ev_matrix[i, idx] for idx in safe_indices]
        
        best_local_idx = int(np.argmax(safe_evs))
        rec_action = safe_a[best_local_idx]
        rec_ev = safe_evs[best_local_idx]
        
        global_act_idx = ALL_ACTIONS.index(rec_action)
        rec_p = float(batch_probs[rec_action][i])
        
        ml_recommended_actions.append(rec_action)
        ml_expected_evs.append(round(float(rec_ev), 4))
        ml_expected_probs.append(round(rec_p, 4))
        
        # Check safety violation
        obs_safe = df_test_obs.iloc[i]["safe_actions"].split("|")
        if rec_action not in obs_safe:
            safety_violations += 1
            
        # Confidence
        if len(safe_a) == 1:
            conf = "high"
        else:
            sorted_evs = sorted(safe_evs, reverse=True)
            margin = sorted_evs[0] - sorted_evs[1]
            if margin > 50.0 and (rec_p > 0.40 or rec_action == "do_nothing"):
                conf = "high"
            elif margin >= 10.0:
                conf = "medium"
            else:
                conf = "low"
        ml_confidences.append(conf)
        
    df_eval = df_test_obs.copy()
    df_eval["ml_action"] = ml_recommended_actions
    df_eval["ml_expected_ev"] = ml_expected_evs
    df_eval["ml_expected_prob"] = ml_expected_probs
    df_eval["ml_confidence"] = ml_confidences
    df_eval["baseline_action"] = baseline_actions
    
    # ----------------------------------------------------
    # EVALUATION B — OFF-POLICY POLICY VALUE (IPS & SNIPS)
    # ----------------------------------------------------
    realized_logged_rewards = (
        df_eval["recovered_gmv"] -
        df_eval["action_cost"] -
        df_eval["downside_penalty"] -
        df_eval["friction_cost"]
    ).values
    
    propensities = df_eval["logging_probability"].values
    logged_actions = df_eval["logged_action"].values
    
    # ML Policy IPS
    ml_matches = (df_eval["ml_action"].values == logged_actions)
    ml_match_count = int(np.sum(ml_matches))
    ml_coverage = float(ml_match_count / N)
    
    if ml_match_count > 0:
        ml_weights = 1.0 / propensities[ml_matches]
        ml_rewards = realized_logged_rewards[ml_matches]
        
        ml_ips_ev = float(np.sum(ml_weights * ml_rewards) / N)
        ml_snips_ev = float(np.sum(ml_weights * ml_rewards) / np.sum(ml_weights))
        ml_ess = float((np.sum(ml_weights) ** 2) / np.sum(ml_weights ** 2))
    else:
        ml_ips_ev, ml_snips_ev, ml_ess = 0.0, 0.0, 0.0
        
    # Baseline Policy IPS
    b_matches = (df_eval["baseline_action"].values == logged_actions)
    b_match_count = int(np.sum(b_matches))
    b_coverage = float(b_match_count / N)
    
    if b_match_count > 0:
        b_weights = 1.0 / propensities[b_matches]
        b_rewards = realized_logged_rewards[b_matches]
        
        b_ips_ev = float(np.sum(b_weights * b_rewards) / N)
        b_snips_ev = float(np.sum(b_weights * b_rewards) / np.sum(b_weights))
        b_ess = float((np.sum(b_weights) ** 2) / np.sum(b_weights ** 2))
    else:
        b_ips_ev, b_snips_ev, b_ess = 0.0, 0.0, 0.0
        
    logged_mean_ev = float(np.mean(realized_logged_rewards))

    # Bootstrap confidence intervals for the SNIPS estimators. SNIPS is a
    # high-variance estimator here (see effective sample size below), so a point
    # estimate on its own is not an honest summary.
    ml_snips_ci = bootstrap_snips_ci(ml_matches, propensities, realized_logged_rewards)
    b_snips_ci = bootstrap_snips_ci(b_matches, propensities, realized_logged_rewards)

    # ----------------------------------------------------
    # EVALUATION C — DIRECT GROUND-TRUTH SIMULATOR BENCHMARK
    #
    # This is the AUTHORITATIVE synthetic-policy benchmark: it evaluates every
    # event in the population against the hidden simulator, rather than the
    # propensity-matched subset SNIPS is restricted to.
    #
    # The merge is validated one-to-one: a many-to-one join silently duplicated
    # events and a left join silently produced NaNs that were then dropped by
    # nanmean, so the O1 mean and the oracle mean were computed over different
    # populations (TASK_16A audit, finding C-1).
    # ----------------------------------------------------
    assert df_test_oracle["event_id"].is_unique, (
        "Oracle frame contains duplicate event_id values; cannot align one-to-one."
    )
    df_merged_ora = df_eval.merge(df_test_oracle, on="event_id", how="inner", validate="one_to_one")
    assert len(df_merged_ora) == N, (
        f"Oracle join changed the population: {len(df_merged_ora)} rows after merge, "
        f"expected {N}. Observed and oracle frames are not aligned."
    )

    ml_act_arr = df_merged_ora["ml_action"].values
    b_act_arr = df_merged_ora["baseline_action"].values

    oracle_true_ev_ml = np.array([
        df_merged_ora[f"SYNTHETIC_ORACLE_ONLY_true_ev_{a}"].values[i]
        for i, a in enumerate(ml_act_arr)
    ], dtype=float)
    oracle_true_ev_baseline = np.array([
        df_merged_ora[f"SYNTHETIC_ORACLE_ONLY_true_ev_{a}"].values[i]
        for i, a in enumerate(b_act_arr)
    ], dtype=float)
    oracle_true_ev_best = df_merged_ora["SYNTHETIC_ORACLE_ONLY_true_best_ev"].values.astype(float)

    # No NaN may survive: both policies are confined to the safe action set, and the
    # oracle records a true EV for every safe action. A NaN here means an evaluated
    # action was outside the safe set at generation time.
    assert not np.isnan(oracle_true_ev_ml).any(), (
        f"{int(np.isnan(oracle_true_ev_ml).sum())} events have no ground-truth EV for the "
        f"O1 action; the policy selected an action outside the generated safe set."
    )
    assert not np.isnan(oracle_true_ev_baseline).any(), (
        f"{int(np.isnan(oracle_true_ev_baseline).sum())} events have no ground-truth EV for "
        f"the baseline action."
    )
    assert not np.isnan(oracle_true_ev_best).any(), "Oracle best EV contains NaN."

    # Per-event dominance: the oracle takes the max over the same safe set the policy
    # chooses from, so regret must be non-negative for EVERY event, not merely on
    # average. This is checked directly rather than inferred from aggregate means.
    per_event_regret = oracle_true_ev_best - oracle_true_ev_ml
    dominance_violations = int(np.sum(per_event_regret < -1e-6))
    assert dominance_violations == 0, (
        f"{dominance_violations} events violate EV_true(O1) <= EV_true(oracle)."
    )

    mean_oracle_best_ev = float(np.mean(oracle_true_ev_best))
    mean_oracle_baseline_ev = float(np.mean(oracle_true_ev_baseline))
    mean_oracle_ml_ev = float(np.mean(oracle_true_ev_ml))
    regret = float(mean_oracle_best_ev - mean_oracle_ml_ev)
    policy_efficiency = float(mean_oracle_ml_ev / mean_oracle_best_ev) if mean_oracle_best_ev else 0.0
    direct_uplift = mean_oracle_ml_ev - mean_oracle_baseline_ev

    # ----------------------------------------------------
    # ACTION & CONFIDENCE DISTRIBUTION METRICS
    # ----------------------------------------------------
    ml_action_dist = df_eval["ml_action"].value_counts(normalize=True).to_dict()
    confidence_dist = df_eval["ml_confidence"].value_counts(normalize=True).to_dict()
    
    ml_recovery_rate_est = float(np.mean(ml_expected_probs))
    ml_expected_gmv = float(np.mean(df_eval["amount"] * ml_expected_probs))
    
    return {
        "test_events_count": N,
        "safety_evaluation": {
            "safety_violations_count": safety_violations,
            "safety_violation_rate": float(safety_violations / N)
        },
        "predictive_expected_metrics": {
            "mean_expected_recovery_probability": float(np.round(ml_recovery_rate_est, 4)),
            "mean_expected_ev_inr": float(np.round(np.mean(ml_expected_evs), 2)),
            "expected_recovered_gmv_inr": float(np.round(ml_expected_gmv, 2))
        },
        "direct_ground_truth_benchmark": {
            "role": "AUTHORITATIVE synthetic-policy benchmark — full population, hidden simulator.",
            "disclaimer": "Synthetic environment only — not Razorpay production evidence.",
            "events_evaluated": int(len(oracle_true_ev_ml)),
            "events_in_population": N,
            "events_missing_ground_truth": int(N - len(oracle_true_ev_ml)),
            "direct_true_o1_policy_ev_inr": float(np.round(mean_oracle_ml_ev, 2)),
            "direct_true_oracle_best_ev_inr": float(np.round(mean_oracle_best_ev, 2)),
            "direct_true_baseline_policy_ev_inr": float(np.round(mean_oracle_baseline_ev, 2)),
            "direct_true_regret_inr_per_event": float(np.round(regret, 4)),
            "direct_policy_efficiency": float(np.round(policy_efficiency, 6)),
            "direct_uplift_over_baseline_inr_per_event": float(np.round(direct_uplift, 2)),
            "direct_uplift_over_baseline_pct": float(np.round(100.0 * direct_uplift / mean_oracle_baseline_ev, 2)),
            "per_event_dominance_violations": dominance_violations,
            "per_event_regret_min": float(np.round(float(np.min(per_event_regret)), 6)),
            "per_event_regret_max": float(np.round(float(np.max(per_event_regret)), 2)),
            "action_matches_oracle_best_rate": float(np.round(
                float(np.mean(ml_act_arr == df_merged_ora["SYNTHETIC_ORACLE_ONLY_true_best_action"].values)), 4))
        },
        "off_policy_snips_evaluation": {
            "role": "Off-policy estimator (deployment-style analogue) — NOT ground truth.",
            "interpretation": (
                "SNIPS estimates policy value from logged episodes where the target policy "
                "happens to agree with the logging policy, reweighted by 1/e(a|X). It is "
                "unbiased in expectation but high-variance at this coverage; the direct "
                "ground-truth benchmark above is the authoritative value."
            ),
            "logged_policy_realized_mean_ev_inr": float(np.round(logged_mean_ev, 2)),
            "baseline_policy_ips_ev_inr": float(np.round(b_ips_ev, 2)),
            "baseline_policy_snips_ev_inr": float(np.round(b_snips_ev, 2)),
            "baseline_policy_snips_ci": b_snips_ci,
            "baseline_policy_coverage_rate": float(np.round(b_coverage, 4)),
            "baseline_matched_events": b_match_count,
            "baseline_effective_sample_size": float(np.round(b_ess, 1)),
            "ml_policy_ips_ev_inr": float(np.round(ml_ips_ev, 2)),
            "ml_policy_snips_ev_inr": float(np.round(ml_snips_ev, 2)),
            "ml_policy_snips_ci": ml_snips_ci,
            "ml_policy_coverage_rate": float(np.round(ml_coverage, 4)),
            "ml_matched_events": ml_match_count,
            "ml_effective_sample_size": float(np.round(ml_ess, 1)),
            "ml_effective_sample_size_fraction": float(np.round(ml_ess / N, 4)),
            "min_logging_propensity": float(np.round(float(np.min(propensities)), 4)),
            "max_importance_weight": float(np.round(float(np.max(1.0 / propensities)), 2)),
            "weight_clipping_applied": False,
            "snips_uplift_over_baseline_inr_per_event": float(np.round(ml_snips_ev - b_snips_ev, 2)),
            "snips_minus_direct_true_ev_inr": float(np.round(ml_snips_ev - mean_oracle_ml_ev, 2))
        },
        "distributions": {
            "ml_action_distribution": {k: float(np.round(v, 4)) for k, v in ml_action_dist.items()},
            "confidence_distribution": {k: float(np.round(v, 4)) for k, v in confidence_dist.items()}
        }
    }
