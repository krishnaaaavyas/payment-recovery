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

  const formatCategory = (cat: string) => {
    switch (cat) {
      case 'authentication_failure': return 'Auth Failure';
      case 'network_timeout': return 'Network Timeout';
      case 'soft_decline': return 'Soft Decline';
      case 'insufficient_funds': return 'Insufficient Funds';
      default: return cat.replace('_', ' ');
    }
  };

  return (
    <div className="space-y-4">

      {/* Top Concise Summary Banner */}
      <div className="bg-white border border-slate-200 rounded p-4 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">Failed Payment Recovery Queue</h2>
          <p className="text-xs text-slate-500">Failed payment episodes evaluated by Payment Recovery for safe economic action selection.</p>
        </div>
        <div className="flex items-center gap-4 text-xs font-mono">
          <div className="text-slate-600">Evaluated: <span className="font-bold text-slate-900">15,000</span></div>
          <div className="text-emerald-600 font-bold">Net EV Uplift: +40.78%</div>
          <div className="text-slate-700">Safety Violations: <span className="font-bold text-emerald-600">0</span></div>
        </div>
      </div>

      {/* Control Header & Filters */}
      <div className="bg-white border border-slate-200 rounded p-3 shadow-sm flex flex-wrap items-center justify-between gap-3">

        {/* Search */}
        <div className="relative flex-1 min-w-[240px]">
          <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-400" />
          <input
            type="text"
            placeholder="Filter by Payment ID or Failure Code..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-slate-50 border border-slate-300 rounded pl-8 pr-4 py-1.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-600 focus:bg-white"
          />
        </div>

        {/* Method Filter */}
        <div className="flex items-center gap-2">
          <Filter className="h-3.5 w-3.5 text-slate-400" />
          <select
            value={methodFilter}
            onChange={(e) => setMethodFilter(e.target.value)}
            className="bg-slate-50 border border-slate-300 rounded px-3 py-1.5 text-xs text-slate-700 focus:outline-none focus:border-blue-600 focus:bg-white"
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
            className="bg-slate-50 border border-slate-300 rounded px-3 py-1.5 text-xs text-slate-700 focus:outline-none focus:border-blue-600 focus:bg-white"
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
          className="p-1.5 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 transition-colors"
          title="Refresh Queue"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
        </button>

      </div>

      {/* Events Table */}
      <div className="bg-white border border-slate-200 rounded shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-700">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="px-3.5 py-2.5">Payment ID</th>
                <th className="px-3.5 py-2.5">Amount</th>
                <th className="px-3.5 py-2.5">Method</th>
                <th className="px-3.5 py-2.5">Failure Reason</th>
                <th className="px-3.5 py-2.5">Failure Code</th>
                <th className="px-3.5 py-2.5 text-center">Attempts</th>
                <th className="px-3.5 py-2.5 text-center">Hist. Success</th>
                <th className="px-3.5 py-2.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
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
                  <tr key={evt.payment_id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="px-3.5 py-2.5 font-mono font-semibold text-blue-600">
                      {evt.payment_id}
                    </td>
                    <td className="px-3.5 py-2.5 font-mono font-bold text-slate-900">
                      ₹{evt.amount.toFixed(2)}
                    </td>
                    <td className="px-3.5 py-2.5 capitalize text-slate-700">
                      {evt.payment_method.replace('_', ' ')}
                    </td>
                    <td className="px-3.5 py-2.5">
                      <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-700 border border-slate-200">
                        {formatCategory(evt.failure_category)}
                      </span>
                    </td>
                    <td className="px-3.5 py-2.5 font-mono text-[11px] text-slate-500 truncate max-w-[180px]">
                      {evt.failure_code}
                    </td>
                    <td className="px-3.5 py-2.5 text-center font-mono text-slate-700">
                      {evt.retry_count_before_event + 1}
                    </td>
                    <td className="px-3.5 py-2.5 text-center font-mono text-slate-700">
                      {(evt.historical_success_rate * 100).toFixed(0)}%
                    </td>
                    <td className="px-3.5 py-2.5 text-right">
                      <button
                        onClick={() => onSelectEvent(evt)}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-white hover:bg-slate-50 text-slate-700 hover:text-blue-600 border border-slate-300 text-xs font-semibold transition-colors shadow-sm"
                      >
                        <span>Review</span>
                        <ArrowRight className="h-3 w-3" />
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
