import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { Navigation, TabType } from './components/Navigation';
import { Overview } from './components/Overview';
import { PaymentQueue } from './components/PaymentQueue';
import { DecisionInspector } from './components/DecisionInspector';
import { AuditTrail } from './components/AuditTrail';
import { Evaluation } from './components/Evaluation';

import { FailedPaymentEvent, RecoveryDecisionResponse } from './types/api';
import { fetchHealth, fetchEvents } from './services/api';
import { AlertCircle } from 'lucide-react';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('queue');
  const [apiOnline, setApiOnline] = useState<boolean>(false);
  const [events, setEvents] = useState<FailedPaymentEvent[]>([]);
  const [eventsLoading, setEventsLoading] = useState<boolean>(true);
  const [selectedEvent, setSelectedEvent] = useState<FailedPaymentEvent | null>(null);
  const [currentDecision, setCurrentDecision] = useState<RecoveryDecisionResponse | null>(null);
  const [auditDecisionId, setAuditDecisionId] = useState<string | null>(null);

  useEffect(() => {
    checkHealth();
    loadEvents();
  }, []);

  const checkHealth = async () => {
    try {
      await fetchHealth();
      setApiOnline(true);
    } catch {
      setApiOnline(false);
    }
  };

  const loadEvents = async () => {
    setEventsLoading(true);
    try {
      const data = await fetchEvents(50);
      setEvents(data);
      if (data.length > 0 && !selectedEvent) {
        setSelectedEvent(data[0]);
      }
    } catch {
      setEvents([]);
    } finally {
      setEventsLoading(false);
    }
  };

  const handleSelectEvent = (evt: FailedPaymentEvent) => {
    setSelectedEvent(evt);
    setCurrentDecision(null);
    setActiveTab('inspector');
  };

  const handleViewAudit = (decisionId: string) => {
    setAuditDecisionId(decisionId);
    setActiveTab('audit');
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 font-sans antialiased">

      {/* Top Header */}
      <Header apiOnline={apiOnline} />

      {/* Navigation */}
      <Navigation
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        selectedPaymentId={selectedEvent?.payment_id}
        activeDecisionId={currentDecision?.decision_id || auditDecisionId}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">

        {!apiOnline && (
          <div className="mb-6 p-4 rounded bg-rose-50 border border-rose-200 text-xs text-rose-800 flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-rose-600 shrink-0" />
            <div>
              <span className="font-bold">FastAPI Backend Server Offline:</span> Ensure the backend service is running locally on <code className="font-mono text-rose-900 font-semibold">http://localhost:8000</code> (<code className="font-mono text-rose-900 font-semibold">uvicorn src.api.app:app --reload</code>).
            </div>
          </div>
        )}

        {activeTab === 'overview' && (
          <Overview onNavigateToQueue={() => setActiveTab('queue')} />
        )}

        {activeTab === 'queue' && (
          <PaymentQueue
            events={events}
            loading={eventsLoading}
            onSelectEvent={handleSelectEvent}
            onRefresh={loadEvents}
          />
        )}

        {activeTab === 'inspector' && (
          <DecisionInspector
            event={selectedEvent}
            decision={currentDecision}
            setDecision={setCurrentDecision}
            onViewAudit={handleViewAudit}
            onBackToQueue={() => setActiveTab('queue')}
          />
        )}

        {activeTab === 'audit' && (
          <AuditTrail decisionId={auditDecisionId || currentDecision?.decision_id || null} />
        )}

        {activeTab === 'evaluation' && (
          <Evaluation />
        )}

      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-500">
        Payment Recovery | Built for Razorpay AI Buildathon 2026 — Track 03 (TIER C — Synthetic Evaluation Data)
      </footer>

    </div>
  );
};

export default App;
