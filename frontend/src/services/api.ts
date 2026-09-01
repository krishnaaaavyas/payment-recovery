import {
  FailedPaymentEvent,
  RecoveryDecisionResponse,
  ExecutionResponse,
  AuditRecordResponse,
  EvaluationSummary
} from '../types/api';

const API_BASE = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000';

export async function fetchHealth(): Promise<{ status: string; service: string; data_tier: string }> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('Backend API unavailable');
  return res.json();
}

export async function fetchEvents(limit = 50): Promise<FailedPaymentEvent[]> {
  const res = await fetch(`${API_BASE}/events?limit=${limit}`);
  if (!res.ok) throw new Error('Failed to load sample failure events');
  return res.json();
}

export async function fetchDecision(event: FailedPaymentEvent): Promise<RecoveryDecisionResponse> {
  const res = await fetch(`${API_BASE}/decide`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(event)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to obtain recovery decision' }));
    throw new Error(err.detail || 'Decision API error');
  }
  return res.json();
}

export async function executeAction(decisionId: string, paymentId: string, action: string): Promise<ExecutionResponse> {
  const res = await fetch(`${API_BASE}/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision_id: decisionId, payment_id: paymentId, action })
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.message || data.detail || 'Execution rejected by backend safety layer');
  }
  return data;
}

export async function fetchAudit(decisionId: string): Promise<AuditRecordResponse> {
  const res = await fetch(`${API_BASE}/audit/${decisionId}`);
  if (!res.ok) throw new Error(`Audit record for ID ${decisionId} not found`);
  return res.json();
}

export async function fetchEvaluationReports(): Promise<EvaluationSummary> {
  const res = await fetch(`${API_BASE}/reports/summary`);
  if (!res.ok) throw new Error('Failed to load evaluation reports');
  return res.json();
}
