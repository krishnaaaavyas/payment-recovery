import React from 'react';
import { ShieldCheck, Server } from 'lucide-react';

interface HeaderProps {
  apiOnline: boolean;
}

export const Header: React.FC<HeaderProps> = ({ apiOnline }) => {
  return (
    <header className="border-b border-slate-200 bg-white text-slate-900 sticky top-0 z-50 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex flex-wrap items-center justify-between gap-4">

        {/* Brand & Track Title */}
        <div className="flex items-center gap-3">
          <div className="h-8 px-2.5 rounded bg-blue-600 text-white font-bold font-sans text-xs flex items-center justify-center shadow-sm tracking-tight">
            PR
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold text-slate-900 tracking-tight">Payment Recovery</h1>
              <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                Built for Razorpay AI Buildathon 2026 — Track 03
              </span>
            </div>
            <p className="text-[11px] text-slate-500">Recover failed payments with safer, smarter decisions.</p>
          </div>
        </div>

        {/* System Status & Data Tier Disclosure */}
        <div className="flex items-center gap-3">
          {/* API Health Badge */}
          <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-semibold border ${
            apiOnline
              ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
              : 'bg-rose-50 text-rose-700 border-rose-200'
          }`}>
            <Server className="h-3.5 w-3.5" />
            <span>{apiOnline ? 'Backend Connected' : 'Backend Disconnected'}</span>
          </div>

          {/* Synthetic Data Disclosure Badge */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200">
            <ShieldCheck className="h-3.5 w-3.5 text-amber-600" />
            <span>TIER C — Synthetic Evaluation Data</span>
          </div>
        </div>

      </div>
    </header>
  );
};
