import React, { useState } from 'react';
import { FailedPaymentEvent, RecoveryDecisionResponse, ExecutionResponse } from '../types/api';
import { fetchDecision, executeAction } from '../services/api';
import { Cpu, ShieldCheck, Play, CheckCircle2, FileText, ArrowRight, Loader2 } from 'lucide-react';

interface DecisionInspectorProps {
  event: FailedPaymentEvent | null;
  decision: RecoveryDecisionResponse | null;
  setDecision: (dec: RecoveryDecisionResponse | null) => void;
  onViewAudit: (decisionId: string) => void;
  onBackToQueue?: () => void;
}

export const DecisionInspector: React.FC<DecisionInspectorProps> = ({
  event,
  decision,
  setDecision,
  onViewAudit,
  onBackToQueue
}) => {
  const [analyzing, setAnalyzing] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState<ExecutionResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);

  if (!event) {
    return (
      <div className="bg-white border border-slate-200 rounded p-12 text-center space-y-4 shadow-sm">
        <Cpu className="h-10 w-10 text-slate-400 mx-auto" />
        <h3 className="text-sm font-bold text-slate-700 uppercase tracking-wider">No Failed Payment Selected</h3>
        <p className="text-xs text-slate-500 max-w-sm mx-auto">
          Select a failed payment episode from the Payments queue to review the economic recovery recommendation.
        </p>
        {onBackToQueue && (
          <button
            onClick={onBackToQueue}
            className="inline-flex items-center gap-2 px-4 py-2 rounded bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-sm"
          >
            <span>Go to Payments Queue</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
    );
  }

  const handleAnalyze = async () => {
    setAnalyzing(true);
    setErrorMsg(null);
    setExecutionResult(null);
    try {
      const res = await fetchDecision(event);
      setDecision(res);
    } catch (err: any) {
      setErrorMsg(err.message || 'Error obtaining decision');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleExecute = async () => {
    if (!decision) return;
    setExecuting(true);
    setErrorMsg(null);
    try {
      const res = await executeAction(decision.decision_id, decision.payment_id, decision.action);
      setExecutionResult(res);
    } catch (err: any) {
      setErrorMsg(err.message || 'Execution failed');
    } finally {
      setExecuting(false);
    }
  };

  return (
    <div className="space-y-5">

      {/* Top Context & Action Bar */}
      <div className="bg-white border border-slate-200 rounded p-4 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          {onBackToQueue && (
            <button
              onClick={onBackToQueue}
              className="text-xs font-semibold text-slate-600 hover:text-blue-600 transition-colors"
            >
              ← Back to Payments
            </button>
          )}
          <div>
            <div className="flex items-center gap-3">
              <span className="font-mono text-sm font-bold text-blue-600">{event.payment_id}</span>
              <span className="text-sm font-mono font-bold text-slate-900">₹{event.amount.toFixed(2)}</span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              {event.payment_method.replace('_', ' ').toUpperCase()} · <span className="text-slate-700 font-medium">{event.failure_category.replace('_', ' ')}</span>
            </p>
          </div>
        </div>

        <button
          onClick={handleAnalyze}
          disabled={analyzing}
          className="flex items-center gap-2 px-4 py-2 rounded bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 text-xs font-semibold transition-colors disabled:opacity-50 shadow-sm"
        >
          {analyzing ? <Loader2 className="h-4 w-4 animate-spin text-blue-600" /> : <Cpu className="h-4 w-4 text-slate-500" />}
          <span>{decision ? 'Re-evaluate Recommendation' : 'Evaluate Recommendation'}</span>
        </button>
      </div>

      {errorMsg && (
        <div className="p-3 rounded bg-rose-50 border border-rose-200 text-xs text-rose-800">
          {errorMsg}
        </div>
      )}

      {!decision ? (
        <div className="bg-white border border-slate-200 rounded p-10 text-center space-y-3 shadow-sm">
          <Cpu className="h-8 w-8 text-blue-600 mx-auto" />
          <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider">Ready to Evaluate</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Click <strong className="text-slate-800">"Evaluate Recommendation"</strong> to determine the safe action that maximizes net expected economic value.
          </p>
        </div>
      ) : (
        <div className="space-y-5">

          {/* Main Recommendation Panel */}
          <div className="bg-white border border-slate-200 rounded p-6 shadow-sm space-y-6">

            <div className="flex flex-wrap items-center justify-between border-b border-slate-200 pb-4 gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Recommended Recovery Action</span>
                  <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                    decision.status === 'APPROVED' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-amber-50 text-amber-800 border border-amber-200'
                  }`}>
                    {decision.status}
                  </span>
                </div>
                <div className="text-2xl font-bold text-slate-900 uppercase font-mono tracking-tight mt-1">
                  {decision.action.replace('_', ' ')}
                </div>
              </div>

              <div className="flex items-center gap-6">
                <div>
                  <div className="text-[11px] font-medium text-slate-500 text-right">Expected Economic Value</div>
                  <div className="text-2xl font-bold text-emerald-600 font-mono text-right">
                    ₹{decision.expected_value.toFixed(2)}
                  </div>
                </div>
                <div>
                  <div className="text-[11px] font-medium text-slate-500 text-right">Recovery Probability</div>
                  <div className="text-xl font-bold text-slate-800 font-mono text-right">
                    {(decision.recovery_probability * 100).toFixed(2)}%
                  </div>
                </div>
              </div>
            </div>

            {/* Decision Rationale & Safety Checks Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

              {/* Plain Reasoning */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Why this action?</h4>
                <p className="text-xs text-slate-700 leading-relaxed bg-slate-50 p-3.5 rounded border border-slate-200">
                  {decision.reason}
                </p>
              </div>

              {/* Safety Checks */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Safety checks</h4>
                <div className="bg-slate-50 p-3.5 rounded border border-slate-200 space-y-2 text-xs">
                  <div className="flex items-center gap-2 text-emerald-700 font-medium">
                    <ShieldCheck className="h-4 w-4 shrink-0 text-emerald-600" />
                    <span>Permitted by policy ({decision.safety_rule})</span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-700">
                    <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                    <span>No active bank or network restriction</span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-700">
                    <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                    <span>Customer friction within policy limits</span>
                  </div>
                </div>
              </div>

            </div>

            {/* Action Execution Footer */}
            <div className="border-t border-slate-200 pt-5 flex flex-wrap items-center justify-between gap-4">
              <div>
                <div className="text-xs font-bold text-slate-900">Execute Recommended Recovery Action</div>
                <div className="text-[11px] text-slate-500">Simulated action execution — no real money movement.</div>
              </div>

              <button
                onClick={handleExecute}
                disabled={executing || !decision.execution_available}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold transition-colors disabled:opacity-40 shadow-sm"
              >
                {executing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                <span>Execute Recommended Action</span>
              </button>
            </div>

            {/* Execution Result Output */}
            {executionResult && (
              <div className="p-4 rounded bg-emerald-50 border border-emerald-200 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs font-bold text-emerald-800">
                    <CheckCircle2 className="h-4 w-4 text-emerald-600" /> Action Executed: {executionResult.action.replace('_', ' ').toUpperCase()} (Status: {executionResult.status.toUpperCase()})
                  </div>
                  <span className="font-mono text-xs text-emerald-900 font-semibold">{executionResult.execution_id}</span>
                </div>
                <p className="text-xs text-emerald-900">{executionResult.message}</p>
                <div className="pt-1 flex justify-end">
                  <button
                    onClick={() => onViewAudit(decision.decision_id)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold transition-colors border border-slate-300 shadow-sm"
                  >
                    <FileText className="h-3.5 w-3.5 text-slate-500" />
                    <span>View Audit Record</span>
                    <ArrowRight className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            )}

          </div>

          {/* Progressive Technical Disclosure Accordion */}
          <div className="bg-white border border-slate-200 rounded shadow-sm overflow-hidden">
            <button
              onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
              className="w-full p-3.5 text-left flex items-center justify-between text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
            >
              <span>Decision &amp; Model Details (Confidence, candidate actions, stopping rules)</span>
              <span className="text-slate-500">{showTechnicalDetails ? '▲ Hide' : '▼ Expand'}</span>
            </button>

            {showTechnicalDetails && (
              <div className="p-5 border-t border-slate-200 space-y-4 bg-slate-50">

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                  <div className="p-3 bg-white border border-slate-200 rounded shadow-sm">
                    <div className="text-slate-500">Decision ID</div>
                    <div className="font-mono font-semibold text-slate-900 mt-0.5">{decision.decision_id}</div>
                  </div>
                  <div className="p-3 bg-white border border-slate-200 rounded shadow-sm">
                    <div className="text-slate-500">Model Confidence</div>
                    <div className="font-semibold text-slate-900 capitalize mt-0.5">{decision.confidence} Confidence</div>
                  </div>
                  <div className="p-3 bg-white border border-slate-200 rounded shadow-sm">
                    <div className="text-slate-500">Stopping Rule</div>
                    <div className="font-mono text-slate-800 mt-0.5">{decision.stopping_rule || 'NONE'}</div>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="text-xs font-semibold text-slate-700">Candidate Actions Evaluated</div>
                  <div className="flex flex-wrap gap-2 text-xs font-mono">
                    {['retry_now', 'retry_later', 'switch_method', 'update_information', 'do_nothing'].map((act) => {
                      const isSelected = act === decision.action;
                      return (
                        <span
                          key={act}
                          className={`px-2.5 py-1 rounded border ${
                            isSelected
                              ? 'bg-blue-50 text-blue-700 border-blue-300 font-bold'
                              : 'bg-white text-slate-600 border-slate-200'
                          }`}
                        >
                          {act} {isSelected ? '(SELECTED)' : ''}
                        </span>
                      );
                    })}
                  </div>
                </div>

              </div>
            )}
          </div>

        </div>
      )}

    </div>
  );
};
