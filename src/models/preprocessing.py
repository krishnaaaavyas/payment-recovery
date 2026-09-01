"""
Preprocessing Module
Defines context features, action feature, and scikit-learn ColumnTransformer pipeline.
Fitted strictly on training data without leakage.
"""

import os
import sys

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder

NUMERIC_FEATURES = [
    "amount",
    "customer_tenure_days",
    "historical_success_rate",
    "historical_failed_attempts",
    "historical_retry_count",
    "time_since_last_success_hours",
    "retry_count_before_event",
    "hour",
    "day_of_week",
    "is_weekend"
]

CATEGORICAL_FEATURES = [
    "currency",
    "product_category",
    "is_subscription",
    "order_value_tier",
    "payment_method",
    "issuer_category",
    "card_network",
    "failure_code",
    "failure_category",
    "error_source",
    "error_step",
    "corridor",
    "merchant_segment",
    "merchant_category"
]

ACTION_FEATURE = "action"

ALL_PREDICTOR_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES + [ACTION_FEATURE]

def build_preprocessing_pipeline() -> ColumnTransformer:
    """
    Constructs a ColumnTransformer preprocessing pipeline.
    StandardScaler for numeric features, OneHotEncoder for categorical features and action.
    """
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES + [ACTION_FEATURE])
        ],
        remainder="drop"
    )
    return preprocessor

def prepare_feature_dataframe(df: pd.DataFrame, action_col: str = "logged_action") -> pd.DataFrame:
    """
    Extracts feature columns from raw dataframe and renames action_col to 'action'.
    """
    cols_to_extract = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    df_feat = df[cols_to_extract].copy()
    
    if action_col in df.columns:
        df_feat["action"] = df[action_col].astype(str)
    elif "action" in df.columns:
        df_feat["action"] = df["action"].astype(str)
    else:
        raise ValueError(f"Action column '{action_col}' or 'action' not found in dataframe.")
        
    return df_feat
