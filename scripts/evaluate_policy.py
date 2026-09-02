"""
Policy Evaluation & Visualization Script
Runs full policy evaluation suite, outputs JSON report, and generates publication plots.
"""

import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
from sklearn.calibration import calibration_curve

from src.models.recovery_predictor import RecoveryPredictor
from src.policy.advisor import PolicyAdvisor
from src.policy.evaluation import run_policy_evaluation

def generate_plots(predictor: RecoveryPredictor, advisor: PolicyAdvisor, df_test_obs: pd.DataFrame, df_test_oracle: pd.DataFrame, eval_results: dict):
    fig_dir = "reports/figures"
    os.makedirs(fig_dir, exist_ok=True)
    
    # 1. Calibration Curve Plot
    X_test_df = df_test_obs.copy()
    y_test = df_test_obs["recovered"].values
    y_probs = predictor.predict_proba(X_test_df, action=df_test_obs["logged_action"].tolist())
    
    prob_true, prob_pred = calibration_curve(y_test, y_probs, n_bins=10)
    
    plt.figure(figsize=(7, 5))
    plt.plot([0, 1], [0, 1], "k--", label="Perfect Calibration")
    plt.plot(prob_pred, prob_true, "s-", color="#2b5c8f", label="O1 RecoveryPredictor")
    plt.xlabel("Mean Predicted Probability", fontsize=11)
    plt.ylabel("Fraction of Positives (Observed Recovery)", fontsize=11)
    plt.title("Model Probability Calibration Curve (Test Set)", fontsize=12, fontweight="bold")
    plt.legend(loc="lower right")
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, "calibration_curve.png"), dpi=300)
    plt.close()
    
    # 2. Predicted Probability Distribution Plot
    plt.figure(figsize=(7, 5))
    plt.hist(y_probs, bins=30, color="#3b82f6", edgecolor="black", alpha=0.75)
    plt.axvline(np.mean(y_probs), color="#ef4444", linestyle="--", linewidth=2, label=f"Mean: {np.mean(y_probs):.4f}")
    plt.xlabel("Predicted Recovery Probability P(recovery | X, logged_action)", fontsize=11)
    plt.ylabel("Frequency", fontsize=11)
    plt.title("Predicted Recovery Probability Distribution (Test Set)", fontsize=12, fontweight="bold")
    plt.legend()
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, "prob_distribution.png"), dpi=300)
    plt.close()
    
    # 3. Policy Action Distribution Plot
    logged_dist = df_test_obs["logged_action"].value_counts(normalize=True)
    ml_dist = pd.Series(eval_results["distributions"]["ml_action_distribution"])
    
    actions = ["retry_now", "retry_later", "switch_method", "update_information", "do_nothing"]
    logged_vals = [logged_dist.get(a, 0.0) * 100 for a in actions]
    ml_vals = [ml_dist.get(a, 0.0) * 100 for a in actions]
    
    x = np.arange(len(actions))
    width = 0.35
    
    plt.figure(figsize=(9, 5))
    plt.bar(x - width/2, logged_vals, width, label="Historical Logged Policy", color="#94a3b8")
    plt.bar(x + width/2, ml_vals, width, label="O1 ML Policy Advisor", color="#2563eb")
    plt.xticks(x, [a.replace("_", "\n") for a in actions], fontsize=10)
    plt.ylabel("Action Selection Share (%)", fontsize=11)
    plt.title("Action Selection Share Comparison", fontsize=12, fontweight="bold")
    plt.legend()
    plt.grid(axis="y", linestyle=":", alpha=0.6)
    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, "action_distribution.png"), dpi=300)
    plt.close()
    
    # 4. EV Comparison Plot (Direct ground truth = authoritative; SNIPS = estimator)
    ips_b = eval_results["off_policy_snips_evaluation"]["baseline_policy_snips_ev_inr"]
    ips_ml = eval_results["off_policy_snips_evaluation"]["ml_policy_snips_ev_inr"]

    ora_b = eval_results["direct_ground_truth_benchmark"]["direct_true_baseline_policy_ev_inr"]
    ora_ml = eval_results["direct_ground_truth_benchmark"]["direct_true_o1_policy_ev_inr"]
    ora_opt = eval_results["direct_ground_truth_benchmark"]["direct_true_oracle_best_ev_inr"]

    fig, ax = plt.subplots(figsize=(9, 5))
    categories = ["SNIPS Off-Policy Estimate\n(38.5% matched episodes)", "Direct Ground-Truth Simulator\n(AUTHORITATIVE, 100% of episodes)"]
    
    b_scores = [ips_b, ora_b]
    ml_scores = [ips_ml, ora_ml]
    
    x = np.arange(len(categories))
    width = 0.25
    
    rects1 = ax.bar(x - width, b_scores, width, label="Deterministic Baseline", color="#f59e0b")
    rects2 = ax.bar(x, ml_scores, width, label="O1 ML Advisor Policy", color="#10b981")
    rects3 = ax.bar(x + width, [np.nan, ora_opt], width, label="Oracle Best Policy", color="#6366f1")
    
    ax.set_ylabel("Expected Economic Value (INR / failure event)", fontsize=11)
    ax.set_title("Policy Economic Performance Comparison", fontsize=12, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=10)
    ax.legend()
    ax.grid(axis="y", linestyle=":", alpha=0.6)
    
    # Value labels
    for rect in rects1 + rects2 + rects3:
        h = rect.get_height()
        if not np.isnan(h):
            ax.annotate(f"₹{h:.1f}",
                        xy=(rect.get_x() + rect.get_width() / 2, h),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha="center", va="bottom", fontsize=9, fontweight="bold")
                        
    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, "ev_comparison.png"), dpi=300)
    plt.close()
    
    print(f"Generated 4 evaluation figures in {fig_dir}/")

