"""
Legacy agents module interface.
Redirects to the upgraded multi-agent parallel LangGraph workflow orchestrator.
"""
from typing import Dict, Any
from .orchestrator import defectiq_workflow, DefectWorkflowState, build_workflow_graph


def run_analysis(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the multi-agent defect intelligence workflow on a payload."""
    initial_state: DefectWorkflowState = {
        "title": payload.get("title", ""),
        "description": payload.get("description", ""),
        "expected_behavior": payload.get("expected_behavior", ""),
        "actual_behavior": payload.get("actual_behavior", ""),
        "logs": payload.get("logs", ""),
        "component": payload.get("component", ""),
        "project": payload.get("project", "Eclipse JDT"),
        "agent_executions": [],
        "errors": []
    }
    final_state = defectiq_workflow.invoke(initial_state)
    return final_state
