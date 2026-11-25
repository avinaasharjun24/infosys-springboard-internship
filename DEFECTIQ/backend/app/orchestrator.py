import json
import logging
import operator
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

from .triage_agent import triage_agent
from .log_agent import log_analysis_agent
from .knowledge import get_kb
from .gemini_service import gemini_service
from .schemas import DuplicateDetectionOutput, RemediationOutput
from .models import (
    BugSubmission,
    AgentExecution,
    TriageResult,
    LogAnalysisResult,
    HistoricalDefectReference,
    FinalAnalysisResult,
    Analysis
)

logger = logging.getLogger("defectiq.orchestrator")


class DefectWorkflowState(TypedDict, total=False):
    submission_id: Optional[int]
    title: str
    project: str
    component: str
    description: str
    expected_behavior: str
    actual_behavior: str
    logs: str
    normalized_text: str
    triage: Dict[str, Any]
    log_analysis: Dict[str, Any]
    historical_matches: List[Dict[str, Any]]
    duplicate_analysis: Dict[str, Any]
    root_cause: Dict[str, Any]
    remediation: Dict[str, Any]
    ai_remediation: Dict[str, Any]
    agent_executions: Annotated[List[Dict[str, Any]], operator.add]
    errors: Annotated[List[str], operator.add]
    status: str


# -------------------------------------------------------------------------
# Workflow Node Implementations
# -------------------------------------------------------------------------

def normalize_input_node(state: DefectWorkflowState) -> Dict[str, Any]:
    """Step 1: Sanitize and normalize defect text and technical evidence."""
    t0 = time.perf_counter()
    title = (state.get("title") or "").strip()
    desc = (state.get("description") or "").strip()
    exp = (state.get("expected_behavior") or "").strip()
    act = (state.get("actual_behavior") or "").strip()
    logs = (state.get("logs") or "").strip()

    normalized = f"{title}\n{desc}"
    if exp:
        normalized += f"\nExpected: {exp}"
    if act:
        normalized += f"\nActual: {act}"

    duration_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "normalized_text": normalized,
        "agent_executions": [{
            "agent_name": "input_normalization",
            "status": "completed",
            "execution_order": 1,
            "is_parallel": False,
            "duration_ms": duration_ms,
            "output_summary": f"Normalized defect input ({len(normalized)} chars). Logs present: {bool(logs)}.",
            "raw_output_json": json.dumps({"normalized_chars": len(normalized), "has_logs": bool(logs)})
        }]
    }


def triage_node(state: DefectWorkflowState) -> Dict[str, Any]:
    """Step 2A (Parallel): Triage Agent identifies severity, priority, component."""
    t0 = time.perf_counter()
    try:
        triage_out = triage_agent.classify(
            title=state.get("title", ""),
            description=state.get("description", ""),
            logs=state.get("logs", ""),
            component=state.get("component", ""),
            historical_matches=state.get("historical_matches", [])
        )
        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        triage_dict = triage_out.model_dump()
        return {
            "triage": triage_dict,
            "agent_executions": [{
                "agent_name": "triage_agent",
                "status": "completed",
                "execution_order": 2,
                "is_parallel": True,
                "duration_ms": duration_ms,
                "output_summary": f"Severity: {triage_out.severity} | Priority: {triage_out.priority} | Component: {triage_out.affected_component} (Conf: {triage_out.confidence:.2f})",
                "raw_output_json": json.dumps(triage_dict)
            }]
        }
    except Exception as exc:
        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        logger.error(f"Triage agent node failed: {exc}")
        return {
            "errors": [f"Triage Agent error: {exc}"],
            "agent_executions": [{
                "agent_name": "triage_agent",
                "status": "failed",
                "execution_order": 2,
                "is_parallel": True,
                "duration_ms": duration_ms,
                "output_summary": "Triage Agent execution encountered an error.",
                "error_message": str(exc),
                "raw_output_json": "{}"
            }]
        }


