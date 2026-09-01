"""
Recovery Predictor Module
Implements RecoveryPredictor interface wrapper for estimating P(recovery | X, action).
Supports candidate selection, probability calibration, evaluation, and serialization.
"""

import os
import sys
import joblib
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any, Union

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.metrics import roc_auc_score, log_loss, brier_score_loss

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from src.models.preprocessing import build_preprocessing_pipeline, prepare_feature_dataframe, ALL_PREDICTOR_FEATURES

class RecoveryPredictor:
    """
    Probabilistic estimator for P(recovery = 1 | X, action).
    """

    def __init__(self, model_type: str = "hist_gb", calibrate: bool = True):
        self.model_type = model_type
        self.calibrate = calibrate
        self.pipeline = build_preprocessing_pipeline()
        self.model = None
        self.is_fitted = False
        
        # Instantiate base estimator
        if model_type == "logistic_regression":
            self.base_estimator = LogisticRegression(max_iter=500, random_state=42)
        elif model_type == "random_forest":
            self.base_estimator = RandomForestClassifier(n_estimators=50, max_depth=10, random_state=42, n_jobs=-1)
        elif model_type == "hist_gb":
            self.base_estimator = HistGradientBoostingClassifier(max_iter=50, max_depth=6, random_state=42)
        else:
            raise ValueError(f"Unknown model_type: {model_type}")

    def fit(self, df_train: pd.DataFrame, df_val: pd.DataFrame = None, target_col: str = "recovered", action_col: str = "logged_action"):
        """
        Fits preprocessing pipeline and estimator on training dataframe.
        """
        X_train_df = prepare_feature_dataframe(df_train, action_col=action_col)
        y_train = df_train[target_col].values
        
        # Fit preprocessor on training data
        X_train_trans = self.pipeline.fit_transform(X_train_df)
        
        if self.calibrate:
            # Fit CalibratedClassifierCV using 5-fold cross-validation on training data
            calibrated_model = CalibratedClassifierCV(estimator=self.base_estimator, method="sigmoid", cv=5)
            calibrated_model.fit(X_train_trans, y_train)
            self.model = calibrated_model
        else:
            self.base_estimator.fit(X_train_trans, y_train)
            self.model = self.base_estimator
            
        self.is_fitted = True
        return self

    def predict_proba(self, df_context: pd.DataFrame, action: Union[str, List[str]]) -> np.ndarray:
        """
        Predicts P(recovery = 1 | X, action).
        df_context: DataFrame containing context features X (single row or multiple rows).
        action: single action string or list of action strings matching rows of df_context.
        """
        if not self.is_fitted:
            raise RuntimeError("RecoveryPredictor must be fitted before calling predict_proba.")
            
        df_eval = df_context.copy()
        if isinstance(action, str):
            df_eval["action"] = action
        elif isinstance(action, list):
            df_eval["action"] = action
        else:
            raise TypeError("action must be a string or a list of strings.")
            
        X_eval = prepare_feature_dataframe(df_eval, action_col="action")
        X_trans = self.pipeline.transform(X_eval)
        
        probs = self.model.predict_proba(X_trans)[:, 1]
        return np.round(probs, 4)

    def predict_proba_all_actions(self, df_context: pd.DataFrame, safe_actions: List[str]) -> Dict[str, np.ndarray]:
        """
        Evaluates candidate probabilities P(recovery = 1 | X, a) for all specified safe actions.
        Returns dict mapping action_name -> proba array.
        """
        results = {}
        for a in safe_actions:
            results[a] = self.predict_proba(df_context, action=a)
        return results

    def evaluate(self, df_test: pd.DataFrame, target_col: str = "recovered", action_col: str = "logged_action") -> Dict[str, float]:
        """
        Evaluates model predictions on observed test set.
        """
        X_test_df = prepare_feature_dataframe(df_test, action_col=action_col)
        y_test = df_test[target_col].values
        
        X_trans = self.pipeline.transform(X_test_df)
        y_probs = self.model.predict_proba(X_trans)[:, 1]
        
        auc = roc_auc_score(y_test, y_probs)
        ll = log_loss(y_test, y_probs)
        bs = brier_score_loss(y_test, y_probs)
        
        prob_true, prob_pred = calibration_curve(y_test, y_probs, n_bins=10)
        cal_error = float(np.mean(np.abs(prob_true - prob_pred)))
        
        return {
            "roc_auc": float(np.round(auc, 4)),
            "log_loss": float(np.round(ll, 4)),
            "brier_score": float(np.round(bs, 4)),
            "mean_calibration_error": float(np.round(cal_error, 4))
        }

    def save(self, filepath: str):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump(self, filepath)

    @classmethod
    def load(cls, filepath: str) -> "RecoveryPredictor":
        return joblib.load(filepath)
