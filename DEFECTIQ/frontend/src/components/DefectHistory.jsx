import React, { useState, useEffect } from 'react';
import {
  Search,
  Filter,
  FileText,
  Clock,
  ArrowUpRight,
  PlusCircle,
  RefreshCw,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';

export default function DefectHistory({ submissions, initialSearch = '', onSelectDefect, onNavigate, onRefresh }) {
  const [searchTerm, setSearchTerm] = useState(initialSearch);
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');

  useEffect(() => {
    if (initialSearch !== undefined) {
      setSearchTerm(initialSearch);
    }
  }, [initialSearch]);

  const filtered = submissions.filter((sub) => {
    const matchesSearch =
      sub.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (sub.submission_uuid && sub.submission_uuid.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (sub.component && sub.component.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesSeverity =
      severityFilter === 'ALL' || (sub.severity && sub.severity.toUpperCase() === severityFilter);

    const matchesStatus =
      statusFilter === 'ALL' || (sub.status && sub.status.toUpperCase() === statusFilter);

    return matchesSearch && matchesSeverity && matchesStatus;
  });

  return (
    <div className="page-container history-page">
      <div className="page-header">
        <div>
          <div className="page-pretitle">AUDIT & SUBMISSION ARCHIVE</div>
          <h1 className="page-title">Defect Investigation History</h1>
          <p className="page-description">
            Complete record of software defects submitted for multi-agent triage, diagnosis, and remediation.
          </p>
        </div>
        <div className="header-actions">
          <button className="btn btn-outline" onClick={onRefresh} title="Refresh records">
            <RefreshCw size={15} />
            <span>Refresh</span>
          </button>
          <button className="btn btn-primary" onClick={() => onNavigate('submit')}>
            <PlusCircle size={16} />
            <span>New Defect</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="filter-bar">
        <div className="search-input-wrapper">
          <Search size={16} className="search-icon" />
          <input
            type="text"
            placeholder="Filter by defect title, UUID, or component..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="filters-group">
          <div className="filter-select-wrapper">
            <label>Severity:</label>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
            >
              <option value="ALL">All Severities</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>
          </div>

          <div className="filter-select-wrapper">
            <label>Status:</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="ALL">All Statuses</option>
              <option value="COMPLETED">Completed</option>
              <option value="PROCESSING">Processing</option>
              <option value="SUBMITTED">Submitted</option>
              <option value="FAILED">Failed</option>
            </select>
          </div>
        </div>
      </div>

      {/* Data Table */}
      <div className="panel table-panel">
        <div className="table-header">
          <span className="table-count">Showing {filtered.length} of {submissions.length} recorded defects</span>
        </div>

        {filtered.length === 0 ? (
          <div className="empty-panel">
            <FileText size={36} className="empty-icon" />
            <h4>No matching defect records found</h4>
            <p>Try clearing filters or submit a new software defect for investigation.</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="enterprise-table">
              <thead>
                <tr>
                  <th>UUID</th>
                  <th>DEFECT TITLE</th>
                  <th>SUBSYSTEM</th>
                  <th>SEVERITY</th>
                  <th>PRIORITY</th>
                  <th>STATUS</th>
                  <th>SUBMITTED</th>
                  <th>ACTION</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((sub) => (
                  <tr key={sub.id} onClick={() => onSelectDefect(sub.id)} className="clickable-row">
                    <td>
                      <span className="table-uuid">{sub.submission_uuid || `DEF-${sub.id}`}</span>
                    </td>
                    <td>
                      <div className="table-title-cell">
                        <strong>{sub.title}</strong>
                        {sub.file_count > 0 && (
                          <span className="table-attachment-badge">
                            {sub.file_count} {sub.file_count === 1 ? 'file' : 'files'} attached
                          </span>
                        )}
                      </div>
                    </td>
                    <td>
                      <span className="table-component">{sub.component || 'Core'}</span>
                    </td>
                    <td>
                      {sub.severity ? (
                        <span className={`badge-severity ${sub.severity.toLowerCase()}`}>
                          {sub.severity}
                        </span>
                      ) : (
                        <span className="badge-severity unassigned">Pending</span>
                      )}
                    </td>
                    <td>
                      <span className="table-priority">{sub.priority || '—'}</span>
                    </td>
                    <td>
                      <span className={`status-pill ${sub.status}`}>
                        {sub.status}
                      </span>
                    </td>
                    <td>
                      <span className="table-date">
                        {sub.created_at ? new Date(sub.created_at).toLocaleString() : '—'}
                      </span>
                    </td>
                    <td>
                      <button
                        className="btn btn-outline btn-sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectDefect(sub.id);
                        }}
                      >
                        <span>View</span>
                        <ArrowUpRight size={13} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