def log_analysis_node(state: DefectWorkflowState) -> Dict[str, Any]:
    """Step 2B (Parallel): Log Analysis Agent examines stack traces and error messages."""
    t0 = time.perf_counter()
    try:
        log_out = log_analysis_agent.analyze(
            logs=state.get("logs", ""),
            title=state.get("title", ""),
            description=state.get("description", "")
        )
        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        log_dict = log_out.model_dump()
        summary = (
            f"Exception: {log_out.exception_type or 'None'} | Failure: {log_out.failure_point or 'N/A'}"
            if log_out.has_logs else "No log content provided (insufficient_log_evidence)."
        )
        return {
            "log_analysis": log_dict,
            "agent_executions": [{
                "agent_name": "log_analysis_agent",
                "status": "completed",
                "execution_order": 2,
                "is_parallel": True,
                "duration_ms": duration_ms,
                "output_summary": summary,
                "raw_output_json": json.dumps(log_dict)
            }]
        }
    except Exception as exc:
        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        logger.error(f"Log analysis node failed: {exc}")
        return {
            "errors": [f"Log Analysis Agent error: {exc}"],
            "agent_executions": [{
                "agent_name": "log_analysis_agent",
                "status": "failed",
                "execution_order": 2,
                "is_parallel": True,
                "duration_ms": duration_ms,
                "output_summary": "Log Analysis Agent execution failed.",
                "error_message": str(exc),
                "raw_output_json": "{}"
            }]
        }


def merge_outputs_node(state: DefectWorkflowState) -> Dict[str, Any]:
    """Step 3: Synchronize and safely merge parallel triage and log findings."""
    t0 = time.perf_counter()
    triage = state.get("triage", {})
    logs = state.get("log_analysis", {})

    merged_summary = (
        f"Merged: Component={triage.get('affected_component', 'Unknown')} | "
        f"Severity={triage.get('severity', 'Medium')} | "
        f"Exception={logs.get('exception_type', 'None')}"
    )
    duration_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "agent_executions": [{
            "agent_name": "structured_output_merge",
            "status": "completed",
            "execution_order": 3,
            "is_parallel": False,
            "duration_ms": duration_ms,
            "output_summary": merged_summary,
            "raw_output_json": json.dumps({"merged": True})
        }]
    }


def historical_retrieval_node(state: DefectWorkflowState) -> Dict[str, Any]:
    """Step 4: Retrieve historical defects from Qdrant vector store with RAG."""
    t0 = time.perf_counter()
    title = state.get("title", "")
    desc = state.get("description", "")
    triage = state.get("triage", {})
    log_analysis = state.get("log_analysis", {})

    # Construct rich technical query containing exception type & failure point
    query_parts = [title]
    if desc:
        query_parts.append(desc[:300])
    if log_analysis.get("exception_type"):
        query_parts.append(f"exception: {log_analysis['exception_type']}")
    if log_analysis.get("failure_point"):
        query_parts.append(f"failure: {log_analysis['failure_point']}")

    full_query = " ".join(query_parts)
    component = triage.get("affected_component")

    matches = []
    try:
        kb = get_kb()
        matches = kb.search(query=full_query, limit=6, component=component)
        if not matches and component:
            # Fallback search without component filter if no hits returned
            matches = kb.search(query=full_query, limit=6, component=None)
    except Exception as exc:
        logger.warning(f"RAG retrieval node error: {exc}")

    duration_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "historical_matches": matches,
        "agent_executions": [{
            "agent_name": "historical_retrieval",
            "status": "completed",
            "execution_order": 4,
            "is_parallel": False,
            "duration_ms": duration_ms,
            "output_summary": f"Retrieved {len(matches)} historical defects from Eclipse JDT knowledge base.",
            "raw_output_json": json.dumps({"count": len(matches), "top_matches": [m.get("source_id") for m in matches[:3]]})
        }]
    }


