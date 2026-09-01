"""
API Data Schemas & Pydantic Request/Response Models
Defines FailedPaymentEvent, RecoveryDecisionResponse, ExecutionRequest, ExecutionResponse, and AuditRecordResponse.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class FailedPaymentEvent(BaseModel):
    """Input request model representing a failed payment episode."""
    payment_id: str = Field(..., description="Unique payment identifier", example="pay_88840335")
    amount: float = Field(..., gt=0.0, description="Order transaction value in INR", example=2500.0)
    currency: str = Field(default="INR", description="Transaction currency", example="INR")
    product_category: str = Field(default="ecommerce", description="Product domain category", example="ecommerce")
    is_subscription: int = Field(default=0, ge=0, le=1, description="Subscription flag (0 or 1)", example=0)
    order_value_tier: str = Field(default="medium", description="Order value classification tier", example="medium")
    
    payment_method: str = Field(..., description="Payment method category", example="card_credit")
    issuer_category: str = Field(default="private_bank", description="Issuer bank category", example="private_bank")
    card_network: str = Field(default="visa", description="Card network brand", example="visa")
    
    failure_code: str = Field(..., description="Taxonomy failure code", example="BAD_REQUEST_PAYMENT_TIMED_OUT")
    failure_category: str = Field(..., description="Taxonomy failure category", example="network_timeout")
    error_source: str = Field(default="issuer", description="Error origin source", example="issuer")
    error_step: str = Field(default="payment_authentication", description="Workflow failure step", example="payment_authentication")
    corridor: str = Field(default="domestic", description="Transaction corridor", example="domestic")
    
    merchant_segment: str = Field(default="sme", description="Merchant size segment", example="sme")
    merchant_category: str = Field(default="ecommerce", description="Merchant industry category", example="ecommerce")
    
    customer_tenure_days: int = Field(default=180, ge=0, description="Customer relationship tenure in days", example=180)
    historical_success_rate: float = Field(default=0.85, ge=0.0, le=1.0, description="Historical customer success rate", example=0.85)
    historical_failed_attempts: int = Field(default=1, ge=0, description="Historical customer failed attempts count", example=1)
    historical_retry_count: int = Field(default=0, ge=0, description="Historical customer retries count", example=0)
    time_since_last_success_hours: float = Field(default=24.0, ge=0.0, description="Hours since last successful payment", example=24.0)
    retry_count_before_event: int = Field(default=0, ge=0, description="Retries already attempted for this specific order episode", example=0)
    
    hour: int = Field(default=14, ge=0, le=23, description="Failure hour (0-23)", example=14)
    day_of_week: int = Field(default=2, ge=0, le=6, description="Failure day of week (0=Mon, 6=Sun)", example=2)
    is_weekend: int = Field(default=0, ge=0, le=1, description="Weekend flag (0 or 1)", example=0)


class RecoveryDecisionResponse(BaseModel):
    """Structured recovery decision response model."""
    decision_id: str = Field(..., description="Unique decision UUID")
    payment_id: str = Field(..., description="Payment identifier")
    action: str = Field(..., description="Selected safe recovery action")
    confidence: str = Field(..., description="Model probability confidence level (high, medium, low)")
    recovery_probability: float = Field(..., ge=0.0, le=1.0, description="Estimated recovery probability P(rec|X, a)")
    expected_value: float = Field(..., description="Net Expected Economic Value EV(a|X) in INR")
    safe: bool = Field(..., description="Flag indicating safety gate clearance")
    safety_rule: str = Field(..., description="Applied safety gate constraint explanation")
    reason: str = Field(..., description="Evidence-based deterministic decision rationale")
    status: str = Field(..., description="Decision status: APPROVED, ESCALATE, or STOP")
    stopping_rule: Optional[str] = Field(default=None, description="Applied stopping rule identifier if stopped or escalated")
    timestamp: str = Field(..., description="Decision ISO-8601 UTC timestamp")
    execution_available: bool = Field(..., description="Flag indicating execution eligibility")


class ExecutionRequest(BaseModel):
    """Request model for simulated action execution."""
    decision_id: str = Field(..., description="Decision UUID to execute")
    payment_id: str = Field(..., description="Associated payment ID")
    action: str = Field(..., description="Approved action string to execute")


class ExecutionResponse(BaseModel):
    """Response model for simulated action execution."""
    execution_id: str = Field(..., description="Unique execution UUID")
    decision_id: str = Field(..., description="Associated decision UUID")
    payment_id: str = Field(..., description="Associated payment ID")
    action: str = Field(..., description="Executed action string")
    status: str = Field(..., description="Execution status: executed, scheduled, stopped, escalated, or rejected")
    message: str = Field(..., description="Execution status detail message")
    timestamp: str = Field(..., description="Execution ISO-8601 UTC timestamp")


class AuditRecordResponse(BaseModel):
    """Full decision audit trail response model."""
    decision_id: str
    timestamp: str
    payment_id: str
    input_context: Dict[str, Any]
    candidate_actions: List[str]
    safe_actions: List[str]
    predicted_probabilities: Dict[str, float]
    expected_values: Dict[str, float]
    selected_action: str
    confidence: str
    recovery_probability: float
    expected_value: float
    safe: bool
    safety_rule: str
    reason: str
    status: str
    stopping_rule: Optional[str]
    execution_status: str = "pending"
