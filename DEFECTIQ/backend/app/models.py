import json
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String, Text, DateTime, Integer, Float, Boolean, ForeignKey, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


class Defect(Base):
    """Historical defect record stored in database (optional reference)."""
    __tablename__ = "defects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    product: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    component: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="")
    comments: Mapped[str] = mapped_column(Text, default="")
    history: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    priority: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    resolution: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    dupe_of: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    issue_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BugSubmission(Base):
    """Primary defect submission record submitted for AI multi-agent analysis."""
    __tablename__ = "bug_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    submission_uuid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    project: Mapped[str] = mapped_column(String(100), default="Eclipse JDT")
    component: Mapped[str] = mapped_column(String(100), default="")
    description: Mapped[str] = mapped_column(Text)
    expected_behavior: Mapped[str] = mapped_column(Text, default="")
    actual_behavior: Mapped[str] = mapped_column(Text, default="")
    raw_logs: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(50), default="submitted")  # submitted, processing, completed, failed, partial
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    uploaded_files: Mapped[List["UploadedFile"]] = relationship("UploadedFile", back_populates="submission", cascade="all, delete-orphan")
    agent_executions: Mapped[List["AgentExecution"]] = relationship("AgentExecution", back_populates="submission", cascade="all, delete-orphan", order_by="AgentExecution.execution_order")
    triage_result: Mapped[Optional["TriageResult"]] = relationship("TriageResult", back_populates="submission", uselist=False, cascade="all, delete-orphan")
    log_analysis_result: Mapped[Optional["LogAnalysisResult"]] = relationship("LogAnalysisResult", back_populates="submission", uselist=False, cascade="all, delete-orphan")
    historical_references: Mapped[List["HistoricalDefectReference"]] = relationship("HistoricalDefectReference", back_populates="submission", cascade="all, delete-orphan")
    final_result: Mapped[Optional["FinalAnalysisResult"]] = relationship("FinalAnalysisResult", back_populates="submission", uselist=False, cascade="all, delete-orphan")


class UploadedFile(Base):
    """Metadata and extracted text of files uploaded alongside defect submissions."""
    __tablename__ = "uploaded_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("bug_submissions.id", ondelete="SET NULL"), nullable=True)
    filename: Mapped[str] = mapped_column(String(255))
    safe_filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    file_size_bytes: Mapped[int] = mapped_column(Integer)
    mime_type: Mapped[str] = mapped_column(String(100), default="application/octet-stream")
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    extracted_chars: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    submission: Mapped[Optional["BugSubmission"]] = relationship("BugSubmission", back_populates="uploaded_files")


class AgentExecution(Base):
    """Audit log of each individual agent execution within the LangGraph workflow."""
    __tablename__ = "agent_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(Integer, ForeignKey("bug_submissions.id", ondelete="CASCADE"), index=True)
    agent_name: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(40), default="pending")  # pending, running, completed, failed, skipped
    execution_order: Mapped[int] = mapped_column(Integer, default=0)
    is_parallel: Mapped[bool] = mapped_column(Boolean, default=False)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    output_summary: Mapped[str] = mapped_column(Text, default="")
    raw_output_json: Mapped[str] = mapped_column(Text, default="{}")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    submission: Mapped["BugSubmission"] = relationship("BugSubmission", back_populates="agent_executions")


class TriageResult(Base):
    """Structured output of the Milestone 2 Triage Agent."""
    __tablename__ = "triage_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(Integer, ForeignKey("bug_submissions.id", ondelete="CASCADE"), unique=True)
    severity: Mapped[str] = mapped_column(String(40))  # Critical, High, Medium, Low
    priority: Mapped[str] = mapped_column(String(40))  # P1, P2, P3, P4
    affected_component: Mapped[str] = mapped_column(String(120))
    confidence: Mapped[float] = mapped_column(Float)
    reasoning: Mapped[str] = mapped_column(Text)
    evidence_json: Mapped[str] = mapped_column(Text, default="[]")
    historical_mapping_json: Mapped[str] = mapped_column(Text, default="{}")
    classification_source: Mapped[str] = mapped_column(String(60), default="deterministic_expert")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    submission: Mapped["BugSubmission"] = relationship("BugSubmission", back_populates="triage_result")


class LogAnalysisResult(Base):
    """Structured output of the Milestone 2 Log Analysis Agent."""
    __tablename__ = "log_analysis_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(Integer, ForeignKey("bug_submissions.id", ondelete="CASCADE"), unique=True)
    has_logs: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(60))  # analyzed, insufficient_log_evidence, malformed_logs
    exception_type: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    failure_point: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    line_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    chained_exceptions_json: Mapped[str] = mapped_column(Text, default="[]")
    affected_code_path_json: Mapped[str] = mapped_column(Text, default="[]")
    technical_findings_json: Mapped[str] = mapped_column(Text, default="[]")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    analysis_source: Mapped[str] = mapped_column(String(60), default="deterministic_parser")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    submission: Mapped["BugSubmission"] = relationship("BugSubmission", back_populates="log_analysis_result")


class HistoricalDefectReference(Base):
    """Traceable evidence linking a submission to retrieved historical JDT defects."""
    __tablename__ = "historical_defect_references"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(Integer, ForeignKey("bug_submissions.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[str] = mapped_column(String(80))
    product: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    component: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    similarity_score: Mapped[float] = mapped_column(Float)
    resolution: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    severity: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    priority: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    issue_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    submission: Mapped["BugSubmission"] = relationship("BugSubmission", back_populates="historical_references")


class FinalAnalysisResult(Base):
    """Consolidated diagnosis, root cause hypothesis, and remediation plan."""
    __tablename__ = "final_analysis_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(Integer, ForeignKey("bug_submissions.id", ondelete="CASCADE"), unique=True)
    root_cause_hypothesis: Mapped[str] = mapped_column(Text)
    remediation_recommendations_json: Mapped[str] = mapped_column(Text, default="[]")
    validation_steps_json: Mapped[str] = mapped_column(Text, default="[]")
    overall_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    full_result_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    submission: Mapped["BugSubmission"] = relationship("BugSubmission", back_populates="final_result")


class IngestionJob(Base):
    """Tracks background or on-demand historical dataset ingestion runs."""
    __tablename__ = "ingestion_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_uuid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    dataset_path: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="pending")  # pending, running, completed, failed, cancelled
    total_records: Mapped[int] = mapped_column(Integer, default=0)
    processed_records: Mapped[int] = mapped_column(Integer, default=0)
    indexed_records: Mapped[int] = mapped_column(Integer, default=0)
    indexed_vectors: Mapped[int] = mapped_column(Integer, default=0)
    skipped_records: Mapped[int] = mapped_column(Integer, default=0)
    failed_records: Mapped[int] = mapped_column(Integer, default=0)
    batch_size: Mapped[int] = mapped_column(Integer, default=1000)
    current_chunk: Mapped[int] = mapped_column(Integer, default=0)
    # Absolute CSV row offset.  It allows a failed job to resume safely; vector
    # point ids are deterministic too, so replaying a committed batch is safe.
    resume_offset: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class Analysis(Base):
    """Backwards-compatible legacy view of submissions and analysis results."""
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(240))
    project: Mapped[str] = mapped_column(String(120), default="Eclipse JDT")
    description: Mapped[str] = mapped_column(Text)
    logs: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="completed")
    severity: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    result_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
