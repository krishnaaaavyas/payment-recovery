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
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-12 text-center space-y-4">
        <Cpu className="h-10 w-10 text-slate-600 mx-auto" />
        <h3 className="text-base font-semibold text-slate-300">No Failed Payment Selected</h3>
        <p className="text-xs text-slate-500 max-w-sm mx-auto">
          Please select a failed payment episode from the Payments queue to review O1's economic recovery recommendation.
        </p>
        {onBackToQueue && (
          <button
            onClick={onBackToQueue}
            className="inline-flex items-center gap-2 px-4 py-2 rounded bg-indigo-600 text-white text-xs font-medium"
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
    <div className="space-y-6">

      {/* Top Navigation & Context Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          {onBackToQueue && (
            <button
              onClick={onBackToQueue}
              className="text-xs text-slate-400 hover:text-slate-200 transition-colors"
            >
              ← Back to Payments
            </button>
          )}
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm font-bold text-indigo-400">{event.payment_id}</span>
              <span className="text-xs font-mono font-bold text-slate-100">₹{event.amount.toFixed(2)}</span>
            </div>
            <p className="text-xs text-slate-400">
              {event.payment_method.replace('_', ' ').toUpperCase()} · <span className="text-slate-300">{event.failure_category.replace('_', ' ')}</span>
            </p>
          </div>
        </div>

        <button
          onClick={handleAnalyze}
          disabled={analyzing}
          className="flex items-center gap-2 px-4 py-2 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-colors disabled:opacity-50"
        >
          {analyzing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Cpu className="h-4 w-4" />}
          <span>{decision ? 'Re-evaluate Recommendation' : 'Evaluate O1 Recommendation'}</span>
        </button>
      </div>

      {errorMsg && (
        <div className="p-3 rounded bg-rose-500/10 border border-rose-500/20 text-xs text-rose-400">
          {errorMsg}
        </div>
      )}

      {!decision ? (
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-10 text-center space-y-3">
          <Cpu className="h-8 w-8 text-indigo-400 mx-auto" />
          <h3 className="text-sm font-semibold text-slate-200">Ready to Analyze</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            Click <strong className="text-indigo-300">"Evaluate O1 Recommendation"</strong> to calculate net expected economic value and safety clearance.
          </p>
        </div>
      ) : (
        <div className="space-y-6">

          {/* Main Hero Recommendation Panel */}
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 space-y-6">

            <div className="flex flex-wrap items-center justify-between border-b border-slate-800 pb-4 gap-4">
              <div>
                <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">O1 Recommended Action</div>
                <div className="text-2xl font-bold text-indigo-400 uppercase font-mono tracking-tight mt-1">
                  {decision.action.replace('_', ' ')}
                </div>
              </div>

              <div className="flex items-center gap-4">
                <div>
                  <div className="text-[11px] font-medium text-slate-400 text-right">Expected Economic Value</div>
                  <div className="text-2xl font-bold text-emerald-400 font-mono text-right">
                    ₹{decision.expected_value.toFixed(2)}
                  </div>
                </div>
                <div>
                  <div className="text-[11px] font-medium text-slate-400 text-right">Recovery Probability</div>
                  <div className="text-xl font-bold text-slate-100 font-mono text-right">
                    {(decision.recovery_probability * 100).toFixed(2)}%
                  </div>
                </div>
              </div>
            </div>

            {/* Decision Explanation & Safety Checks Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

              {/* Plain Reasoning */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Why this action?</h4>
                <p className="text-xs text-slate-300 leading-relaxed bg-slate-950 p-3.5 rounded border border-slate-800">
                  {decision.reason}
                </p>
              </div>

              {/* Safety Checks */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Safety checks</h4>
                <div className="bg-slate-950 p-3.5 rounded border border-slate-800 space-y-2 text-xs">
                  <div className="flex items-center gap-2 text-emerald-400 font-medium">
                    <ShieldCheck className="h-4 w-4 shrink-0" />
                    <span>Allowed by domain safety rules ({decision.safety_rule})</span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-300">
                    <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                    <span>No active issuer outage or network conflict detected</span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-300">
                    <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                    <span>Customer friction within acceptable policy limits</span>
                  </div>
                </div>
              </div>

            </div>

            {/* Execute Primary CTA */}
            <div className="border-t border-slate-800 pt-5 flex flex-wrap items-center justify-between gap-4">
              <div>
                <div className="text-xs font-semibold text-slate-200">Ready to execute recovery action</div>
                <div className="text-[11px] text-slate-400">Simulated recovery dispatch — no live money movement.</div>
              </div>

              <button
                onClick={handleExecute}
                disabled={executing || !decision.execution_available}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition-colors disabled:opacity-40 shadow-md"
              >
                {executing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                <span>Execute Recommended Action</span>
              </button>
            </div>

            {/* Execution Result Banner */}
            {executionResult && (
              <div className="p-4 rounded bg-slate-950 border border-emerald-500/30 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs font-bold text-emerald-400">
                    <CheckCircle2 className="h-4 w-4" /> Action Executed: {executionResult.action.replace('_', ' ').toUpperCase()} (Status: {executionResult.status.toUpperCase()})
                  </div>
                  <span className="font-mono text-xs text-slate-400">{executionResult.execution_id}</span>
                </div>
                <p className="text-xs text-slate-300">{executionResult.message}</p>
                <div className="pt-1 flex justify-end">
                  <button
                    onClick={() => onViewAudit(decision.decision_id)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-indigo-300 text-xs font-medium transition-colors"
                  >
                    <FileText className="h-3.5 w-3.5" />
                    <span>View Audit Record</span>
                    <ArrowRight className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            )}

          </div>

          {/* Progressive Technical Disclosure Accordion */}
          <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
            <button
              onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
              className="w-full p-4 text-left flex items-center justify-between text-xs font-semibold text-slate-300 hover:bg-slate-800/50 transition-colors"
            >
              <span>Technical details (Model confidence, candidate actions, raw metrics)</span>
              <span>{showTechnicalDetails ? '▲ Hide' : '▼ Expand'}</span>
            </button>

            {showTechnicalDetails && (
              <div className="p-5 border-t border-slate-800 space-y-4 bg-slate-950">

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                  <div className="p-3 bg-slate-900 border border-slate-800 rounded">
                    <div className="text-slate-400">Decision ID</div>
                    <div className="font-mono font-semibold text-slate-200 mt-0.5">{decision.decision_id}</div>
                  </div>
                  <div className="p-3 bg-slate-900 border border-slate-800 rounded">
                    <div className="text-slate-400">Model Confidence</div>
                    <div className="font-semibold text-slate-200 capitalize mt-0.5">{decision.confidence} Confidence</div>
                  </div>
                  <div className="p-3 bg-slate-900 border border-slate-800 rounded">
                    <div className="text-slate-400">Stopping Rule</div>
                    <div className="font-mono text-slate-300 mt-0.5">{decision.stopping_rule || 'NONE'}</div>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="text-xs font-semibold text-slate-300">Candidate Actions Evaluated</div>
                  <div className="flex flex-wrap gap-2 text-xs font-mono">
                    {['retry_now', 'retry_later', 'switch_method', 'update_information', 'do_nothing'].map((act) => {
                      const isSelected = act === decision.action;
                      return (
                        <span
                          key={act}
                          className={`px-2.5 py-1 rounded border ${
                            isSelected
                              ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40 font-bold'
                              : 'bg-slate-900 text-slate-400 border-slate-800'
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
