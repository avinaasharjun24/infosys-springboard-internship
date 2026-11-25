import React, { useState } from 'react';
import {
  UploadCloud,
  FileText,
  AlertCircle,
  Loader2,
  CheckCircle2,
  X,
  Sparkles,
  ShieldCheck,
  Terminal,
  Paperclip
} from 'lucide-react';

export default function SubmitDefect({ api, onSubmitted, notify }) {
  const [title, setTitle] = useState('');
  const [project, setProject] = useState('Eclipse JDT');
  const [component, setComponent] = useState('Core');
  const [description, setDescription] = useState('');
  const [expectedBehavior, setExpectedBehavior] = useState('');
  const [actualBehavior, setActualBehavior] = useState('');
  const [logs, setLogs] = useState('');
  
  const [attachedFiles, setAttachedFiles] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const samplePresets = [
    {
      label: 'NPE in Batch Compiler',
      title: 'NullPointerException in SourceTypeBinding.resolveTypesFor during batch compile',
      component: 'Core',
      description: 'When building a Java 8 project with generic lambda expressions and anonymous inner classes, the batch compiler fails unexpectedly with an unhandled exception.',
      expected: 'Compilation succeeds or produces a clean compiler diagnostic error.',
      actual: 'Internal compiler error with NullPointerException in lookup tables.',
      logs: `java.lang.NullPointerException: null
\tat org.eclipse.jdt.internal.compiler.lookup.SourceTypeBinding.resolveTypesFor(SourceTypeBinding.java:1770)
\tat org.eclipse.jdt.internal.compiler.lookup.SourceTypeBinding.methods(SourceTypeBinding.java:1464)
\tat org.eclipse.jdt.internal.compiler.lookup.ParameterizedTypeBinding.methods(ParameterizedTypeBinding.java:951)
\tat org.eclipse.jdt.internal.compiler.lookup.ReferenceBinding.availableMethods(ReferenceBinding.java:229)
\tat org.eclipse.jdt.core.dom.TypeBinding.getDeclaredMethods(TypeBinding.java:289)
\tat org.eclipse.jdt.internal.corext.dom.Bindings.findOverriddenMethodInType(Bindings.java:464)`
    },
    {
      label: 'SWT Editor Crash (Critical)',
      title: 'Fatal UI freeze and crash when opening large source file in Java editor',
      component: 'UI',
      description: 'Opening a large compilation unit (>10,000 LOC) causes the UI thread to hang completely, causing system crash and data loss in uncommitted buffers.',
      expected: 'Editor loads asynchronously with progress monitor.',
      actual: 'UI deadlocks and workbench terminates abruptly with fatal data loss.',
      logs: `org.eclipse.swt.SWTError: No more handles [out of OS resources]
\tat org.eclipse.swt.SWT.error(SWT.java:4559)
\tat org.eclipse.swt.widgets.Widget.error(Widget.java:472)
\tat org.eclipse.swt.widgets.Control.internal_new_GC(Control.java:2276)
\tat org.eclipse.jface.text.source.CompositeRuler.layoutTextViewer(CompositeRuler.java:702)`
    },
    {
      label: 'Cosmetic Typo (Low)',
      title: 'Typo in Java Editor preference page description label',
      component: 'UI',
      description: 'Under Window > Preferences > Java > Editor, the word "appearance" is misspelled as "appearence". Cosmetic typo with no functional impact.',
      expected: 'Correct spelling displayed in preferences dialog.',
      actual: 'Spelling error visible in preferences pane.',
      logs: ''
    }
  ];

  const loadPreset = (preset) => {
    setTitle(preset.title);
    setComponent(preset.component);
    setDescription(preset.description);
    setExpectedBehavior(preset.expected);
    setActualBehavior(preset.actual);
    setLogs(preset.logs);
    notify(`Loaded preset: ${preset.label}`);
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${api}/uploads`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'File upload failed');

      setAttachedFiles((prev) => [...prev, data]);
      notify(`Attached ${data.filename} (${data.extracted_chars.toLocaleString()} chars extracted)`);
    } catch (err) {
      notify(`Upload error: ${err.message}`);
    } finally {
      setIsUploading(false);
      e.target.value = '';
    }
  };

  const removeFile = (fileId) => {
    setAttachedFiles((prev) => prev.filter((f) => f.id !== fileId));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title.trim() || !description.trim()) {
      return notify('Please provide both a Title and a Problem Description.');
    }

    setIsSubmitting(true);
    try {
      // 1. Submit defect
      const subRes = await fetch(`${api}/bugs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: title.trim(),
          project: project.trim(),
          component: component.trim(),
          description: description.trim(),
          expected_behavior: expectedBehavior.trim(),
          actual_behavior: actualBehavior.trim(),
          logs: logs.trim(),
          file_ids: attachedFiles.map((f) => f.id),
        }),
      });

      const subData = await subRes.json();
      if (!subRes.ok) throw new Error(subData.detail || 'Submission failed');

      notify(`Defect #${subData.id} submitted! Running LangGraph multi-agent analysis...`);

      // 2. Trigger analysis
      const runRes = await fetch(`${api}/analyses/${subData.id}/run`, {
        method: 'POST',
      });
      const runData = await runRes.json();
      if (!runRes.ok) throw new Error(runData.detail || 'Analysis execution failed');

      notify(`Analysis completed for Defect #${subData.id}!`);
      onSubmitted(subData.id);
    } catch (err) {
      notify(`Error: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="page-container submit-defect-page">
      <div className="page-header">
        <div>
          <div className="page-pretitle">DEFECT INTAKE & TRIAGE</div>
          <h1 className="page-title">Submit Defect for Analysis</h1>
          <p className="page-description">
            Provide issue descriptions, reproduction steps, error logs, or document attachments for automated multi-agent triage.
          </p>
        </div>
        <div className="presets-container">
          <span className="presets-label">Quick Test Presets:</span>
          {samplePresets.map((p) => (
            <button
              key={p.label}
              type="button"
              className="btn-preset"
              onClick={() => loadPreset(p)}
            >
              <Sparkles size={13} />
              <span>{p.label}</span>
            </button>
          ))}
        </div>
      </div>

      <form className="defect-form" onSubmit={handleSubmit}>
        <div className="form-card">
          <div className="form-section-title">
            <span className="section-number">01</span>
            <div>
              <h3>Defect Summary & Subsystem</h3>
              <p>Identify the software issue and affected workspace component.</p>
            </div>
          </div>

          <div className="form-row">
            <div className="form-group flex-3">
              <label htmlFor="defect-title">
                Defect Title <span className="required">*</span>
              </label>
              <input
                id="defect-title"
                type="text"
                required
                minLength={4}
                placeholder="e.g. NullPointerException in SourceTypeBinding.resolveTypesFor during compile"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>

            <div className="form-group flex-1">
              <label htmlFor="defect-component">Subsystem / Component</label>
              <select
                id="defect-component"
                value={component}
                onChange={(e) => setComponent(e.target.value)}
              >
                <option value="Core">Core (Compiler, AST, JDT)</option>
                <option value="UI">UI (Views, Editor, Dialogs)</option>
                <option value="Debug">Debug (JDI, Breakpoints, VM)</option>
                <option value="Text">Text (Reconciler, Editor)</option>
                <option value="APT">APT (Annotation Processing)</option>
                <option value="Other">Other / Unspecified</option>
              </select>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="defect-description">
              Problem Description & Reproduction Steps <span className="required">*</span>
            </label>
            <textarea
              id="defect-description"
              required
              minLength={10}
              rows={5}
              placeholder="Describe the failure scenario, environment details (JDK version, OS), and exact reproduction steps..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          <div className="form-row">
            <div className="form-group flex-1">
              <label htmlFor="expected-behavior">Expected Behavior</label>
              <textarea
                id="expected-behavior"
                rows={2}
                placeholder="What was expected to happen..."
                value={expectedBehavior}
                onChange={(e) => setExpectedBehavior(e.target.value)}
              />
            </div>
            <div className="form-group flex-1">
              <label htmlFor="actual-behavior">Actual Observed Behavior</label>
              <textarea
                id="actual-behavior"
                rows={2}
                placeholder="What actually occurred (error message, crash, wrong output)..."
                value={actualBehavior}
                onChange={(e) => setActualBehavior(e.target.value)}
              />
            </div>
          </div>
        </div>

        <div className="form-card">
          <div className="form-section-title">
            <span className="section-number">02</span>
            <div>
              <h3>Technical Evidence (Logs & Stack Traces)</h3>
              <p>Paste console errors, Java stack traces, or attach diagnostic files.</p>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="defect-logs">
              <Terminal size={15} />
              <span>Stack Trace / Error Console Output</span>
            </label>
            <textarea
              id="defect-logs"
              className="monospace-textarea"
              rows={7}
              placeholder="Paste Java stack traces, Exception in thread 'main', Caused by: chains, or error logs..."
              value={logs}
              onChange={(e) => setLogs(e.target.value)}
            />
          </div>

          {/* File Upload Area */}
          <div className="upload-section">
            <label className="upload-dropzone">
              <UploadCloud size={28} className="upload-icon" />
              <div className="upload-prompt">
                <strong>{isUploading ? 'Extracting document text...' : 'Click to attach evidence file'}</strong>
                <span>Supports TXT, LOG, CSV, PDF, or DOCX (up to 20 MB)</span>
              </div>
              <input
                type="file"
                accept=".txt,.log,.csv,.pdf,.docx"
                disabled={isUploading}
                onChange={handleFileUpload}
              />
            </label>

            {attachedFiles.length > 0 && (
              <div className="attached-files-list">
                <span className="attached-title">Attached Evidence Files:</span>
                {attachedFiles.map((file) => (
                  <div key={file.id} className="file-chip">
                    <Paperclip size={14} />
                    <span className="file-chip-name">{file.filename}</span>
                    <span className="file-chip-chars">({file.extracted_chars.toLocaleString()} chars)</span>
                    <button
                      type="button"
                      className="btn-remove-file"
                      onClick={() => removeFile(file.id)}
                    >
                      <X size={14} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="form-footer">
          <div className="security-notice">
            <ShieldCheck size={16} />
            <span>Submissions and attached files are stored securely in your local PostgreSQL/SQLite database.</span>
          </div>

          <button
            type="submit"
            className="btn btn-primary btn-lg"
            disabled={isSubmitting || isUploading}
          >
            {isSubmitting ? (
              <>
                <Loader2 size={18} className="spin" />
                <span>Running LangGraph Multi-Agent Analysis...</span>
              </>
            ) : (
              <>
                <Sparkles size={18} />
                <span>Submit & Run Analysis</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
