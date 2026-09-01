"""
Synthetic Dataset Generator Module (High-Performance Vectorized Implementation)
Generates reproducible, non-circular synthetic payment failure events dataset.
"""

import os
import sys

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import yaml
import argparse
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any

from src.data.failure_taxonomy import FAILURE_TAXONOMY, ALL_ACTIONS
from src.data.safety import evaluate_safety_gate
from src.data.economics import calculate_ev, get_action_cost, get_friction_cost, get_downside_penalty
from src.data.logging_policy import select_logged_action
from src.data.ground_truth import compute_true_recovery_probability, sample_recovery_outcome

PAYMENT_METHODS = ["card_credit", "card_debit", "upi_intent", "upi_collect", "netbanking"]
ISSUER_CATEGORIES = ["psu_bank", "private_bank", "foreign_bank", "neobank"]
CARD_NETWORKS = ["visa", "mastercard", "rupay", "amex", "none"]
CORRIDORS = ["domestic_in", "cross_border_in_us", "cross_border_in_eu", "cross_border_in_sg"]
PRODUCT_CATEGORIES = ["electronics", "apparel", "saas_subscription", "digital_goods", "travel", "food_delivery"]
MERCHANT_SEGMENTS = ["e_commerce", "saas", "gaming", "travel_hospitality", "retail"]

TAXONOMY_KEYS = list(FAILURE_TAXONOMY.keys())
TAX_PROBS = [0.05, 0.03, 0.03, 0.08, 0.07, 0.20, 0.15, 0.08, 0.06, 0.08, 0.07, 0.06, 0.04]

def load_config(config_path: str) -> Dict[str, Any]:
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def get_deterministic_baseline_action(context: Dict[str, Any], safe_actions: List[str]) -> str:
    """Competent deterministic rules baseline."""
    cat = context.get("failure_category", "")
    
    if "do_nothing" in safe_actions and len(safe_actions) == 1:
        return "do_nothing"
        
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

