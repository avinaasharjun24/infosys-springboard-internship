import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import Topbar from './components/Topbar';
import Dashboard from './components/Dashboard';
import SubmitDefect from './components/SubmitDefect';
import DefectHistory from './components/DefectHistory';
import KnowledgeBase from './components/KnowledgeBase';
import AgentExecution from './components/AgentExecution';
import AnalysisResults from './components/AnalysisResults';
import SettingsView from './components/Settings';

const API_BASE = 'http://127.0.0.1:8000/api';

export default function App() {
  const [activePage, setActivePage] = useState('dashboard');
  const [overview, setOverview] = useState(null);
  const [health, setHealth] = useState(null);
  const [submissions, setSubmissions] = useState([]);
  const [selectedDefect, setSelectedDefect] = useState(null);
  const [globalSearch, setGlobalSearch] = useState('');
  const [toastMessage, setToastMessage] = useState('');

  const notify = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(''), 4500);
  };

  const fetchHealth = async () => {
    try {
      const res = await fetch(`${API_BASE}/health`);
      if (res.ok) {
        const data = await res.json();
        setHealth(data);
      } else {
        setHealth(null);
      }
    } catch (err) {
      setHealth(null);
    }
  };

  const fetchOverview = async () => {
    try {
      const res = await fetch(`${API_BASE}/overview`);
      if (res.ok) {
        const data = await res.json();
        setOverview(data);
      }
    } catch (err) {
      console.warn('Overview fetch error:', err);
    }
  };

  const fetchSubmissions = async () => {
    try {
      const res = await fetch(`${API_BASE}/submissions`);
      if (res.ok) {
        const data = await res.json();
        setSubmissions(data);
      }
    } catch (err) {
      console.warn('Submissions fetch error:', err);
    }
  };

  const loadDefectDetail = async (id) => {
    try {
      const res = await fetch(`${API_BASE}/submissions/${id}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedDefect(data);
        setActivePage('results');
      } else {
        notify('Failed to load defect details.');
      }
    } catch (err) {
      notify(`Error: ${err.message}`);
    }
  };

  useEffect(() => {
    fetchHealth();
    fetchOverview();
    fetchSubmissions();
    const timer = setInterval(() => {
      fetchHealth();
      fetchOverview();
      fetchSubmissions();
    }, 15000);
    return () => clearInterval(timer);
  }, []);

  const handleGlobalSearch = (e) => {
    e?.preventDefault();
    if (!globalSearch.trim()) return;
    setActivePage('history');
  };

  return (
    <div className="defectiq-app-shell">
      <Sidebar
        activePage={activePage}
        setActivePage={(page) => {
          setActivePage(page);
        }}
        overview={overview}
        health={health}
      />

      <div className="defectiq-main-area">
        <Topbar
          activePage={activePage}
          setActivePage={setActivePage}
          globalSearch={globalSearch}
          setGlobalSearch={setGlobalSearch}
          onSearchSubmit={handleGlobalSearch}
          toast={toastMessage}
        />

        <main className="defectiq-content-scroll">
          {activePage === 'dashboard' && (
            <Dashboard
              overview={overview}
              onNavigate={setActivePage}
              onSelectDefect={loadDefectDetail}
            />
          )}

          {activePage === 'submit' && (
            <SubmitDefect
              api={API_BASE}
              notify={notify}
              onSubmitted={(newId) => {
                fetchOverview();
                fetchSubmissions();
                loadDefectDetail(newId);
              }}
            />
          )}

          {activePage === 'history' && (
            <DefectHistory
              submissions={submissions}
              initialSearch={globalSearch}
              onSelectDefect={loadDefectDetail}
              onNavigate={setActivePage}
              onRefresh={() => {
                fetchSubmissions();
                notify('Refreshed submissions archive.');
              }}
            />
          )}

          {activePage === 'knowledge' && (
            <KnowledgeBase
              api={API_BASE}
              notify={notify}
            />
          )}

          {activePage === 'agents' && (
            <AgentExecution
              submissions={submissions}
              selectedDefect={selectedDefect}
              onSelectDefect={loadDefectDetail}
            />
          )}

          {activePage === 'results' && (
            <AnalysisResults
              defect={selectedDefect}
              onBackToHistory={() => setActivePage('history')}
            />
          )}

          {activePage === 'settings' && (
            <SettingsView
              api={API_BASE}
              notify={notify}
            />
          )}
        </main>
      </div>
    </div>
  );
}
