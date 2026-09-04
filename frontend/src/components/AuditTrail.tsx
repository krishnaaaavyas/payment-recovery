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
    <div className="space-y-5">

      {/* Search Bar Header */}
      <div className="bg-white border border-slate-200 rounded p-4 shadow-sm flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-700">
          <FileCheck className="h-4 w-4 text-blue-600" />
          <span>Decision Audit Trail Search</span>
        </div>

        <div className="flex items-center gap-2 flex-1 max-w-md">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-400" />
            <input
              type="text"
              placeholder="Enter Decision ID (e.g. dec_bbea3051)..."
              value={searchId}
              onChange={(e) => setSearchId(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && loadAudit(searchId)}
              className="w-full bg-slate-50 border border-slate-300 rounded pl-8 pr-4 py-1.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-600 focus:bg-white"
            />
          </div>
          <button
            onClick={() => loadAudit(searchId)}
            disabled={loading}
            className="px-4 py-1.5 rounded bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold transition-colors disabled:opacity-50 shadow-sm"
          >
            Lookup
          </button>
        </div>
      </div>

      {!record && !errorMsg && !loading && (
        <div className="bg-white border border-slate-200 rounded p-12 text-center space-y-3 shadow-sm">
          <FileCheck className="h-10 w-10 text-slate-400 mx-auto" />
          <h3 className="text-sm font-bold text-slate-700 uppercase tracking-wider">No Audit Record Loaded</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            Evaluate a payment failure episode to generate an immutable decision audit log, or enter a Decision ID above to search.
          </p>
        </div>
      )}

      {errorMsg && (
        <div className="p-4 rounded bg-rose-50 border border-rose-200 text-xs text-rose-800">
          {errorMsg}
        </div>
      )}

      {record && (
        <div className="bg-white border border-slate-200 rounded p-6 shadow-sm space-y-6">

          {/* Header Summary Row */}
          <div className="flex flex-wrap items-center justify-between border-b border-slate-200 pb-4 gap-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-base font-bold text-blue-600">{record.decision_id}</span>
                <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                  record.status === 'APPROVED' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-amber-50 text-amber-800 border border-amber-200'
                }`}>
                  {record.status}
                </span>
                <span className="px-2 py-0.5 rounded text-xs font-mono bg-slate-100 text-slate-700 border border-slate-200">
                  Exec Status: {record.execution_status.toUpperCase()}
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-1">Payment ID: <span className="font-mono text-slate-800 font-semibold">{record.payment_id}</span> | Timestamp: {record.timestamp}</p>
            </div>

            <button
              onClick={() => setShowRawJson(!showRawJson)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold transition-colors border border-slate-300 shadow-sm"
            >
              <Code className="h-3.5 w-3.5 text-slate-500" />
              <span>{showRawJson ? 'Hide Raw JSON' : 'View Raw JSON'}</span>
            </button>
          </div>

          {showRawJson ? (
            <pre className="p-4 rounded bg-slate-900 border border-slate-800 text-xs font-mono text-emerald-400 overflow-x-auto">
              {JSON.stringify(record, null, 2)}
            </pre>
          ) : (
            <div className="space-y-6">

              {/* Evaluated Action Probability & EV Matrix */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Candidate Action Evaluation Matrix</h4>
                <div className="bg-white border border-slate-200 rounded overflow-hidden shadow-sm">
                  <table className="w-full text-left text-xs text-slate-700">
                    <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider text-[11px]">
                      <tr>
                        <th className="px-3.5 py-2.5">Action</th>
                        <th className="px-3.5 py-2.5">Safety Clearance</th>
                        <th className="px-3.5 py-2.5">Predicted P(rec)</th>
                        <th className="px-3.5 py-2.5">Expected Value EV</th>
                        <th className="px-3.5 py-2.5 text-right">Selection Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      {record.candidate_actions.map((act) => {
                        const isSafe = record.safe_actions.includes(act);
                        const isSelected = record.selected_action === act;
                        const p = record.predicted_probabilities[act] ?? 0.0;
                        const ev = record.expected_values[act] ?? 0.0;
                        return (
                          <tr key={act} className={isSelected ? 'bg-blue-50/60' : 'hover:bg-slate-50/50'}>
                            <td className="px-3.5 py-2.5 font-mono font-semibold capitalize text-slate-900">
                              {act.replace('_', ' ')}
                            </td>
                            <td className="px-3.5 py-2.5">
                              {isSafe ? (
                                <span className="text-emerald-700 font-semibold flex items-center gap-1">
                                  <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" /> Safe
                                </span>
                              ) : (
                                <span className="text-rose-700 font-semibold">Blocked by Safety Gate</span>
                              )}
                            </td>
                            <td className="px-3.5 py-2.5 font-mono text-slate-700">
                              {(p * 100).toFixed(2)}%
                            </td>
                            <td className="px-3.5 py-2.5 font-mono font-bold text-slate-900">
                              ₹{ev.toFixed(2)}
                            </td>
                            <td className="px-3.5 py-2.5 text-right">
                              {isSelected ? (
                                <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
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
                <div className="p-4 rounded bg-slate-50 border border-slate-200 space-y-1.5">
                  <div className="text-xs font-bold text-slate-700">Safety Rule Applied</div>
                  <p className="text-xs text-slate-700 font-mono">{record.safety_rule}</p>
                </div>

                <div className="p-4 rounded bg-slate-50 border border-slate-200 space-y-1.5">
                  <div className="text-xs font-bold text-slate-700">Decision Rationale</div>
                  <p className="text-xs text-slate-700 leading-relaxed font-sans">{record.reason}</p>
                </div>
              </div>

            </div>
          )}

        </div>
      )}

    </div>
  );
};