def generate_dataset(config_path: str, num_events: int = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Generates observed dataframe and oracle dataframe using high-performance numpy sampling."""
    cfg = load_config(config_path)
    seed = cfg.get("seed", 42)
    rng = np.random.RandomState(seed)
    
    N = num_events if num_events is not None else cfg.get("num_events", 100000)
    epsilon = cfg.get("logging_policy", {}).get("epsilon", 0.30)
    econ_cfg = cfg.get("economics", {})
    
    start_dt = datetime.strptime(cfg["temporal"]["start_date"], "%Y-%m-%d")
    end_dt = datetime.strptime(cfg["temporal"]["end_date"], "%Y-%m-%d")
    total_sec = int((end_dt - start_dt).total_seconds())
    
    # Vectorized random sampling
    offsets = rng.randint(0, total_sec, size=N)
    amounts_raw = np.exp(rng.normal(loc=7.5, scale=1.2, size=N))
    amounts = np.round(np.clip(amounts_raw, 10.0, 500000.0), 2)
    currencies = np.where(rng.rand(N) > 0.1, "INR", "USD")
    subscriptions = rng.rand(N) < 0.15
    
    pm_indices = rng.choice(len(PAYMENT_METHODS), p=[0.25, 0.25, 0.30, 0.10, 0.10], size=N)
    iss_indices = rng.choice(len(ISSUER_CATEGORIES), p=[0.35, 0.45, 0.15, 0.05], size=N)
    card_net_indices = rng.choice(4, p=[0.40, 0.35, 0.20, 0.05], size=N)
    corr_indices = rng.choice(len(CORRIDORS), p=[0.85, 0.08, 0.04, 0.03], size=N)
    prod_indices = rng.randint(0, len(PRODUCT_CATEGORIES), size=N)
    merch_indices = rng.randint(0, len(MERCHANT_SEGMENTS), size=N)
    fail_indices = rng.choice(len(TAXONOMY_KEYS), p=TAX_PROBS, size=N)
    
    tenures = rng.randint(1, 1000, size=N)
    hist_success = np.round(rng.beta(a=7, b=3, size=N), 4)
    hist_failed = rng.geometric(p=0.3, size=N) - 1
    hist_retry = rng.geometric(p=0.4, size=N) - 1
    time_since_succ = np.round(rng.exponential(scale=48.0, size=N), 2)
    retry_before = rng.choice([0, 1, 2, 3], p=[0.60, 0.25, 0.10, 0.05], size=N)
    
    event_ids = [f"evt_{x}" for x in rng.randint(10000000, 99999999, size=N)]
    order_ids = [f"ord_{x}" for x in rng.randint(10000000, 99999999, size=N)]
    cust_ids = [f"cust_{x}" for x in rng.randint(100000, 999999, size=N)]
    
    observed_rows = []
    oracle_rows = []
    
    for i in range(N):
        ts = start_dt + timedelta(seconds=int(offsets[i]))
        amt = float(amounts[i])
        
        if amt < 500:
            tier = "low"
        elif amt < 5000:
            tier = "medium"
        elif amt < 25000:
            tier = "high"
        else:
            tier = "enterprise"
            
        pm = PAYMENT_METHODS[pm_indices[i]]
        iss = ISSUER_CATEGORIES[iss_indices[i]]
        cn = CARD_NETWORKS[card_net_indices[i]] if pm.startswith("card") else "none"
        corr = CORRIDORS[corr_indices[i]]
        prod = PRODUCT_CATEGORIES[prod_indices[i]]
        merch = MERCHANT_SEGMENTS[merch_indices[i]]
        fail_cat = TAXONOMY_KEYS[fail_indices[i]]
        cat_meta = FAILURE_TAXONOMY[fail_cat]
        fail_code = str(rng.choice(cat_meta["default_codes"]))
        
        ctx = {
            "event_id": event_ids[i],
            "order_id": order_ids[i],
            "customer_id": cust_ids[i],
            "failure_timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "amount": amt,
            "currency": str(currencies[i]),
            "product_category": prod,
            "is_subscription": bool(subscriptions[i]),
            "order_value_tier": tier,
            "payment_method": pm,
            "issuer_category": iss,
            "card_network": cn,
            "failure_code": fail_code,
            "failure_category": fail_cat,
            "error_source": cat_meta["error_source"],
            "error_step": cat_meta["error_step"],
            "corridor": corr,
            "customer_tenure_days": int(tenures[i]),
            "historical_success_rate": float(hist_success[i]),
            "historical_failed_attempts": int(hist_failed[i]),
            "historical_retry_count": int(hist_retry[i]),
            "time_since_last_success_hours": float(time_since_succ[i]),
            "retry_count_before_event": int(retry_before[i]),
            "hour": ts.hour,
            "day_of_week": ts.weekday(),
            "is_weekend": int(ts.weekday() >= 5),
            "merchant_segment": merch,
            "merchant_category": f"cat_{merch}"
        }
        
        # Safety gate
        safe_actions, constraints = evaluate_safety_gate(ctx)
        ctx["safe_actions"] = "|".join(safe_actions)
        ctx["safety_constraints_applied"] = "|".join(constraints)
        
        # Historical logging policy
        logged_action, logging_prob = select_logged_action(ctx, safe_actions, epsilon=epsilon, rng=rng)
        
        # True probabilities for ALL feasible actions (for Oracle EV calculation)
        true_probs = {}
        true_evs = {}
        for a in safe_actions:
            p_a = compute_true_recovery_probability(ctx, a)
            true_probs[a] = p_a
            true_evs[a] = calculate_ev(a, p_a, amt, ctx, econ_cfg)
            
        best_a = max(true_evs, key=true_evs.get)
        true_best_ev = true_evs[best_a]
        true_logged_p = true_probs[logged_action]
        
        # Sample recovery outcome for logged action
        recovered, time_to_rec, rec_gmv = sample_recovery_outcome(
            p_true=true_logged_p,
            action=logged_action,
            amount=amt,
            rng=rng
        )
        
        # Action economics for logged action
        c_logged = get_action_cost(logged_action, econ_cfg)
        d_logged = get_downside_penalty(ctx, logged_action, econ_cfg)
        f_logged = get_friction_cost(logged_action, econ_cfg)
        
        # Deterministic Baseline Action
        baseline_action = get_deterministic_baseline_action(ctx, safe_actions)
        p_baseline = true_probs.get(baseline_action, 0.0)
        baseline_ev = calculate_ev(baseline_action, p_baseline, amt, ctx, econ_cfg)
        
        # Observed Row (Features + Logged Action + Outcome + Action Costs)
        obs_row = ctx.copy()
        obs_row.update({
            "logged_action": logged_action,
            "logging_probability": logging_prob,
            "recovered": recovered,
            "recovery_timestamp": (ts + timedelta(hours=time_to_rec)).strftime("%Y-%m-%d %H:%M:%S") if recovered == 1 else "",
            "time_to_recovery_hours": time_to_rec,
            "recovered_gmv": rec_gmv,
            "action_cost": c_logged,
            "downside_penalty": d_logged,
            "friction_cost": f_logged
        })
        observed_rows.append(obs_row)
        
        # Oracle Row (SYNTHETIC_ORACLE_ONLY - excluded from model input)
        oracle_row = {
            "event_id": ctx["event_id"],
            "SYNTHETIC_ORACLE_ONLY_true_recovery_probability_logged": true_logged_p,
            "SYNTHETIC_ORACLE_ONLY_true_best_action": best_a,
            "SYNTHETIC_ORACLE_ONLY_true_best_ev": true_best_ev,
            "SYNTHETIC_ORACLE_ONLY_baseline_action": baseline_action,
            "SYNTHETIC_ORACLE_ONLY_baseline_true_p": p_baseline,
            "SYNTHETIC_ORACLE_ONLY_baseline_ev": baseline_ev
        }
        for a in ALL_ACTIONS:
            oracle_row[f"SYNTHETIC_ORACLE_ONLY_true_p_{a}"] = true_probs.get(a, np.nan)
            oracle_row[f"SYNTHETIC_ORACLE_ONLY_true_ev_{a}"] = true_evs.get(a, np.nan)
            
        oracle_rows.append(oracle_row)
        
    df_obs = pd.DataFrame(observed_rows)
    df_oracle = pd.DataFrame(oracle_rows)
    
    # Sort chronologically by failure_timestamp
    df_obs = df_obs.sort_values("failure_timestamp").reset_index(drop=True)
    df_oracle = df_oracle.set_index("event_id").loc[df_obs["event_id"]].reset_index()
    
    return df_obs, df_oracle


def save_and_split_dataset(df_obs: pd.DataFrame, df_oracle: pd.DataFrame, output_dir: str, cfg: Dict[str, Any]):
    """Splits dataset temporally into train/val/test and writes CSVs."""
    os.makedirs(output_dir, exist_ok=True)
    
    N = len(df_obs)
    train_end = int(N * cfg["splits"]["train"])
    val_end = int(N * (cfg["splits"]["train"] + cfg["splits"]["val"]))
    
    splits = {
        "train": (0, train_end),
        "val": (train_end, val_end),
        "test": (val_end, N)
    }
    
    print("=== DATASET TEMPORAL SPLIT SUMMARY ===")
    for split_name, (s, e) in splits.items():
        obs_sub = df_obs.iloc[s:e]
        ora_sub = df_oracle.iloc[s:e]
        
        obs_sub.to_csv(os.path.join(output_dir, f"{split_name}.csv"), index=False)
        ora_sub.to_csv(os.path.join(output_dir, f"{split_name}_oracle.csv"), index=False)
        
        print(f"  {split_name.capitalize()}: {len(obs_sub)} events | Range: {obs_sub['failure_timestamp'].min()} to {obs_sub['failure_timestamp'].max()}")
        
    print(f"Dataset successfully saved to {output_dir}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic payment failure dataset")
    parser.add_argument("--config", type=str, default="configs/synthetic_config.yaml", help="Path to config file")
    parser.add_argument("--events", type=int, default=None, help="Override number of events to generate")
    parser.add_argument("--outdir", type=str, default="data/synthetic", help="Output directory")
    args = parser.parse_args()
    
    print("Generating synthetic failure dataset...")
    df_obs, df_ora = generate_dataset(args.config, num_events=args.events)
    cfg = load_config(args.config)
    save_and_split_dataset(df_obs, df_ora, args.outdir, cfg)
