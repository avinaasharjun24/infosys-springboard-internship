import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc, text

from .config import settings
from .db import Base, engine, get_db, check_db_connection, init_db
from .models import (
    Defect,
    BugSubmission,
    UploadedFile,
    AgentExecution,
    TriageResult,
    LogAnalysisResult,
    HistoricalDefectReference,
    FinalAnalysisResult,
    IngestionJob,
    Analysis
)
from .schemas import (
    BugCreate,
    BugSubmissionOut,
    UploadResponse,
    SearchRequest,
    HistoricalMatch,
    AnalysisDetailOut,
    AnalysisSummaryOut,
    TriageOutput,
    LogAnalysisOutput,
    AgentExecutionOut,
    IngestRequest,
    IngestJobStatus,
    KBStats
)
from .knowledge import get_kb
from .gemini_service import gemini_service
from .file_service import process_uploaded_file
from .orchestrator import execute_and_persist_workflow

# Configure structured logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("defectiq.api")

# Ensure database tables and storage directories exist.  An unavailable
# PostgreSQL service should be reported by /api/health instead of preventing
# the diagnostics server from starting.
try:
    init_db()
except Exception as exc:
    logger.warning("Database initialization deferred: %s", exc)
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="DEFECTIQ API",
    version=settings.version,
    description="Enterprise AI Software Defect Intelligence Platform — Milestones 1 & 2"
)

