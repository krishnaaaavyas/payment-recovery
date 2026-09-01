import React, { useState } from 'react';
import { FailedPaymentEvent, RecoveryDecisionResponse, ExecutionResponse } from '../types/api';
import { fetchDecision, executeAction } from '../services/api';
import { Cpu, ShieldCheck, Play, CheckCircle2, FileText, ArrowRight, Loader2 } from 'lucide-react';

interface DecisionInspectorProps {
  event: FailedPaymentEvent | null;
  decision: RecoveryDecisionResponse | null;
  setDecision: (dec: RecoveryDecisionResponse | null) => void;
  onViewAudit: (decisionId: string) => void;
}

export const DecisionInspector: React.FC<DecisionInspectorProps> = ({
  event,
  decision,
  setDecision,
  onViewAudit
}) => {
  const [analyzing, setAnalyzing] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState<ExecutionResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!event) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-12 text-center space-y-3">
        <Cpu className="h-10 w-10 text-slate-600 mx-auto" />
        <h3 className="text-base font-semibold text-slate-300">No Payment Episode Selected</h3>
        <p className="text-xs text-slate-500 max-w-sm mx-auto">
          Please select a failed payment event from the Payment Queue to inspect context and trigger an AI recovery decision.
        </p>
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
      
      {/* Grid: Left Context Panel, Right Decision Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Context Snapshot */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4 lg:col-span-1">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Payment Context</h3>
            <span className="font-mono text-xs text-indigo-400 font-semibold">{event.payment_id}</span>
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex justify-between">
              <span className="text-slate-400">Order Amount</span>
              <span className="font-mono font-bold text-slate-100">₹{event.amount.toFixed(2)} {event.currency}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Payment Method</span>
              <span className="capitalize font-medium text-slate-200">{event.payment_method.replace('_', ' ')}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Failure Category</span>
              <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-200 font-mono text-[11px]">{event.failure_category}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Failure Code</span>
              <span className="font-mono text-[11px] text-slate-300 truncate max-w-[160px]">{event.failure_code}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Episode Attempts</span>
              <span className="font-mono font-semibold text-slate-200">{event.retry_count_before_event + 1}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Merchant Segment</span>
              <span className="capitalize text-slate-300">{event.merchant_segment}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Customer Tenure</span>
              <span className="text-slate-300">{event.customer_tenure_days} days</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Historical Success</span>
              <span className="font-mono text-slate-200">{(event.historical_success_rate * 100).toFixed(0)}%</span>
            </div>
          </div>

          {/* Trigger Decision Button */}
          <button
            onClick={handleAnalyze}
            disabled={analyzing}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-colors disabled:opacity-50 shadow-lg shadow-indigo-600/20"
          >
            {analyzing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Cpu className="h-4 w-4" />}
            <span>{decision ? 'Re-evaluate with O1' : 'Analyze Recovery with O1'}</span>
          </button>

          {errorMsg && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-xs text-rose-400">
              {errorMsg}
            </div>
          )}
        </div>

        {/* Right Column: AI Recovery Decision & Execution Panel */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-5 lg:col-span-2">
          
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">AI Recovery Recommendation</h3>
            {decision && (
              <span className={`px-2.5 py-0.5 rounded text-xs font-bold border ${
                decision.status === 'APPROVED' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                decision.status === 'ESCALATE' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' :
                'bg-rose-500/10 text-rose-400 border-rose-500/20'
              }`}>
                STATUS: {decision.status} {decision.stopping_rule ? `(${decision.stopping_rule})` : ''}
              </span>
            )}
          </div>

          {!decision ? (
            <div className="p-8 text-center space-y-2 text-slate-500">
              <Cpu className="h-8 w-8 mx-auto text-slate-600" />
              <p className="text-xs">Click "Analyze Recovery with O1" to evaluate safe economic actions.</p>
            </div>
          ) : (
            <div className="space-y-5">
              
              {/* Top Decision Metrics Row */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                
                {/* Action Card */}
                <div className="bg-slate-950 border border-slate-800 rounded-lg p-3.5 space-y-1">
                  <div className="text-[11px] font-medium text-slate-400">Selected Safe Action</div>
                  <div className="text-lg font-bold text-indigo-400 uppercase font-mono tracking-tight">
                    {decision.action.replace('_', ' ')}
                  </div>
                </div>

                {/* Probability Card */}
                <div className="bg-slate-950 border border-slate-800 rounded-lg p-3.5 space-y-1">
                  <div className="flex justify-between text-[11px] font-medium text-slate-400">
                    <span>Recovery Probability</span>
                    <span className="text-slate-300 font-mono">P(rec|X,a)</span>
                  </div>
                  <div className="text-lg font-bold text-slate-100 font-mono">
                    {(decision.recovery_probability * 100).toFixed(2)}%
                  </div>
                </div>

                {/* Expected Value Card */}
                <div className="bg-slate-950 border border-slate-800 rounded-lg p-3.5 space-y-1">
                  <div className="flex justify-between text-[11px] font-medium text-slate-400">
                    <span>Expected Economic Value</span>
                    <span className="text-slate-300 font-mono">EV(a|X)</span>
                  </div>
                  <div className="text-lg font-bold text-emerald-400 font-mono">
                    ₹{decision.expected_value.toFixed(2)}
                  </div>
                </div>

              </div>

              {/* Safety Gate & Confidence Banner */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400">
                    <ShieldCheck className="h-4 w-4" /> Safety Gate Clearance
                  </div>
                  <div className="text-xs text-slate-300 font-mono">Rule: {decision.safety_rule}</div>
                </div>

                <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                  <div className="text-xs font-medium text-slate-400">Model Confidence Level</div>
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded text-xs font-bold uppercase ${
                      decision.confidence === 'high' ? 'bg-emerald-500/10 text-emerald-400' :
                      decision.confidence === 'medium' ? 'bg-amber-500/10 text-amber-400' :
                      'bg-rose-500/10 text-rose-400'
                    }`}>
                      {decision.confidence} Confidence
                    </span>
                  </div>
                </div>
              </div>

              {/* Evidence Rationale Box */}
              <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 space-y-1.5">
                <div className="text-xs font-semibold text-slate-300">Decision Rationale (Deterministic Explanation)</div>
                <p className="text-xs text-slate-300 leading-relaxed font-sans">{decision.reason}</p>
              </div>

              {/* Action Execution Section */}
              <div className="border-t border-slate-800 pt-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-xs font-bold text-slate-200">Simulated Action Execution</h4>
                    <p className="text-[11px] text-slate-400">Simulation only — No real Razorpay or gateway API called.</p>
                  </div>
                  <button
                    onClick={handleExecute}
                    disabled={executing || !decision.execution_available}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-colors disabled:opacity-40 shadow-lg shadow-emerald-600/20"
                  >
                    {executing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
                    <span>Execute Action</span>
                  </button>
                </div>

                {/* Execution Result Output Box */}
                {executionResult && (
                  <div className="p-4 rounded-lg bg-slate-950 border border-emerald-500/30 space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-xs font-bold text-emerald-400">
                        <CheckCircle2 className="h-4 w-4" /> Action Dispatch Status: {executionResult.status.toUpperCase()}
                      </div>
                      <span className="font-mono text-[11px] text-slate-400">{executionResult.execution_id}</span>
                    </div>
                    <p className="text-xs text-slate-300">{executionResult.message}</p>
                    <div className="pt-2 flex justify-end">
                      <button
                        onClick={() => onViewAudit(decision.decision_id)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-indigo-300 text-xs font-medium transition-colors"
                      >
                        <FileText className="h-3.5 w-3.5" />
                        <span>Inspect Full Decision Audit Record</span>
                        <ArrowRight className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                )}
              </div>

            </div>
          )}

        </div>

      </div>

    </div>
  );
};
