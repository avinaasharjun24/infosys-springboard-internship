import React, { useState, useEffect } from 'react';
import {
  Database,
  Search,
  BookOpen,
  Cpu,
  ShieldCheck,
  Play,
  Loader2,
  CheckCircle2,
  AlertCircle,
  ArrowUpRight,
  Filter,
  FileCheck2,
  HardDrive
} from 'lucide-react';

export default function KnowledgeBase({ api, notify }) {
  const [stats, setStats] = useState(null);
  const [loadingStats, setLoadingStats] = useState(false);

  // Ingestion state
  const [batchSize, setBatchSize] = useState(500);
  const [ingestLimit, setIngestLimit] = useState('');
  const [isIngesting, setIsIngesting] = useState(false);
  const [activeJob, setActiveJob] = useState(null);

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchComponent, setSearchComponent] = useState('ALL');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);

  const fetchStats = async () => {
    setLoadingStats(true);
    try {
      const res = await fetch(`${api}/knowledge/stats`);
      const data = await res.json();
      setStats(data);
    } catch (err) {
      console.error('Failed to load KB stats:', err);
    } finally {
      setLoadingStats(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  // Poll active ingestion job if running
  useEffect(() => {
    let interval = null;
    if (activeJob && (activeJob.status === 'pending' || activeJob.status === 'running')) {
      interval = setInterval(async () => {
        try {
          const res = await fetch(`${api}/knowledge/ingest/status/${activeJob.job_id}`);
          const data = await res.json();
          setActiveJob(data);
          if (data.status === 'completed' || data.status === 'failed') {
            setIsIngesting(false);
            fetchStats();
            if (data.status === 'completed') {
              notify(`Ingestion finished! Indexed ${data.indexed_records} records into Qdrant.`);
            } else {
              notify(`Ingestion failed: ${data.error_message}`);
            }
          }
        } catch (err) {
          console.error('Error polling ingest job:', err);
        }
      }, 3000);
    }
    return () => clearInterval(interval);
  }, [activeJob]);

  const handleStartIngest = async (mode = 'custom') => {
    setIsIngesting(true);
    try {
      const queryParams = new URLSearchParams({
        batch_size: String(batchSize),
        run_async: 'true',
      });
      const selectedLimit = mode === 'test' ? 100 : mode === 'full' ? null : ingestLimit;
      if (selectedLimit && Number(selectedLimit) > 0) {
        queryParams.append('limit', String(selectedLimit));
      }

      const res = await fetch(`${api}/knowledge/ingest?${queryParams.toString()}`, {
        method: 'POST',
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Ingestion trigger failed');

      setActiveJob(data);
      notify(`Historical defect ingestion started (Job ${data.job_uuid})`);
    } catch (err) {
      notify(`Ingest error: ${err.message}`);
      setIsIngesting(false);
    }
  };

  const handleSearch = async (e) => {
    e?.preventDefault();
    if (!searchQuery.trim() || searchQuery.trim().length < 2) return;

    setIsSearching(true);
    try {
      const res = await fetch(`${api}/knowledge/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: searchQuery.trim(),
          limit: 10,
          component: searchComponent === 'ALL' ? null : searchComponent,
          min_score: 0.20,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Search query failed');
      setSearchResults(data.results || []);
    } catch (err) {
      notify(`Search error: ${err.message}`);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="page-container knowledge-page">
      <div className="page-header">
        <div>
          <div className="page-pretitle">RETRIEVAL AUGMENTED GENERATION (RAG)</div>
          <h1 className="page-title">Historical Defect Knowledge Base</h1>
          <p className="page-description">
            Vector embeddings of 63,266 Eclipse JDT defect records indexed in Qdrant with all-MiniLM-L6-v2.
          </p>
        </div>
      </div>

      {/* KPI Stats Grid */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-label">INDEXED VECTORS</span>
            <Database size={18} className="kpi-icon blue" />
          </div>
          <div className="kpi-value">{stats?.indexed_defects?.toLocaleString() ?? '—'}</div>
          <div className="kpi-footer">Active Qdrant collection vectors</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-label">SOURCE CORPUS</span>
            <BookOpen size={18} className="kpi-icon purple" />
          </div>
          <div className="kpi-value">Eclipse JDT</div>
          <div className="kpi-footer">63,266 historical defect records</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-label">EMBEDDING MODEL</span>
            <Cpu size={18} className="kpi-icon teal" />
          </div>
          <div className="kpi-value">MiniLM-L6-v2</div>
          <div className="kpi-footer">384 dims · Cosine similarity</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-label">DATASET VALIDATION</span>
            <ShieldCheck size={18} className="kpi-icon green" />
          </div>
          <div className="kpi-value">{stats?.dataset_valid ? 'Verified' : 'Pending'}</div>
          <div className="kpi-footer">Local Windows CSV configured</div>
        </div>
      </div>

      {/* Ingestion & Config Panel */}
      <div className="panel ingest-control-panel">
        <div className="panel-header">
          <div>
            <h3 className="panel-title">Historical Ingestion Engine</h3>
            <p className="panel-subtitle">Memory-efficient chunked CSV processor with PII redaction and deterministic UUIDs</p>
          </div>
          <span className="badge badge-subtle">Operator Controlled</span>
        </div>

        <div className="dataset-path-box">
          <div className="path-icon-col">
            <HardDrive size={20} className="path-icon" />
          </div>
          <div className="path-details-col">
            <div className="path-label">CONFIGURED LOCAL DATASET PATH:</div>
            <code className="path-string">
              {stats?.dataset_metadata?.path || 'C:/Users/avina/Downloads/JDT/JDT_dataset_issues (1).csv'}
            </code>
            <div className="path-meta-row">
              {stats?.dataset_metadata?.size_gb && (
                <span>File Size: ~{stats.dataset_metadata.size_gb} GB</span>
              )}
              <span>Extraction: Chunked Pandas reader</span>
              <span>Sanitization: PII emails redacted</span>
            </div>
          </div>
        </div>

        <div className="ingest-controls-row">
          <div className="control-group">
            <label>Record Limit (optional custom batch):</label>
            <input
              type="number"
              min={10}
              max={63266}
              placeholder="Blank only for full ingestion"
              value={ingestLimit}
              onChange={(e) => setIngestLimit(e.target.value)}
              disabled={isIngesting}
            />
          </div>

          <div className="control-group">
            <label>Chunk Batch Size:</label>
            <select
              value={batchSize}
              onChange={(e) => setBatchSize(Number(e.target.value))}
              disabled={isIngesting}
            >
              <option value={250}>250 records per chunk</option>
              <option value={500}>500 records per chunk</option>
              <option value={1000}>1,000 records per chunk</option>
            </select>
          </div>

          <div className="control-group action-group">
            <button
              className="btn btn-primary"
              onClick={() => handleStartIngest('test')}
              disabled={isIngesting}
            >
              {isIngesting ? (
                <>
                  <Loader2 size={16} className="spin" />
                  <span>Processing Chunks...</span>
                </>
              ) : (
                <>
                  <Play size={16} />
                  <span>Run 100-Record Test</span>
                </>
              )}
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => handleStartIngest('full')}
              disabled={isIngesting}
              title="Processes the complete local CSV; only use after the test succeeds"
            >
              <Play size={16} />
              <span>Start Full Ingestion</span>
            </button>
          </div>
        </div>

        {/* Live Ingestion Job Progress Bar */}
        {activeJob && (
          <div className="ingest-job-card">
            <div className="job-header">
              <span className="job-uuid">{activeJob.job_uuid}</span>
              <span className={`status-pill ${activeJob.status}`}>{activeJob.status}</span>
            </div>
            <div className="job-stats-row">
              <span>Processed: <strong>{activeJob.processed_records || 0}</strong></span>
              <span>Indexed Defects: <strong>{activeJob.indexed_records || 0}</strong></span>
              <span>Vectors: <strong>{activeJob.indexed_vectors || 0}</strong></span>
              <span>Skipped: <strong>{activeJob.skipped_records || 0}</strong></span>
              <span>Failed: <strong>{activeJob.failed_records || 0}</strong></span>
              <span>Current Chunk: <strong>{activeJob.current_chunk || 0}</strong></span>
            </div>
            {isIngesting && (
              <div className="progress-bar-container">
                <div className="progress-bar-indeterminate" />
              </div>
            )}
          </div>
        )}
      </div>

      {/* Semantic Search Interactive Playground */}
      <div className="panel search-playground-panel">
        <div className="panel-header">
          <div>
            <h3 className="panel-title">Semantic Historical Search Playground</h3>
            <p className="panel-subtitle">Test vector retrieval directly against indexed Eclipse JDT defect knowledge</p>
          </div>
          <span className="badge badge-subtle">RAG Verification</span>
        </div>

        <form className="playground-search-form" onSubmit={handleSearch}>
          <div className="search-input-field flex-3">
            <Search size={18} className="search-field-icon" />
            <input
              type="text"
              placeholder="Query error message, stack trace, or bug description (e.g. NullPointerException compiler)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <div className="search-component-select flex-1">
            <select
              value={searchComponent}
              onChange={(e) => setSearchComponent(e.target.value)}
            >
              <option value="ALL">All Subsystems</option>
              <option value="Core">Core Subsystem</option>
              <option value="UI">UI Subsystem</option>
              <option value="Debug">Debug Subsystem</option>
              <option value="Text">Text Subsystem</option>
              <option value="APT">APT Subsystem</option>
            </select>
          </div>

          <button className="btn btn-primary" type="submit" disabled={isSearching}>
            {isSearching ? <Loader2 size={16} className="spin" /> : <Search size={16} />}
            <span>Search Corpus</span>
          </button>
        </form>

        {/* Search Results Display */}
        <div className="search-results-container">
          {searchResults.length > 0 && (
            <div className="results-meta-header">
              <strong>{searchResults.length} Historical Evidence Matches</strong>
              <span>Ranked by MiniLM Cosine Similarity Score</span>
            </div>
          )}

          {searchResults.map((item) => (
            <div key={item.source_id} className="search-result-card">
              <div className="result-card-top">
                <div className="result-id-group">
                  <span className="source-id-tag">JDT-{item.source_id}</span>
                  <span className={`badge-severity ${item.severity?.toLowerCase() || 'medium'}`}>
                    {item.severity}
                  </span>
                  <span className="result-comp">{item.component}</span>
                </div>
                <div className="similarity-score-badge">
                  <span>{(item.similarity_score * 100).toFixed(1)}% match</span>
                </div>
              </div>

              <h4 className="result-summary">{item.summary}</h4>
              <p className="result-desc">
                {item.description ? item.description.slice(0, 300) : 'No description text recorded.'}
                {item.description && item.description.length > 300 ? '…' : ''}
              </p>

              <div className="result-card-bottom">
                <div className="provenance-info">
                  <span>Resolution: <strong>{item.resolution || 'Unresolved'}</strong></span>
                  <span>Priority: <strong>{item.priority || 'P3'}</strong></span>
                </div>
                {item.issue_url && (
                  <a
                    href={item.issue_url}
                    target="_blank"
                    rel="noreferrer"
                    className="provenance-link"
                  >
                    <span>View Eclipse Bugzilla</span>
                    <ExternalLink size={13} />
                  </a>
                )}
              </div>
            </div>
          ))}

          {searchResults.length === 0 && !isSearching && (
            <div className="empty-panel compact">
              <Search size={28} className="empty-icon" />
              <h4>No search results</h4>
              <p>Enter natural language bug symptoms or stack traces to retrieve historical precedents.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
