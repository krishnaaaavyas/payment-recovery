"""
Model Training Script
Trains, calibrates, evaluates, and selects best RecoveryPredictor model.
"""

import os
import sys

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import json
import pandas as pd
from src.models.recovery_predictor import RecoveryPredictor

def main():
    print("Loading datasets...")
    df_train = pd.read_csv("data/synthetic/train.csv")
    df_val = pd.read_csv("data/synthetic/val.csv")
    
    candidates = [
        ("logistic_regression", False),
        ("logistic_regression", True),
        ("random_forest", False),
        ("random_forest", True),
        ("hist_gb", False),
        ("hist_gb", True),
    ]
    
    results = {}
    best_predictor = None
    best_brier = float("inf")
    best_name = ""
    
    print("\n--- EVALUATING MODEL CANDIDATES ON VALIDATION SET ---")
    for model_type, calibrate in candidates:
        name = f"{model_type}_calibrated" if calibrate else f"{model_type}_uncalibrated"
        print(f"Training {name}...")
        
        predictor = RecoveryPredictor(model_type=model_type, calibrate=calibrate)
        predictor.fit(df_train=df_train, df_val=df_val if calibrate else None)
        
        metrics = predictor.evaluate(df_val)
        results[name] = metrics
        print(f"  [{name}] ROC AUC: {metrics['roc_auc']:.4f} | Log Loss: {metrics['log_loss']:.4f} | Brier Score: {metrics['brier_score']:.4f} | Cal Error: {metrics['mean_calibration_error']:.4f}")
        
        # Select best model prioritizing Brier Score and Log Loss
        if metrics["brier_score"] < best_brier:
            best_brier = metrics["brier_score"]
            best_predictor = predictor
            best_name = name
            
    print(f"\n========================================================")
    print(f"  SELECTED OPTIMAL MODEL: {best_name}")
    print(f"  Validation Brier Score: {results[best_name]['brier_score']:.4f}")
    print(f"  Validation Log Loss:    {results[best_name]['log_loss']:.4f}")
    print(f"  Validation ROC AUC:     {results[best_name]['roc_auc']:.4f}")
    print(f"========================================================\n")
    
    # Save model
    model_path = "models/recovery_predictor.joblib"
    best_predictor.save(model_path)
    print(f"Saved optimal RecoveryPredictor model to {model_path}")
    
    # Save results JSON
    os.makedirs("reports", exist_ok=True)
    report_data = {
        "selected_model": best_name,
        "validation_metrics": results[best_name],
        "all_candidate_metrics": results
    }
    with open("reports/task11_model_results.json", "w") as f:
        json.dump(report_data, f, indent=2)
    print("Saved training results to reports/task11_model_results.json")

if __name__ == "__main__":
    main()
