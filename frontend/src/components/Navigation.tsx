import React from 'react';
import { LayoutDashboard, ListFilter, Crosshair, FileCheck, BarChart3 } from 'lucide-react';

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
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'queue', label: 'Payment Queue', icon: ListFilter },
    { 
      id: 'inspector', 
      label: selectedPaymentId ? `Inspector (${selectedPaymentId.slice(-8)})` : 'Decision Inspector', 
      icon: Crosshair 
    },
    { 
      id: 'audit', 
      label: activeDecisionId ? `Audit Trail (${activeDecisionId.slice(-8)})` : 'Audit Trail', 
      icon: FileCheck 
    },
    { id: 'evaluation', label: 'Evaluation Metrics', icon: BarChart3 },
  ];

  return (
    <nav className="border-b border-slate-800 bg-slate-900/50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex overflow-x-auto space-x-1 py-2">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as TabType)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-colors whitespace-nowrap ${
                isActive
                  ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <Icon className={`h-4 w-4 ${isActive ? 'text-indigo-400' : 'text-slate-500'}`} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
};
