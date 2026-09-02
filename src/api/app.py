"""
FastAPI Application Module
Provides endpoints:
- GET /health
- POST /decide
- POST /execute
- GET /audit/{decision_id}
- GET /events
- GET /reports/summary
"""

import os
import sys
import json
import pandas as pd

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from src.api.schemas import (
    FailedPaymentEvent,
    RecoveryDecisionResponse,
    ExecutionRequest,
    ExecutionResponse,
    AuditRecordResponse
)
from src.api.dependencies import get_recovery_agent, get_executor
from src.agent.recovery_agent import RecoveryAgent
from src.agent.executor import SimulatedRecoveryExecutor
from src.agent.audit import audit_store

app = FastAPI(
    title="O1 — Payment Failure Economic Recovery Advisor API",
    description="Post-payment-failure economic decision service for Razorpay Track 03 (Synthetic Environment)",
    version="1.0.0"
)

# Enable CORS for frontend dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=dict, tags=["Health"])
def health_check():
    """Returns service health status."""
    return {
        "status": "ok",
        "service": "payment-recovery-advisor",
        "version": "1.0.0",
        "data_tier": "TIER C — Synthetic Evaluation Environment"
    }


@app.get("/events", response_model=list, tags=["Events"])
def get_sample_events(limit: int = Query(default=50, ge=1, le=500)):
    """
    Returns a sample list of synthetic failed payment events for dashboard queue inspection.
    """
    test_csv = os.path.join(repo_root, "data/synthetic/test.csv")
    if not os.path.exists(test_csv):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Synthetic test dataset not found."
        )
    df_test = pd.read_csv(test_csv).head(limit)
    events = []
    for _, row in df_test.iterrows():
        events.append({
            "payment_id": f"pay_{row['event_id']}",
            "amount": float(row["amount"]),
            "currency": row["currency"],
            "product_category": row["product_category"],
            "is_subscription": int(row["is_subscription"]),
            "order_value_tier": row["order_value_tier"],
            "payment_method": row["payment_method"],
            "issuer_category": row["issuer_category"],
            "card_network": row["card_network"],
            "failure_code": row["failure_code"],
            "failure_category": row["failure_category"],
            "error_source": row["error_source"],
            "error_step": row["error_step"],
            "corridor": row["corridor"],
            "merchant_segment": row["merchant_segment"],
            "merchant_category": row["merchant_category"],
            "customer_tenure_days": int(row["customer_tenure_days"]),
            "historical_success_rate": float(row["historical_success_rate"]),
            "historical_failed_attempts": int(row["historical_failed_attempts"]),
            "historical_retry_count": int(row["historical_retry_count"]),
            "time_since_last_success_hours": float(row["time_since_last_success_hours"]),
            "retry_count_before_event": int(row["retry_count_before_event"]),
            "hour": int(row["hour"]),
            "day_of_week": int(row["day_of_week"]),
            "is_weekend": int(row["is_weekend"]),
            "logged_action": row["logged_action"],
            "failure_timestamp": row["failure_timestamp"]
        })
    return events


@app.get("/reports/summary", response_model=dict, tags=["Reports"])
def get_evaluation_reports():
    """
    Returns Task 11 and Task 12 evaluation metrics JSON objects for dashboard evaluation view.
    """
    def _load(rel_path):
        full = os.path.join(repo_root, rel_path)
        if not os.path.exists(full):
            return {}
        with open(full, "r") as f:
            return json.load(f)

    return {
        "task11_model_results": _load("reports/task11_model_results.json"),
        "task11_policy_evaluation": _load("reports/task11_policy_evaluation.json"),
        "task12_robustness": _load("reports/task12_robustness.json"),
    }


@app.post("/decide", response_model=RecoveryDecisionResponse, tags=["Decision"])
def evaluate_payment_failure(
    event: FailedPaymentEvent,
    agent: RecoveryAgent = Depends(get_recovery_agent)
):
    """
    Evaluates a payment failure event episode and returns a bounded, safe, economic recovery decision.
    """
    try:
        decision_dict = agent.decide(event)
        return RecoveryDecisionResponse(**decision_dict)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error evaluating payment failure decision: {str(e)}"
        )


@app.post("/execute", response_model=ExecutionResponse, tags=["Execution"])
def execute_simulated_action(
    req: ExecutionRequest,
    executor: SimulatedRecoveryExecutor = Depends(get_executor)
):
    """
    Simulates recovery action execution for an approved decision ID.
    Rejects unsafe, unknown, stopped, or escalated decisions.
    """
    success, res = executor.execute(
        decision_id=req.decision_id,
        payment_id=req.payment_id,
        action=req.action
    )
    if not success and res.get("status") in ["rejected", "stopped", "escalated"]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=res
        )
    return ExecutionResponse(**res)


@app.get("/audit/{decision_id}", response_model=AuditRecordResponse, tags=["Audit"])
def get_decision_audit(decision_id: str):
    """
    Retrieves full audit trail record for a given decision_id.
    Returns HTTP 404 if decision_id is not found.
    """
    record = audit_store.get_audit(decision_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit record for decision_id '{decision_id}' not found."
        )
    return AuditRecordResponse(**record)
