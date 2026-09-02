"""
API Data Schemas & Pydantic Request/Response Models
Defines FailedPaymentEvent, RecoveryDecisionResponse, ExecutionRequest, ExecutionResponse, and AuditRecordResponse.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, ConfigDict, Field

from src.data.failure_taxonomy import (
    FAILURE_CATEGORIES,
    FAILURE_CODES,
    PAYMENT_METHODS,
    ISSUER_CATEGORIES,
    CARD_NETWORKS,
    CORRIDORS,
    PRODUCT_CATEGORIES,
    MERCHANT_SEGMENTS,
    MERCHANT_CATEGORIES,
    ORDER_VALUE_TIERS,
    CURRENCIES,
    ERROR_SOURCES,
    ERROR_STEPS,
)


def _str_enum(name: str, values) -> type:
    """Builds a str-valued Enum so Pydantic rejects out-of-vocabulary input with HTTP 422."""
    return Enum(name, {v: v for v in values}, type=str)


# Closed vocabularies, derived from the single source of truth in failure_taxonomy.
# Any value outside these sets is rejected by FastAPI with HTTP 422 rather than being
# silently encoded as an all-zero one-hot block (TASK_16A audit, findings C-2 and N-1).
FailureCategoryEnum = _str_enum("FailureCategoryEnum", FAILURE_CATEGORIES)
FailureCodeEnum = _str_enum("FailureCodeEnum", FAILURE_CODES)
PaymentMethodEnum = _str_enum("PaymentMethodEnum", PAYMENT_METHODS)
IssuerCategoryEnum = _str_enum("IssuerCategoryEnum", ISSUER_CATEGORIES)
CardNetworkEnum = _str_enum("CardNetworkEnum", CARD_NETWORKS)
CorridorEnum = _str_enum("CorridorEnum", CORRIDORS)
ProductCategoryEnum = _str_enum("ProductCategoryEnum", PRODUCT_CATEGORIES)
MerchantSegmentEnum = _str_enum("MerchantSegmentEnum", MERCHANT_SEGMENTS)
MerchantCategoryEnum = _str_enum("MerchantCategoryEnum", MERCHANT_CATEGORIES)
OrderValueTierEnum = _str_enum("OrderValueTierEnum", ORDER_VALUE_TIERS)
CurrencyEnum = _str_enum("CurrencyEnum", CURRENCIES)
ErrorSourceEnum = _str_enum("ErrorSourceEnum", ERROR_SOURCES)
ErrorStepEnum = _str_enum("ErrorStepEnum", ERROR_STEPS)


class FailedPaymentEvent(BaseModel):
    """
    Input request model representing a failed payment episode.

    Every categorical field is constrained to the synthetic environment's closed
    vocabulary. Defaults are in-vocabulary: the previous defaults ("ecommerce",
    "domestic", "sme", "payment_authentication") did not exist in the training data
    and were silently one-hot encoded as all zeros.
    """
    # Store plain strings, not Enum members, so model_dump() feeds the safety gate,
    # the one-hot encoder and the audit record exactly the values they saw in training.
    # validate_default is required as well: without it Pydantic skips validation of
    # unset fields, so use_enum_values never runs on them and a defaulted field leaks
    # an Enum member (rendering as "CurrencyEnum.INR") into the feature vector and the
    # audit record, while explicitly-supplied fields become plain strings.
    model_config = ConfigDict(use_enum_values=True, validate_default=True)

    payment_id: str = Field(..., min_length=1, max_length=128, description="Unique payment identifier", example="pay_evt_00000001")
    amount: float = Field(..., gt=0.0, description="Order transaction value in INR", example=2500.0)
    currency: CurrencyEnum = Field(default=CurrencyEnum.INR, description="Transaction currency", example="INR")
    product_category: ProductCategoryEnum = Field(default=ProductCategoryEnum.digital_goods, description="Product domain category", example="digital_goods")
    is_subscription: int = Field(default=0, ge=0, le=1, description="Subscription flag (0 or 1)", example=0)
    order_value_tier: OrderValueTierEnum = Field(default=OrderValueTierEnum.medium, description="Order value classification tier", example="medium")

    payment_method: PaymentMethodEnum = Field(..., description="Payment method category", example="card_credit")
    issuer_category: IssuerCategoryEnum = Field(default=IssuerCategoryEnum.private_bank, description="Issuer bank category", example="private_bank")
    card_network: CardNetworkEnum = Field(default=CardNetworkEnum.visa, description="Card network brand", example="visa")

    failure_code: FailureCodeEnum = Field(..., description="Taxonomy failure code", example="BAD_REQUEST_PAYMENT_TIMED_OUT")
    failure_category: FailureCategoryEnum = Field(..., description="Taxonomy failure category", example="network_timeout")
    error_source: ErrorSourceEnum = Field(default=ErrorSourceEnum.issuer, description="Error origin source", example="issuer")
    error_step: ErrorStepEnum = Field(default=ErrorStepEnum.authorization, description="Workflow failure step", example="authorization")
    corridor: CorridorEnum = Field(default=CorridorEnum.domestic_in, description="Transaction corridor", example="domestic_in")

    merchant_segment: MerchantSegmentEnum = Field(default=MerchantSegmentEnum.e_commerce, description="Merchant size segment", example="e_commerce")
    merchant_category: MerchantCategoryEnum = Field(default=MerchantCategoryEnum.cat_e_commerce, description="Merchant industry category", example="cat_e_commerce")

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
