import json
import logging
import re
from typing import Optional, Dict, Any, List
from .config import settings
from .schemas import TriageOutput, LogAnalysisOutput, RootCauseOutput

logger = logging.getLogger("defectiq.gemini")

JSON_BLOCK_REGEX = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```")


class GeminiService:
    """Wrapper around Google Gemini API using google-genai SDK with graceful fallback."""

    def __init__(self):
        self._client = None
        self._initialized = False

    @property
    def is_configured(self) -> bool:
        return bool(settings.gemini_api_key and settings.gemini_api_key.strip())

    def _get_client(self):
        if not self.is_configured:
            return None
        if self._client is None and not self._initialized:
            try:
                from google import genai
                from google.genai import types
                self._client = genai.Client(
                    api_key=settings.gemini_api_key.strip(),
                    http_options=types.HttpOptions(timeout=30000),
                )
                self._initialized = True
                logger.info(f"Gemini client initialized with model: {settings.gemini_model}")
            except Exception as exc:
                logger.warning("Failed to initialize Gemini client (%s)", type(exc).__name__)
                self._client = None
                self._initialized = True
        return self._client

    def connectivity_check(self) -> Dict[str, Any]:
        """Perform one explicit, low-token API capability request when asked.

        This is intentionally never called on startup or during ingestion.
        """
        client = self._get_client()
        if not client:
            return {"configured": False, "connected": False, "message": "GEMINI_API_KEY is not configured."}
        try:
            # Listing models validates credentials without sending defect data.
            models = client.models.list(config={"page_size": 100})
            names = [getattr(item, "name", "") for item in models]
            supported = any(name.endswith(settings.gemini_model) or name == settings.gemini_model for name in names)
            return {"configured": True, "connected": True, "model": settings.gemini_model, "model_available": supported}
        except Exception as exc:
            logger.warning("Gemini connectivity check failed: %s", type(exc).__name__)
            return {"configured": True, "connected": False, "model": settings.gemini_model, "message": "Gemini verification request failed. Check the local key, model access, quota, and network."}

    def _generate_json(self, prompt: str, max_output_tokens: int = 700) -> Optional[Dict[str, Any]]:
        client = self._get_client()
        if not client:
            return None
        try:
            from google.genai import types
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json", temperature=0.1,
                    max_output_tokens=max_output_tokens,
                ),
            )
            return self._clean_json_response(response.text)
        except Exception as exc:
            # Never log prompts or secrets. Authentication, quota and timeout
            # failures are intentionally reduced to an operational warning.
            logger.warning("Gemini request failed (%s): %s", type(exc).__name__, str(exc)[:200])
            return None

    def _clean_json_response(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract and parse structured JSON from model output."""
        if not text:
            return None
        # Try finding markdown code block
        match = JSON_BLOCK_REGEX.search(text)
        candidate = match.group(1).strip() if match else text.strip()
        try:
            return json.loads(candidate)
        except Exception:
            # Try finding first { and last }
            start = candidate.find("{")
            end = candidate.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(candidate[start:end+1])
                except Exception:
                    pass
        return None

    def triage_defect(
        self,
        title: str,
        description: str,
        logs: str,
        component: str,
        historical_evidence: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Query Gemini for grounded defect triage classification and reasoning."""
        if not self._get_client():
            return None

        evidence_str = "\n".join(
            f"- Historical ID: {e.get('source_id')} | Component: {e.get('component')} | Severity: {e.get('severity')} | Summary: {e.get('summary')}"
            for e in historical_evidence[:5]
        ) or "None provided"

        prompt = f"""You are DEFECTIQ's Senior Triage AI Agent analyzing an enterprise software defect.
Evaluate the defect and return a STRICT JSON object with these exact keys:
{{
  "severity": "Critical" | "High" | "Medium" | "Low",
  "priority": "P1" | "P2" | "P3" | "P4",
  "affected_component": "Core" | "UI" | "Debug" | "Text" | "APT" | "Search" | "Other",
  "confidence": <float between 0.0 and 1.0>,
  "reasoning": "<clear evidence-based explanation>",
  "evidence": ["<bullet point 1>", "<bullet point 2>"]
}}

Definitions:
- Critical: System crash, data loss, deadlock, fatal freeze, or security vulnerability.
- High: Core compiler or runtime failure, major feature regression, broken workflow with no easy workaround.
- Medium: Normal defect, functional discrepancy, incorrect behavior where a workaround exists.
- Low: Cosmetic, documentation, minor layout/typo, visual polish.

Priorities:
- P1: Urgent blocker for current release.
- P2: High priority defect.
- P3: Normal priority.
- P4: Low priority / backlog.

DEFECT DETAILS:
Title: {title}
Reported Component: {component or 'Unspecified'}
Description: {description}
Logs / Stack Trace snippet: {logs[:2000] if logs else 'None provided'}

HISTORICAL EVIDENCE MATCHES:
{evidence_str}

Respond ONLY with valid JSON.
"""
        parsed = self._generate_json(prompt)
        if parsed:
            try:
                return TriageOutput.model_validate({**parsed, "historical_mapping": {}, "classification_source": "gemini_grounded"}).model_dump()
            except Exception as exc:
                logger.warning("Gemini triage response rejected by schema: %s", str(exc)[:200])
        return None

    def analyze_logs(self, logs: str, title: str, description: str) -> Optional[Dict[str, Any]]:
        """Query Gemini for deep technical interpretation of stack traces and logs."""
        if not self._get_client():
            return None

        prompt = f"""You are DEFECTIQ's Log Analysis AI Agent inspecting software error logs and stack traces.
Analyze the provided log output and return a STRICT JSON object with these exact keys:
{{
  "exception_type": "<e.g. java.lang.NullPointerException or error type>",
  "error_message": "<error message if present>",
  "failure_point": "<e.g. SourceTypeBinding.java:1681>",
  "file_name": "<file name>",
  "line_number": <integer line number or null>,
  "chained_exceptions": [
    {{"type": "<exception>", "message": "<msg>", "location": "<loc>"}}
  ],
  "affected_code_path": ["<call stack frame 1>", "<call stack frame 2>"],
  "technical_findings": ["<finding 1>", "<finding 2>"],
  "confidence": <float between 0.0 and 1.0>
}}

DEFECT TITLE: {title}
DESCRIPTION: {description[:1000]}
LOGS:
{logs[:6000]}

Respond ONLY with valid JSON.
"""
        parsed = self._generate_json(prompt)
        if parsed:
            try:
                return LogAnalysisOutput.model_validate({**parsed, "has_logs": True, "status": "analyzed", "analysis_source": "gemini_enhanced"}).model_dump()
            except Exception as exc:
                logger.warning("Gemini log response rejected by schema: %s", str(exc)[:200])
        return None

    def synthesize_root_cause_and_remediation(
        self,
        title: str,
        description: str,
        triage: Dict[str, Any],
        log_analysis: Dict[str, Any],
        historical_evidence: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Synthesize root cause hypothesis and remediation plan using all collected evidence."""
        client = self._get_client()
        if not client:
            return None

        evidence_str = "\n".join(
            f"- Historical ID: JDT-{e.get('source_id')} (Resolution: {e.get('resolution')}) | Similarity: {e.get('similarity_score')} | Summary: {e.get('summary')}"
            for e in historical_evidence[:5]
        ) or "No historical evidence available"

        prompt = f"""You are DEFECTIQ's Root Cause and Remediation Specialist.
Synthesize the investigation findings into an evidence-backed root cause hypothesis and remediation strategy.
Strictly separate verified evidence (observed facts from logs/triage/historical records) from hypotheses (inferred causes).
Never suggest automatically modifying any user repository.
Return a STRICT JSON object with these exact keys:
{{
  "root_cause_hypothesis": "<clear technical hypothesis explaining why the defect occurred>",
  "verified_evidence": ["<observed fact 1>", "<observed fact 2>"],
  "hypotheses": ["<inferred hypothesis 1>"],
  "reasoning": "<step-by-step reasoning connecting evidence to hypothesis>",
  "affected_files": ["<file or component supported by evidence>"],
  "remediation_recommendations": [
    "<specific remediation action 1>",
    "<specific remediation action 2>",
    "<regression prevention action 3>"
  ],
  "validation_steps": [
    "<reproduction and testing step 1>",
    "<unit test verification step 2>"
  ],
  "overall_confidence": <float between 0.0 and 1.0>
}}

INVESTIGATION EVIDENCE:
Title: {title}
Description: {description}
Triage Classification: Severity={triage.get('severity')} | Component={triage.get('affected_component')}
Log Analysis: Exception={log_analysis.get('exception_type')} | Failure Point={log_analysis.get('failure_point')}
Technical Findings: {json.dumps(log_analysis.get('technical_findings', []))}
Historical Precedents:
{evidence_str}

Respond ONLY with valid JSON.
"""
        parsed = self._generate_json(prompt, max_output_tokens=1000)
        if parsed:
            try:
                return RootCauseOutput.model_validate(parsed).model_dump()
            except Exception as exc:
                logger.warning("Gemini synthesis response rejected by schema: %s", str(exc)[:200])
        return None


gemini_service = GeminiService()
