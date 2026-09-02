"""
Robustness Evaluation Runner Script
Runs Task 12 experimental suite, generates reports/task12_robustness.json, and creates publication figures.
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
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.data.failure_taxonomy import ALL_ACTIONS
from src.models.recovery_predictor import RecoveryPredictor
from src.policy.advisor import PolicyAdvisor
from src.evaluation.robustness import (
    run_economic_sensitivity,
    run_ablation_study,
    run_distribution_shifts,
    run_stress_testing,
    run_ground_truth_robustness
)

def generate_robustness_plots(results: dict, fig_dir: str = "reports/figures/task12"):
    os.makedirs(fig_dir, exist_ok=True)
    
    # 1. Economic Sensitivity Plot
    econ_res = results["economic_sensitivity"]
    scenarios = list(econ_res.keys())
    
    ml_evs = [econ_res[s]["ml_policy_ev_ci"]["mean"] for s in scenarios]
    base_evs = [econ_res[s]["baseline_policy_ev_ci"]["mean"] for s in scenarios]
    ora_evs = [econ_res[s]["oracle_best_ev_ci"]["mean"] for s in scenarios]
    
    x = np.arange(len(scenarios))
    width = 0.25
    
    plt.figure(figsize=(10, 5))
    plt.bar(x - width, base_evs, width, label="Deterministic Baseline", color="#f59e0b")
    plt.bar(x, ml_evs, width, label="O1 ML Advisor Policy", color="#10b981")
    plt.bar(x + width, ora_evs, width, label="Oracle Best Policy", color="#6366f1")
    plt.xticks(x, [s.replace("_", "\n") for s in scenarios], fontsize=9)
    plt.ylabel("Mean Oracle Expected Value (INR / event)", fontsize=11)
    plt.title("Economic Sensitivity Analysis (Task 12 Synthetic Environment)", fontsize=12, fontweight="bold")
    plt.legend()
    plt.grid(axis="y", linestyle=":", alpha=0.6)
    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, "fig1_economic_sensitivity.png"), dpi=300)
    plt.close()
    
    # 2. Ablation Comparison Plot
    abl_res = results["ablation_study"]
    abl_names = list(abl_res.keys())
    abl_evs = [abl_res[a]["mean_oracle_ev_inr"] for a in abl_names]
    
    fig, ax1 = plt.subplots(figsize=(10, 5))
    x_abl = np.arange(len(abl_names))
    
    bars = ax1.bar(x_abl, abl_evs, color="#2563eb", width=0.4, label="Mean Oracle EV (INR)")
    ax1.set_ylabel("Mean Oracle Expected Value (INR)", fontsize=11, color="#2563eb")
    ax1.set_xticks(x_abl)
    ax1.set_xticklabels([a.replace("_", "\n") for a in abl_names], fontsize=9)
    ax1.grid(axis="y", linestyle=":", alpha=0.6)
    
    for bar in bars:
        h = bar.get_height()
        ax1.annotate(f"₹{h:.1f}", xy=(bar.get_x() + bar.get_width() / 2, h),
                     xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=9, fontweight="bold")
                     
    plt.title("Ablation Study: Architecture Components & Safety Gate Impact", fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, "fig2_ablation_comparison.png"), dpi=300)
    plt.close()
    
    # 3. Distribution Shift Performance Plot
    shift_res = results["distribution_shifts"]
    shift_names = list(shift_res.keys())
    shift_ml = [shift_res[s]["ml_policy_ev_ci"]["mean"] for s in shift_names]
    shift_base = [shift_res[s]["baseline_policy_ev_ci"]["mean"] for s in shift_names]
    shift_ora = [shift_res[s]["oracle_best_ev_ci"]["mean"] for s in shift_names]
    
    x_shift = np.arange(len(shift_names))
    
    plt.figure(figsize=(10, 5))
    plt.bar(x_shift - width, shift_base, width, label="Deterministic Baseline", color="#f59e0b")
    plt.bar(x_shift, shift_ml, width, label="O1 ML Advisor Policy", color="#10b981")
    plt.bar(x_shift + width, shift_ora, width, label="Oracle Best Policy", color="#6366f1")
    plt.xticks(x_shift, [s.replace("_", "\n") for s in shift_names], fontsize=9)
    plt.ylabel("Mean Oracle Expected Value (INR / event)", fontsize=11)
    plt.title("Distribution Shift Performance (Without Retraining)", fontsize=12, fontweight="bold")
    plt.legend()
    plt.grid(axis="y", linestyle=":", alpha=0.6)
    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, "fig3_distribution_shift.png"), dpi=300)
    plt.close()
    
    # 4. Regret Distribution Plot
    baseline_regrets = [econ_res["BASELINE"]["regret_ci"]["mean"]]
    plt.figure(figsize=(7, 5))
    plt.bar(["Baseline Scenario"], baseline_regrets, color="#ef4444", width=0.3)
    plt.ylabel("Mean Policy Regret vs Oracle Best (INR)", fontsize=11)
    plt.title("O1 ML Policy Regret Relative to Oracle Best (Test Set)", fontsize=12, fontweight="bold")
    plt.grid(axis="y", linestyle=":", alpha=0.6)
    for i, v in enumerate(baseline_regrets):
        plt.text(i, v + 0.05, f"₹{v:.2f}", ha="center", fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, "fig4_regret_distribution.png"), dpi=300)
    plt.close()
    
    # 5. Action Distributions Across Scenarios Plot
    plt.figure(figsize=(10, 5))
    actions = ["retry_now", "retry_later", "switch_method", "update_information", "do_nothing"]
    base_dist = econ_res["BASELINE"]["action_distribution"]
    high_val_dist = econ_res["HIGH_VALUE"]["action_distribution"]
    high_fric_dist = econ_res["HIGH_FRICTION"]["action_distribution"]
    
    x_act = np.arange(len(actions))
    w = 0.25
    plt.bar(x_act - w, [base_dist.get(a, 0)*100 for a in actions], w, label="Baseline Economics", color="#3b82f6")
    plt.bar(x_act, [high_val_dist.get(a, 0)*100 for a in actions], w, label="High Order Value (2.0x)", color="#10b981")
    plt.bar(x_act + w, [high_fric_dist.get(a, 0)*100 for a in actions], w, label="High Friction (2.0x)", color="#8b5cf6")
    plt.xticks(x_act, [a.replace("_", "\n") for a in actions], fontsize=9)
    plt.ylabel("Action Share (%)", fontsize=11)
    plt.title("Action Selection Sensitivity Across Economic Scenarios", fontsize=12, fontweight="bold")
    plt.legend()
    plt.grid(axis="y", linestyle=":", alpha=0.6)
    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, "fig5_action_distributions.png"), dpi=300)
    plt.close()
    
    print(f"Generated 5 Task 12 robustness figures in {fig_dir}/")

def main():
    print("Loading test datasets...")
    df_test_obs = pd.read_csv("data/synthetic/test.csv")
    df_test_oracle = pd.read_csv("data/synthetic/test_oracle.csv")
    
    model_path = "models/recovery_predictor.joblib"
    print(f"Loading RecoveryPredictor from {model_path}...")
    predictor = RecoveryPredictor.load(model_path)
    advisor = PolicyAdvisor(predictor=predictor, config_path="configs/synthetic_config.yaml")
    
    print("Pre-computing batch model predictions for test dataset...")
    precomputed_probs = {a: predictor.predict_proba(df_test_obs, action=a) for a in ALL_ACTIONS}
    
    print("\n--- RUNNING TASK 12 EXPERIMENTAL SUITE ---")
    
    print("1. Running Economic Sensitivity Scenarios...")
    econ_results = run_economic_sensitivity(advisor, df_test_obs, df_test_oracle, precomputed_probs=precomputed_probs)
    
    print("2. Running Ablation Study...")
    ablation_results = run_ablation_study(advisor, df_test_obs, df_test_oracle, precomputed_probs=precomputed_probs)
    
    print("3. Running Distribution Shift Scenarios...")
    shift_results = run_distribution_shifts(advisor, df_test_obs, df_test_oracle)
    
    print("4. Running Stress Testing...")
    stress_results = run_stress_testing(advisor, df_test_obs, df_test_oracle, precomputed_probs=precomputed_probs)

    print("5. Running Ground-Truth Interaction Robustness...")
    gt_results = run_ground_truth_robustness(advisor, df_test_obs, precomputed_probs=precomputed_probs)

    all_results = {
        "economic_sensitivity": econ_results,
        "ground_truth_robustness": gt_results,
        "ablation_study": ablation_results,
        "distribution_shifts": shift_results,
        "stress_testing": stress_results
    }
    
    os.makedirs("reports", exist_ok=True)
    report_path = "reports/task12_robustness.json"
    with open(report_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nSaved Task 12 results JSON to {report_path}")
    
    generate_robustness_plots(all_results)

if __name__ == "__main__":
    main()