def duplicate_detection_node(state: DefectWorkflowState) -> Dict[str, Any]:
    """Step 5: Evaluate potential duplicate defects from historical matches without treating similarity as proof."""
    t0 = time.perf_counter()
    matches = state.get("historical_matches", [])
    matching_evidence = [
        {
            "source_id": str(m.get("source_id")),
            "similarity_score": round(float(m.get("similarity_score", 0.0)), 4),
            "summary": m.get("summary", ""),
            "component": m.get("component"),
            "resolution": m.get("resolution"),
            "dupe_of": m.get("dupe_of"),
        }
        for m in matches[:5]
    ]

    potential_dup = False
    dup_id = None
    top_sim = 0.0
    reason = "No high-similarity historical defect candidates found."

    if matches:
        top = matches[0]
        top_sim = round(float(top.get("similarity_score", 0.0)), 4)
        if top_sim >= 0.80:
            potential_dup = True
            dup_id = str(top.get("source_id"))
            reason = (
                f"High semantic similarity ({top_sim * 100:.1f}%) with historical issue JDT-{dup_id}: "
                f"'{top.get('summary')}'. Similarity is supporting evidence only, not proof of duplication."
            )
        elif top.get("is_duplicate") and top.get("dupe_of"):
            dup_id = str(top.get("dupe_of"))
            reason = (
                f"Closest historical match JDT-{top.get('source_id')} ({top_sim * 100:.1f}% similarity) "
                f"is linked as a duplicate of JDT-{dup_id}. Manual verification is required."
            )
        else:
            reason = (
                f"Top historical match JDT-{top.get('source_id')} has {top_sim * 100:.1f}% semantic similarity "
                "(below high-confidence duplicate threshold; presented as supporting context only)."
            )

    duplicate_out = DuplicateDetectionOutput(
        potential_duplicate=potential_dup,
        is_duplicate=False,  # Never assert similarity alone as proof of duplication
        duplicate_of_id=dup_id,
        confidence=top_sim,
        reason=reason,
        matching_evidence=matching_evidence,
    ).model_dump()

    duration_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "duplicate_analysis": duplicate_out,
        "agent_executions": [{
            "agent_name": "duplicate_detection",
            "status": "completed",
            "execution_order": 5,
            "is_parallel": False,
            "duration_ms": duration_ms,
            "output_summary": duplicate_out["reason"],
            "raw_output_json": json.dumps(duplicate_out)
        }]
    }


def root_cause_node(state: DefectWorkflowState) -> Dict[str, Any]:
    """Step 6: Synthesize evidence-backed root cause hypothesis, separating verified evidence from hypotheses."""
    t0 = time.perf_counter()
    title = state.get("title", "")
    desc = state.get("description", "")
    triage = state.get("triage", {})
    logs = state.get("log_analysis", {})
    matches = state.get("historical_matches", [])

    verified_evidence: List[str] = []
    if triage.get("affected_component"):
        verified_evidence.append(
            f"Triage classification: {triage.get('severity', 'Unknown')} severity in {triage.get('affected_component')} component."
        )
    if logs.get("exception_type"):
        verified_evidence.append(f"Observed exception in logs: {logs['exception_type']}")
    if logs.get("failure_point"):
        verified_evidence.append(f"Top stack trace failure point: {logs['failure_point']}")
    for m in matches[:3]:
        verified_evidence.append(
            f"Historical precedent JDT-{m.get('source_id')} ({round(float(m.get('similarity_score', 0)) * 100, 1)}% similarity): {m.get('summary')}"
        )

    # If Gemini is configured, use grounded AI synthesis
    if gemini_service.is_configured:
        ai_res = gemini_service.synthesize_root_cause_and_remediation(
            title=title,
            description=desc,
            triage=triage,
            log_analysis=logs,
            historical_evidence=matches
        )
        if ai_res and ai_res.get("root_cause_hypothesis"):
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            rc_payload = {
                "hypothesis": ai_res["root_cause_hypothesis"],
                "verified_evidence": ai_res.get("verified_evidence") or verified_evidence,
                "hypotheses": ai_res.get("hypotheses") or [ai_res["root_cause_hypothesis"]],
                "reasoning": ai_res.get("reasoning") or "Synthesized from triage, log analysis, and historical precedents.",
                "confidence": float(ai_res.get("overall_confidence", 0.85)),
                "evidence": verified_evidence,
            }
            return {
                "root_cause": rc_payload,
                "ai_remediation": {
                    "recommendations": ai_res.get("remediation_recommendations", []),
                    "validation_steps": ai_res.get("validation_steps", []),
                    "affected_files": ai_res.get("affected_files", []),
                    "reasoning": ai_res.get("reasoning", ""),
                },
                "agent_executions": [{
                    "agent_name": "root_cause_agent",
                    "status": "completed",
                    "execution_order": 6,
                    "is_parallel": False,
                    "duration_ms": duration_ms,
                    "output_summary": ai_res["root_cause_hypothesis"][:140] + "...",
                    "raw_output_json": json.dumps(rc_payload)
                }]
            }

    # Deterministic Expert Synthesis
    hypotheses: List[str] = []
    if logs.get("failure_point") and logs.get("exception_type"):
        hypothesis = (
            f"Hypothesis: The defect likely originates from an unhandled {logs['exception_type']} triggered at {logs['failure_point']}. "
            f"A null reference or state invariant violation may have occurred in {triage.get('affected_component', 'Core')}."
        )
        hypotheses.append(hypothesis)
        reasoning = (
            f"Derived directly from stack trace exception {logs['exception_type']} at {logs['failure_point']} "
            f"combined with {triage.get('affected_component', 'Core')} component triage."
        )
    elif matches:
        top = matches[0]
        hypothesis = (
            f"Hypothesis: Observed symptoms correlate with historical issue JDT-{top.get('source_id')} "
            f"({top.get('summary')}, Resolution: {top.get('resolution') or 'Unresolved'}). "
            f"Inspect {triage.get('affected_component', 'Core')} for a similar underlying logic defect."
        )
        hypotheses.append(hypothesis)
        reasoning = (
            f"No stack trace failure frame was available; hypothesis is inferred from top semantic match "
            f"JDT-{top.get('source_id')} ({round(float(top.get('similarity_score', 0)) * 100, 1)}% similarity)."
        )
    else:
        hypothesis = (
            f"Hypothesis: Defect classified as {triage.get('severity', 'Medium')} severity in {triage.get('affected_component', 'Core')}. "
            "Insufficient stack trace or historical matches to formulate an isolated code-level hypothesis."
        )
        hypotheses.append(hypothesis)
        reasoning = "Neither stack trace frames nor high-confidence historical matches were available; confidence is reduced."

    duration_ms = round((time.perf_counter() - t0) * 1000, 2)
    rc_result = {
        "hypothesis": hypothesis,
        "verified_evidence": verified_evidence,
        "hypotheses": hypotheses,
        "reasoning": reasoning,
        "confidence": 0.82 if logs.get("failure_point") else (0.68 if matches else 0.50),
        "evidence": verified_evidence,
    }
    return {
        "root_cause": rc_result,
        "agent_executions": [{
            "agent_name": "root_cause_agent",
            "status": "completed",
            "execution_order": 6,
            "is_parallel": False,
            "duration_ms": duration_ms,
            "output_summary": hypothesis[:140] + "...",
            "raw_output_json": json.dumps(rc_result)
        }]
    }


