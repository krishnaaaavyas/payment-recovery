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

def get_precomputed_safety_and_baseline(df: pd.DataFrame) -> Tuple[List[List[str]], List[str]]:
    """Pre-computes safe actions list and baseline action list instantaneously."""
    safe_actions_list = [s.split("|") for s in df["safe_actions"].values]
    
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
    
    safe_actions_list, baseline_actions = get_precomputed_safety_and_baseline(df_test_obs)
    
    df_ora_clean = df_test_oracle.drop_duplicates("event_id")
    df_merged_ora = df_test_obs.merge(df_ora_clean, on="event_id", how="left")
    ora_p_matrix = np.zeros((N, len(ALL_ACTIONS)))
    for a_idx, a in enumerate(ALL_ACTIONS):
        ora_p_matrix[:, a_idx] = df_merged_ora[f"SYNTHETIC_ORACLE_ONLY_true_p_{a}"].values
        
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
        
        ev_matrix = np.zeros((N, len(ALL_ACTIONS)))
        ora_ev_matrix = np.zeros((N, len(ALL_ACTIONS)))
        
        for a_idx, a in enumerate(ALL_ACTIONS):
            c_val = econ_pert["direct_costs"][a]
            f_val = econ_pert["friction_costs"][a]
            
            d_vec = np.zeros(N)
            if a in ["retry_now", "retry_later"]:
                d_vec += np.where(retry_counts >= 2, econ_pert["downside_penalties"]["retry_excessive"], 0.0)
            if a == "update_information":
                d_vec += np.where(~np.isin(fail_cats, ["expired_card", "invalid_information"]), econ_pert["downside_penalties"]["misaligned_action"], 0.0)
                
            ev_matrix[:, a_idx] = (batch_probs[a] * amounts) - c_val - d_vec - f_val
            ora_ev_matrix[:, a_idx] = (ora_p_matrix[:, a_idx] * amounts) - c_val - d_vec - f_val
            
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
        
        masked_ora_matrix = ora_ev_matrix.copy()
        for i in range(N):
            unsafe_indices = [idx for idx, a in enumerate(ALL_ACTIONS) if a not in safe_actions_list[i]]
            masked_ora_matrix[i, unsafe_indices] = -999999.0
            
        ora_best_arr = np.max(masked_ora_matrix, axis=1)
        
        uplift_arr = ora_ml_arr - ora_base_arr
        regret_arr = ora_best_arr - ora_ml_arr
        
        results[sc_name] = {
            "parameters": sc_params,
            "ml_policy_ev_ci": compute_bootstrap_ci(ora_ml_arr),
            "baseline_policy_ev_ci": compute_bootstrap_ci(ora_base_arr),
            "oracle_best_ev_ci": compute_bootstrap_ci(ora_best_arr),
            "uplift_ci": compute_bootstrap_ci(uplift_arr),
            "regret_ci": compute_bootstrap_ci(regret_arr),
            "safety_violations": safety_violations,
            "ranking_stable": bool(np.mean(ora_best_arr) >= np.mean(ora_ml_arr) - 1e-5 and np.mean(ora_ml_arr) >= np.mean(ora_base_arr) - 1e-5),
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
        
    safe_actions_list, baseline_actions = get_precomputed_safety_and_baseline(df_test_obs)
    
    df_ora_clean = df_test_oracle.drop_duplicates("event_id")
    df_merged_ora = df_test_obs.merge(df_ora_clean, on="event_id", how="left")
    ora_ev_matrix = np.zeros((N, len(ALL_ACTIONS)))
    for a_idx, a in enumerate(ALL_ACTIONS):
        ora_ev_matrix[:, a_idx] = df_merged_ora[f"SYNTHETIC_ORACLE_ONLY_true_ev_{a}"].values
        
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
        
        violations = 0
        for i in range(N):
            if action_list[i] not in safe_actions_list[i]:
                violations += 1
                
        ablations[abl_name] = {
            "mean_oracle_ev_inr": float(np.round(np.nanmean(ora_ev_arr), 2)),
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
            
        soft_w = shift_params.get("soft_decline_weight", None)
        if soft_w is not None:
            rng = np.random.RandomState(42)
            mask_soft = rng.rand(N) < soft_w
            df_shifted["failure_category"] = np.where(mask_soft, "soft_decline", df_shifted["failure_category"])
            
        upi_w = shift_params.get("upi_weight", None)
        if upi_w is not None:
            rng = np.random.RandomState(43)
            mask_upi = rng.rand(N) < upi_w
            df_shifted["payment_method"] = np.where(mask_upi, "upi_intent", df_shifted["payment_method"])
            
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
            
        safe_actions_list, baseline_actions = get_precomputed_safety_and_baseline(df_shifted)
        
        ml_actions = []
        violations = 0
        
        for i in range(N):
            safe_a = safe_actions_list[i]
            safe_indices = [ALL_ACTIONS.index(a) for a in safe_a]
            safe_evs = [ev_matrix[i, idx] for idx in safe_indices]
            
            rec_act = safe_a[int(np.argmax(safe_evs))]
            ml_actions.append(rec_act)
            
            if rec_act not in safe_a:
                violations += 1
                
        df_ora_clean = df_test_oracle.drop_duplicates("event_id")
        df_merged_ora = df_shifted.merge(df_ora_clean, on="event_id", how="left")
        
        ora_ev_matrix = np.zeros((N, len(ALL_ACTIONS)))
        for a_idx, a in enumerate(ALL_ACTIONS):
            p_true_col = df_merged_ora[f"SYNTHETIC_ORACLE_ONLY_true_p_{a}"].values
            c_val = get_action_cost(a, econ_cfg)
            f_val = get_friction_cost(a, econ_cfg)
            d_vec = np.zeros(N)
            if a in ["retry_now", "retry_later"]:
                d_vec += np.where(retry_counts >= 2, 15.00, 0.0)
            if a == "update_information":
                d_vec += np.where(~np.isin(fail_cats, ["expired_card", "invalid_information"]), 5.00, 0.0)
                
            ora_ev_matrix[:, a_idx] = (p_true_col * amounts) - c_val - d_vec - f_val
            
        ml_act_indices = [ALL_ACTIONS.index(a) for a in ml_actions]
        base_act_indices = [ALL_ACTIONS.index(a) for a in baseline_actions]
        
        ora_ml_arr = ora_ev_matrix[np.arange(N), ml_act_indices]
        ora_b_arr = ora_ev_matrix[np.arange(N), base_act_indices]
        
        masked_ora_matrix = ora_ev_matrix.copy()
        for i in range(N):
            unsafe_indices = [idx for idx, a in enumerate(ALL_ACTIONS) if a not in safe_actions_list[i]]
            masked_ora_matrix[i, unsafe_indices] = -999999.0
            
        ora_best_arr = np.max(masked_ora_matrix, axis=1)
        
        shifts_results[shift_name] = {
            "parameters": shift_params,
            "ml_policy_ev_ci": compute_bootstrap_ci(ora_ml_arr),
            "baseline_policy_ev_ci": compute_bootstrap_ci(ora_b_arr),
            "oracle_best_ev_ci": compute_bootstrap_ci(ora_best_arr),
            "uplift_ci": compute_bootstrap_ci(ora_ml_arr - ora_b_arr),
            "regret_ci": compute_bootstrap_ci(ora_best_arr - ora_ml_arr),
            "safety_violations": violations,
            "action_distribution": pd.Series(ml_actions).value_counts(normalize=True).to_dict()
        }
        
    return shifts_results


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
        
    safe_actions_list, baseline_actions = get_precomputed_safety_and_baseline(df_test_obs)
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
    
    df_ora_clean = df_test_oracle.drop_duplicates("event_id")
    df_merged = df_stress.merge(df_ora_clean, on="event_id", how="left")
    
    ml_act_indices = [ALL_ACTIONS.index(a) for a in ml_actions]
    base_act_indices = [ALL_ACTIONS.index(a) for a in baseline_actions]
    
    ora_ev_matrix = np.zeros((N, len(ALL_ACTIONS)))
    for a_idx, a in enumerate(ALL_ACTIONS):
        ora_ev_matrix[:, a_idx] = df_merged[f"SYNTHETIC_ORACLE_ONLY_true_ev_{a}"].values
        
    df_merged["ml_ora_ev"] = ora_ev_matrix[np.arange(N), ml_act_indices]
    df_merged["base_ora_ev"] = ora_ev_matrix[np.arange(N), base_act_indices]
    df_merged["regret"] = df_merged["SYNTHETIC_ORACLE_ONLY_true_best_ev"] - df_merged["ml_ora_ev"]
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
