"""
Validation Module
Runs 10 mandatory sanity tests and Anti-Circularity Validation.
"""

import os
import sys

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import numpy as np
import pandas as pd
from typing import Dict, Any
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer

def run_sanity_tests(df_obs: pd.DataFrame, df_oracle: pd.DataFrame) -> Dict[str, Any]:
    """Runs all 10 mandatory validation tests."""
    results = {}
    
    # Test 1: Action Overlap
    # For common segment e.g. soft_decline, check multiple actions exist
    soft_decline_actions = df_obs[df_obs["failure_category"] == "soft_decline"]["logged_action"].nunique()
    results["test1_action_overlap"] = {
        "pass": soft_decline_actions >= 3,
        "detail": f"soft_decline has {soft_decline_actions} unique logged actions."
    }
    
    # Test 2: No Deterministic Action Rule
    max_action_share = df_obs.groupby(["failure_category", "logged_action"]).size().unstack(fill_value=0)
    max_action_share_pct = (max_action_share.T / max_action_share.sum(axis=1)).T
    # Non-safety categories should not have 100% deterministic action selection
    soft_share = max_action_share_pct.loc["soft_decline"].max()
    results["test2_no_deterministic_rule"] = {
        "pass": soft_share < 0.95,
        "detail": f"Max single action share for soft_decline is {soft_share:.2%}."
    }
    
    # Test 3: Outcome Stochasticity
    recovery_rate = df_obs["recovered"].mean()
    results["test3_outcome_stochasticity"] = {
        "pass": 0.10 <= recovery_rate <= 0.60,
        "detail": f"Overall recovery rate is {recovery_rate:.2%}."
    }
    
    # Test 4: Hidden Signal Existence
    p_logged = df_oracle["SYNTHETIC_ORACLE_ONLY_true_recovery_probability_logged"]
    results["test4_hidden_signal"] = {
        "pass": float(p_logged.std()) > 0.05,
        "detail": f"Standard deviation of true recovery probability is {p_logged.std():.4f}."
    }
    
    # Test 5: Baseline Limitation
    b_ev = df_oracle["SYNTHETIC_ORACLE_ONLY_baseline_ev"].mean()
    o_ev = df_oracle["SYNTHETIC_ORACLE_ONLY_true_best_ev"].mean()
    results["test5_baseline_limited"] = {
        "pass": o_ev > b_ev + 5.0,
        "detail": f"Oracle Mean EV ({o_ev:.2f}) beats Baseline Mean EV ({b_ev:.2f}) by {o_ev - b_ev:.2f} INR."
    }
    
    # Test 6: Oracle Sanity
    results["test6_oracle_sanity"] = {
        "pass": o_ev > b_ev,
        "detail": f"Oracle EV ({o_ev:.2f}) is strictly greater than Baseline EV ({b_ev:.2f})."
    }
    
    # Test 7: ML Learnability
    # Train simple Logistic Regression on train split to predict recovery given (features + action)
    feature_cols = [
        "amount", "hour", "day_of_week", "historical_success_rate", "retry_count_before_event",
        "payment_method", "issuer_category", "failure_category", "logged_action", "corridor"
    ]
    
    cat_cols = ["payment_method", "issuer_category", "failure_category", "logged_action", "corridor"]
    num_cols = ["amount", "hour", "day_of_week", "historical_success_rate", "retry_count_before_event"]
    
    from sklearn.preprocessing import StandardScaler
    
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), num_cols),
            ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols)
        ]
    )
    
    X_train = preprocessor.fit_transform(df_obs[feature_cols])
    y_train = df_obs["recovered"]
    
    model = LogisticRegression(max_iter=1000)
    model.fit(X_train, y_train)
    
    y_pred_prob = model.predict_proba(X_train)[:, 1]
    auc = roc_auc_score(y_train, y_pred_prob)
    
    results["test7_ml_learnability"] = {
        "pass": auc > 0.65,
        "detail": f"Baseline ML model achieved ROC AUC of {auc:.4f} on observed training data."
    }
    
    # Test 8: Safety Violations
    violations = 0
    for idx, row in df_obs.iterrows():
        safe_list = row["safe_actions"].split("|")
        if row["logged_action"] not in safe_list:
            violations += 1
            
    results["test8_safety_enforcement"] = {
        "pass": violations == 0,
        "detail": f"Total safety violations found: {violations}."
    }
    
    # Test 9: Feature Leakage Check
    oracle_cols_in_obs = [col for col in df_obs.columns if "ORACLE" in col or "true" in col or "best" in col]
    results["test9_no_feature_leakage"] = {
        "pass": len(oracle_cols_in_obs) == 0,
        "detail": f"Oracle columns present in observed feature dataset: {len(oracle_cols_in_obs)}."
    }
    
    # Test 10: Distribution Summary
    results["test10_distribution_summary"] = {
        "pass": True,
        "detail": {
            "total_events": len(df_obs),
            "overall_recovery_rate": f"{df_obs['recovered'].mean():.2%}",
            "logged_action_counts": df_obs["logged_action"].value_counts().to_dict(),
            "failure_category_counts": df_obs["failure_category"].value_counts().to_dict()
        }
    }
    
    return results

def print_validation_report(results: Dict[str, Any]):
    print("\n========================================================")
    print("           TASK 10 SANITY & VALIDATION SUITE            ")
    print("========================================================")
    all_passed = True
    for key, val in results.items():
        if key == "test10_distribution_summary":
            continue
        status = "PASSED [OK]" if val["pass"] else "FAILED [FAIL]"
        if not val["pass"]:
            all_passed = False
        print(f"[{status}] {key}: {val['detail']}")
        
    print("--------------------------------------------------------")
    print("DISTRIBUTION SUMMARY:")
    summary = results["test10_distribution_summary"]["detail"]
    print(f"  Total Events: {summary['total_events']}")
    print(f"  Recovery Rate: {summary['overall_recovery_rate']}")
    print("  Actions Distribution:")
    for act, count in summary["logged_action_counts"].items():
        print(f"    - {act}: {count} ({count / summary['total_events']:.1%})")
    print("========================================================\n")
    return all_passed
