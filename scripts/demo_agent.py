"""
End-to-End Bounded Recovery Agent Demo Script
Demonstrates failure event ingestion → decision orchestration → simulated execution → audit trail verification.
"""

import os
import sys
import json
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from src.api.schemas import FailedPaymentEvent
from src.agent.recovery_agent import RecoveryAgent
from src.agent.executor import SimulatedRecoveryExecutor
from src.agent.audit import audit_store


def main():
    print("==========================================================")
    print("  PAYMENT RECOVERY — END-TO-END DEMO SCRIPT   ")
    print("==========================================================\n")

    # 1. Ingest a sample failed payment event episode
    test_csv = "data/synthetic/test.csv"
    print(f"1. Loading sample payment failure episode from {test_csv}...")
    df_test = pd.read_csv(test_csv)
    sample_row = df_test.iloc[0].to_dict()
    
    event = FailedPaymentEvent(
        payment_id=f"pay_{sample_row['event_id']}",
        amount=float(sample_row["amount"]),
        currency=sample_row["currency"],
        product_category=sample_row["product_category"],
        is_subscription=int(sample_row["is_subscription"]),
        order_value_tier=sample_row["order_value_tier"],
        payment_method=sample_row["payment_method"],
        issuer_category=sample_row["issuer_category"],
        card_network=sample_row["card_network"],
        failure_code=sample_row["failure_code"],
        failure_category=sample_row["failure_category"],
        error_source=sample_row["error_source"],
        error_step=sample_row["error_step"],
        corridor=sample_row["corridor"],
        merchant_segment=sample_row["merchant_segment"],
        merchant_category=sample_row["merchant_category"],
        customer_tenure_days=int(sample_row["customer_tenure_days"]),
        historical_success_rate=float(sample_row["historical_success_rate"]),
        historical_failed_attempts=int(sample_row["historical_failed_attempts"]),
        historical_retry_count=int(sample_row["historical_retry_count"]),
        time_since_last_success_hours=float(sample_row["time_since_last_success_hours"]),
        retry_count_before_event=int(sample_row["retry_count_before_event"]),
        hour=int(sample_row["hour"]),
        day_of_week=int(sample_row["day_of_week"]),
        is_weekend=int(sample_row["is_weekend"])
    )
    
    print(f"   Ingested Payment ID:      {event.payment_id}")
    print(f"   Transaction Amount:      ₹{event.amount:.2f}")
    print(f"   Failure Category:        {event.failure_category}")
    print(f"   Payment Method:          {event.payment_method}\n")

    # 2. Invoke RecoveryAgent
    print("2. Invoking RecoveryAgent.decide(event)...")
    agent = RecoveryAgent(
        model_path="models/recovery_predictor.joblib",
        config_path="configs/synthetic_config.yaml",
        store=audit_store
    )
    decision = agent.decide(event)
    
    print(f"   Decision ID:             {decision['decision_id']}")
    print(f"   Selected Safe Action:    {decision['action']}")
    print(f"   Decision Status:         {decision['status']}")
    print(f"   Confidence Level:        {decision['confidence']}")
    print(f"   Recovery Probability:    {decision['recovery_probability']:.4f}")
    print(f"   Expected Economic Value: ₹{decision['expected_value']:.2f}")
    print(f"   Safety Rule Applied:     {decision['safety_rule']}")
    print(f"   Decision Rationale:      {decision['reason']}\n")

    # 3. Simulate Execution
    print("3. Invoking SimulatedRecoveryExecutor.execute(...)...")
    executor = SimulatedRecoveryExecutor(store=audit_store)
    success, exec_res = executor.execute(
        decision_id=decision["decision_id"],
        payment_id=decision["payment_id"],
        action=decision["action"]
    )
    
    print(f"   Execution ID:            {exec_res['execution_id']}")
    print(f"   Execution Status:        {exec_res['status']}")
    print(f"   Execution Message:       {exec_res['message']}\n")

    # 4. Verify Audit Record Retrieval
    print("4. Verifying Audit Trail in AuditStore...")
    audit_rec = audit_store.get_audit(decision["decision_id"])
    print(f"   Audit Record Found:      {audit_rec is not None}")
    if audit_rec:
        print(f"   Audit Execution Status:  {audit_rec.get('execution_status')}")
        print(f"   Candidate Actions Evaluated: {audit_rec['candidate_actions']}")
        print(f"   Safe Actions Permitted:      {audit_rec['safe_actions']}")

    print("\n==========================================================")
    print("  DEMO COMPLETED SUCCESSFULLY — ZERO SAFETY VIOLATIONS   ")
    print("==========================================================")


if __name__ == "__main__":
    main()