def main():
    print("Loading test datasets...")
    df_test_obs = pd.read_csv("data/synthetic/test.csv")
    df_test_oracle = pd.read_csv("data/synthetic/test_oracle.csv")
    
    model_path = "models/recovery_predictor.joblib"
    print(f"Loading RecoveryPredictor model from {model_path}...")
    predictor = RecoveryPredictor.load(model_path)
    
    advisor = PolicyAdvisor(predictor=predictor, config_path="configs/synthetic_config.yaml")
    
    print("Executing Policy Evaluation Suite...")
    eval_results = run_policy_evaluation(advisor, df_test_obs, df_test_oracle)
    
    # Print evaluation summary to stdout
    direct = eval_results["direct_ground_truth_benchmark"]
    snips = eval_results["off_policy_snips_evaluation"]

    print("\n========================================================")
    print("         TASK 11 POLICY EVALUATION SUMMARY              ")
    print("========================================================")
    print(f"Test Failure Episodes:         {eval_results['test_events_count']}")
    print(f"Safety Violation Count / Rate: {eval_results['safety_evaluation']['safety_violations_count']} ({eval_results['safety_evaluation']['safety_violation_rate']:.2%})")
    print("--------------------------------------------------------")
    print("[AUTHORITATIVE] DIRECT GROUND-TRUTH SIMULATOR BENCHMARK:")
    print(f"  Events Evaluated:                {direct['events_evaluated']} / {direct['events_in_population']} (missing: {direct['events_missing_ground_truth']})")
    print(f"  Direct True Baseline Policy EV:  ₹{direct['direct_true_baseline_policy_ev_inr']:.2f}")
    print(f"  Direct True O1 Policy EV:        ₹{direct['direct_true_o1_policy_ev_inr']:.2f}")
    print(f"  Direct True Oracle Best EV:      ₹{direct['direct_true_oracle_best_ev_inr']:.2f}")
    print(f"  Direct True Regret:              ₹{direct['direct_true_regret_inr_per_event']:.4f} / event")
    print(f"  Direct Policy Efficiency:        {direct['direct_policy_efficiency']:.4%}")
    print(f"  Direct Uplift over Baseline:     ₹{direct['direct_uplift_over_baseline_inr_per_event']:.2f} / event ({direct['direct_uplift_over_baseline_pct']:.2f}%)")
    print(f"  Per-Event Dominance Violations:  {direct['per_event_dominance_violations']} (regret min ₹{direct['per_event_regret_min']:.6f})")
    print("--------------------------------------------------------")
    print("[ESTIMATOR] SNIPS OFF-POLICY EVALUATION (not ground truth):")
    print(f"  Logged Policy Realized Mean EV:  ₹{snips['logged_policy_realized_mean_ev_inr']:.2f}")
    print(f"  Baseline Policy SNIPS EV:        ₹{snips['baseline_policy_snips_ev_inr']:.2f} "
          f"[95% CI ₹{snips['baseline_policy_snips_ci']['ci_lower']:.2f}–₹{snips['baseline_policy_snips_ci']['ci_upper']:.2f}] "
          f"(Coverage: {snips['baseline_policy_coverage_rate']:.1%}, ESS: {snips['baseline_effective_sample_size']:.1f})")
    print(f"  O1 ML Policy SNIPS EV:           ₹{snips['ml_policy_snips_ev_inr']:.2f} "
          f"[95% CI ₹{snips['ml_policy_snips_ci']['ci_lower']:.2f}–₹{snips['ml_policy_snips_ci']['ci_upper']:.2f}] "
          f"(Coverage: {snips['ml_policy_coverage_rate']:.1%}, ESS: {snips['ml_effective_sample_size']:.1f})")
    print(f"  SNIPS minus Direct True EV:      ₹{snips['snips_minus_direct_true_ev_inr']:.2f} (estimator variance, not a gain)")
    print("========================================================\n")
    
    # Save evaluation report JSON
    os.makedirs("reports", exist_ok=True)
    report_path = "reports/task11_policy_evaluation.json"
    with open(report_path, "w") as f:
        json.dump(eval_results, f, indent=2)
    print(f"Saved evaluation results JSON to {report_path}")
    
    # Generate Plots
    generate_plots(predictor, advisor, df_test_obs, df_test_oracle, eval_results)

if __name__ == "__main__":
    main()
