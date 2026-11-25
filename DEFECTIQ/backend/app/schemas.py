from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field


# -------------------------------------------------------------------------
# Bug Submission Schemas
# -------------------------------------------------------------------------

class BugCreate(BaseModel):
    title: str = Field(min_length=4, max_length=255, description="Brief summary of the observed defect")
    project: str = Field(default="Eclipse JDT", description="Target project or ecosystem")
    component: str = Field(default="", description="Affected subsystem or component (e.g. Core, UI, Debug)")
    description: str = Field(min_length=10, description="Detailed problem description, steps to reproduce, environment")
    expected_behavior: str = Field(default="", description="What was expected to happen")
    actual_behavior: str = Field(default="", description="What actually occurred")
    logs: str = Field(default="", description="Raw console logs, stack traces, or exception messages")
    file_ids: List[int] = Field(default=[], description="IDs of previously uploaded files associated with this report")


class UploadResponse(BaseModel):
    id: int
    filename: str
    safe_filename: str
    file_size_bytes: int
    mime_type: str
    extracted_chars: int
    preview_text: str


class BugSubmissionOut(BaseModel):
    id: int
    submission_uuid: str
    title: str
    project: str
    component: str
    description: str
    logs: str
    status: str
    created_at: datetime
    file_count: int = 0


# -------------------------------------------------------------------------
# Agent Schemas (Milestone 2)
# -------------------------------------------------------------------------

class TriageOutput(BaseModel):
    severity: Literal["Critical", "High", "Medium", "Low"] = Field(description="Normalized enterprise severity level")
    priority: Literal["P1", "P2", "P3", "P4"] = Field(description="Operational priority rating")
    affected_component: str = Field(description="Predicted or verified subsystem component")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    reasoning: str = Field(description="Detailed explanation justifying severity and component assignment")
    evidence: List[str] = Field(default=[], description="Key indicators or historical matches supporting classification")
    historical_mapping: Dict[str, str] = Field(default={}, description="Mapping from historical Eclipse labels to system levels")
    classification_source: Literal["gemini_grounded", "deterministic_expert"] = Field(
        default="deterministic_expert",
        description="Engine used to generate triage decision"
    )


class LogAnalysisOutput(BaseModel):
    has_logs: bool = Field(description="Whether technical logs or stack traces were provided")
    status: Literal["analyzed", "insufficient_log_evidence", "malformed_logs"] = Field(
        description="Overall log parsing outcome"
    )
    exception_type: Optional[str] = Field(default=None, description="Primary exception or error class name")
    error_message: Optional[str] = Field(default=None, description="Detailed error message accompanying the exception")
    failure_point: Optional[str] = Field(default=None, description="Top implicated file and line number (e.g. TypeBinding.java:1681)")
    file_name: Optional[str] = Field(default=None, description="Extracted file name")
    line_number: Optional[int] = Field(default=None, description="Extracted source code line number")
    chained_exceptions: List[Dict[str, Any]] = Field(default=[], description="Nested 'Caused by:' exceptions in the stack trace")
    affected_code_path: List[str] = Field(default=[], description="Relevant package or module call stack frames")
    technical_findings: List[str] = Field(default=[], description="Specific diagnostic takeaways extracted from logs")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in log analysis findings")
    analysis_source: Literal["deterministic_parser", "gemini_enhanced", "insufficient_evidence"] = Field(
        default="deterministic_parser"
    )


class RootCauseOutput(BaseModel):
    root_cause_hypothesis: str = Field(min_length=1)
    verified_evidence: List[str] = Field(default_factory=list)
    hypotheses: List[str] = Field(default_factory=list)
    reasoning: str = Field(default="")
    affected_files: List[str] = Field(default_factory=list)
    remediation_recommendations: List[str] = Field(min_length=1)
    validation_steps: List[str] = Field(default_factory=list)
    overall_confidence: float = Field(ge=0.0, le=1.0)


class DuplicateDetectionOutput(BaseModel):
    potential_duplicate: bool = False
    is_duplicate: bool = False
    duplicate_of_id: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str
    matching_evidence: List[Dict[str, Any]] = Field(default_factory=list)


class RemediationOutput(BaseModel):
    recommendations: List[str] = Field(min_length=1)
    validation_steps: List[str] = Field(default_factory=list)
    reasoning: str = Field(default="")
    affected_components_or_files: List[str] = Field(default_factory=list)
    source: str = Field(default="deterministic_expert")


class HistoricalMatch(BaseModel):
    source_id: str
    product: Optional[str] = "JDT"
    component: Optional[str] = None
    summary: str
    similarity_score: float
    resolution: Optional[str] = None
    severity: Optional[str] = None
    priority: Optional[str] = None
    is_duplicate: bool = False
    issue_url: Optional[str] = None


class AgentExecutionOut(BaseModel):
    agent_name: str
    status: str
    execution_order: int
    is_parallel: bool
    duration_ms: float
    output_summary: str
    error_message: Optional[str] = None


class AnalysisDetailOut(BaseModel):
    id: int
    submission_uuid: str
    title: str
    project: str
    component: str
    description: str
    logs: str
    status: str
    severity: Optional[str] = None
    priority: Optional[str] = None
    confidence: Optional[float] = None
    triage: Optional[TriageOutput] = None
    log_analysis: Optional[LogAnalysisOutput] = None
    historical_matches: List[HistoricalMatch] = []
    root_cause_hypothesis: Optional[str] = None
    remediation_recommendations: List[str] = []
    validation_steps: List[str] = []
    agent_executions: List[AgentExecutionOut] = []
    created_at: datetime


class AnalysisSummaryOut(BaseModel):
    id: int
    title: str
    status: str
    severity: Optional[str] = None
    category: Optional[str] = None
    confidence: Optional[float] = None
    created_at: Optional[str] = None


# -------------------------------------------------------------------------
# Knowledge Base & Ingestion Schemas
# -------------------------------------------------------------------------

class SearchRequest(BaseModel):
    query: str = Field(min_length=2, description="Natural language bug description or error query")
    limit: int = Field(default=8, ge=1, le=30, description="Number of historical matches to retrieve")
    component: Optional[str] = Field(default=None, description="Optional component filter (e.g. Core, UI, Debug)")
    min_score: float = Field(default=0.25, ge=0.0, le=1.0, description="Minimum cosine similarity threshold")


class IngestRequest(BaseModel):
    path: Optional[str] = Field(default=None, description="Dataset CSV path. Defaults to configured DATASET_PATH.")
    limit: Optional[int] = Field(default=None, ge=1, description="Optional cap on records to ingest (for testing/partial runs)")
    batch_size: int = Field(default=500, ge=50, le=2000, description="Chunk size for memory-efficient processing")
    resume_job_id: Optional[int] = Field(default=None, description="Failed ingestion job to resume safely")


class IngestJobStatus(BaseModel):
    job_uuid: str
    dataset_path: str
    status: str
    total_records: int
    processed_records: int
    indexed_records: int
    indexed_vectors: int = 0
    skipped_records: int = 0
    failed_records: int
    current_chunk: int
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None


class KBStats(BaseModel):
    indexed_defects: int
    collection_name: str
    embedding_model: str
    dataset_configured: bool
    dataset_valid: bool
    dataset_metadata: Dict[str, Any]