# CORS middleware
origins = [x.strip() for x in settings.cors_origins.split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------------------
# Health & Diagnostics Endpoints
# -------------------------------------------------------------------------

@app.get("/api/health", summary="System Health Check")
def health_check():
    """Verify operational health of database, vector store, and configuration."""
    db_ok, db_msg = check_db_connection()
    kb_count = 0
    qdrant_ok = False
    try:
        kb_count = get_kb().count()
        qdrant_ok = True
    except Exception as exc:
        logger.warning(f"Qdrant health probe failed: {exc}")

    ds_ok, ds_msg, ds_meta = settings.validate_dataset()

    return {
        "status": "operational" if db_ok and qdrant_ok else "degraded",
        "service": "defectiq-backend",
        "version": settings.version,
        "database": {"connected": db_ok, "message": db_msg},
        "qdrant": {"connected": qdrant_ok, "indexed_vectors": kb_count},
        "dataset": {"configured": bool(settings.dataset_path), "valid": ds_ok, "message": ds_msg},
        "gemini": {"configured": bool(settings.gemini_api_key), "model": settings.gemini_model}
    }


@app.get("/api/overview", summary="Executive Dashboard Overview")
def get_dashboard_overview(db: Session = Depends(get_db)):
    """Return live system telemetry, defect volume, severity distribution, and recent activity."""
    total_submissions = db.query(BugSubmission).count()
    completed_analyses = db.query(BugSubmission).filter(BugSubmission.status == "completed").count()
    processing_analyses = db.query(BugSubmission).filter(BugSubmission.status == "processing").count()
    failed_analyses = db.query(BugSubmission).filter(BugSubmission.status == "failed").count()

    # Calculate live severity distribution from analyzed records
    severity_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    triages = db.query(TriageResult).all()
    for t in triages:
        if t.severity in severity_counts:
            severity_counts[t.severity] += 1

    # Fetch recent submissions
    recent_submissions = (
        db.query(BugSubmission)
        .order_by(desc(BugSubmission.created_at))
        .limit(6)
        .all()
    )

    kb_count = 0
    try:
        kb_count = get_kb().count()
    except Exception:
        pass

    recent_list = []
    for s in recent_submissions:
        sev = s.triage_result.severity if s.triage_result else None
        cat = s.triage_result.affected_component if s.triage_result else (s.component or "Core")
        recent_list.append({
            "id": s.id,
            "submission_uuid": s.submission_uuid,
            "title": s.title,
            "status": s.status,
            "severity": sev,
            "component": cat,
            "created_at": s.created_at.isoformat() if s.created_at else None
        })

    return {
        "total_submissions": total_submissions,
        "completed_analyses": completed_analyses,
        "processing_analyses": processing_analyses,
        "failed_analyses": failed_analyses,
        "indexed_historical_defects": kb_count,
        "severity_distribution": [
            {"name": k, "count": v} for k, v in severity_counts.items()
        ],
        "recent_submissions": recent_list,
        "dataset_source": "Eclipse JDT (63,266 records)"
    }


@app.get("/api/settings/diagnostics", summary="Environment Diagnostics")
def get_diagnostics():
    """Return environment settings diagnostics for administrative inspection."""
    diag = settings.get_diagnostics()
    db_ok, db_message = check_db_connection()
    diag["database_connected"] = db_ok
    diag["database_message"] = db_message
    try:
        diag["indexed_vectors"] = get_kb().count()
        diag["qdrant_connected"] = True
    except Exception as exc:
        diag["indexed_vectors"] = 0
        diag["qdrant_connected"] = False
        diag["qdrant_message"] = str(exc)
    return diag


@app.post("/api/gemini/verify", summary="Verify Gemini Credentials and Configured Model")
def verify_gemini():
    """Explicit operator-triggered check; never runs during startup or ingestion."""
    return gemini_service.connectivity_check()


# -------------------------------------------------------------------------
# Bug Submission & File Upload Endpoints (Milestone 1)
# -------------------------------------------------------------------------

@app.post("/api/uploads", response_model=UploadResponse, summary="Upload Defect Log or Document")
async def upload_attachment(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload and securely parse TXT, LOG, CSV, PDF, or DOCX technical evidence files."""
    file_info = await process_uploaded_file(file)

    # Persist uploaded file record
    record = UploadedFile(
        filename=file_info["original_filename"],
        safe_filename=file_info["safe_filename"],
        file_path=file_info["file_path"],
        file_size_bytes=file_info["file_size_bytes"],
        mime_type=file_info["mime_type"],
        extracted_text=file_info["extracted_text"],
        extracted_chars=file_info["extracted_chars"]
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    preview = file_info["extracted_text"][:500] if file_info["extracted_text"] else "No text extracted."
    return UploadResponse(
        id=record.id,
        filename=record.filename,
        safe_filename=record.safe_filename,
        file_size_bytes=record.file_size_bytes,
        mime_type=record.mime_type,
        extracted_chars=record.extracted_chars,
        preview_text=preview
    )


@app.post("/api/bugs", summary="Submit Defect for Analysis")
def create_bug_submission(bug: BugCreate, db: Session = Depends(get_db)):
    """Submit a new defect report with technical context, logs, and associated uploads."""
    sub_uuid = f"DEF-{uuid.uuid4().hex[:8].upper()}"

    combined_logs = bug.logs.strip()
    attached_files = []
    if bug.file_ids:
        attached_files = db.query(UploadedFile).filter(UploadedFile.id.in_(bug.file_ids)).all()
        for af in attached_files:
            if af.extracted_text and af.extracted_text not in combined_logs:
                combined_logs = f"{combined_logs}\n\n[Attached File: {af.filename}]\n{af.extracted_text}".strip()

    submission = BugSubmission(
        submission_uuid=sub_uuid,
        title=bug.title.strip(),
        project=bug.project.strip() or "Eclipse JDT",
        component=bug.component.strip(),
        description=bug.description.strip(),
        expected_behavior=bug.expected_behavior.strip(),
        actual_behavior=bug.actual_behavior.strip(),
        raw_logs=combined_logs,
        status="submitted"
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    # Associate uploaded files with this submission
    for af in attached_files:
        af.submission_id = submission.id
    db.commit()

    # Also maintain legacy Analysis table row for backward compatibility
    legacy = Analysis(
        id=submission.id,
        title=submission.title,
        project=submission.project,
        description=submission.description,
        logs=submission.raw_logs,
        status="submitted"
    )
    db.add(legacy)
    db.commit()

    return {
        "id": submission.id,
        "submission_uuid": submission.submission_uuid,
        "title": submission.title,
        "status": submission.status,
        "message": "Defect report successfully registered."
    }


# -------------------------------------------------------------------------
# Submissions & Analysis History Endpoints
# -------------------------------------------------------------------------

@app.get("/api/submissions", summary="List All Submissions")
def list_submissions(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Retrieve history of defect submissions with filtering options."""
    query = db.query(BugSubmission).order_by(desc(BugSubmission.created_at))
    if status:
        query = query.filter(BugSubmission.status == status)

    rows = query.limit(limit).all()
    results = []
    for s in rows:
        triage = s.triage_result
        sev = triage.severity if triage else None
        if severity and sev != severity:
            continue
        results.append({
            "id": s.id,
            "submission_uuid": s.submission_uuid,
            "title": s.title,
            "project": s.project,
            "component": triage.affected_component if triage else (s.component or "Core"),
            "status": s.status,
            "severity": sev,
            "priority": triage.priority if triage else None,
            "confidence": triage.confidence if triage else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "file_count": len(s.uploaded_files)
        })
    return results


# Legacy alias route for /api/analyses
@app.get("/api/analyses", summary="List Analyses (Legacy Compatible)")
def list_analyses_legacy(db: Session = Depends(get_db)):
    return list_submissions(db=db)


@app.get("/api/submissions/{submission_id}", summary="Get Detailed Submission & Analysis Findings")
def get_submission_detail(submission_id: int, db: Session = Depends(get_db)):
    """Retrieve complete multi-agent findings, historical evidence, and execution trace."""
    sub = db.get(BugSubmission, submission_id)
    if not sub:
        raise HTTPException(404, f"Submission #{submission_id} not found")

    triage_dto = None
    if sub.triage_result:
        t = sub.triage_result
        triage_dto = {
            "severity": t.severity,
            "priority": t.priority,
            "affected_component": t.affected_component,
            "confidence": t.confidence,
            "reasoning": t.reasoning,
            "evidence": json.loads(t.evidence_json or "[]"),
            "historical_mapping": json.loads(t.historical_mapping_json or "{}"),
            "classification_source": t.classification_source,
        }

    log_dto = None
    if sub.log_analysis_result:
        l = sub.log_analysis_result
        log_dto = {
            "has_logs": l.has_logs,
            "status": l.status,
            "exception_type": l.exception_type,
            "error_message": l.error_message,
            "failure_point": l.failure_point,
            "file_name": l.file_name,
            "line_number": l.line_number,
            "chained_exceptions": json.loads(l.chained_exceptions_json or "[]"),
            "affected_code_path": json.loads(l.affected_code_path_json or "[]"),
            "technical_findings": json.loads(l.technical_findings_json or "[]"),
            "confidence": l.confidence,
            "analysis_source": l.analysis_source,
        }

    hist_matches = []
    for h in sub.historical_references:
        hist_matches.append({
            "source_id": h.source_id,
            "product": h.product,
            "component": h.component,
            "summary": h.summary,
            "similarity_score": h.similarity_score,
            "resolution": h.resolution,
            "severity": h.severity,
            "priority": h.priority,
            "is_duplicate": h.is_duplicate,
            "issue_url": h.issue_url
        })

    agent_execs = []
    for a in sub.agent_executions:
        agent_execs.append({
            "agent_name": a.agent_name,
            "status": a.status,
            "execution_order": a.execution_order,
            "is_parallel": a.is_parallel,
            "duration_ms": a.duration_ms,
            "output_summary": a.output_summary,
            "error_message": a.error_message
        })

    rc_hypo = sub.final_result.root_cause_hypothesis if sub.final_result else None
    rem_recs = json.loads(sub.final_result.remediation_recommendations_json or "[]") if sub.final_result else []
    val_steps = json.loads(sub.final_result.validation_steps_json or "[]") if sub.final_result else []
    full_state = {}
    if sub.final_result and sub.final_result.full_result_json:
        try:
            full_state = json.loads(sub.final_result.full_result_json)
        except Exception:
            full_state = {}
    duplicate_analysis = full_state.get("duplicate_analysis")
    root_cause_details = full_state.get("root_cause")
    remediation_details = full_state.get("remediation", {})

    # Format result dict for legacy consumer compatibility
    legacy_result = {
        "triage": triage_dto,
        "log_analysis": log_dto,
        "similar": hist_matches,
        "duplicate_analysis": duplicate_analysis,
        "root_cause": root_cause_details or {"hypothesis": rc_hypo, "evidence": hist_matches[:3]},
        "remediation": {
            "recommendations": rem_recs,
            "validation_steps": val_steps,
            "reasoning": remediation_details.get("reasoning", ""),
            "affected_components_or_files": remediation_details.get("affected_components_or_files", []),
        },
        "agent_executions": agent_execs,
    }

    return {
        "id": sub.id,
        "submission_uuid": sub.submission_uuid,
        "title": sub.title,
        "project": sub.project,
        "component": sub.component,
        "description": sub.description,
        "expected_behavior": sub.expected_behavior,
        "actual_behavior": sub.actual_behavior,
        "logs": sub.raw_logs,
        "status": sub.status,
        "severity": triage_dto.get("severity") if triage_dto else None,
        "priority": triage_dto.get("priority") if triage_dto else None,
        "confidence": triage_dto.get("confidence") if triage_dto else None,
        "triage": triage_dto,
        "log_analysis": log_dto,
        "historical_matches": hist_matches,
        "duplicate_analysis": duplicate_analysis,
        "root_cause_hypothesis": rc_hypo,
        "root_cause_details": root_cause_details,
        "remediation_recommendations": rem_recs,
        "validation_steps": val_steps,
        "remediation_reasoning": remediation_details.get("reasoning", ""),
        "affected_files": remediation_details.get("affected_components_or_files", []),
        "agent_executions": agent_execs,
        "files": [{"id": f.id, "filename": f.filename, "size": f.file_size_bytes} for f in sub.uploaded_files],
        "created_at": sub.created_at.isoformat() if sub.created_at else None,
        "result": legacy_result,  # Legacy field for existing App.jsx
    }


# Legacy alias route for /api/analyses/{id}
@app.get("/api/analyses/{analysis_id}", summary="Get Analysis Detail (Legacy Compatible)")
def get_analysis_legacy(analysis_id: int, db: Session = Depends(get_db)):
    return get_submission_detail(submission_id=analysis_id, db=db)


# -------------------------------------------------------------------------
# Multi-Agent Workflow Execution (Milestone 2)
# -------------------------------------------------------------------------

@app.post("/api/analyses/{submission_id}/run", summary="Trigger LangGraph Multi-Agent Workflow")
def run_defect_analysis(submission_id: int, db: Session = Depends(get_db)):
    """Execute parallel Triage & Log Analysis agents through LangGraph with full persistence."""
    sub = db.get(BugSubmission, submission_id)
    if not sub:
        # Fallback to legacy Analysis table if BugSubmission not found
        legacy = db.get(Analysis, submission_id)
        if not legacy:
            raise HTTPException(404, f"Submission #{submission_id} not found")
        sub = BugSubmission(
            id=legacy.id,
            submission_uuid=f"DEF-{legacy.id:05d}",
            title=legacy.title,
            project=legacy.project,
            description=legacy.description,
            raw_logs=legacy.logs,
            status="submitted"
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)

    try:
        final_state = execute_and_persist_workflow(sub, db)
        return get_submission_detail(submission_id=sub.id, db=db)
    except Exception as exc:
        logger.error(f"Failed to execute analysis on #{submission_id}: {exc}")
        raise HTTPException(500, f"Analysis execution failed: {exc}")


@app.get("/api/submissions/{submission_id}/agents", summary="Get Live Agent Execution Audit")
def get_agent_executions(submission_id: int, db: Session = Depends(get_db)):
    """Inspect trace and execution times of each agent in the LangGraph workflow."""
    sub = db.get(BugSubmission, submission_id)
    if not sub:
        raise HTTPException(404, f"Submission #{submission_id} not found")
    
    execs = db.query(AgentExecution).filter(AgentExecution.submission_id == submission_id).order_by(AgentExecution.execution_order).all()
    return [
        {
            "agent_name": e.agent_name,
            "status": e.status,
            "execution_order": e.execution_order,
            "is_parallel": e.is_parallel,
            "duration_ms": e.duration_ms,
            "output_summary": e.output_summary,
            "error_message": e.error_message
        }
        for e in execs
    ]


# -------------------------------------------------------------------------
# Knowledge Base & Ingestion Endpoints (Milestone 1)
# -------------------------------------------------------------------------

@app.get("/api/knowledge/stats", response_model=KBStats, summary="Knowledge Base Statistics")
def get_knowledge_stats():
    """Retrieve indexed defect count, embedding specifications, and dataset health."""
    kb_count = 0
    try:
        kb_count = get_kb().count()
    except Exception:
        pass

    ds_ok, _, ds_meta = settings.validate_dataset()
    try:
        collection_info = get_kb().collection_info()
    except Exception as exc:
        collection_info = {"error": str(exc)}
    return KBStats(
        indexed_defects=kb_count,
        collection_name=settings.collection_name,
        embedding_model=settings.embedding_model,
        dataset_configured=bool(settings.dataset_path),
        dataset_valid=ds_ok,
        dataset_metadata={**ds_meta, "collection": collection_info}
    )


@app.post("/api/knowledge/search", summary="Semantic RAG Search")
def search_knowledge_base(request: SearchRequest):
    """Retrieve semantically similar historical defects using SentenceTransformers and Qdrant."""
    try:
        kb = get_kb()
        results = kb.search(
            query=request.query,
            limit=request.limit,
            component=request.component,
            min_score=request.min_score
        )
        return {"query": request.query, "count": len(results), "results": results}
    except Exception as exc:
        logger.error(f"Knowledge search error: {exc}")
        raise HTTPException(503, f"Knowledge base search unavailable: {exc}")


def _run_background_ingest(job_id: int, target_path: str, limit: Optional[int], batch_size: int, start_offset: int = 0):
    """Background task function to process historical dataset in chunks."""
    from .db import SessionLocal
    db = SessionLocal()
    job = db.get(IngestionJob, job_id)
    if not job:
        db.close()
        return

    job.status = "running"
    db.commit()

    def update_progress(data: dict):
        try:
            job.current_chunk = data.get("chunk", 0)
            job.processed_records = data.get("processed", 0)
            job.indexed_records = data.get("indexed", 0)
            job.indexed_vectors = data.get("indexed_vectors", 0)
            job.failed_records = data.get("failed", 0)
            job.skipped_records = data.get("skipped", 0)
            job.resume_offset = data.get("resume_offset", 0)
            db.commit()
        except Exception:
            pass

    try:
        kb = get_kb()
        res = kb.ingest_csv(
            csv_path=target_path,
            limit=limit,
            batch_size=batch_size,
            start_offset=start_offset,
            progress_callback=update_progress
        )
        job.status = "completed"
        job.total_records = res.get("total_processed", 0)
        job.indexed_records = res.get("total_indexed", 0)
        job.indexed_vectors = res.get("total_indexed_vectors", 0)
        job.failed_records = res.get("total_failed", 0)
        job.skipped_records = res.get("total_skipped", 0)
        job.resume_offset = res.get("resume_offset", 0)
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:
        logger.error(f"Background ingestion failed for job #{job_id}: {exc}")
        job.status = "failed"
        job.error_message = str(exc)
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()


@app.post("/api/knowledge/ingest", summary="Ingest Historical Defect Dataset")
def trigger_ingest(
    background_tasks: BackgroundTasks,
    path: Optional[str] = None,
    limit: Optional[int] = Query(None, ge=1, description="Optional limit for test/partial ingestion"),
    batch_size: int = Query(500, ge=50, le=2000),
    resume_job_id: Optional[int] = Query(None, description="Resume a failed or replay a completed ingestion job"),
    run_async: bool = Query(True, description="Run in background or synchronously"),
    db: Session = Depends(get_db)
):
    """
    Ingest the Eclipse JDT historical defect dataset in memory-efficient chunks.
    Reads from configured DATASET_PATH, sanitizes PII, embeds with MiniLM-L6-v2, and indexes into Qdrant.
    """
    target_path = path or settings.dataset_path
    if not target_path or not Path(target_path).exists():
        raise HTTPException(
            404,
            f"Configured dataset path not found: {target_path}. Please check DATASET_PATH setting."
        )

    start_offset = 0
    if resume_job_id:
        job = db.get(IngestionJob, resume_job_id)
        if not job:
            raise HTTPException(404, f"Ingestion job #{resume_job_id} not found")
        if job.status not in {"failed", "completed"}:
            raise HTTPException(409, "Only failed or completed jobs can be safely resumed or replayed")
        start_offset = job.resume_offset or job.processed_records
        job.status, job.error_message, job.completed_at = "pending", None, None
        db.commit()
        db.refresh(job)
    else:
        job = IngestionJob(
            job_uuid=f"JOB-{uuid.uuid4().hex[:8].upper()}",
            dataset_path=str(target_path), status="pending", batch_size=batch_size, total_records=0
        )
        db.add(job)
        db.commit()
        db.refresh(job)

    if run_async:
        background_tasks.add_task(_run_background_ingest, job.id, str(target_path), limit, batch_size, start_offset)
        return {
            "job_id": job.id,
            "job_uuid": job.job_uuid,
            "status": "pending",
            "message": f"Background ingestion started for {target_path}. Monitor status via /api/knowledge/ingest/status/{job.id}"
        }
    else:
        # Run synchronously for test verification
        _run_background_ingest(job.id, str(target_path), limit, batch_size, start_offset)
        db.refresh(job)
        return {
            "job_id": job.id,
            "job_uuid": job.job_uuid,
            "status": job.status,
            "indexed_records": job.indexed_records,
            "indexed_vectors": job.indexed_vectors,
            "total_records": job.total_records,
            "failed_records": job.failed_records,
            "skipped_records": job.skipped_records,
            "error_message": job.error_message
        }


@app.get("/api/knowledge/ingest/status/{job_id}", summary="Check Ingestion Job Status")
def get_ingest_job_status(job_id: int, db: Session = Depends(get_db)):
    """Poll progress of a background historical defect ingestion job."""
    job = db.get(IngestionJob, job_id)
    if not job:
        raise HTTPException(404, f"Ingestion job #{job_id} not found")
    return {
        "job_id": job.id,
        "job_uuid": job.job_uuid,
        "status": job.status,
        "current_chunk": job.current_chunk,
        "processed_records": job.processed_records,
        "indexed_records": job.indexed_records,
        "indexed_vectors": job.indexed_vectors,
        "failed_records": job.failed_records,
        "skipped_records": job.skipped_records,
        "resume_offset": job.resume_offset,
        "error_message": job.error_message,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None
    }
