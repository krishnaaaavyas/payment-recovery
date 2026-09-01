import React from 'react';
import { AlertCircle, Cpu } from 'lucide-react';

interface HeaderProps {
  apiOnline: boolean;
}

export const Header: React.FC<HeaderProps> = ({ apiOnline }) => {
  return (
    <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex flex-wrap items-center justify-between gap-4">
        
        {/* Brand & Track Title */}
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            <Cpu className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-slate-100 tracking-tight">O1 Recovery Advisor</h1>
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                Track 03 — AI Revenue Recovery
              </span>
            </div>
            <p className="text-xs text-slate-400">Post-Payment-Failure Economic Decision Console</p>
          </div>
        </div>

        {/* System Status & Data Tier Disclosure */}
        <div className="flex items-center gap-3">
          {/* API Health Pill */}
          <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border ${
            apiOnline 
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' 
              : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
          }`}>
            <span className={`h-2 w-2 rounded-full ${apiOnline ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'}`} />
            {apiOnline ? 'FastAPI Backend Online' : 'API Disconnected'}
          </div>

          {/* Persistent Synthetic Data Disclosure Badge */}
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertCircle className="h-3.5 w-3.5" />
            <span>TIER C — Synthetic Evaluation Environment</span>
          </div>
        </div>

      </div>
    </header>
  );
};
