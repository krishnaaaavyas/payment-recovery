# Task 13A — Backend API & Bounded Recovery Decision Agent Report

> **Razorpay Buildathon — Track 03: AI Revenue Recovery**  
> **Project**: O1 — Payment Failure Economic Recovery Advisor  

---

## 1. Architecture Overview

Task 13A establishes a production-grade **FastAPI REST Service** and a **Bounded Recovery Decision Agent** (`RecoveryAgent`) that orchestrates the frozen Task 10–12 machine learning estimator (`RecoveryPredictor`), Safety Gate filter (`evaluate_safety_gate`), Economic Valuation Engine, and decision layer (`PolicyAdvisor`).

```
Payment Failure Event Request (POST /decide)
                  │
                  ▼
         Input Validation & Schema Normalization (FailedPaymentEvent)
                  │
                  ▼
         Safety Gate Pre-filtering (evaluate_safety_gate -> A_safe(X))
                  │
                  ▼
         Recovery Probability Estimator (RecoveryPredictor P_hat)
                  │
                  ▼
         Expected Economic Value Engine (EV(a|X) = P_hat * V - C - D - F)
                  │
                  ▼
         PolicyAdvisor Decision Engine (Argmax EV over A_safe)
                  │
                  ▼
         Stopping Rules & Escalation Evaluator
                  │
                  ├──────────────────────────────┐
                  ▼                              ▼
         Audit Record Logger (AuditStore)   Evidence Explanation Generator
                  │
                  ▼
         Structured Decision Response
                  │
                  ▼
         Simulated Execution Engine (POST /execute)
```

---

## 2. API Endpoints Specification

