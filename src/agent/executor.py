"""
Simulated Recovery Executor Module
Simulates action execution without calling real Razorpay or gateway APIs.
Strictly rejects unsafe, unknown, stopped, or escalated recovery decisions.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Tuple

from src.data.failure_taxonomy import ALL_ACTIONS
from src.agent.audit import audit_store


class SimulatedRecoveryExecutor:
    """Simulates recovery action execution for approved economic recovery decisions."""
    
    def __init__(self, store=audit_store):
        self.store = store

    def execute(self, decision_id: str, payment_id: str, action: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Simulates execution of an approved recovery action.
        Returns (success_flag, execution_result_dict).
        """
        audit_record = self.store.get_audit(decision_id)
        now_iso = datetime.now(timezone.utc).isoformat()
        exec_id = f"exec_{uuid.uuid4().hex[:8]}"

        # 1. Reject if decision audit record does not exist
        if not audit_record:
            res = {
                "execution_id": exec_id,
                "decision_id": decision_id,
                "payment_id": payment_id,
                "action": action,
                "status": "rejected",
                "message": f"Execution rejected: Decision ID '{decision_id}' not found in audit store.",
                "timestamp": now_iso
            }
            return False, res

        # 2. Reject if the request is not bound to the payment the decision was made for.
        # payment_id was previously accepted and echoed back without ever being compared
        # to the audit record, so a decision could be executed against a different
        # payment (TASK_16A audit, finding M-5).
        record_payment_id = audit_record.get("payment_id")
        if record_payment_id is not None and payment_id != record_payment_id:
            res = {
                "execution_id": exec_id,
                "decision_id": decision_id,
                "payment_id": payment_id,
                "action": action,
                "status": "rejected",
                "message": (
                    f"Execution rejected: payment_id '{payment_id}' does not match the "
                    f"payment this decision was issued for."
                ),
                "timestamp": now_iso
            }
            return False, res

        # 3. Reject replays. Each decision authorises exactly one execution attempt;
        # without this check the same approval could dispatch unbounded retries, which
        # is precisely what the bounded-agent retry cap exists to prevent.
        prior_status = audit_record.get("execution_status", "pending")
        if prior_status != "pending":
            res = {
                "execution_id": exec_id,
                "decision_id": decision_id,
                "payment_id": payment_id,
                "action": action,
                "status": "rejected",
                "message": (
                    f"Execution rejected: decision '{decision_id}' has already been "
                    f"actioned (execution_status='{prior_status}'). Each decision "
                    f"authorises a single execution."
                ),
                "timestamp": now_iso
            }
            return False, res

        # 4. Reject if action does not match approved action
        if action != audit_record["selected_action"]:
            res = {
                "execution_id": exec_id,
                "decision_id": decision_id,
                "payment_id": payment_id,
                "action": action,
                "status": "rejected",
                "message": f"Execution rejected: Requested action '{action}' does not match approved action '{audit_record['selected_action']}'.",
                "timestamp": now_iso
            }
            return False, res

        # 5. Reject if action is not in allowed bounded action set
        if action not in ALL_ACTIONS:
            res = {
                "execution_id": exec_id,
                "decision_id": decision_id,
                "payment_id": payment_id,
                "action": action,
                "status": "rejected",
                "message": f"Execution rejected: Action '{action}' is not in the allowed bounded action space.",
                "timestamp": now_iso
            }
            return False, res

        # 6. Reject if decision was stopped or escalated
        decision_status = audit_record.get("status", "STOP")
        if decision_status == "STOP":
            res = {
                "execution_id": exec_id,
                "decision_id": decision_id,
                "payment_id": payment_id,
                "action": action,
                "status": "stopped",
                "message": f"Execution rejected: Decision was STOPPED by rule '{audit_record.get('stopping_rule')}'.",
                "timestamp": now_iso
            }
            self.store.update_execution_status(decision_id, "stopped")
            return False, res

        if decision_status == "ESCALATE":
            res = {
                "execution_id": exec_id,
                "decision_id": decision_id,
                "payment_id": payment_id,
                "action": action,
                "status": "escalated",
                "message": "Execution rejected: Decision requires human/merchant ESCALATION due to low confidence.",
                "timestamp": now_iso
            }
            self.store.update_execution_status(decision_id, "escalated")
            return False, res

        # 7. Reject if action is not in safe actions list
        if action not in audit_record.get("safe_actions", []):
            res = {
                "execution_id": exec_id,
                "decision_id": decision_id,
                "payment_id": payment_id,
                "action": action,
                "status": "rejected",
                "message": f"Execution rejected: Action '{action}' violates Safety Gate constraints.",
                "timestamp": now_iso
            }
            self.store.update_execution_status(decision_id, "rejected")
            return False, res

        # 8. Execute approved simulation
        if action == "retry_now":
            exec_status = "executed"
            msg = "Simulated immediate retry successfully dispatched to gateway"
        elif action == "retry_later":
            exec_status = "scheduled"
            msg = "Simulated delayed retry scheduled for attribution window"
        elif action == "switch_method":
            exec_status = "scheduled"
            msg = "Simulated payment method switch prompt dispatched to customer checkout session"
        elif action == "update_information":
            exec_status = "scheduled"
            msg = "Simulated information update prompt dispatched to customer"
        elif action == "do_nothing":
            exec_status = "stopped"
            msg = "Simulation acknowledged: recovery attempt safely terminated"
        else:
            exec_status = "rejected"
            msg = f"Unknown action string '{action}'"

        res = {
            "execution_id": exec_id,
            "decision_id": decision_id,
            "payment_id": payment_id,
            "action": action,
            "status": exec_status,
            "message": msg,
            "timestamp": now_iso
        }
        self.store.update_execution_status(decision_id, exec_status)
        return True, res
