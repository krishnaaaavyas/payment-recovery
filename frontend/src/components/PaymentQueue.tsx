import React, { useState } from 'react';
import { FailedPaymentEvent } from '../types/api';
import { Search, Filter, ArrowRight, RefreshCw } from 'lucide-react';

interface PaymentQueueProps {
  events: FailedPaymentEvent[];
  loading: boolean;
  onSelectEvent: (event: FailedPaymentEvent) => void;
  onRefresh: () => void;
}

export const PaymentQueue: React.FC<PaymentQueueProps> = ({
  events,
  loading,
  onSelectEvent,
  onRefresh
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [methodFilter, setMethodFilter] = useState('ALL');
  const [categoryFilter, setCategoryFilter] = useState('ALL');

  const filteredEvents = events.filter((evt) => {
    const matchesSearch = evt.payment_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          evt.failure_code.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesMethod = methodFilter === 'ALL' || evt.payment_method === methodFilter;
    const matchesCategory = categoryFilter === 'ALL' || evt.failure_category === categoryFilter;
    return matchesSearch && matchesMethod && matchesCategory;
  });

  return (
    <div className="space-y-5">

      {/* Top Concise Summary Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-100">Failed Payments</h2>
          <p className="text-xs text-slate-400">O1 analyzes failure context and recommends safe, high-value recovery actions.</p>
        </div>
        <div className="flex items-center gap-4 text-xs font-mono">
          <div className="text-slate-400">Evaluated: <span className="font-bold text-slate-200">15,000</span></div>
          <div className="text-emerald-400 font-bold">Net EV Uplift: +40.78%</div>
          <div className="text-slate-300">Safety Violations: <span className="font-bold text-emerald-400">0</span></div>
        </div>
      </div>

      {/* Control Header & Filters */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-3 flex flex-wrap items-center justify-between gap-3">

        {/* Search */}
        <div className="relative flex-1 min-w-[240px]">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search by Payment ID or Failure Code..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-md pl-9 pr-4 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        {/* Method Filter */}
        <div className="flex items-center gap-2">
          <Filter className="h-3.5 w-3.5 text-slate-500" />
          <select
            value={methodFilter}
            onChange={(e) => setMethodFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-md px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
          >
            <option value="ALL">All Methods</option>
            <option value="card_credit">Credit Card</option>
            <option value="upi_intent">UPI Intent</option>
            <option value="netbanking">Netbanking</option>
          </select>
        </div>

        {/* Category Filter */}
        <div>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-md px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
          >
            <option value="ALL">All Failure Categories</option>
            <option value="network_timeout">Network Timeout</option>
            <option value="soft_decline">Soft Decline</option>
            <option value="authentication_failure">Auth Failure</option>
            <option value="insufficient_funds">Insufficient Funds</option>
          </select>
        </div>

        {/* Refresh Button */}
        <button
          onClick={onRefresh}
          className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
          title="Refresh Events"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </button>

      </div>

      {/* Events Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="px-4 py-3">Payment ID</th>
                <th className="px-4 py-3">Amount</th>
                <th className="px-4 py-3">Method</th>
                <th className="px-4 py-3">Failure Category</th>
                <th className="px-4 py-3">Failure Code</th>
                <th className="px-4 py-3 text-center">Attempts</th>
                <th className="px-4 py-3 text-center">Hist. Success</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {loading ? (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-slate-500">
                    Loading failed payment episodes...
                  </td>
                </tr>
              ) : filteredEvents.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-slate-500">
                    No failed payment events match current filters.
                  </td>
                </tr>
              ) : (
                filteredEvents.map((evt) => (
                  <tr key={evt.payment_id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="px-4 py-3 font-mono font-semibold text-indigo-400">
                      {evt.payment_id}
                    </td>
                    <td className="px-4 py-3 font-mono font-bold text-slate-100">
                      ₹{evt.amount.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 capitalize text-slate-300">
                      {evt.payment_method.replace('_', ' ')}
                    </td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-800 text-slate-300 border border-slate-700">
                        {evt.failure_category.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-[11px] text-slate-400 truncate max-w-[180px]">
                      {evt.failure_code}
                    </td>
                    <td className="px-4 py-3 text-center font-mono text-slate-300">
                      {evt.retry_count_before_event + 1}
                    </td>
                    <td className="px-4 py-3 text-center font-mono text-slate-300">
                      {(evt.historical_success_rate * 100).toFixed(0)}%
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => onSelectEvent(evt)}
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 text-xs font-medium transition-colors"
                      >
                        <span>Review Decision</span>
                        <ArrowRight className="h-3.5 w-3.5" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
};
