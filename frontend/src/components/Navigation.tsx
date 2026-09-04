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
      label: selectedPaymentId ? `Decisions (${selectedPaymentId.slice(-8)})` : 'Decisions',
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
    <nav className="border-b border-slate-200 bg-white">
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
                  ? 'border-blue-600 text-blue-600 bg-white'
                  : 'border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-50'
              }`}
            >
              <Icon className={`h-3.5 w-3.5 ${isActive ? 'text-blue-600' : 'text-slate-400'}`} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
};
