import React, { useState, useEffect } from 'react';
import {
  Settings,
  ShieldCheck,
  Database,
  Cpu,
  Server,
  Key,
  HardDrive,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Info
} from 'lucide-react';

export default function SettingsView({ api, notify }) {
  const [diagnostics, setDiagnostics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [geminiCheck, setGeminiCheck] = useState(null);
  const [verifyingGemini, setVerifyingGemini] = useState(false);

  const fetchDiagnostics = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${api}/settings/diagnostics`);
      const data = await res.json();
      setDiagnostics(data);
    } catch (err) {
      console.error('Failed to load diagnostics:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyGemini = async () => {
    setVerifyingGemini(true);
    try {
      const res = await fetch(`${api}/gemini/verify`, { method: 'POST' });
      const data = await res.json();
      setGeminiCheck(data);
      if (data.connected) {
        notify(`Gemini verified (${data.model})`);
      } else {
        notify(data.message || 'Gemini verification failed');
      }
    } catch (err) {
      setGeminiCheck({ configured: false, connected: false, message: err.message });
    } finally {
      setVerifyingGemini(false);
    }
  };

  useEffect(() => {
    fetchDiagnostics();
  }, []);

  return (
    <div className="page-container settings-page">
      <div className="page-header">
        <div>
          <div className="page-pretitle">ENVIRONMENT & SERVICES</div>
          <h1 className="page-title">System Settings & Diagnostics</h1>
          <p className="page-description">
            Inspect active configuration, database connections, vector store parameters, and AI model integrations.
          </p>
        </div>
        <button className="btn btn-outline" onClick={fetchDiagnostics} disabled={loading}>
          <RefreshCw size={15} className={loading ? 'spin' : ''} />
          <span>Refresh Status</span>
        </button>
      </div>

      <div className="settings-cards-grid">
        {/* Database Configuration Card */}
        <div className="panel settings-card">
          <div className="settings-card-header">
            <Database size={20} className="panel-icon blue" />
            <div>
              <h4>Application Database</h4>
              <p>Primary relational storage for defects, executions & results</p>
            </div>
          </div>
          <div className="settings-fields-list">
            <div className="setting-field">
              <span className="field-name">Engine Type:</span>
              <strong className="field-val">{diagnostics?.database_type || 'Unknown'}</strong>
            </div>
            <div className="setting-field">
              <span className="field-name">Connection Status:</span>
              {diagnostics?.database_connected ? (
                <span className="badge badge-success"><CheckCircle2 size={12} /><span>Connected</span></span>
              ) : (
                <span className="badge badge-warning"><AlertTriangle size={12} /><span>{diagnostics?.database_message || 'Disconnected'}</span></span>
              )}
            </div>
            <div className="setting-field note">
              <Info size={14} />
              <span>To switch to PostgreSQL, set <code>DATABASE_URL=postgresql+psycopg://...</code> in <code>backend/.env</code>.</span>
            </div>
          </div>
        </div>

        {/* Vector Database Card */}
        <div className="panel settings-card">
          <div className="settings-card-header">
            <Server size={20} className="panel-icon purple" />
            <div>
              <h4>Qdrant Vector Database</h4>
              <p>Persistent vector index for historical defect retrieval</p>
            </div>
          </div>
          <div className="settings-fields-list">
            <div className="setting-field">
              <span className="field-name">Connection Status:</span>
              {diagnostics?.qdrant_connected ? (
                <span className="badge badge-success"><CheckCircle2 size={12} /><span>Connected</span></span>
              ) : (
                <span className="badge badge-warning"><AlertTriangle size={12} /><span>{diagnostics?.qdrant_message || 'Unavailable'}</span></span>
              )}
            </div>
            <div className="setting-field">
              <span className="field-name">Storage Mode:</span>
              <strong className="field-val">{diagnostics?.qdrant_mode || 'Local Embedded'}</strong>
            </div>
            <div className="setting-field">
              <span className="field-name">Collection Name:</span>
              <code className="field-code">{diagnostics?.collection_name || 'eclipse_jdt_defects'}</code>
            </div>
            <div className="setting-field">
              <span className="field-name">Indexed Vectors:</span>
              <strong className="field-val">{diagnostics?.indexed_vectors ?? 0} vectors</strong>
            </div>
            <div className="setting-field">
              <span className="field-name">Storage Location:</span>
              <code className="field-code">{diagnostics?.qdrant_location || './storage/qdrant'}</code>
            </div>
          </div>
        </div>

        {/* AI & Embeddings Card */}
        <div className="panel settings-card">
          <div className="settings-card-header">
            <Cpu size={20} className="panel-icon teal" />
            <div>
              <h4>AI & Embedding Models</h4>
              <p>SentenceTransformers and Google Gemini API integration</p>
            </div>
          </div>
          <div className="settings-fields-list">
            <div className="setting-field">
              <span className="field-name">Embedding Model:</span>
              <code className="field-code">{diagnostics?.embedding_model || 'all-MiniLM-L6-v2 (384 dims)'}</code>
            </div>
            <div className="setting-field">
              <span className="field-name">Gemini Grounded Reasoning:</span>
              {diagnostics?.gemini_configured ? (
                <span className="badge badge-success">
                  <CheckCircle2 size={12} />
                  <span>Configured</span>
                </span>
              ) : (
                <span className="badge badge-warning">
                  <AlertTriangle size={12} />
                  <span>API Key Not Configured (Using Deterministic Expert Engine)</span>
                </span>
              )}
            </div>
            <div className="setting-field">
              <span className="field-name">Target Gemini Model:</span>
              <strong className="field-val">{diagnostics?.gemini_model || 'gemini-3.8-flash'}</strong>
            </div>
            <div className="setting-field">
              <span className="field-name">Live Connectivity:</span>
              <button
                type="button"
                className="btn btn-outline btn-sm"
                onClick={handleVerifyGemini}
                disabled={verifyingGemini}
              >
                <RefreshCw size={13} className={verifyingGemini ? 'spin' : ''} />
                <span>{verifyingGemini ? 'Verifying...' : 'Verify Gemini Connection'}</span>
              </button>
            </div>
            {geminiCheck && (
              <div className="setting-field note">
                <Info size={14} />
                <span>
                  {geminiCheck.connected
                    ? `Connected to ${geminiCheck.model} (model available: ${geminiCheck.model_available ? 'Yes' : 'Check access'})`
                    : geminiCheck.message || 'Not connected'}
                </span>
              </div>
            )}
            <div className="setting-field note">
              <Info size={14} />
              <span>Configure <code>GEMINI_API_KEY</code> in <code>backend/.env</code> to enable LLM-grounded triage and synthesis.</span>
            </div>
          </div>
        </div>

        {/* Dataset Configuration Card */}
        <div className="panel settings-card">
          <div className="settings-card-header">
            <HardDrive size={20} className="panel-icon orange" />
            <div>
              <h4>Historical Defect Dataset</h4>
              <p>Eclipse JDT Bugzilla corpus specification</p>
            </div>
          </div>
          <div className="settings-fields-list">
            <div className="setting-field">
              <span className="field-name">Configured Path:</span>
              <code className="field-code">{diagnostics?.dataset_configured_path || 'C:/Users/avina/Downloads/JDT/JDT_dataset_issues (1).csv'}</code>
            </div>
            <div className="setting-field">
              <span className="field-name">Status:</span>
              {diagnostics?.dataset_valid ? (
                <span className="badge badge-success">
                  <CheckCircle2 size={12} />
                  <span>Valid Local File</span>
                </span>
              ) : (
                <span className="badge badge-warning">
                  <span>{diagnostics?.dataset_message || 'Verification Pending'}</span>
                </span>
              )}
            </div>
            <div className="setting-field">
              <span className="field-name">File Size:</span>
              <strong className="field-val">
                {diagnostics?.dataset_metadata?.size_gb
                  ? `${diagnostics.dataset_metadata.size_gb} GB (${diagnostics.dataset_metadata.filename || 'CSV'})`
                  : diagnostics?.dataset_message || 'Not verified'}
              </strong>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
