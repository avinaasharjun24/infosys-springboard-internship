import React from 'react';
import {
  FileText,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Database,
  Cpu,
  ArrowUpRight,
  PlusCircle,
  ExternalLink,
  ShieldCheck,
  Server
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell
} from 'recharts';

export default function Dashboard({ overview, onNavigate, onSelectDefect }) {
  const severityColors = {
    Critical: '#dc2626',
    High: '#ea580c',
    Medium: '#d97706',
    Low: '#64748b',
  };

  const chartData = overview?.severity_distribution || [
    { name: 'Critical', count: 0 },
    { name: 'High', count: 0 },
    { name: 'Medium', count: 0 },
    { name: 'Low', count: 0 },
  ];

  return (
    <div className="page-container dashboard-page">
      <div className="page-header">
        <div>
          <div className="page-pretitle">ENTERPRISE OBSERVABILITY</div>
          <h1 className="page-title">Defect Intelligence Overview</h1>
          <p className="page-description">
            Live telemetry of submitted software defects, automated triage classifications, and historical knowledge base health.
          </p>
        </div>
        <div className="header-actions">
          <button className="btn btn-primary" onClick={() => onNavigate('submit')}>
            <PlusCircle size={16} />
            <span>Submit New Defect</span>
          </button>
        </div>
      </div>

      {/* KPI Metric Cards */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-label">TOTAL SUBMISSIONS</span>
            <FileText size={18} className="kpi-icon blue" />
          </div>
          <div className="kpi-value">{overview?.total_submissions ?? '—'}</div>
          <div className="kpi-footer">All defect reports received</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-label">DEFECTS ANALYZED</span>
            <CheckCircle2 size={18} className="kpi-icon green" />
          </div>
          <div className="kpi-value">{overview?.completed_analyses ?? '—'}</div>
          <div className="kpi-footer">Multi-agent workflow completed</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-label">INDEXED JDT DEFECTS</span>
            <Database size={18} className="kpi-icon purple" />
          </div>
          <div className="kpi-value">
            {overview?.indexed_historical_defects?.toLocaleString?.() ?? '—'}
          </div>
          <div className="kpi-footer">Qdrant vector knowledge base</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-label">MULTI-AGENT ENGINE</span>
            <Cpu size={18} className="kpi-icon teal" />
          </div>
          <div className="kpi-value">LangGraph</div>
          <div className="kpi-footer">Parallel Triage & Log Analysis</div>
        </div>
      </div>

      {/* Charts and Activity Grid */}
      <div className="dashboard-columns">
        {/* Severity Distribution Chart */}
        <div className="panel chart-panel">
          <div className="panel-header">
            <div>
              <h3 className="panel-title">Analyzed Defect Severity Distribution</h3>
              <p className="panel-subtitle">Real telemetry classified by DEFECTIQ Triage Agent</p>
            </div>
            <span className="badge badge-subtle">Live Database Metrics</span>
          </div>
          <div className="chart-wrapper">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={chartData} margin={{ top: 20, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#64748b' }} axisLine={false} tickLine={false} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: '#64748b' }} axisLine={false} tickLine={false} />
                <Tooltip
                  cursor={{ fill: '#f8fafc' }}
                  contentStyle={{
                    backgroundColor: '#ffffff',
                    borderRadius: '8px',
                    border: '1px solid #e2e8f0',
                    boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)',
                  }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={48}>
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={severityColors[entry.name] || '#3b82f6'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="chart-legend-row">
            {Object.entries(severityColors).map(([sev, color]) => (
              <span key={sev} className="legend-chip">
                <span className="chip-dot" style={{ backgroundColor: color }} />
                <span>{sev}</span>
              </span>
            ))}
          </div>
        </div>

        {/* Recent Defect Submissions */}
        <div className="panel recent-panel">
          <div className="panel-header">
            <div>
              <h3 className="panel-title">Recent Submissions</h3>
              <p className="panel-subtitle">Latest defect reports evaluated by AI agents</p>
            </div>
            <button className="btn-text" onClick={() => onNavigate('history')}>
              View All <ArrowUpRight size={14} />
            </button>
          </div>

          <div className="recent-list">
            {!overview?.recent_submissions || overview.recent_submissions.length === 0 ? (
              <div className="empty-panel">
                <FileText size={32} className="empty-icon" />
                <h4>No defect submissions recorded yet</h4>
                <p>Submit your first software bug report or stack trace to begin analysis.</p>
                <button className="btn btn-primary btn-sm" onClick={() => onNavigate('submit')}>
                  Submit Bug Report
                </button>
              </div>
            ) : (
              overview.recent_submissions.map((item) => (
                <div
                  key={item.id}
                  className="recent-item"
                  onClick={() => onSelectDefect(item.id)}
                >
                  <div className="recent-item-main">
                    <div className="recent-item-title-row">
                      <span className="recent-id">{item.submission_uuid || `#${item.id}`}</span>
                      <span className={`badge-severity ${item.severity?.toLowerCase() || 'medium'}`}>
                        {item.severity || 'Triage Pending'}
                      </span>
                      <span className="recent-component">{item.component || 'Core'}</span>
                    </div>
                    <div className="recent-title">{item.title}</div>
                  </div>
                  <div className="recent-item-meta">
                    <span className={`status-pill ${item.status}`}>{item.status}</span>
                    <ArrowUpRight size={15} className="item-arrow" />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Workflow Capability Cards */}
      <div className="workflow-overview-section">
        <div className="panel-header">
          <div>
            <h3 className="panel-title">LangGraph Multi-Agent Architecture</h3>
            <p className="panel-subtitle">Coordinated pipeline executing specialized defect analysis agents</p>
          </div>
          <button className="btn-text" onClick={() => onNavigate('agents')}>
            View Workflow DAG <ArrowUpRight size={14} />
          </button>
        </div>
        <div className="agents-cards-grid">
          <div className="agent-overview-card">
            <div className="agent-badge">STAGE 01</div>
            <h4>Input Normalizer</h4>
            <p>Cleans HTML markup, unescapes logs, redacts PII, and validates defect schema.</p>
          </div>
          <div className="agent-overview-card highlight">
            <div className="agent-badge parallel">STAGE 02 · PARALLEL</div>
            <h4>Triage Agent</h4>
            <p>Classifies severity (Critical-Low), priority (P1-P4), component with grounded justification.</p>
          </div>
          <div className="agent-overview-card highlight">
            <div className="agent-badge parallel">STAGE 02 · PARALLEL</div>
            <h4>Log Analysis Agent</h4>
            <p>Parses Java exceptions, stack frames, file:line failure points, and chained causes.</p>
          </div>
          <div className="agent-overview-card">
            <div className="agent-badge">STAGE 03</div>
            <h4>Historical RAG Retrieval</h4>
            <p>Queries 384-dim MiniLM vectors from Qdrant with component metadata filters.</p>
          </div>
          <div className="agent-overview-card">
            <div className="agent-badge">STAGE 04</div>
            <h4>Root Cause & Remediation</h4>
            <p>Synthesizes evidence-backed defect hypotheses, fixes, and regression test suites.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