def remediation_node(state: DefectWorkflowState) -> Dict[str, Any]:
    """Step 7: Formulate practical remediation recommendations without modifying any repository."""
    t0 = time.perf_counter()
    triage = state.get("triage", {})
    logs = state.get("log_analysis", {})
    matches = state.get("historical_matches", [])
    ai_rem = state.get("ai_remediation", {})

    affected_files: List[str] = []
    if logs.get("file_name"):
        loc = f"{logs['file_name']}:{logs['line_number']}" if logs.get("line_number") else logs["file_name"]
        affected_files.append(loc)
    elif logs.get("failure_point"):
        affected_files.append(logs["failure_point"])
    for f in ai_rem.get("affected_files", []):
        if f and f not in affected_files:
            affected_files.append(f)
    if not affected_files and triage.get("affected_component"):
        affected_files.append(f"Component: {triage['affected_component']}")

    if ai_rem.get("recommendations"):
        rem_out = RemediationOutput(
            recommendations=ai_rem["recommendations"],
            validation_steps=ai_rem.get("validation_steps") or [
                "Create an isolated regression test reproducing the failure scenario.",
                f"Run unit test suite for affected component ({triage.get('affected_component', 'Core')}).",
            ],
            reasoning=ai_rem.get("reasoning") or "Recommendations grounded in Gemini synthesis, triage, log trace, and historical precedents.",
            affected_components_or_files=affected_files,
            source="gemini_grounded",
        ).model_dump()
    else:
        recommendations = []
        validation_steps = [
            "Create an isolated regression test reproducing the failure scenario.",
            f"Run unit test suite for affected component ({triage.get('affected_component', 'Core')}).",
            "Verify system behavior under edge conditions (null inputs, empty AST nodes, concurrent threads)."
        ]

        fixed_matches = [m for m in matches if m.get("resolution") == "FIXED"]
        for m in fixed_matches[:2]:
            recommendations.append(
                f"Review historical resolution pattern in JDT-{m.get('source_id')}: '{m.get('summary')}'."
            )

        if logs.get("failure_point"):
            recommendations.append(
                f"Add defensive null-check and state validation guarding execution at {logs['failure_point']}."
            )
        else:
            recommendations.append(
                f"Review recent changes touching {triage.get('affected_component', 'Core')} and add input/state guards."
            )

        recommendations.append(
            "Ensure explicit exception handling or fallback state rather than allowing unhandled propagation."
        )

        rem_out = RemediationOutput(
            recommendations=recommendations,
            validation_steps=validation_steps,
            reasoning=(
                f"Derived from {len(fixed_matches)} historical FIXED matches, "
                f"log failure point ({logs.get('failure_point') or 'none'}), and {triage.get('affected_component', 'Core')} triage."
            ),
            affected_components_or_files=affected_files,
            source="deterministic_expert",
        ).model_dump()

    duration_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "remediation": rem_out,
        "agent_executions": [{
            "agent_name": "remediation_agent",
            "status": "completed",
            "execution_order": 7,
            "is_parallel": False,
            "duration_ms": duration_ms,
            "output_summary": f"Generated {len(rem_out['recommendations'])} recommendations and {len(rem_out['validation_steps'])} validation steps.",
            "raw_output_json": json.dumps(rem_out)
        }]
    }


