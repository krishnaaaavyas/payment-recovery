import React from 'react';
import { ListFilter, Zap, FileCheck, BarChart3, LayoutDashboard } from 'lucide-react';

export type TabType = 'overview' | 'queue' | 'inspector' | 'audit' | 'evaluation';

interface NavigationProps {
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
  selectedPaymentId?: string | null;
  activeDecisionId?: string | null;
}

export const Navigation: React.FC<NavigationProps> = ({
  activeTab,
  setActiveTab,
  selectedPaymentId,
  activeDecisionId
}) => {
  const tabs = [
    { id: 'queue', label: 'Payments', icon: ListFilter },
    {
      id: 'inspector',
      label: selectedPaymentId ? `Decision (${selectedPaymentId.slice(-8)})` : 'Decision',
      icon: Zap
    },
    {
      id: 'audit',
      label: activeDecisionId ? `Audit (${activeDecisionId.slice(-8)})` : 'Audit',
      icon: FileCheck
    },
    { id: 'evaluation', label: 'Evaluation', icon: BarChart3 },
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  ];

  return (
    <nav className="border-b border-slate-800 bg-slate-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex overflow-x-auto space-x-1 pt-1">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as TabType)}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors whitespace-nowrap ${
                isActive
                  ? 'border-indigo-500 text-indigo-300 bg-slate-800/60'
                  : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-800/30'
              }`}
            >
              <Icon className={`h-3.5 w-3.5 ${isActive ? 'text-indigo-400' : 'text-slate-500'}`} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
};
