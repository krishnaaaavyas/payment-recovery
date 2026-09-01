"""
In-Memory Audit Store Module
Provides thread-safe storage and retrieval for decision audit records.
"""

import threading
from typing import Dict, Any, Optional

class AuditStore:
    """Thread-safe in-memory audit store for recovery advisor decisions."""
    
    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def save_audit(self, decision_id: str, record: Dict[str, Any]):
        """Saves a decision audit record."""
        with self._lock:
            self._store[decision_id] = record

    def get_audit(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a decision audit record by decision_id."""
        with self._lock:
            return self._store.get(decision_id)

    def update_execution_status(self, decision_id: str, execution_status: str):
        """Updates the execution status of an existing audit record."""
        with self._lock:
            if decision_id in self._store:
                self._store[decision_id]["execution_status"] = execution_status

    def clear(self):
        """Clears all audit records (used for test setup/teardown)."""
        with self._lock:
            self._store.clear()

# Global shared audit store instance
audit_store = AuditStore()
