import React from 'react';
import { BarChart3, Info } from 'lucide-react';

export const Evaluation: React.FC = () => {

  return (
    <div className="space-y-6">
      
      {/* Header Banner */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-indigo-400" />
            <h2 className="text-lg font-bold text-slate-100">Task 11 & 12 Off-Policy & Robustness Evaluation</h2>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">Comprehensive counterfactual off-policy SNIPS, synthetic oracle benchmark, and sensitivity analysis</p>
        </div>

        <div className="px-3 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 text-xs font-semibold">
          Synthetic Off-Policy Benchmark
        </div>
      </div>

      {/* Grid: Predictive Metrics & Policy Performance */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* ROC AUC */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-1">
          <div className="text-xs font-medium text-slate-400">Predictive ROC AUC</div>
          <div className="text-2xl font-bold text-slate-100 font-mono">0.8532</div>
          <p className="text-xs text-slate-400">High recovery probability discrimination</p>
        </div>

        {/* Brier Score */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-1">
          <div className="text-xs font-medium text-slate-400">Model Brier Score</div>
          <div className="text-2xl font-bold text-slate-100 font-mono">0.1516</div>
          <p className="text-xs text-slate-400">Well-calibrated probability predictions</p>
        </div>

        {/* SNIPS Uplift */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-1">
          <div className="text-xs font-medium text-slate-400">SNIPS Off-Policy Uplift</div>
          <div className="text-2xl font-bold text-emerald-400 font-mono">+56.8%</div>
          <p className="text-xs text-emerald-400 font-medium">+₹879.32 / event over baseline</p>
        </div>

        {/* Oracle Regret */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-1">
          <div className="text-xs font-medium text-slate-400">Oracle Policy Regret</div>
          <div className="text-2xl font-bold text-indigo-400 font-mono">₹0.94</div>
          <p className="text-xs text-slate-400">Near-zero regret vs true theoretical maximum</p>
        </div>

      </div>

      {/* Grid: Off-Policy SNIPS Evaluation vs Synthetic Oracle Benchmark */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Off-Policy SNIPS Summary Card */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Evaluation B: SNIPS Off-Policy Policy Evaluation</h3>
            <span className="text-xs font-mono text-slate-400">N = 15,000 Episodes</span>
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex justify-between items-center py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Logged Epsilon-Greedy Policy Realized EV</span>
              <span className="font-mono font-semibold text-slate-200">₹1,555.19</span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Deterministic Baseline Policy SNIPS EV</span>
              <span className="font-mono font-semibold text-amber-400">₹1,546.59 <span className="text-slate-500 font-normal">(Coverage 72.9%)</span></span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-slate-800/60">
              <span className="text-slate-400">O1 Economic ML Policy SNIPS EV</span>
              <span className="font-mono font-bold text-emerald-400 text-sm">₹2,425.91 <span className="text-slate-400 font-normal text-xs">(Coverage 38.5%)</span></span>
            </div>
            <div className="flex justify-between items-center py-1">
              <span className="text-slate-300 font-semibold">Net Expected Economic Value Uplift</span>
              <span className="font-mono font-bold text-emerald-400 text-sm">+₹879.32 / event (+56.8%)</span>
            </div>
          </div>

          <div className="p-3 rounded-lg bg-indigo-500/5 border border-indigo-500/10 text-xs text-slate-400 leading-relaxed">
            <span className="font-semibold text-indigo-300">Off-Policy Rigor:</span> Uses Self-Normalized Importance Sampling (SNIPS) with actual historical propensity logging probabilities $e(a|X)$, strictly avoiding counterfactual outcome leakage.
          </div>
        </div>

        {/* Synthetic Oracle Benchmark Card */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Evaluation C: Ground-Truth Oracle Benchmark</h3>
            <span className="text-xs font-mono text-indigo-400 font-semibold">Oracle Ground Truth</span>
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex justify-between items-center py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Oracle Evaluated Baseline Policy EV</span>
              <span className="font-mono font-semibold text-slate-200">₹1,668.04</span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Oracle Evaluated O1 ML Policy EV</span>
              <span className="font-mono font-bold text-emerald-400">₹2,349.72</span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Oracle Theoretical Best Policy EV</span>
              <span className="font-mono font-bold text-slate-100">₹2,350.67</span>
            </div>
            <div className="flex justify-between items-center py-1">
              <span className="text-slate-300 font-semibold">O1 Policy Regret vs Theoretical Best</span>
              <span className="font-mono font-bold text-indigo-400">₹0.94 / event</span>
            </div>
          </div>

          <div className="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/10 text-xs text-slate-400 leading-relaxed">
            <span className="font-semibold text-emerald-300">Near-Optimal Performance:</span> O1 achieves 99.96% of the theoretical maximum oracle recovery value, demonstrating that the ML predictor accurately captures underlying recovery dynamics.
          </div>
        </div>

      </div>

      {/* Task 12 Robustness Matrix Table */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Task 12 Economic Sensitivity & Robustness Matrix</h3>
            <p className="text-xs text-slate-400 mt-0.5">Policy stability across economic parameter perturbations and distribution shifts</p>
          </div>
          <span className="px-2 py-0.5 rounded text-xs font-mono bg-slate-800 text-slate-300">
            6 Economic Scenarios + 3 Shifts
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950 border-b border-slate-800 text-slate-400 font-semibold text-[11px]">
              <tr>
                <th className="px-4 py-2.5">Scenario / Shift</th>
                <th className="px-4 py-2.5">Baseline EV</th>
                <th className="px-4 py-2.5">O1 ML Policy EV</th>
                <th className="px-4 py-2.5">Oracle Best EV</th>
                <th className="px-4 py-2.5">O1 Uplift</th>
                <th className="px-4 py-2.5 text-right">Ranking Stability</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              <tr>
                <td className="px-4 py-2.5 font-semibold text-slate-200">Baseline Scenario</td>
                <td className="px-4 py-2.5 font-mono">₹1,668.04</td>
                <td className="px-4 py-2.5 font-mono text-emerald-400 font-bold">₹2,349.72</td>
                <td className="px-4 py-2.5 font-mono">₹2,350.67</td>
                <td className="px-4 py-2.5 font-mono text-emerald-400">+₹681.68</td>
                <td className="px-4 py-2.5 text-right"><span className="text-emerald-400 font-bold">STABLE</span></td>
              </tr>
              <tr>
                <td className="px-4 py-2.5 font-semibold text-slate-200">High Retry Cost (2.5x)</td>
                <td className="px-4 py-2.5 font-mono">₹1,659.54</td>
                <td className="px-4 py-2.5 font-mono text-emerald-400 font-bold">₹2,343.83</td>
                <td className="px-4 py-2.5 font-mono">₹2,344.82</td>
                <td className="px-4 py-2.5 font-mono text-emerald-400">+₹684.29</td>
                <td className="px-4 py-2.5 text-right"><span className="text-emerald-400 font-bold">STABLE</span></td>
              </tr>
              <tr>
                <td className="px-4 py-2.5 font-semibold text-slate-200">High Friction (2.0x)</td>
                <td className="px-4 py-2.5 font-mono">₹1,656.32 font-mono</td>
                <td className="px-4 py-2.5 font-mono text-emerald-400 font-bold">₹2,345.92</td>
                <td className="px-4 py-2.5 font-mono">₹2,347.01</td>
                <td className="px-4 py-2.5 font-mono text-emerald-400">+₹689.60</td>
                <td className="px-4 py-2.5 text-right"><span className="text-emerald-400 font-bold">STABLE</span></td>
              </tr>
              <tr>
                <td className="px-4 py-2.5 font-semibold text-slate-200">Distribution Shift (3.0x Amount)</td>
                <td className="px-4 py-2.5 font-mono">₹5,004.12</td>
                <td className="px-4 py-2.5 font-mono text-emerald-400 font-bold">₹7,057.89</td>
                <td className="px-4 py-2.5 font-mono">₹7,060.75</td>
                <td className="px-4 py-2.5 font-mono text-emerald-400">+₹2,053.77</td>
                <td className="px-4 py-2.5 text-right"><span className="text-emerald-400 font-bold">STABLE</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Persistent Disclaimer */}
      <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800 flex items-start gap-3">
        <Info className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
        <div className="text-xs text-slate-400 leading-relaxed">
          <span className="font-semibold text-amber-300">Research Evaluation Notice:</span> All metrics are calculated strictly on synthetic test datasets using counterfactual propensity weighting and ground-truth environment simulation. They demonstrate methodology correctness and robust uplift bounds under synthetic conditions.
        </div>
      </div>

    </div>
  );
};
