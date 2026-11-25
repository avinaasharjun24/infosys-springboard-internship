import io
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure backend directory is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app

client = TestClient(app)


def test_health_check():
    print("\n[TEST] Starting test_health_check...", flush=True)
    response = client.get("/api/health")
    print(f"[TEST] Health response: {response.status_code}", flush=True)
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "defectiq-backend"
    assert "database" in data
    assert "qdrant" in data


def test_overview():
    print("\n[TEST] Starting test_overview...", flush=True)
    response = client.get("/api/overview")
    print(f"[TEST] Overview response: {response.status_code}", flush=True)
    assert response.status_code == 200
    data = response.json()
    assert "total_submissions" in data
    assert "severity_distribution" in data


def test_file_upload():
    print("\n[TEST] Starting test_file_upload...", flush=True)
    sample_content = b"java.lang.NullPointerException: null\n\tat org.eclipse.jdt.internal.compiler.lookup.SourceTypeBinding.resolveTypesFor(SourceTypeBinding.java:1770)"
    file_payload = {"file": ("crash.log", io.BytesIO(sample_content), "text/plain")}
    response = client.post("/api/uploads", files=file_payload)
    print(f"[TEST] Upload response: {response.status_code}", flush=True)
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "crash.log"
    assert data["extracted_chars"] > 0
    return data["id"]


def test_bug_submission_and_parallel_workflow():
    print("\n[TEST] Starting test_bug_submission_and_parallel_workflow...", flush=True)
    upload_id = test_file_upload()

    # 1. Submit defect
    bug_payload = {
        "title": "Compiler crashes with NPE when compiling generic inner classes",
        "project": "Eclipse JDT",
        "component": "Core",
        "description": "When building project with JDK 8 features, the batch compiler fails unexpectedly.",
        "expected_behavior": "Compilation succeeds or produces a compiler error.",
        "actual_behavior": "NullPointerException thrown in compiler lookup.",
        "logs": "java.lang.NullPointerException: null\n\tat org.eclipse.jdt.internal.compiler.lookup.SourceTypeBinding.resolveTypesFor(SourceTypeBinding.java:1770)",
        "file_ids": [upload_id]
    }
    sub_response = client.post("/api/bugs", json=bug_payload)
    assert sub_response.status_code == 200
    sub_data = sub_response.json()
    sub_id = sub_data["id"]
    assert sub_data["status"] == "submitted"
    print(f"[TEST] Created submission #{sub_id}", flush=True)

    # 2. Trigger multi-agent parallel workflow
    print(f"[TEST] Invoking workflow on #{sub_id}...", flush=True)
    run_response = client.post(f"/api/analyses/{sub_id}/run")
    print(f"[TEST] Workflow execution response: {run_response.status_code}", flush=True)
    assert run_response.status_code == 200
    analysis = run_response.json()

    assert analysis["id"] == sub_id
    assert analysis["status"] in ["completed", "partial"]

    # Verify Triage Agent output
    triage = analysis["triage"]
    assert triage is not None
    assert triage["severity"] in ["Critical", "High", "Medium", "Low"]
    assert triage["priority"] in ["P1", "P2", "P3", "P4"]
    assert triage["affected_component"] in ["Core", "UI", "Debug", "Text", "APT"]
    assert 0.0 <= triage["confidence"] <= 1.0
    assert len(triage["reasoning"]) > 0

    # Verify Log Analysis Agent output
    log_out = analysis["log_analysis"]
    assert log_out is not None
    assert log_out["has_logs"] is True
    assert log_out["exception_type"] == "java.lang.NullPointerException"
    assert "SourceTypeBinding.java:1770" in (log_out["failure_point"] or "")

    # Verify Agent Execution Audit
    agents_res = client.get(f"/api/submissions/{sub_id}/agents")
    assert agents_res.status_code == 200
    agent_execs = agents_res.json()
    assert len(agent_execs) >= 5

    parallel_agents = [a for a in agent_execs if a["is_parallel"]]
    assert len(parallel_agents) == 2  # Triage Agent and Log Analysis Agent

    # Verify Detail Endpoint
    detail_res = client.get(f"/api/submissions/{sub_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["title"] == bug_payload["title"]
    print("[TEST] Bug submission and parallel workflow test passed!", flush=True)


def test_missing_logs_behavior():
    print("\n[TEST] Starting test_missing_logs_behavior...", flush=True)
    bug_payload = {
        "title": "Minor typo in documentation of Java editor preference page",
        "description": "Under Preferences > Java > Editor, there is a spelling mistake in the description label.",
        "component": "UI",
        "logs": ""
    }
    sub_response = client.post("/api/bugs", json=bug_payload)
    sub_id = sub_response.json()["id"]

    run_response = client.post(f"/api/analyses/{sub_id}/run")
    assert run_response.status_code == 200
    analysis = run_response.json()

    # Severity should be Low
    assert analysis["triage"]["severity"] == "Low"
    # Log analysis should indicate insufficient_log_evidence
    assert analysis["log_analysis"]["has_logs"] is False
    assert analysis["log_analysis"]["status"] == "insufficient_log_evidence"
    assert analysis["log_analysis"]["exception_type"] is None
    print("[TEST] Missing logs behavior test passed!", flush=True)


if __name__ == "__main__":
    test_health_check()
    test_overview()
    test_file_upload()
    test_bug_submission_and_parallel_workflow()
    test_missing_logs_behavior()
    print("ALL API AND AGENT INTEGRATION TESTS PASSED!")
