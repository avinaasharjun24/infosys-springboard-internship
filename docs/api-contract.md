# API Contract — Proposed for Implementation

Base path: `/api/v1`

## `POST /bugs`

Accept a pasted bug report.

Example request:

```json
{
  "title": "Application fails during startup",
  "description": "The service exits immediately after initialization.",
  "steps_to_reproduce": ["Install dependencies", "Start the service"],
  "expected_behavior": "The service starts successfully.",
  "actual_behavior": "The process exits with an exception.",
  "stack_trace": "Optional stack trace text",
  "logs": "Optional log text",
  "environment": {
    "os": "Ubuntu",
    "runtime": "Python 3.x",
    "version": "Application version"
  }
}
```

Expected response: submission identifier and initial processing status.

## `POST /bugs/upload`

Accept multipart form data containing a report/log file and optional metadata fields.

Initial supported formats proposed: `.txt`, `.log`, `.md`, `.pdf`, `.docx`.

The implementation must validate file content, not just extension. Exact size limits will be configured in the backend.

## `GET /bugs/{bug_id}`

Return stored submission metadata and current processing status.

## `GET /bugs/{bug_id}/analysis`

Return the analysis result when completed, including:
- Triage findings
- Log analysis
- Retrieved historical defect references
- Duplicate assessment
- Root-cause hypotheses
- Remediation recommendations
- Warnings and uncertainty indicators

## `GET /health`

Return service health. A production-grade health check should distinguish API process health from database/vector-store dependency health.

> These are proposed endpoint contracts, not claims that the endpoints are already implemented.
