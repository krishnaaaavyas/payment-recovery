"""
Failure Taxonomy Module
Defines 13 payment failure categories inspired by Razorpay documentation and payment semantics.
"""

from typing import Dict, List, Any

FAILURE_TAXONOMY: Dict[str, Dict[str, Any]] = {
    "hard_decline": {
        "retryable": False,
        "error_source": "issuer",
        "error_step": "authorization",
        "default_codes": ["BAD_REQUEST_PAYMENT_BLOCKED", "CARD_STOLEN", "SUSPECTED_FRAUD"],
        "description": "Hard decline by issuer due to fraud risk, stolen card, or permanent decline."
    },
    "blocked_instrument": {
        "retryable": False,
        "error_source": "issuer",
        "error_step": "authorization",
        "default_codes": ["ACCOUNT_CLOSED", "CARD_INACTIVE", "INSTRUMENT_BLACKLISTED"],
        "description": "Permanently closed or blacklisted account/instrument."
    },
    "velocity_limit": {
        "retryable": False,
        "error_source": "gateway",
        "error_step": "payment_initiation",
        "default_codes": ["MAX_LIMIT_EXCEEDED", "DAILY_VELOCITY_REACHED"],
        "description": "Customer or merchant velocity limit breached."
    },
    "expired_card": {
        "retryable": True,
        "requires_update": True,
        "error_source": "customer",
        "error_step": "authentication",
        "default_codes": ["EXPIRED_CARD", "INVALID_CARD_EXPIRY"],
        "description": "Card expiry date is past or invalid."
    },
    "invalid_information": {
        "retryable": True,
        "requires_update": True,
        "error_source": "customer",
        "error_step": "authentication",
        "default_codes": ["INVALID_CVV", "INVALID_VPA", "ADDRESS_VERIFICATION_FAILED"],
        "description": "Customer entered invalid CVV, VPA format, or billing details."
    },
    "soft_decline": {
        "retryable": True,
        "error_source": "issuer",
        "error_step": "authorization",
        "default_codes": ["GENERIC_DECLINE", "DO_NOT_HONOR", "TRANSACTION_NOT_PERMITTED"],
        "description": "Transient soft decline by issuer."
    },
    "insufficient_funds": {
        "retryable": True,
        "error_source": "issuer",
        "error_step": "authorization",
        "default_codes": ["INSUFFICIENT_FUNDS", "BALANCE_EXCEEDED"],
        "description": "Customer account balance is insufficient for transaction amount."
    },
    "issuer_unavailable": {
        "retryable": True,
        "error_source": "issuer",
        "error_step": "authorization",
        "default_codes": ["ISSUER_DOWN", "BANK_SYSTEM_OUTAGE"],
        "description": "Issuer core banking system or authorization engine unavailable."
    },
    "bank_unavailable": {
        "retryable": True,
        "error_source": "gateway",
        "error_step": "payment_initiation",
        "default_codes": ["NETBANKING_GATEWAY_DOWN", "AGGR_BANK_OUTAGE"],
        "description": "Netbanking aggregator or bank portal unavailable."
    },
    "network_timeout": {
        "retryable": True,
        "error_source": "network",
        "error_step": "authorization",
        "default_codes": ["GATEWAY_TIMEOUT", "NETWORK_DROPPED_CONNECTION"],
        "description": "Network timeout between PSP, card network, and issuer."
    },
    "authentication_failure": {
        "retryable": True,
        "error_source": "customer",
        "error_step": "authentication",
        "default_codes": ["BAD_REQUEST_PAYMENT_TIMED_OUT", "OTP_EXPIRED", "3DS_AUTH_FAILED"],
        "description": "Customer 3DS / OTP authentication failed or timed out."
    },
    "upi_timeout": {
        "retryable": True,
        "error_source": "network",
        "error_step": "authorization",
        "default_codes": ["UPI_PSP_TIMEOUT", "NPCI_QUEUE_TIMEOUT"],
        "description": "UPI PSP / NPCI infrastructure response timeout."
    },
    "upi_decline": {
        "retryable": True,
        "error_source": "customer",
        "error_step": "authorization",
        "default_codes": ["UPI_PIN_INCORRECT", "UPI_USER_DECLINED"],
        "description": "UPI PIN entered incorrectly or payment declined by user in app."
    }
}

ALL_ACTIONS = ["retry_now", "retry_later", "switch_method", "update_information", "do_nothing"]