# -------------------------------------------------------------------------
# LangGraph Workflow Construction
# -------------------------------------------------------------------------

def build_workflow_graph():
    """
    Construct the intended multi-agent LangGraph workflow:
    Input Normalization -> Parallel [Triage Agent || Log Analysis Agent] ->
    Merge Outputs -> Historical Defect Retrieval -> Duplicate Detection ->
    Root Cause -> Remediation -> END
    """
    graph = StateGraph(DefectWorkflowState)

    # Register all nodes
    graph.add_node("normalize_input", normalize_input_node)
    graph.add_node("triage", triage_node)
    graph.add_node("log_analysis", log_analysis_node)
    graph.add_node("merge_outputs", merge_outputs_node)
    graph.add_node("historical_retrieval", historical_retrieval_node)
    graph.add_node("duplicate_detection", duplicate_detection_node)
    graph.add_node("root_cause", root_cause_node)
    graph.add_node("remediation", remediation_node)

    # Set Entry Point
    graph.set_entry_point("normalize_input")

    # Parallel Fan-Out: normalize_input triggers BOTH triage and log_analysis concurrently
    graph.add_edge("normalize_input", "triage")
    graph.add_edge("normalize_input", "log_analysis")

    # Parallel Fan-In: Both triage and log_analysis converge into merge_outputs
    graph.add_edge("triage", "merge_outputs")
    graph.add_edge("log_analysis", "merge_outputs")

    # Sequential Downstream Pipeline
    graph.add_edge("merge_outputs", "historical_retrieval")
    graph.add_edge("historical_retrieval", "duplicate_detection")
    graph.add_edge("duplicate_detection", "root_cause")
    graph.add_edge("root_cause", "remediation")
    graph.add_edge("remediation", END)

    return graph.compile()


# Compiled LangGraph Workflow singleton
defectiq_workflow = build_workflow_graph()


# -------------------------------------------------------------------------
# Execution & Persistence Engine
# -------------------------------------------------------------------------

