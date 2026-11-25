import React from 'react';
import { Search, Bell, Sparkles, ChevronRight, CheckCircle2 } from 'lucide-react';

export default function Topbar({ activePage, setActivePage, globalSearch, setGlobalSearch, onSearchSubmit, toast }) {
  const pageTitles = {
    dashboard: 'Executive Defect Intelligence Dashboard',
    submit: 'Submit Software Defect for Multi-Agent Analysis',
    history: 'Defect Submission & Audit History',
    knowledge: 'Eclipse JDT Historical Defect Knowledge Base',
    agents: 'LangGraph Multi-Agent Orchestration & Trace',
    results: 'Defect Analysis Findings & Remediation',
    settings: 'System Diagnostics & Configuration',
  };

  return (
    <header className="enterprise-topbar">
      <div className="topbar-breadcrumbs">
        <span className="crumb-root">Workspace</span>
        <ChevronRight size={14} className="crumb-separator" />
        <span className="crumb-active">{pageTitles[activePage] || activePage}</span>
      </div>

      <div className="topbar-actions">
        <form className="quick-search-form" onSubmit={onSearchSubmit}>
          <Search size={15} className="search-icon" />
          <input
            type="text"
            placeholder="Search defects or stack traces (Press Enter)..."
            value={globalSearch}
            onChange={(e) => setGlobalSearch(e.target.value)}
          />
        </form>

        <div className="engine-badge">
          <Sparkles size={14} />
          <span>LangGraph + MiniLM RAG</span>
        </div>

        {toast && (
          <div className="toast-notification">
            <CheckCircle2 size={16} />
            <span>{toast}</span>
          </div>
        )}
      </div>
    </header>
  );
}
