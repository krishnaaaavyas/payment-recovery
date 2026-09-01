import React, { useState, useEffect } from 'react';
import { AuditRecordResponse } from '../types/api';
import { fetchAudit } from '../services/api';
import { FileCheck, Search, ShieldCheck, Code } from 'lucide-react';

interface AuditTrailProps {
  decisionId: string | null;
}

export const AuditTrail: React.FC<AuditTrailProps> = ({ decisionId }) => {
  const [searchId, setSearchId] = useState(decisionId || '');
  const [record, setRecord] = useState<AuditRecordResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [showRawJson, setShowRawJson] = useState(false);

  useEffect(() => {
    if (decisionId) {
      setSearchId(decisionId);
      loadAudit(decisionId);
    }
  }, [decisionId]);

  const loadAudit = async (id: string) => {
    if (!id.trim()) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      const data = await fetchAudit(id.trim());
      setRecord(data);
    } catch (err: any) {
      setErrorMsg(err.message || `Audit record '${id}' not found.`);
      setRecord(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Search Bar Header */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
          <FileCheck className="h-4 w-4 text-indigo-400" />
          <span>Decision Audit Trail Search</span>
        </div>

        <div className="flex items-center gap-2 flex-1 max-w-md">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
            <input
              type="text"
              placeholder="Enter Decision ID (e.g. dec_bbea3051)..."
              value={searchId}
              onChange={(e) => setSearchId(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && loadAudit(searchId)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-4 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>
          <button
            onClick={() => loadAudit(searchId)}
            disabled={loading}
            className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-colors disabled:opacity-50"
          >
            Lookup Audit
          </button>
        </div>
      </div>

      {!record && !errorMsg && !loading && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-12 text-center space-y-3">
          <FileCheck className="h-10 w-10 text-slate-600 mx-auto" />
          <h3 className="text-base font-semibold text-slate-300">No Decision Audit Loaded</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            Analyze a payment failure episode in the Decision Inspector to automatically generate and inspect an immutable decision audit record.
          </p>
        </div>
      )}

      {errorMsg && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-400">
          {errorMsg}
        </div>
      )}

      {record && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-6">
          
          {/* Header Summary Row */}
          <div className="flex flex-wrap items-center justify-between border-b border-slate-800 pb-4 gap-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-base font-bold text-indigo-400">{record.decision_id}</span>
                <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                  record.status === 'APPROVED' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                }`}>
                  {record.status}
                </span>
                <span className="px-2 py-0.5 rounded text-xs font-mono bg-slate-800 text-slate-300 border border-slate-700">
                  Exec Status: {record.execution_status}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1">Payment ID: <span className="font-mono text-slate-200">{record.payment_id}</span> | Timestamp: {record.timestamp}</p>
            </div>

            <button
              onClick={() => setShowRawJson(!showRawJson)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors"
            >
              <Code className="h-3.5 w-3.5" />
              <span>{showRawJson ? 'Hide Raw JSON' : 'View Raw JSON'}</span>
            </button>
          </div>

          {showRawJson ? (
            <pre className="p-4 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono text-emerald-400 overflow-x-auto">
              {JSON.stringify(record, null, 2)}
            </pre>
          ) : (
            <div className="space-y-6">
              
              {/* Evaluated Action Probability & EV Matrix */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Candidate Action Evaluation Matrix</h4>
                <div className="bg-slate-950 border border-slate-800 rounded-lg overflow-hidden">
                  <table className="w-full text-left text-xs text-slate-300">
                    <thead className="bg-slate-900 border-b border-slate-800 text-slate-400 font-semibold text-[11px]">
                      <tr>
                        <th className="px-4 py-2.5">Action</th>
                        <th className="px-4 py-2.5">Safety Clearance</th>
                        <th className="px-4 py-2.5">Predicted P(rec)</th>
                        <th className="px-4 py-2.5">Expected Value EV</th>
                        <th className="px-4 py-2.5 text-right">Selection Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {record.candidate_actions.map((act) => {
                        const isSafe = record.safe_actions.includes(act);
                        const isSelected = record.selected_action === act;
                        const p = record.predicted_probabilities[act] ?? 0.0;
                        const ev = record.expected_values[act] ?? 0.0;
                        return (
                          <tr key={act} className={isSelected ? 'bg-indigo-500/10' : ''}>
                            <td className="px-4 py-2.5 font-mono font-medium capitalize text-slate-200">
                              {act.replace('_', ' ')}
                            </td>
                            <td className="px-4 py-2.5">
                              {isSafe ? (
                                <span className="text-emerald-400 font-semibold flex items-center gap-1">
                                  <ShieldCheck className="h-3.5 w-3.5" /> Safe
                                </span>
                              ) : (
                                <span className="text-rose-400 font-semibold">Blocked by Safety Gate</span>
                              )}
                            </td>
                            <td className="px-4 py-2.5 font-mono text-slate-300">
                              {(p * 100).toFixed(2)}%
                            </td>
                            <td className="px-4 py-2.5 font-mono font-bold text-slate-100">
                              ₹{ev.toFixed(2)}
                            </td>
                            <td className="px-4 py-2.5 text-right">
                              {isSelected ? (
                                <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                                  SELECTED ACTION
                                </span>
                              ) : (
                                <span className="text-slate-500 text-[11px]">Evaluated</span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Rationale & Safety Rule Details */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 space-y-1.5">
                  <div className="text-xs font-semibold text-slate-300">Safety Rule Applied</div>
                  <p className="text-xs text-slate-300 font-mono">{record.safety_rule}</p>
                </div>

                <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 space-y-1.5">
                  <div className="text-xs font-semibold text-slate-300">Decision Rationale</div>
                  <p className="text-xs text-slate-300 leading-relaxed font-sans">{record.reason}</p>
                </div>
              </div>

            </div>
          )}

        </div>
      )}

    </div>
  );
};
