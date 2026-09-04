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

      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded p-5 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-blue-600" />
            <h2 className="text-lg font-bold text-slate-900">Payment Recovery Evaluation &amp; Scientific Benchmarks</h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Direct ground-truth simulator benchmark, off-policy SNIPS estimation, safety gate ablations, and sensitivity robustness matrix
          </p>
        </div>
        <div className="px-3 py-1 rounded bg-amber-50 text-amber-800 border border-amber-200 text-xs font-semibold">
          TIER C — Synthetic Evaluation Data
        </div>
      </div>

      {/* Headline Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded p-4 shadow-sm space-y-1">
          <div className="text-xs font-medium text-slate-500">Model ROC AUC (held-out test)</div>
          <div className="text-2xl font-bold text-slate-900 font-mono">
            {model.test_metrics?.roc_auc?.toFixed(4) ?? '—'}
          </div>
          <p className="text-xs text-slate-500">
            Validation (selection split): {model.validation_metrics?.roc_auc?.toFixed(4) ?? '—'}
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded p-4 shadow-sm space-y-1">
          <div className="text-xs font-medium text-slate-500">Model Brier (held-out test)</div>
          <div className="text-2xl font-bold text-slate-900 font-mono">
            {model.test_metrics?.brier_score?.toFixed(4) ?? '—'}
          </div>
          <p className="text-xs text-slate-500">
            Validation (selection split): {model.validation_metrics?.brier_score?.toFixed(4) ?? '—'}
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded p-4 shadow-sm space-y-1">
          <div className="text-xs font-medium text-slate-500">Direct Uplift over Baseline</div>
          <div className="text-2xl font-bold text-emerald-600 font-mono">
            +{direct?.direct_uplift_over_baseline_pct?.toFixed(2) ?? '—'}%
          </div>
          <p className="text-xs text-emerald-700 font-semibold">
            +{inr(direct?.direct_uplift_over_baseline_inr_per_event)} / event · full population
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded p-4 shadow-sm space-y-1">
          <div className="text-xs font-medium text-slate-500">Regret vs Oracle</div>
          <div className="text-2xl font-bold text-blue-600 font-mono">
            {inr(direct?.direct_true_regret_inr_per_event)}
          </div>
          <p className="text-xs text-slate-500">
            {direct ? `${(direct.direct_policy_efficiency * 100).toFixed(2)}% of oracle ceiling` : '—'}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Direct Ground-Truth Benchmark */}
        <div className="bg-white border border-slate-200 rounded p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-200 pb-3">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Direct Ground-Truth Simulator
            </h3>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
              AUTHORITATIVE
            </span>
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex justify-between items-center py-1 border-b border-slate-100">
              <span className="text-slate-600">Episodes Evaluated</span>
              <span className="font-mono font-semibold text-slate-900">
                {direct?.events_evaluated?.toLocaleString()} / {direct?.events_in_population?.toLocaleString()}
                {direct?.events_missing_ground_truth === 0 && <span className="text-emerald-700"> · none dropped</span>}
              </span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-slate-100">
              <span className="text-slate-600">Deterministic Baseline Policy EV</span>
              <span className="font-mono font-semibold text-amber-700">{inr(direct?.direct_true_baseline_policy_ev_inr)}</span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-slate-100">
              <span className="text-slate-600">Payment Recovery Policy EV</span>
              <span className="font-mono font-bold text-emerald-600 text-sm">{inr(direct?.direct_true_o1_policy_ev_inr)}</span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-slate-100">
              <span className="text-slate-600">Oracle Best Achievable EV</span>
              <span className="font-mono font-bold text-slate-900">{inr(direct?.direct_true_oracle_best_ev_inr)}</span>
            </div>
            <div className="flex justify-between items-center py-1">
              <span className="text-slate-800 font-semibold">Regret vs Oracle</span>
              <span className="font-mono font-bold text-blue-600">
                {inr(direct?.direct_true_regret_inr_per_event)} / event
              </span>
            </div>
          </div>

          <div className="p-3 rounded bg-slate-50 border border-slate-200 text-xs text-slate-600 leading-relaxed">
            <span className="font-semibold text-slate-900">Why this is the headline:</span> every episode is scored
            against the hidden simulator, so there is no matched-subset restriction and no estimator variance.
            Per-event dominance violations: <span className="font-mono font-semibold text-slate-800">{direct?.per_event_dominance_violations ?? '—'}</span> —
            Policy never exceeds the oracle on any individual event.
          </div>
        </div>

        {/* SNIPS Off-Policy Estimator */}
        <div className="bg-white border border-slate-200 rounded p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-200 pb-3">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              SNIPS Off-Policy Estimator
            </h3>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200">
              ESTIMATE — NOT GROUND TRUTH
            </span>
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex justify-between items-center py-1 border-b border-slate-100">
              <span className="text-slate-600">Logged ε-Greedy Policy Realized EV</span>
              <span className="font-mono font-semibold text-slate-800">{inr(snips?.logged_policy_realized_mean_ev_inr)}</span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-slate-100">
              <span className="text-slate-600">Baseline SNIPS EV</span>
              <span className="font-mono font-semibold text-amber-700">
                {inr(snips?.baseline_policy_snips_ev_inr)}
                <span className="text-slate-500 font-normal"> ({pct(snips?.baseline_policy_coverage_rate)} cov.)</span>
              </span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-slate-100">
              <span className="text-slate-600">Payment Recovery SNIPS EV</span>
              <span className="font-mono font-bold text-emerald-600 text-sm">
                {inr(snips?.ml_policy_snips_ev_inr)}
                <span className="text-slate-500 font-normal text-xs"> ({pct(snips?.ml_policy_coverage_rate)} cov.)</span>
              </span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-slate-100">
              <span className="text-slate-600">O1 SNIPS 95% CI</span>
              <span className="font-mono text-slate-800">
                {inr(snips?.ml_policy_snips_ci?.ci_lower)} – {inr(snips?.ml_policy_snips_ci?.ci_upper)}
              </span>
            </div>
            <div className="flex justify-between items-center py-1">
              <span className="text-slate-600">Effective Sample Size</span>
              <span className="font-mono text-slate-800">
                {snips?.ml_effective_sample_size?.toFixed(1)} ({pct(snips?.ml_effective_sample_size_fraction)} of N)
              </span>
            </div>
          </div>

          <div className="p-3 rounded bg-slate-50 border border-slate-200 text-xs text-slate-600 leading-relaxed">
            <span className="font-semibold text-slate-900">How to read it:</span> SNIPS reweights only the logged
            episodes where O1 agrees with the historical policy, so it uses a fraction of the data and carries wide
            uncertainty. Its gap to the direct value ({inr(snips?.snips_minus_direct_true_ev_inr)}) is estimator
            variance, not additional recovered value.
          </div>
        </div>
      </div>

      {/* Architecture Ablation */}
      <div className="bg-white border border-slate-200 rounded p-5 shadow-sm space-y-4">
        <div>
          <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Architecture Ablation</h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Every variant scored on the identical full population — denominators shown explicitly
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-700">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold text-[11px]">
              <tr>
                <th className="px-4 py-2.5">Variant</th>
                <th className="px-4 py-2.5 text-right">Mean True EV</th>
                <th className="px-4 py-2.5 text-right">Episodes Scored</th>
                <th className="px-4 py-2.5 text-right">Safety Violations</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {Object.entries(ablation).map(([name, v]) => (
                <tr key={name}>
                  <td className="px-4 py-2.5 font-semibold text-slate-900">{name.replace(/_/g, ' ')}</td>
                  <td className="px-4 py-2.5 font-mono text-right">{inr(v.mean_oracle_ev_inr)}</td>
                  <td className="px-4 py-2.5 font-mono text-right text-slate-500">
                    {v.events_evaluated?.toLocaleString()} / {v.events_in_population?.toLocaleString()}
                  </td>
                  <td className={`px-4 py-2.5 font-mono text-right font-bold ${v.safety_violations_count > 0 ? 'text-rose-700' : 'text-emerald-700'}`}>
                    {v.safety_violations_count?.toLocaleString()} ({(v.safety_violation_rate * 100).toFixed(2)}%)
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="p-3 rounded bg-slate-50 border border-slate-200 text-xs text-slate-600 leading-relaxed">
          Removing the Safety Gate raises simulated EV while breaching the action constraints on most episodes. In this
          environment the Safety Gate is a <span className="text-slate-900 font-semibold">compliance boundary that costs
          expected value</span>, not a free optimization.
        </div>
      </div>

      {/* Robustness scenarios */}
      <div className="bg-white border border-slate-200 rounded p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Robustness Matrix</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Economic perturbations, ground-truth interaction scaling, and distribution shifts — policy frozen throughout
            </p>
          </div>
          <span className="px-2 py-0.5 rounded text-xs font-mono bg-slate-100 text-slate-700 border border-slate-200">
            {scenarioRows.length} scenarios
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-700">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold text-[11px]">
              <tr>
                <th className="px-4 py-2.5">Family</th>
                <th className="px-4 py-2.5">Scenario</th>
                <th className="px-4 py-2.5 text-right">Baseline EV</th>
                <th className="px-4 py-2.5 text-right">Policy EV</th>
                <th className="px-4 py-2.5 text-right">Oracle EV</th>
                <th className="px-4 py-2.5 text-right">Uplift</th>
                <th className="px-4 py-2.5 text-right">Regret</th>
                <th className="px-4 py-2.5 text-right">Ranking</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {scenarioRows.map(([family, name, v]) => (
                <tr key={`${family}-${name}`}>
                  <td className="px-4 py-2.5 text-slate-500">{family}</td>
                  <td className="px-4 py-2.5 font-semibold text-slate-900">{name.replace(/_/g, ' ')}</td>
                  <td className="px-4 py-2.5 font-mono text-right">{inr(v.baseline_policy_ev_ci?.mean)}</td>
                  <td className="px-4 py-2.5 font-mono text-right text-emerald-700 font-bold">{inr(v.ml_policy_ev_ci?.mean)}</td>
                  <td className="px-4 py-2.5 font-mono text-right">{inr(v.oracle_best_ev_ci?.mean)}</td>
                  <td className="px-4 py-2.5 font-mono text-right text-emerald-700 font-semibold">+{inr(v.uplift_ci?.mean)}</td>
                  <td className="px-4 py-2.5 font-mono text-right text-slate-500">{inr(v.regret_ci?.mean)}</td>
                  <td className="px-4 py-2.5 text-right">
                    {v.ranking_stable === undefined ? (
                      <span className="text-slate-400">—</span>
                    ) : v.ranking_stable ? (
                      <span className="text-emerald-700 font-bold">STABLE</span>
                    ) : (
                      <span className="text-rose-700 font-bold">UNSTABLE</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="p-4 rounded bg-amber-50 border border-amber-200 flex items-start gap-3">
        <Info className="h-4 w-4 text-amber-700 shrink-0 mt-0.5" />
        <div className="text-xs text-amber-900 leading-relaxed">
          <span className="font-semibold">Synthetic evaluation notice:</span> in our synthetic evaluation
          environment, all recovery probabilities, expected values and policy metrics are generated by a hidden
          simulator. They demonstrate methodology under controlled conditions and are not measured Razorpay production
          performance, real customer recovery rates, or real money movement.
        </div>
      </div>

    </div>
  );
};