def execute_and_persist_workflow(
    submission: BugSubmission,
    db: Session
) -> Dict[str, Any]:
    """Execute LangGraph workflow, persist all intermediate agent executions and structured results."""
    submission.status = "processing"
    db.commit()

    initial_state: DefectWorkflowState = {
        "submission_id": submission.id,
        "title": submission.title,
        "project": submission.project,
        "component": submission.component,
        "description": submission.description,
        "expected_behavior": submission.expected_behavior,
        "actual_behavior": submission.actual_behavior,
        "logs": submission.raw_logs,
        "agent_executions": [],
        "errors": [],
    }

    try:
        final_state = defectiq_workflow.invoke(initial_state)

        # Clear any prior analysis rows so re-running analysis is idempotent
        db.query(AgentExecution).filter(AgentExecution.submission_id == submission.id).delete()
        db.query(TriageResult).filter(TriageResult.submission_id == submission.id).delete()
        db.query(LogAnalysisResult).filter(LogAnalysisResult.submission_id == submission.id).delete()
        db.query(HistoricalDefectReference).filter(HistoricalDefectReference.submission_id == submission.id).delete()
        db.query(FinalAnalysisResult).filter(FinalAnalysisResult.submission_id == submission.id).delete()
        db.flush()

        # 1. Persist Agent Executions
        for exec_data in final_state.get("agent_executions", []):
            agent_exec = AgentExecution(
                submission_id=submission.id,
                agent_name=exec_data["agent_name"],
                status=exec_data["status"],
                execution_order=exec_data["execution_order"],
                is_parallel=exec_data["is_parallel"],
                duration_ms=exec_data["duration_ms"],
                output_summary=exec_data.get("output_summary", ""),
                raw_output_json=exec_data.get("raw_output_json", "{}"),
                error_message=exec_data.get("error_message")
            )
            db.add(agent_exec)

        # 2. Persist Triage Result
        triage_data = final_state.get("triage")
        if triage_data:
            triage_record = TriageResult(
                submission_id=submission.id,
                severity=triage_data["severity"],
                priority=triage_data["priority"],
                affected_component=triage_data["affected_component"],
                confidence=triage_data["confidence"],
                reasoning=triage_data["reasoning"],
                evidence_json=json.dumps(triage_data.get("evidence", [])),
                historical_mapping_json=json.dumps(triage_data.get("historical_mapping", {})),
                classification_source=triage_data.get("classification_source", "deterministic_expert")
            )
            db.add(triage_record)

        # 3. Persist Log Analysis Result
        log_data = final_state.get("log_analysis")
        if log_data:
            log_record = LogAnalysisResult(
                submission_id=submission.id,
                has_logs=log_data["has_logs"],
                status=log_data["status"],
                exception_type=log_data.get("exception_type"),
                error_message=log_data.get("error_message"),
                failure_point=log_data.get("failure_point"),
                file_name=log_data.get("file_name"),
                line_number=log_data.get("line_number"),
                chained_exceptions_json=json.dumps(log_data.get("chained_exceptions", [])),
                affected_code_path_json=json.dumps(log_data.get("affected_code_path", [])),
                technical_findings_json=json.dumps(log_data.get("technical_findings", [])),
                confidence=log_data.get("confidence", 0.0),
                analysis_source=log_data.get("analysis_source", "deterministic_parser")
            )
            db.add(log_record)

        # 4. Persist Historical Defect References
        matches = final_state.get("historical_matches", [])
        for match in matches:
            ref = HistoricalDefectReference(
                submission_id=submission.id,
                source_id=str(match["source_id"]),
                product=match.get("product"),
                component=match.get("component"),
                summary=match.get("summary", ""),
                similarity_score=match.get("similarity_score", 0.0),
                resolution=match.get("resolution"),
                severity=match.get("severity"),
                priority=match.get("priority"),
                is_duplicate=match.get("is_duplicate", False),
                issue_url=match.get("issue_url")
            )
            db.add(ref)

        # 5. Persist Final Consolidated Analysis Result
        rc = final_state.get("root_cause", {})
        rem = final_state.get("remediation", {})
        final_record = FinalAnalysisResult(
            submission_id=submission.id,
            root_cause_hypothesis=rc.get("hypothesis", ""),
            remediation_recommendations_json=json.dumps(rem.get("recommendations", [])),
            validation_steps_json=json.dumps(rem.get("validation_steps", [])),
            overall_confidence=rc.get("confidence", 0.80),
            full_result_json=json.dumps(final_state, default=str)
        )
        db.add(final_record)

        # Update submission status
        has_errors = bool(final_state.get("errors"))
        submission.status = "partial" if has_errors else "completed"

        # Sync with legacy Analysis table for backwards compatibility
        legacy_analysis = db.query(Analysis).filter(Analysis.id == submission.id).first()
        if not legacy_analysis:
            legacy_analysis = Analysis(id=submission.id, title=submission.title, project=submission.project, description=submission.description, logs=submission.raw_logs)
            db.add(legacy_analysis)
        legacy_analysis.status = submission.status
        legacy_analysis.severity = triage_data.get("severity") if triage_data else None
        legacy_analysis.category = triage_data.get("affected_component") if triage_data else None
        legacy_analysis.confidence = triage_data.get("confidence") if triage_data else None
        legacy_analysis.result_json = json.dumps(final_state, default=str)

        db.commit()
        return final_state

    except Exception as exc:
        logger.error(f"Workflow execution failure for submission #{submission.id}: {exc}")
        submission.status = "failed"
        db.commit()
        raise
