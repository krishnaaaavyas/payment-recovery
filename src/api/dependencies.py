"""
API Dependencies Module
Provides dependency injection instances for RecoveryAgent and SimulatedRecoveryExecutor.
"""

from typing import Optional
from src.agent.recovery_agent import RecoveryAgent
from src.agent.executor import SimulatedRecoveryExecutor
from src.agent.audit import audit_store

_agent_instance: Optional[RecoveryAgent] = None
_executor_instance: Optional[SimulatedRecoveryExecutor] = None

def get_recovery_agent() -> RecoveryAgent:
    """Returns singleton instance of RecoveryAgent."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = RecoveryAgent(
            model_path="models/recovery_predictor.joblib",
            config_path="configs/synthetic_config.yaml",
            store=audit_store
        )
    return _agent_instance

def get_executor() -> SimulatedRecoveryExecutor:
    """Returns singleton instance of SimulatedRecoveryExecutor."""
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = SimulatedRecoveryExecutor(store=audit_store)
    return _executor_instance
