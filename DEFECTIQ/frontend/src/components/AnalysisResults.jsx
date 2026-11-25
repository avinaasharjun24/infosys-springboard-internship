import React, { useState } from 'react';
import {
  Sparkles,
  Terminal,
  Database,
  BrainCircuit,
  Wrench,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Clock,
  Paperclip,
  ShieldCheck,
  FileText,
  AlertCircle
} from 'lucide-react';

export default function AnalysisResults({ defect, onBackToHistory }) {
  const [showRawLogs, setShowRawLogs] = useState(false);
  const [showStackFrames, setShowStackFrames] = useState(false);

  if (!defect) {
    return (
      <div className="page-container">
        <div className="empty-panel">
          <FileText size={40} className="empty-icon" />
          <h3>No Defect Selected</h3>
          <p>Please select a defect record from History or submit a new defect.</p>
          <button className="btn btn-primary" onClick={onBackToHistory}>
            Go to Defect History
          </button>
        </div>
      </div>
    );
  }

  const triage = defect.triage || defect.result?.triage;
  const logAnalysis = defect.log_analysis || defect.result?.log_analysis;
  const historicalMatches = defect.historical_matches || defect.result?.similar || [];
  const duplicateAnalysis = defect.duplicate_analysis || defect.result?.duplicate_analysis;
  const rootCause = defect.root_cause_hypothesis || defect.result?.root_cause?.hypothesis;
  const rootCauseDetails = defect.root_cause_details || defect.result?.root_cause;
  const remediation = defect.remediation_recommendations || defect.result?.remediation?.recommendations || [];
  const validationSteps = defect.validation_steps || defect.result?.remediation?.validation_steps || [];
  const remediationReasoning = defect.remediation_reasoning || defect.result?.remediation?.reasoning;
  const affectedFiles = defect.affected_files || defect.result?.remediation?.affected_components_or_files || [];

  return (
    <div className="page-container results-page">
      {/* Top Header Card */}
      <div className="defect-banner-card">
        <div className="banner-top-row">
          <div className="banner-id-group">
            <span className="banner-uuid">{defect.submission_uuid || `DEF-${defect.id}`}</span>
            <span className="banner-project">{defect.project || 'Eclipse JDT'}</span>
            <span className="banner-component">{triage?.affected_component || defect.component || 'Core'}</span>
          </div>
          <div className="banner-status-group">
            <span className={`status-pill ${defect.status}`}>{defect.status}</span>
            <button className="btn btn-outline btn-sm" onClick={onBackToHistory}>
              Back to History
            </button>
          </div>
        </div>

        <h1 className="banner-title">{defect.title}</h1>

        <div className="banner-meta-row">
          <span>Submitted: <strong>{defect.created_at ? new Date(defect.created_at).toLocaleString() : '—'}</strong></span>
          {defect.files && defect.files.length > 0 && (
            <span>Evidence Files: <strong>{defect.files.length} attached</strong></span>
          )}
          <span>Engine: <strong>LangGraph Multi-Agent Orchestrator</strong></span>
        </div>
      </div>

      {/* Grid: Triage Agent & Log Analysis Agent Findings */}
      <div className="results-two-col-grid">
        {/* Triage Agent Card */}
        <div className="panel finding-panel triage-panel">
          <div className="panel-header">
            <div className="panel-title-with-icon">
              <Sparkles size={20} className="panel-icon orange" />
              <div>
                <h3 className="panel-title">Triage Agent Findings</h3>
                <p className="panel-subtitle">Automated severity classification & priority estimation</p>
              </div>
            </div>
            {triage && (
              <span className="badge badge-source">
                {triage.classification_source === 'gemini_grounded' ? 'Gemini Grounded' : 'Deterministic Expert'}
              </span>
            )}
          </div>

          {triage ? (
            <div className="finding-body">
              <div className="triage-metrics-row">
                <div className="triage-metric-box">
                  <span className="metric-label">SEVERITY LEVEL</span>
                  <span className={`badge-severity lg ${triage.severity?.toLowerCase()}`}>
                    {triage.severity}
                  </span>
                </div>

                <div className="triage-metric-box">
                  <span className="metric-label">OPERATIONAL PRIORITY</span>
                  <span className="priority-tag">{triage.priority || 'P3'}</span>
                </div>

                <div className="triage-metric-box">
                  <span className="metric-label">SUBSYSTEM</span>
                  <span className="component-tag">{triage.affected_component}</span>
                </div>

                <div className="triage-metric-box">
                  <span className="metric-label">CONFIDENCE</span>
                  <div className="confidence-meter">
                    <span className="confidence-pct">{(triage.confidence * 100).toFixed(0)}%</span>
                    <div className="confidence-track">
                      <div
                        className="confidence-fill"
                        style={{ width: `${Math.round(triage.confidence * 100)}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              <div className="finding-section">
                <span className="section-heading">CLASSIFICATION REASONING:</span>
                <p className="reasoning-text">{triage.reasoning}</p>
              </div>

              {triage.evidence && triage.evidence.length > 0 && (
                <div className="finding-section">
                  <span className="section-heading">SUPPORTING EVIDENCE:</span>
                  <ul className="evidence-bullet-list">
                    {triage.evidence.map((item, idx) => (
                      <li key={idx}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="empty-panel compact">
              <AlertCircle size={24} className="empty-icon" />
              <p>Triage classification not yet generated.</p>
            </div>
          )}
        </div>

        {/* Log Analysis Agent Card */}
        <div className="panel finding-panel log-panel">
          <div className="panel-header">
            <div className="panel-title-with-icon">
              <Terminal size={20} className="panel-icon purple" />
              <div>
                <h3 className="panel-title">Log Analysis Findings</h3>
                <p className="panel-subtitle">AST & stack trace failure point extraction</p>
              </div>
            </div>
            {logAnalysis && (
              <span className={`badge badge-source ${logAnalysis.status}`}>
                {logAnalysis.status}
              </span>
            )}
          </div>

          {logAnalysis ? (
            <div className="finding-body">
              {logAnalysis.has_logs ? (
                <>
                  <div className="log-coordinates-box">
                    <div className="coordinate-item">
                      <span className="coord-label">PRIMARY EXCEPTION:</span>
                      <code className="coord-value exception">{logAnalysis.exception_type || 'Unspecified Error'}</code>
                    </div>
                    {logAnalysis.error_message && (
                      <div className="coordinate-item">
                        <span className="coord-label">ERROR MESSAGE:</span>
                        <code className="coord-value message">{logAnalysis.error_message}</code>
                      </div>
                    )}
                    <div className="coordinate-item">
                      <span className="coord-label">IMPLICATED FAILURE POINT:</span>
                      <code className="coord-value failure-point">{logAnalysis.failure_point || 'Not isolated'}</code>
                    </div>
                    {logAnalysis.file_name && (
                      <div className="coordinate-item file-line">
                        <span>File: <strong>{logAnalysis.file_name}</strong></span>
                        {logAnalysis.line_number && (
                          <span>Line: <strong>{logAnalysis.line_number}</strong></span>
                        )}
                      </div>
                    )}
                  </div>

                  {logAnalysis.technical_findings && logAnalysis.technical_findings.length > 0 && (
                    <div className="finding-section">
                      <span className="section-heading">TECHNICAL FINDINGS:</span>
                      <ul className="evidence-bullet-list">
                        {logAnalysis.technical_findings.map((item, idx) => (
                          <li key={idx}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {logAnalysis.affected_code_path && logAnalysis.affected_code_path.length > 0 && (
                    <div className="finding-section">
                      <button
                        className="btn-toggle-frames"
                        onClick={() => setShowStackFrames(!showStackFrames)}
                      >
                        <span>{showStackFrames ? 'Hide Call Stack Frames' : `Show Top Call Stack Frames (${logAnalysis.affected_code_path.length})`}</span>
                        {showStackFrames ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      </button>

                      {showStackFrames && (
                        <div className="stack-frames-container">
                          {logAnalysis.affected_code_path.map((frame, idx) => (
                            <code key={idx} className="stack-frame-line">{frame}</code>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </>
              ) : (
                <div className="insufficient-logs-box">
                  <div className="info-callout">
                    <AlertCircle size={18} />
                    <span>No log or stack trace was supplied with this report. The Log Analysis Agent correctly recorded <code>insufficient_log_evidence</code> without hallucinating exceptions.</span>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="empty-panel compact">
              <AlertCircle size={24} className="empty-icon" />
              <p>Log analysis not yet generated.</p>
            </div>
          )}
        </div>
      </div>

      {/* Root Cause Hypothesis Card */}
      <div className="panel root-cause-panel">
        <div className="panel-header">
          <div className="panel-title-with-icon">
            <BrainCircuit size={20} className="panel-icon red" />
            <div>
              <h3 className="panel-title">Evidence-Backed Root Cause Hypothesis</h3>
              <p className="panel-subtitle">Distinguishes verified evidence from inferred hypotheses</p>
            </div>
          </div>
          <span className="badge badge-subtle">
            {rootCauseDetails?.confidence
              ? `Confidence: ${Math.round(rootCauseDetails.confidence * 100)}%`
              : 'Hypothesis · Supporting Evidence'}
          </span>
        </div>

        <div className="finding-body">
          <div className="hypothesis-box">
            <span className="section-heading">PRIMARY HYPOTHESIS:</span>
            <p className="hypothesis-text">
              {rootCause || 'Insufficient historical or log evidence to formulate an isolated code-level hypothesis.'}
            </p>
            {rootCauseDetails?.reasoning && (
              <p className="reasoning-text" style={{ marginTop: '0.5rem' }}>
                <strong>Reasoning:</strong> {rootCauseDetails.reasoning}
              </p>
            )}
          </div>

          {rootCauseDetails?.verified_evidence && rootCauseDetails.verified_evidence.length > 0 && (
            <div className="finding-section" style={{ marginTop: '0.75rem' }}>
              <span className="section-heading">VERIFIED EVIDENCE (OBSERVED):</span>
              <ul className="evidence-bullet-list">
                {rootCauseDetails.verified_evidence.map((ev, idx) => (
                  <li key={idx}>{ev}</li>
                ))}
              </ul>
            </div>
          )}

          {duplicateAnalysis && (
            <div className="finding-section" style={{ marginTop: '0.75rem' }}>
              <span className="section-heading">DUPLICATE SIMILARITY ASSESSMENT:</span>
              <div className="info-callout">
                <AlertTriangle size={16} />
                <span>{duplicateAnalysis.reason}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Remediation & Validation Card */}
      <div className="panel remediation-panel">
        <div className="panel-header">
          <div className="panel-title-with-icon">
            <Wrench size={20} className="panel-icon green" />
            <div>
              <h3 className="panel-title">Remediation Strategies & Validation Plan</h3>
              <p className="panel-subtitle">Actionable code fix recommendations and regression testing checklist</p>
            </div>
          </div>
          <span className="badge badge-subtle">Remediation Agent</span>
        </div>

        <div className="remediation-columns">
          <div className="remediation-col">
            {remediationReasoning && (
              <p className="reasoning-text" style={{ marginBottom: '0.75rem' }}>
                <strong>Rationale:</strong> {remediationReasoning}
              </p>
            )}
            {affectedFiles.length > 0 && (
              <div style={{ marginBottom: '0.75rem' }}>
                <span className="section-heading">IMPLICATED FILES / COMPONENTS:</span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginTop: '0.25rem' }}>
                  {affectedFiles.map((f, idx) => (
                    <code key={idx} className="coord-value">{f}</code>
                  ))}
                </div>
              </div>
            )}
            <span className="section-heading">RECOMMENDED ACTIONS & FIXES:</span>
            <div className="actions-checklist">
              {remediation.length > 0 ? (
                remediation.map((rec, idx) => (
                  <div key={idx} className="checklist-item">
                    <CheckCircle2 size={16} className="checklist-icon green" />
                    <span>{rec}</span>
                  </div>
                ))
              ) : (
                <p className="muted-text">Standard remediation: add defensive null check and unit test.</p>
              )}
            </div>
          </div>

          <div className="remediation-col">
            <span className="section-heading">VALIDATION & REGRESSION CHECKLIST:</span>
            <div className="actions-checklist">
              {validationSteps.length > 0 ? (
                validationSteps.map((step, idx) => (
                  <div key={idx} className="checklist-item">
                    <ShieldCheck size={16} className="checklist-icon blue" />
                    <span>{step}</span>
                  </div>
                ))
              ) : (
                <p className="muted-text">Run affected subsystem regression test suite.</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Historical Similar Defects (RAG Retrieval) */}
      <div className="panel historical-matches-panel">
        <div className="panel-header">
          <div className="panel-title-with-icon">
            <Database size={20} className="panel-icon blue" />
            <div>
              <h3 className="panel-title">Retrieved Historical Eclipse JDT Matches (RAG)</h3>
              <p className="panel-subtitle">Semantically similar historical issues retrieved from the Eclipse JDT corpus (evidence only, not proof of duplication)</p>
            </div>
          </div>
          <span className="badge badge-subtle">{historicalMatches.length} Historical Matches</span>
        </div>

        <div className="matches-grid">
          {historicalMatches.length === 0 ? (
            <div className="empty-panel compact">
              <Database size={28} className="empty-icon" />
              <h4>No historical precedents retrieved</h4>
              <p>Knowledge base vectors will match once historical defect dataset is ingested.</p>
            </div>
          ) : (
            historicalMatches.map((m, idx) => (
              <div key={idx} className="historical-match-card">
                <div className="match-card-top">
                  <div className="match-id-group">
                    <span className="source-id-tag">JDT-{m.source_id}</span>
                    <span className={`badge-severity ${m.severity?.toLowerCase() || 'medium'}`}>
                      {m.severity || 'normal'}
                    </span>
                    <span className="match-comp">{m.component || 'Core'}</span>
                  </div>
                  <div className="similarity-pill">
                    {(m.similarity_score * 100).toFixed(1)}% match
                  </div>
                </div>

                <h4 className="match-summary">{m.summary}</h4>

                <div className="match-card-bottom">
                  <span>Resolution: <strong>{m.resolution || 'Unresolved'}</strong></span>
                  {m.issue_url && (
                    <a
                      href={m.issue_url}
                      target="_blank"
                      rel="noreferrer"
                      className="provenance-link"
                    >
                      <span>Eclipse Bugzilla</span>
                      <ExternalLink size={12} />
                    </a>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Submitted Problem Context & Logs Accordion */}
      <div className="panel context-panel">
        <div
          className="panel-header clickable"
          onClick={() => setShowRawLogs(!showRawLogs)}
        >
          <div>
            <h3 className="panel-title">Original Submitted Description & Technical Evidence</h3>
            <p className="panel-subtitle">Inspect the raw text and logs submitted with this report</p>
          </div>
          <button className="btn-icon">
            {showRawLogs ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </div>

        {showRawLogs && (
          <div className="context-content">
            <div className="context-block">
              <strong>Description:</strong>
              <p>{defect.description}</p>
            </div>

            {defect.expected_behavior && (
              <div className="context-block">
                <strong>Expected Behavior:</strong>
                <p>{defect.expected_behavior}</p>
              </div>
            )}

            {defect.actual_behavior && (
              <div className="context-block">
                <strong>Actual Behavior:</strong>
                <p>{defect.actual_behavior}</p>
              </div>
            )}

            {defect.logs && (
              <div className="context-block">
                <strong>Raw Technical Logs / Stack Trace:</strong>
                <pre className="raw-logs-code">{defect.logs}</pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
