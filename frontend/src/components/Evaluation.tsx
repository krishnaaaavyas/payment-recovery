import React, { useEffect, useState } from 'react';
import { BarChart3, Info, AlertCircle, Loader2 } from 'lucide-react';
import { EvaluationSummary } from '../types/api';
import { fetchEvaluationReports } from '../services/api';

const inr = (v: number | undefined) =>
  v === undefined || v === null ? '—' : `₹${v.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const pct = (v: number | undefined, digits = 1) =>
  v === undefined || v === null ? '—' : `${(v * 100).toFixed(digits)}%`;

export const Evaluation: React.FC = () => {
  const [summary, setSummary] = useState<EvaluationSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchEvaluationReports()
      .then((data) => { if (!cancelled) { setSummary(data); setError(null); } })
      .catch((e) => { if (!cancelled) setError(e.message || 'Could not load evaluation reports'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return (
      <div className="flex items-center gap-3 p-8 text-slate-400 text-sm">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading evaluation reports from backend…
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="p-5 rounded-xl bg-rose-500/5 border border-rose-500/20 flex items-start gap-3">
        <AlertCircle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
        <div className="text-xs text-slate-300 leading-relaxed">
          <span className="font-semibold text-rose-300">Evaluation reports unavailable.</span>{' '}
          {error}. Metrics on this page are read from <span className="font-mono">GET /reports/summary</span>;
          run <span className="font-mono">python scripts/evaluate_policy.py</span> and{' '}
          <span className="font-mono">python scripts/run_robustness.py</span>, then start the backend.
        </div>
      </div>
    );
  }

  const t11 = summary.task11_policy_evaluation ?? {};
  const model = summary.task11_model_results ?? {};
  const direct = t11.direct_ground_truth_benchmark;
  const snips = t11.off_policy_snips_evaluation;
  const econ = summary.task12_robustness?.economic_sensitivity ?? {};
  const shifts = summary.task12_robustness?.distribution_shifts ?? {};
  const gtRobust = summary.task12_robustness?.ground_truth_robustness ?? {};
  const ablation = summary.task12_robustness?.ablation_study ?? {};

  const scenarioRows: Array<[string, string, any]> = [
    ...Object.entries(econ).map(([k, v]) => ['Economic', k, v] as [string, string, any]),
    ...Object.entries(gtRobust).map(([k, v]) => ['Ground truth', k, v] as [string, string, any]),
    ...Object.entries(shifts).map(([k, v]) => ['Shift', k, v] as [string, string, any]),
  ];

  return (
    <div className="space-y-6">

      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-indigo-400" />
            <h2 className="text-lg font-bold text-slate-100">Task 11 &amp; 12 Evaluation</h2>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Live from <span className="font-mono">GET /reports/summary</span> — direct ground-truth simulator benchmark,
            SNIPS off-policy estimator, robustness and ablation
          </p>
        </div>
        <div className="px-3 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 text-xs font-semibold">
          Synthetic Evaluation Environment
        </div>
      </div>

      {/* Headline metric cards — all sourced from generated artifacts */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-1">
          <div className="text-xs font-medium text-slate-400">Model ROC AUC (held-out test)</div>
          <div className="text-2xl font-bold text-slate-100 font-mono">
            {model.test_metrics?.roc_auc?.toFixed(4) ?? '—'}
          </div>
          <p className="text-xs text-slate-400">
            Validation (selection split): {model.validation_metrics?.roc_auc?.toFixed(4) ?? '—'}
          </p>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-1">
          <div className="text-xs font-medium text-slate-400">Model Brier (held-out test)</div>
          <div className="text-2xl font-bold text-slate-100 font-mono">
            {model.test_metrics?.brier_score?.toFixed(4) ?? '—'}
          </div>
          <p className="text-xs text-slate-400">
            Validation (selection split): {model.validation_metrics?.brier_score?.toFixed(4) ?? '—'}
          </p>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-1">
          <div className="text-xs font-medium text-slate-400">Direct Uplift over Baseline</div>
          <div className="text-2xl font-bold text-emerald-400 font-mono">
            +{direct?.direct_uplift_over_baseline_pct?.toFixed(2) ?? '—'}%
          </div>
          <p className="text-xs text-emerald-400 font-medium">
            +{inr(direct?.direct_uplift_over_baseline_inr_per_event)} / event · full population
          </p>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-1">
          <div className="text-xs font-medium text-slate-400">Regret vs Oracle</div>
          <div className="text-2xl font-bold text-indigo-400 font-mono">
            {inr(direct?.direct_true_regret_inr_per_event)}
          </div>
          <p className="text-xs text-slate-400">
            {direct ? `${(direct.direct_policy_efficiency * 100).toFixed(2)}% of oracle ceiling` : '—'}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Direct ground truth — authoritative */}
        <div className="bg-slate-900/60 border border-emerald-500/20 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
              Direct Ground-Truth Simulator
            </h3>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              AUTHORITATIVE
            </span>
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex justify-between items-center py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Episodes Evaluated</span>
              <span className="font-mono font-semibold text-slate-200">
                {direct?.events_evaluated?.toLocaleString()} / {direct?.events_in_population?.toLocaleString()}
                {direct?.events_missing_ground_truth === 0 && <span className="text-emerald-400"> · none dropped</span>}
              </span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Deterministic Baseline Policy EV</span>
              <span className="font-mono font-semibold text-amber-400">{inr(direct?.direct_true_baseline_policy_ev_inr)}</span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-slate-800/60">
              <span className="text-slate-400">O1 Economic Policy EV</span>
              <span className="font-mono font-bold text-emerald-400 text-sm">{inr(direct?.direct_true_o1_policy_ev_inr)}</span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Oracle Best Achievable EV</span>
              <span className="font-mono font-bold text-slate-100">{inr(direct?.direct_true_oracle_best_ev_inr)}</span>
            </div>
            <div className="flex justify-between items-center py-1">
              <span className="text-slate-300 font-semibold">Regret vs Oracle</span>
              <span className="font-mono font-bold text-indigo-400">
                {inr(direct?.direct_true_regret_inr_per_event)} / event
              </span>
            </div>
          </div>

          <div className="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/10 text-xs text-slate-400 leading-relaxed">
            <span className="font-semibold text-emerald-300">Why this is the headline:</span> every episode is scored
            against the hidden simulator, so there is no matched-subset restriction and no estimator variance.
            Per-event dominance violations: <span className="font-mono">{direct?.per_event_dominance_violations ?? '—'}</span> —
            O1 never exceeds the oracle on any individual event.
          </div>
        </div>

        {/* SNIPS — estimator */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
              SNIPS Off-Policy Estimator
            </h3>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-700/50 text-slate-300 border border-slate-600/40">
              ESTIMATE — NOT GROUND TRUTH
            </span>
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex justify-between items-center py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Logged ε-Greedy Policy Realized EV</span>
              <span className="font-mono font-semibold text-slate-200">{inr(snips?.logged_policy_realized_mean_ev_inr)}</span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Baseline SNIPS EV</span>
              <span className="font-mono font-semibold text-amber-400">
                {inr(snips?.baseline_policy_snips_ev_inr)}
                <span className="text-slate-500 font-normal"> ({pct(snips?.baseline_policy_coverage_rate)} cov.)</span>
              </span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-slate-800/60">
              <span className="text-slate-400">O1 SNIPS EV</span>
              <span className="font-mono font-bold text-emerald-400 text-sm">
                {inr(snips?.ml_policy_snips_ev_inr)}
                <span className="text-slate-400 font-normal text-xs"> ({pct(snips?.ml_policy_coverage_rate)} cov.)</span>
              </span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-slate-800/60">
              <span className="text-slate-400">O1 SNIPS 95% CI</span>
              <span className="font-mono text-slate-300">
                {inr(snips?.ml_policy_snips_ci?.ci_lower)} – {inr(snips?.ml_policy_snips_ci?.ci_upper)}
              </span>
            </div>
            <div className="flex justify-between items-center py-1">
              <span className="text-slate-400">Effective Sample Size</span>
              <span className="font-mono text-slate-300">
                {snips?.ml_effective_sample_size?.toFixed(1)} ({pct(snips?.ml_effective_sample_size_fraction)} of N)
              </span>
            </div>
          </div>

          <div className="p-3 rounded-lg bg-indigo-500/5 border border-indigo-500/10 text-xs text-slate-400 leading-relaxed">
            <span className="font-semibold text-indigo-300">How to read it:</span> SNIPS reweights only the logged
            episodes where O1 agrees with the historical policy, so it uses a fraction of the data and carries wide
            uncertainty. Its gap to the direct value ({inr(snips?.snips_minus_direct_true_ev_inr)}) is estimator
            variance, not additional recovered value. It is included because off-policy estimation is what a real
            deployment would have to rely on.
          </div>
        </div>
      </div>

      {/* Ablation */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
        <div>
          <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Architecture Ablation</h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Every variant scored on the identical full population — denominators shown explicitly
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950 border-b border-slate-800 text-slate-400 font-semibold text-[11px]">
              <tr>
                <th className="px-4 py-2.5">Variant</th>
                <th className="px-4 py-2.5 text-right">Mean True EV</th>
                <th className="px-4 py-2.5 text-right">Episodes Scored</th>
                <th className="px-4 py-2.5 text-right">Safety Violations</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {Object.entries(ablation).map(([name, v]) => (
                <tr key={name}>
                  <td className="px-4 py-2.5 font-semibold text-slate-200">{name.replace(/_/g, ' ')}</td>
                  <td className="px-4 py-2.5 font-mono text-right">{inr(v.mean_oracle_ev_inr)}</td>
                  <td className="px-4 py-2.5 font-mono text-right text-slate-400">
                    {v.events_evaluated?.toLocaleString()} / {v.events_in_population?.toLocaleString()}
                  </td>
                  <td className={`px-4 py-2.5 font-mono text-right font-bold ${v.safety_violations_count > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                    {v.safety_violations_count?.toLocaleString()} ({(v.safety_violation_rate * 100).toFixed(2)}%)
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-700/40 text-xs text-slate-400 leading-relaxed">
          Removing the Safety Gate raises simulated EV while breaching the action constraints on most episodes. In this
          environment the Safety Gate is a <span className="text-slate-200 font-medium">compliance boundary that costs
          expected value</span>, not a free optimization — the modelled misalignment penalty does not by itself justify it.
        </div>
      </div>

      {/* Robustness scenarios */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Robustness Matrix</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Economic perturbations, ground-truth interaction scaling, and distribution shifts — policy frozen throughout
            </p>
          </div>
          <span className="px-2 py-0.5 rounded text-xs font-mono bg-slate-800 text-slate-300">
            {scenarioRows.length} scenarios
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950 border-b border-slate-800 text-slate-400 font-semibold text-[11px]">
              <tr>
                <th className="px-4 py-2.5">Family</th>
                <th className="px-4 py-2.5">Scenario</th>
                <th className="px-4 py-2.5 text-right">Baseline EV</th>
                <th className="px-4 py-2.5 text-right">O1 EV</th>
                <th className="px-4 py-2.5 text-right">Oracle EV</th>
                <th className="px-4 py-2.5 text-right">Uplift</th>
                <th className="px-4 py-2.5 text-right">Regret</th>
                <th className="px-4 py-2.5 text-right">Ranking</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {scenarioRows.map(([family, name, v]) => (
                <tr key={`${family}-${name}`}>
                  <td className="px-4 py-2.5 text-slate-500">{family}</td>
                  <td className="px-4 py-2.5 font-semibold text-slate-200">{name.replace(/_/g, ' ')}</td>
                  <td className="px-4 py-2.5 font-mono text-right">{inr(v.baseline_policy_ev_ci?.mean)}</td>
                  <td className="px-4 py-2.5 font-mono text-right text-emerald-400 font-bold">{inr(v.ml_policy_ev_ci?.mean)}</td>
                  <td className="px-4 py-2.5 font-mono text-right">{inr(v.oracle_best_ev_ci?.mean)}</td>
                  <td className="px-4 py-2.5 font-mono text-right text-emerald-400">+{inr(v.uplift_ci?.mean)}</td>
                  <td className="px-4 py-2.5 font-mono text-right text-slate-400">{inr(v.regret_ci?.mean)}</td>
                  <td className="px-4 py-2.5 text-right">
                    {v.ranking_stable === undefined ? (
                      <span className="text-slate-500">—</span>
                    ) : v.ranking_stable ? (
                      <span className="text-emerald-400 font-bold">STABLE</span>
                    ) : (
                      <span className="text-rose-400 font-bold">UNSTABLE</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800 flex items-start gap-3">
        <Info className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
        <div className="text-xs text-slate-400 leading-relaxed">
          <span className="font-semibold text-amber-300">Synthetic evaluation notice:</span> in our synthetic evaluation
          environment, all recovery probabilities, expected values and policy metrics are generated by a hidden
          simulator. They demonstrate methodology under controlled conditions and are not measured Razorpay production
          performance, real customer recovery rates, or real money movement.
        </div>
      </div>

    </div>
  );
};