| Method | Endpoint | Description | Request Model | Response Model |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/health` | Service health & data tier status | None | `{"status": "ok", ...}` |
| `POST` | `/decide` | Primary recovery decision endpoint | `FailedPaymentEvent` | `RecoveryDecisionResponse` |
| `POST` | `/execute` | Simulated action execution | `ExecutionRequest` | `ExecutionResponse` |
| `GET` | `/audit/{id}`| Decision audit trail lookup | None | `AuditRecordResponse` |

---

## 3. Request Schema (`FailedPaymentEvent`)

Maps API payload fields to the 24 decision context features required by `RecoveryPredictor` and `PolicyAdvisor`:
- **Identifiers & Values**: `payment_id`, `amount`, `currency`, `product_category`, `is_subscription`, `order_value_tier`
- **Method & Issuer**: `payment_method`, `issuer_category`, `card_network`
- **Taxonomy**: `failure_code`, `failure_category`, `error_source`, `error_step`, `corridor`
- **Merchant**: `merchant_segment`, `merchant_category`
- **Customer History**: `customer_tenure_days`, `historical_success_rate`, `historical_failed_attempts`, `historical_retry_count`, `time_since_last_success_hours`, `retry_count_before_event`
- **Temporal**: `hour`, `day_of_week`, `is_weekend`

---

## 4. Decision Response Schema (`RecoveryDecisionResponse`)

```json
{
  "decision_id": "dec_42d63e03",
  "payment_id": "pay_evt_88840335",
  "action": "switch_method",
  "confidence": "high",
  "recovery_probability": 0.5245,
  "expected_value": 276.17,
  "safe": true,
  "safety_rule": "EXCLUDE_UPDATE_INFO_ON_TECHNICAL_FAILURES",
  "reason": "'switch_method' was selected because its estimated recovery probability (P=0.5245) and net Expected Economic Value (EV=INR 276.17) maximize economic return among safe candidate interventions [do_nothing, retry_later, retry_now, switch_method] under synthetic environment evaluation.",
  "status": "APPROVED",
  "stopping_rule": null,
  "timestamp": "2026-09-02T00:02:40.123456+00:00",
  "execution_available": true
}
```

---

## 5. Agent Orchestration (`RecoveryAgent`)

`RecoveryAgent` coordinates the components without introducing LLM non-determinism or secondary policy logic:
1. Validates and normalizes context.
2. Invokes deterministic `evaluate_safety_gate` to establish $A_{\text{safe}}(X)$.
3. Invokes authoritative `PolicyAdvisor` decision engine.
4. Evaluates stopping rules and status constraints.
5. Formulates deterministic evidence-based rationale.
6. Saves complete audit trail to `AuditStore`.

---

## 6. Safety Enforcement

- **Pre-Filtering**: Unsafe actions are filtered before policy evaluation.
- **Execution Rejection**: `SimulatedRecoveryExecutor` strictly verifies that requested execution actions match the approved action, are contained in $A_{\text{safe}}(X)$, and belong to the allowed action set (`retry_now`, `retry_later`, `switch_method`, `update_information`, `do_nothing`).
- **Violation Rate**: **0.00% safety violations** across all operations.

---

## 7. Stopping Rules & Escalation

- **Rule 1 (`MAX_ATTEMPTS_EXCEEDED`)**: `retry_count_before_event >= 3` forces `status = "STOP"`, `stopping_rule = "MAX_ATTEMPTS_EXCEEDED"`, `action = "do_nothing"`.
- **Rule 2 (`UNSAFE_ACTION`)**: Action violating $A_{\text{safe}}(X)$ forces `status = "STOP"`, `stopping_rule = "UNSAFE_ACTION"`, `action = "do_nothing"`.
- **Rule 3 (`NON_POSITIVE_EV`)**: Net $EV \le 0.0$ for active interventions forces `status = "STOP"`, `stopping_rule = "NON_POSITIVE_EV"`, `action = "do_nothing"`.
- **Rule 4 (`LOW_CONFIDENCE`)**: Model confidence = `low` sets `status = "ESCALATE"`, `stopping_rule = "LOW_CONFIDENCE"`, requiring merchant escalation.

---

## 8. Simulated Execution (`SimulatedRecoveryExecutor`)

> [!IMPORTANT]
> **SIMULATION DISCLAIMER**: The executor is a simulation and does NOT perform real Razorpay payment operations or call gateway APIs.

Execution Mapping:
- `retry_now` $\rightarrow$ Status `executed` ("Simulated immediate retry successfully dispatched to gateway")
- `retry_later` $\rightarrow$ Status `scheduled` ("Simulated delayed retry scheduled for attribution window")
- `switch_method` $\rightarrow$ Status `scheduled` ("Simulated payment method switch prompt dispatched to customer checkout session")
- `update_information` $\rightarrow$ Status `scheduled` ("Simulated information update prompt dispatched to customer")
- `do_nothing` $\rightarrow$ Status `stopped` ("Simulation acknowledged: recovery attempt safely terminated")

---

## 9. Audit Trail (`AuditStore`)

- Thread-safe in-memory audit store keyed by `decision_id`.
- Records complete decision metadata, input context, candidate actions, safe actions, predicted probabilities, EV matrix, selected action, confidence, safety status, stopping rules, execution status, and timestamp.

---

## 10. Test Suite Verification

- `tests/test_generator.py` (6 / 6 PASSED)
- `tests/test_anti_circularity.py` (7 / 7 PASSED)
- `tests/test_task11_policy.py` (10 / 10 PASSED)
- `tests/test_task12_robustness.py` (10 / 10 PASSED)
- `tests/test_task13_agent.py` (4 / 4 PASSED)
- `tests/test_task13_executor.py` (5 / 5 PASSED)
- `tests/test_task13_api.py` (5 / 5 PASSED)

**Total Unit Tests Passed**: **47 / 47**

---

## 11. Example End-to-End Workflow (`scripts/demo_agent.py`)

Run the local interactive demo:

```bash
python scripts/demo_agent.py
```

---

## 12. Project Limitations & Data Disclosure

> [!IMPORTANT]
> **TIER C DISCLOSURE**: Recovery probabilities and economic outcomes are derived from the project's synthetic evaluation environment and do NOT represent measured Razorpay production performance or real customer behavior. The executor is a simulation and does NOT perform real money movement.
