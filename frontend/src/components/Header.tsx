import React from 'react';
import { ShieldCheck, Server } from 'lucide-react';

interface HeaderProps {
  apiOnline: boolean;
}

export const Header: React.FC<HeaderProps> = ({ apiOnline }) => {
  return (
    <header className="border-b border-slate-800 bg-slate-900 text-slate-100 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex flex-wrap items-center justify-between gap-4">

        {/* Brand & Track Title */}
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded bg-indigo-950 border border-indigo-700/50 flex items-center justify-center text-indigo-400 font-bold font-mono text-sm">
            O1
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold text-slate-100 tracking-tight">O1 Recovery Advisor</h1>
              <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                Track 03 — AI Revenue Recovery
              </span>
            </div>
            <p className="text-[11px] text-slate-400">Payment Recovery Operations Console</p>
          </div>
        </div>

        {/* System Status & Data Tier Disclosure */}
        <div className="flex items-center gap-3">
          {/* API Health Badge */}
          <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium border ${
            apiOnline
              ? 'bg-slate-950 text-emerald-400 border-emerald-500/30'
              : 'bg-slate-950 text-rose-400 border-rose-500/30'
          }`}>
            <Server className="h-3.5 w-3.5" />
            <span>{apiOnline ? 'Backend Connected' : 'Backend Disconnected'}</span>
          </div>

          {/* Synthetic Data Disclosure Badge */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium bg-slate-950 text-amber-400 border border-amber-500/30">
            <ShieldCheck className="h-3.5 w-3.5" />
            <span>Synthetic Evaluation Data</span>
          </div>
        </div>

      </div>
    </header>
  );
};
