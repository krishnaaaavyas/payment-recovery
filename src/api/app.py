"""
FastAPI Application Module
Provides endpoints:
- GET /health
- POST /decide
- POST /execute
- GET /audit/{decision_id}
"""

import os
import sys

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import JSONResponse

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


@app.get("/health", response_model=dict, tags=["Health"])
def health_check():
    """Returns service health status."""
    return {
        "status": "ok",
        "service": "payment-recovery-advisor",
        "version": "1.0.0",
        "data_tier": "TIER C — Synthetic Evaluation Environment"
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
