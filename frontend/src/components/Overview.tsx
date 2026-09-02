import React, { useEffect, useState } from 'react';
import { TrendingUp, ShieldCheck, AlertTriangle, ArrowRight, Zap, CheckCircle2, Info } from 'lucide-react';
import { EvaluationSummary } from '../types/api';
import { fetchEvaluationReports } from '../services/api';

interface OverviewProps {
  onNavigateToQueue: () => void;
}

// Presentation metadata only. The percentages themselves come from the generated
// evaluation artifact via GET /reports/summary - they are never restated here.
const ACTION_META: Record<string, { label: string; color: string; desc: string }> = {
  switch_method: { label: 'Switch Method', color: 'bg-sky-500', desc: 'Prompt user to switch payment instrument' },
  do_nothing: { label: 'Do Nothing', color: 'bg-slate-500', desc: 'Safe termination to avoid friction/fees' },
  update_information: { label: 'Update Info', color: 'bg-purple-500', desc: 'Prompt for card expiry/CVV update' },
  retry_later: { label: 'Retry Later', color: 'bg-indigo-500', desc: 'Scheduled for optimal issuer window' },
  retry_now: { label: 'Retry Now', color: 'bg-emerald-500', desc: 'Immediate retry on transient network glitch' },
};

const inr = (v?: number) =>
  v === undefined || v === null ? '-' : `₹${v.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export const Overview: React.FC<OverviewProps> = ({ onNavigateToQueue }) => {
  const [summary, setSummary] = useState<EvaluationSummary | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchEvaluationReports()
      .then((d) => { if (!cancelled) setSummary(d); })
      .catch(() => { if (!cancelled) setSummary(null); });
    return () => { cancelled = true; };
  }, []);

  const t11 = summary?.task11_policy_evaluation;
  const direct = t11?.direct_ground_truth_benchmark;
  const safety = t11?.safety_evaluation;
  const a3 = summary?.task12_robustness?.ablation_study?.A3_ML_Economic_No_Safety_Gate;

  const dist = t11?.distributions?.ml_action_distribution ?? {};
  const actionDistribution = Object.entries(dist)
    .sort((a, b) => b[1] - a[1])
    .map(([action, share]) => ({
      action,
      label: ACTION_META[action]?.label ?? action,
      color: ACTION_META[action]?.color ?? 'bg-slate-500',
      desc: ACTION_META[action]?.desc ?? '',
      percentage: share * 100,
    }));

  const a3Rate = a3 ? a3.safety_violation_rate * 100 : undefined;

  return (
    <div className="space-y-6">
      
      {/* Hero Welcome Banner */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 relative overflow-hidden">
        <div className="absolute -right-10 -bottom-10 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="max-w-3xl space-y-3">
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-md bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold">
            <Zap className="h-3.5 w-3.5" /> 30-Second Overview
          </div>
          <h2 className="text-2xl font-bold text-slate-100 tracking-tight">
            Post-Payment Failure Economic Recovery Layer
          </h2>
          <p className="text-sm text-slate-300 leading-relaxed">
            When a payment fails, <span className="font-semibold text-slate-100">O1</span> estimates recovery probability <span className="text-indigo-400 font-mono">P(rec|X,a)</span> and net Expected Economic Value <span className="text-indigo-400 font-mono">EV(a|X)</span> to select the optimal safe action, outperforming deterministic decline-code policies while enforcing hard safety constraints before any economic optimization.
          </p>
          <div className="pt-2 flex items-center gap-3">
            <button
              onClick={onNavigateToQueue}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-colors shadow-lg shadow-indigo-600/20"
            >
              <span>Explore Payment Queue & Decision Engine</span>
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Top Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* Card 1: Revenue at Risk */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-2">
          <div className="flex items-center justify-between text-xs font-medium text-slate-400">
            <span>Evaluated Volume</span>
            <Info className="h-3.5 w-3.5 text-slate-500" />
          </div>
          <div className="text-2xl font-bold text-slate-100 font-mono">
            {(direct?.events_evaluated ?? t11?.test_events_count ?? 0).toLocaleString()} Events
          </div>
          <p className="text-xs text-slate-400">Chronological held-out test split</p>
        </div>

        {/* Card 2: Baseline Expected Value */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-2">
          <div className="flex items-center justify-between text-xs font-medium text-slate-400">
            <span>Baseline Policy EV</span>
            <span className="text-amber-400 font-medium">Deterministic</span>
          </div>
          <div className="text-2xl font-bold text-slate-100 font-mono">{inr(direct?.direct_true_baseline_policy_ev_inr)}</div>
          <p className="text-xs text-slate-400">Decline-code rules, direct simulator</p>
        </div>

        {/* Card 3: O1 Policy Expected Value */}
        <div className="bg-slate-900/60 border border-indigo-500/30 rounded-xl p-4 space-y-2 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-24 h-24 bg-indigo-500/10 rounded-full blur-xl pointer-events-none" />
          <div className="flex items-center justify-between text-xs font-medium text-indigo-300">
            <span>O1 Economic Policy EV</span>
            <span className="text-emerald-400 font-bold">Optimal Safe</span>
          </div>
          <div className="text-2xl font-bold text-emerald-400 font-mono">{inr(direct?.direct_true_o1_policy_ev_inr)}</div>
          <p className="text-xs text-slate-300">Direct ground-truth simulator, full population</p>
        </div>

        {/* Card 4: Economic Gain / Uplift */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-2">
          <div className="flex items-center justify-between text-xs font-medium text-slate-400">
            <span>Net Economic Uplift</span>
            <TrendingUp className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 font-mono">
            +{direct?.direct_uplift_over_baseline_pct?.toFixed(2) ?? '-'}%
          </div>
          <p className="text-xs text-emerald-400 font-medium">
            +{inr(direct?.direct_uplift_over_baseline_inr_per_event)} / event vs baseline
          </p>
        </div>

      </div>

      {/* Grid: Safety Gate Ablation Comparison + Action Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Safety Gate Ablation Highlight */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-emerald-400" />
              <h3 className="text-sm font-semibold text-slate-100">Safety Gate Architectural Guarantee</h3>
            </div>
            <span className="px-2 py-0.5 rounded text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              {safety?.safety_violations_count ?? 0} Violations
            </span>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed">
            The Safety Gate enforces hard domain constraints <span className="font-mono text-slate-100">A_safe(X)</span> before economic optimization, preventing invalid interventions such as asking users to update card details during bank downtime.
          </p>

          {/* Side-by-Side Bar Comparison */}
          <div className="space-y-4 pt-2">
            
            {/* Full Architecture */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-medium text-slate-200 flex items-center gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" /> Full O1 Architecture (With Safety Gate)
                </span>
                <span className="font-mono font-bold text-emerald-400">
                  {((safety?.safety_violation_rate ?? 0) * 100).toFixed(2)}% Safety Violations ({safety?.safety_violations_count ?? 0} events)
                </span>
              </div>
              <div className="w-full h-3 bg-slate-800 rounded-full overflow-hidden">
                <div className="h-full bg-emerald-500 rounded-full w-full" />
              </div>
            </div>

            {/* Without Safety Gate */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-medium text-slate-300 flex items-center gap-1.5">
                  <AlertTriangle className="h-3.5 w-3.5 text-rose-400" /> Ablation A3 (Without Safety Gate)
                </span>
                <span className="font-mono font-bold text-rose-400">
                  {a3Rate !== undefined ? a3Rate.toFixed(2) : '-'}% Violations ({a3?.safety_violations_count?.toLocaleString() ?? '-'} events)
                </span>
              </div>
              <div className="w-full h-3 bg-slate-800 rounded-full overflow-hidden">
                <div className="h-full bg-rose-500 rounded-full" style={{ width: `${a3Rate ?? 0}%` }} />
              </div>
            </div>

          </div>

          <div className="p-3 rounded-lg bg-rose-500/5 border border-rose-500/10 text-xs text-slate-400 leading-relaxed">
            <span className="font-semibold text-rose-300">Ablation Finding:</span> Without Safety Gate constraints,
            unconstrained EV maximization breaches the action constraints on{' '}
            {a3Rate !== undefined ? a3Rate.toFixed(2) : '-'}% of episodes. The cause is action-space extrapolation:
            <span className="font-mono text-slate-300"> update_information</span> is only ever observed in the contexts
            where it is permitted, so the model over-generalizes it to contexts it was never logged in.
          </div>
        </div>

        {/* Action Share Distribution */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-100">Recommended Action Distribution</h3>
            <span className="text-xs text-slate-400">From /reports/summary</span>
          </div>

          <p className="text-xs text-slate-300">
            Action selection share across {(direct?.events_evaluated ?? 0).toLocaleString()} held-out test episodes:
          </p>

          <div className="space-y-3 pt-1">
            {actionDistribution.map((item) => (
              <div key={item.action} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-slate-200">{item.label}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400 text-[11px]">{item.desc}</span>
                    <span className="font-mono font-bold text-slate-100">{item.percentage.toFixed(2)}%</span>
                  </div>
                </div>
                <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                  <div className={`h-full ${item.color} rounded-full`} style={{ width: `${item.percentage}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>

      {/* Persistent Synthetic Evaluation Disclaimer Footer */}
      <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800 flex items-start gap-3">
        <Info className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
        <div className="text-xs text-slate-400 leading-relaxed">
          <span className="font-semibold text-amber-300">Synthetic Environment Disclaimer:</span> In our synthetic
          evaluation environment, recovery probabilities, expected economic values and policy metrics are produced by a
          hidden simulator (Task 10-12) and read live from the generated evaluation artifacts. They do not represent
          measured Razorpay production performance, real customer recovery rates, or real money movement.
        </div>
      </div>

    </div>
  );
};
