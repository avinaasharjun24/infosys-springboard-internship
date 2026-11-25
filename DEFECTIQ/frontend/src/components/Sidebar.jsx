import React from 'react';
import {
  LayoutDashboard,
  PlusCircle,
  Clock,
  Database,
  Cpu,
  FileCheck2,
  Settings,
  ShieldCheck,
  ChevronRight
} from 'lucide-react';

export default function Sidebar({ activePage, setActivePage, overview, health }) {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'submit', label: 'Submit Defect', icon: PlusCircle, badge: 'Intake' },
    { id: 'history', label: 'Defect History', icon: Clock },
    { id: 'knowledge', label: 'Knowledge Base', icon: Database },
    { id: 'agents', label: 'Agent Execution', icon: Cpu },
    { id: 'results', label: 'Analysis Results', icon: FileCheck2 },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside className="enterprise-sidebar">
      <div className="sidebar-brand">
        <div className="brand-icon">
          <ShieldCheck size={22} />
        </div>
        <div className="brand-text">
          <div className="brand-name">DEFECTIQ</div>
          <div className="brand-tagline">AI Software Defect Intelligence</div>
        </div>
      </div>

      <div className="workspace-badge">
        <span className="workspace-indicator">EJ</span>
        <div className="workspace-info">
          <span className="workspace-title">Eclipse JDT Workspace</span>
          <span className="workspace-subtitle">Local Enterprise Edition</span>
        </div>
      </div>

      <div className="sidebar-section-label">PLATFORM MODULES</div>
      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activePage === item.id;
          return (
            <button
              key={item.id}
              className={`nav-button ${isActive ? 'active' : ''}`}
              onClick={() => setActivePage(item.id)}
            >
              <Icon size={18} className="nav-icon" />
              <span className="nav-label">{item.label}</span>
              {item.badge && <span className="nav-badge">{item.badge}</span>}
              {isActive && <ChevronRight size={15} className="active-arrow" />}
            </button>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div className="service-status-pill">
          <span
            className={`status-dot ${
              health?.status === 'operational'
                ? 'operational'
                : health
                ? 'degraded'
                : 'connecting'
            }`}
          />
          <div className="status-text">
            <b>
              {health?.status === 'operational'
                ? 'Services Operational'
                : health
                ? 'Service Degraded'
                : 'Backend Offline'}
            </b>
            <small>
              {health
                ? `DB: ${health.database?.connected ? 'OK' : 'Down'} · Qdrant: ${
                    health.qdrant?.connected ? 'OK' : 'Down'
                  }`
                : 'Connecting to API...'}
            </small>
          </div>
        </div>
        <div className="build-version">v2.0.0 · DEFECTIQ Local</div>
      </div>
    </aside>
  );
}
