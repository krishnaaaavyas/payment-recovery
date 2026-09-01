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
    else:
        b_ips_ev, b_snips_ev = 0.0, 0.0
        
    logged_mean_ev = float(np.mean(realized_logged_rewards))
    
    # ----------------------------------------------------
    # EVALUATION C — SYNTHETIC ORACLE BENCHMARK
    # ----------------------------------------------------
    df_merged_ora = df_eval.merge(df_test_oracle, on="event_id", how="left")
    
    oracle_true_ev_ml = []
    oracle_true_ev_baseline = []
    
    for idx, row in df_merged_ora.iterrows():
        ml_act = row["ml_action"]
        b_act = row["baseline_action"]
        
        ora_ev_ml = row[f"SYNTHETIC_ORACLE_ONLY_true_ev_{ml_act}"]
        ora_ev_b = row[f"SYNTHETIC_ORACLE_ONLY_true_ev_{b_act}"]
        
        oracle_true_ev_ml.append(ora_ev_ml)
        oracle_true_ev_baseline.append(ora_ev_b)
        
    mean_oracle_best_ev = float(df_test_oracle["SYNTHETIC_ORACLE_ONLY_true_best_ev"].mean())
    mean_oracle_baseline_ev = float(df_test_oracle["SYNTHETIC_ORACLE_ONLY_baseline_ev"].mean())
    mean_oracle_ml_ev = float(np.nanmean(oracle_true_ev_ml))
    regret = float(mean_oracle_best_ev - mean_oracle_ml_ev)
    
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
        "off_policy_ips_evaluation": {
            "logged_policy_realized_mean_ev_inr": float(np.round(logged_mean_ev, 2)),
            "baseline_policy_ips_ev_inr": float(np.round(b_ips_ev, 2)),
            "baseline_policy_snips_ev_inr": float(np.round(b_snips_ev, 2)),
            "baseline_policy_coverage_rate": float(np.round(b_coverage, 4)),
            "ml_policy_ips_ev_inr": float(np.round(ml_ips_ev, 2)),
            "ml_policy_snips_ev_inr": float(np.round(ml_snips_ev, 2)),
            "ml_policy_coverage_rate": float(np.round(ml_coverage, 4)),
            "ml_effective_sample_size": float(np.round(ml_ess, 1))
        },
        "synthetic_oracle_benchmark": {
            "disclaimer": "Synthetic oracle benchmark — not production evidence.",
            "oracle_baseline_policy_ev_inr": float(np.round(mean_oracle_baseline_ev, 2)),
            "oracle_ml_policy_ev_inr": float(np.round(mean_oracle_ml_ev, 2)),
            "oracle_best_policy_ev_inr": float(np.round(mean_oracle_best_ev, 2)),
            "oracle_policy_regret_inr": float(np.round(regret, 2))
        },
        "distributions": {
            "ml_action_distribution": {k: float(np.round(v, 4)) for k, v in ml_action_dist.items()},
            "confidence_distribution": {k: float(np.round(v, 4)) for k, v in confidence_dist.items()}
        }
    }
