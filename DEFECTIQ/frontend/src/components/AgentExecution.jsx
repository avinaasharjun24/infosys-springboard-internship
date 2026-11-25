import React, { useState } from 'react';
import {
  Cpu,
  Clock,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  GitFork,
  ArrowDown,
  Activity,
  Terminal,
  Database,
  Copy,
  BrainCircuit,
  Wrench,
  Sparkles
} from 'lucide-react';

export default function AgentExecution({ submissions, selectedDefect, onSelectDefect }) {
  const [selectedSubId, setSelectedSubId] = useState(selectedDefect?.id || submissions[0]?.id || null);

  const currentDefect =
    selectedDefect?.id === selectedSubId
      ? selectedDefect
      : submissions.find((s) => s.id === selectedSubId) || selectedDefect;

  const agentExecutions = currentDefect?.agent_executions || [];

  const getAgentIcon = (name) => {
    switch (name) {
      case 'input_normalization':
        return <Activity size={18} className="agent-icon blue" />;
      case 'triage_agent':
        return <Sparkles size={18} className="agent-icon orange" />;
      case 'log_analysis_agent':
        return <Terminal size={18} className="agent-icon purple" />;
      case 'structured_output_merge':
        return <GitFork size={18} className="agent-icon teal" />;
      case 'historical_retrieval':
        return <Database size={18} className="agent-icon blue" />;
      case 'duplicate_detection':
        return <Copy size={18} className="agent-icon amber" />;
      case 'root_cause_agent':
        return <BrainCircuit size={18} className="agent-icon red" />;
      case 'remediation_agent':
        return <Wrench size={18} className="agent-icon green" />;
      default:
        return <Cpu size={18} className="agent-icon blue" />;
    }
  };

  const getExecutionFor = (name) => {
    return agentExecutions.find((e) => e.agent_name === name);
  };

  return (
    <div className="page-container agents-page">
      <div className="page-header">
        <div>
          <div className="page-pretitle">LANGGRAPH MULTI-AGENT ORCHESTRATION</div>
          <h1 className="page-title">Agent Execution Architecture & Trace</h1>
          <p className="page-description">
            Inspect the coordinated LangGraph workflow, parallel execution branches, and agent telemetry.
          </p>
        </div>

        {submissions.length > 0 && (
          <div className="defect-selector-box">
            <label>Inspect Defect Execution:</label>
            <select
              value={selectedSubId || ''}
              onChange={(e) => {
                const id = Number(e.target.value);
                setSelectedSubId(id);
                onSelectDefect(id);
              }}
            >
              {submissions.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.submission_uuid || `#${s.id}`} — {s.title.slice(0, 45)}...
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Visual Workflow DAG */}
      <div className="panel dag-panel">
        <div className="panel-header">
          <div>
            <h3 className="panel-title">Active LangGraph Workflow Topology</h3>
            <p className="panel-subtitle">Deterministic parallel fan-out and synchronized merge</p>
          </div>
          <span className="badge badge-subtle">Parallel Graph</span>
        </div>

        <div className="workflow-dag-visualizer">
          {/* Node 1: Input Normalization */}
          <div className="dag-node entry-node">
            <div className="dag-node-badge">STEP 01 · SEQUENTIAL</div>
            <div className="dag-node-content">
              {getAgentIcon('input_normalization')}
              <div>
                <strong>Input Validation & Normalizer</strong>
                <p>Sanitizes HTML, unescapes characters, redacts PII</p>
              </div>
            </div>
            {getExecutionFor('input_normalization') && (
              <div className="dag-node-status completed">
                <CheckCircle2 size={14} />
                <span>{getExecutionFor('input_normalization').duration_ms} ms</span>
              </div>
            )}
          </div>

          <div className="dag-split-connector">
            <div className="connector-label">PARALLEL FORK (CONCURRENT EXECUTION)</div>
            <div className="fork-lines">
              <span className="fork-left" />
              <span className="fork-right" />
            </div>
          </div>

          {/* Parallel Nodes 2A and 2B */}
          <div className="dag-parallel-row">
            <div className="dag-node parallel-node left">
              <div className="dag-node-badge parallel">STAGE 02A · PARALLEL</div>
              <div className="dag-node-content">
                {getAgentIcon('triage_agent')}
                <div>
                  <strong>Triage Agent</strong>
                  <p>Classifies severity, priority & component</p>
                </div>
              </div>
              {getExecutionFor('triage_agent') && (
                <div className="dag-node-status completed">
                  <CheckCircle2 size={14} />
                  <span>{getExecutionFor('triage_agent').duration_ms} ms</span>
                </div>
              )}
            </div>

            <div className="dag-node parallel-node right">
              <div className="dag-node-badge parallel">STAGE 02B · PARALLEL</div>
              <div className="dag-node-content">
                {getAgentIcon('log_analysis_agent')}
                <div>
                  <strong>Log Analysis Agent</strong>
                  <p>Extracts exception headers, frames, failure points</p>
                </div>
              </div>
              {getExecutionFor('log_analysis_agent') && (
                <div className="dag-node-status completed">
                  <CheckCircle2 size={14} />
                  <span>{getExecutionFor('log_analysis_agent').duration_ms} ms</span>
                </div>
              )}
            </div>
          </div>

          <div className="dag-merge-connector">
            <div className="connector-label">SYNCHRONIZED FAN-IN MERGE</div>
            <div className="join-lines">
              <span className="join-left" />
              <span className="join-right" />
            </div>
          </div>

          {/* Node 3: Merge */}
          <div className="dag-node merge-node">
            <div className="dag-node-badge">STEP 03 · SYNCHRONIZATION</div>
            <div className="dag-node-content">
              {getAgentIcon('structured_output_merge')}
              <div>
                <strong>Structured Output Merge</strong>
                <p>Combines triage decisions with log findings for downstream context</p>
              </div>
            </div>
            {getExecutionFor('structured_output_merge') && (
              <div className="dag-node-status completed">
                <CheckCircle2 size={14} />
                <span>{getExecutionFor('structured_output_merge').duration_ms} ms</span>
              </div>
            )}
          </div>

          <div className="dag-arrow-connector"><ArrowDown size={18} /></div>

          {/* Node 4: RAG Retrieval */}
          <div className="dag-node sequential-node">
            <div className="dag-node-badge">STEP 04 · VECTOR RAG</div>
            <div className="dag-node-content">
              {getAgentIcon('historical_retrieval')}
              <div>
                <strong>Historical Defect Retrieval</strong>
                <p>Retrieves top-k historical precedents from Qdrant vector database</p>
              </div>
            </div>
            {getExecutionFor('historical_retrieval') && (
              <div className="dag-node-status completed">
                <CheckCircle2 size={14} />
                <span>{getExecutionFor('historical_retrieval').duration_ms} ms</span>
              </div>
            )}
          </div>

          <div className="dag-arrow-connector"><ArrowDown size={18} /></div>

          {/* Node 5: Duplicate Detection */}
          <div className="dag-node sequential-node">
            <div className="dag-node-badge">STEP 05 · CLUSTERING</div>
            <div className="dag-node-content">
              {getAgentIcon('duplicate_detection')}
              <div>
                <strong>Duplicate Detection Agent</strong>
                <p>Cross-references similarity thresholds & historical dupe links</p>
              </div>
            </div>
            {getExecutionFor('duplicate_detection') && (
              <div className="dag-node-status completed">
                <CheckCircle2 size={14} />
                <span>{getExecutionFor('duplicate_detection').duration_ms} ms</span>
              </div>
            )}
          </div>

          <div className="dag-arrow-connector"><ArrowDown size={18} /></div>

          {/* Node 6: Root Cause Synthesis */}
          <div className="dag-node sequential-node">
            <div className="dag-node-badge">STEP 06 · SYNTHESIS</div>
            <div className="dag-node-content">
              {getAgentIcon('root_cause_agent')}
              <div>
                <strong>Root Cause Synthesis Agent</strong>
                <p>Formulates grounded technical hypothesis from combined evidence</p>
              </div>
            </div>
            {getExecutionFor('root_cause_agent') && (
              <div className="dag-node-status completed">
                <CheckCircle2 size={14} />
                <span>{getExecutionFor('root_cause_agent').duration_ms} ms</span>
              </div>
            )}
          </div>

          <div className="dag-arrow-connector"><ArrowDown size={18} /></div>

          {/* Node 7: Remediation */}
          <div className="dag-node terminal-node">
            <div className="dag-node-badge">STEP 07 · REMEDIATION</div>
            <div className="dag-node-content">
              {getAgentIcon('remediation_agent')}
              <div>
                <strong>Remediation & Testing Agent</strong>
                <p>Recommends actionable code fixes and regression test checklist</p>
              </div>
            </div>
            {getExecutionFor('remediation_agent') && (
              <div className="dag-node-status completed">
                <CheckCircle2 size={14} />
                <span>{getExecutionFor('remediation_agent').duration_ms} ms</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Execution Audit Log Table */}
      <div className="panel audit-table-panel">
        <div className="panel-header">
          <div>
            <h3 className="panel-title">Agent Execution Audit Log</h3>
            <p className="panel-subtitle">
              Persisted trace records for Defect #{currentDefect?.id} ({currentDefect?.submission_uuid})
            </p>
          </div>
          <span className="badge badge-subtle">{agentExecutions.length} Execution Steps</span>
        </div>

        {agentExecutions.length === 0 ? (
          <div className="empty-panel compact">
            <Clock size={28} className="empty-icon" />
            <h4>No execution records found for this submission</h4>
            <p>Run the multi-agent investigation to populate execution telemetry.</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="enterprise-table">
              <thead>
                <tr>
                  <th>ORDER</th>
                  <th>AGENT</th>
                  <th>EXECUTION MODE</th>
                  <th>LATENCY</th>
                  <th>STATUS</th>
                  <th>OUTPUT SUMMARY</th>
                </tr>
              </thead>
              <tbody>
                {agentExecutions.map((e, idx) => (
                  <tr key={idx}>
                    <td>
                      <span className="order-badge">#{e.execution_order}</span>
                    </td>
                    <td>
                      <div className="agent-name-cell">
                        {getAgentIcon(e.agent_name)}
                        <strong>{e.agent_name}</strong>
                      </div>
                    </td>
                    <td>
                      {e.is_parallel ? (
                        <span className="badge badge-parallel">Parallel Fork</span>
                      ) : (
                        <span className="badge badge-sequential">Sequential</span>
                      )}
                    </td>
                    <td>
                      <span className="latency-metric">{e.duration_ms} ms</span>
                    </td>
                    <td>
                      <span className={`status-pill ${e.status}`}>{e.status}</span>
                    </td>
                    <td>
                      <span className="output-summary-text">{e.output_summary}</span>
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
