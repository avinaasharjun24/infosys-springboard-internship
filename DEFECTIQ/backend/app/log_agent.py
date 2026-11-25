import logging
import re
from typing import Dict, Any, List, Optional
from .schemas import LogAnalysisOutput
from .gemini_service import gemini_service

logger = logging.getLogger("defectiq.log_agent")

# Regex to capture Java exceptions and throwables
EXCEPTION_HEADER_REGEX = re.compile(
    r"(?:Exception in thread \"[^\"]+\"\s+)?([a-zA-Z_$][a-zA-Z0-9_$.]*(?:Exception|Error|Throwable|Fault))(?::\s*(.*))?",
    re.IGNORECASE
)

# Regex to capture Java stack frame lines:
# "at org.eclipse.jdt.internal.compiler.lookup.SourceTypeBinding.resolveTypesFor(SourceTypeBinding.java:1770)"
STACK_FRAME_REGEX = re.compile(
    r"^\s*at\s+([a-zA-Z_$][a-zA-Z0-9_$.]*)\.([a-zA-Z_$][a-zA-Z0-9_$<>]*) *\((?:([a-zA-Z0-9_$.-]+\.java):(\d+)|(Native Method)|(Unknown Source))\)",
    re.MULTILINE
)

# Regex for chained exceptions
CAUSED_BY_REGEX = re.compile(
    r"^\s*Caused by:\s+([a-zA-Z_$][a-zA-Z0-9_$.]*(?:Exception|Error|Throwable))(?::\s*(.*))?",
    re.MULTILINE
)


class LogAnalysisAgent:
    """Specialized Log Analysis Agent performing deterministic AST/stack-trace parsing and AI diagnosis."""

    def analyze(
        self,
        logs: str,
        title: str = "",
        description: str = ""
    ) -> LogAnalysisOutput:
        """Analyze supplied logs and stack traces."""
        cleaned_logs = (logs or "").strip()

        # Handle missing logs appropriately without fabricating exceptions
        if not cleaned_logs:
            return LogAnalysisOutput(
                has_logs=False,
                status="insufficient_log_evidence",
                exception_type=None,
                error_message=None,
                failure_point=None,
                file_name=None,
                line_number=None,
                chained_exceptions=[],
                affected_code_path=[],
                technical_findings=[
                    "No log or stack trace content was supplied; log analysis is limited to text description."
                ],
                confidence=1.0,
                analysis_source="insufficient_evidence",
            )

        # Step 1: Deterministic Parsing of Stack Traces and Exceptions
        parsed = self._parse_deterministic(cleaned_logs)

        # Step 2: If Gemini is available, enhance findings with semantic code interpretation
        if gemini_service.is_configured:
            gemini_findings = gemini_service.analyze_logs(
                logs=cleaned_logs,
                title=title,
                description=description
            )
            if gemini_findings:
                # Merge deterministic high-fidelity coordinates with Gemini's technical insights
                return LogAnalysisOutput(
                    has_logs=True,
                    status=parsed["status"],
                    exception_type=parsed["exception_type"] or gemini_findings.get("exception_type"),
                    error_message=parsed["error_message"] or gemini_findings.get("error_message"),
                    failure_point=parsed["failure_point"] or gemini_findings.get("failure_point"),
                    file_name=parsed["file_name"] or gemini_findings.get("file_name"),
                    line_number=parsed["line_number"] or gemini_findings.get("line_number"),
                    chained_exceptions=parsed["chained_exceptions"] or gemini_findings.get("chained_exceptions", []),
                    affected_code_path=parsed["affected_code_path"] or gemini_findings.get("affected_code_path", []),
                    technical_findings=list(dict.fromkeys(parsed["technical_findings"] + gemini_findings.get("technical_findings", []))),
                    confidence=max(parsed["confidence"], float(gemini_findings.get("confidence", 0.85))),
                    analysis_source="gemini_enhanced",
                )

        return LogAnalysisOutput(
            has_logs=True,
            status=parsed["status"],
            exception_type=parsed["exception_type"],
            error_message=parsed["error_message"],
            failure_point=parsed["failure_point"],
            file_name=parsed["file_name"],
            line_number=parsed["line_number"],
            chained_exceptions=parsed["chained_exceptions"],
            affected_code_path=parsed["affected_code_path"],
            technical_findings=parsed["technical_findings"],
            confidence=parsed["confidence"],
            analysis_source="deterministic_parser",
        )

    def _parse_deterministic(self, logs: str) -> Dict[str, Any]:
        """Extract exception headers, frames, chained causes, and failure points."""
        lines = logs.splitlines()

        exception_type = None
        error_message = None
        chained_exceptions = []
        frames = []
        technical_findings = []

        # Find primary exception
        for line in lines:
            line_clean = line.strip()
            match = EXCEPTION_HEADER_REGEX.search(line_clean)
            if match and not exception_type:
                exception_type = match.group(1).strip()
                error_message = match.group(2).strip() if match.group(2) else None
                technical_findings.append(f"Detected primary exception: {exception_type}")
                if error_message:
                    technical_findings.append(f"Error message: '{error_message}'")
                break

        # Find chained exceptions ("Caused by:")
        for cause_match in CAUSED_BY_REGEX.finditer(logs):
            c_type = cause_match.group(1).strip()
            c_msg = cause_match.group(2).strip() if cause_match.group(2) else ""
            chained_exceptions.append({"type": c_type, "message": c_msg})
            technical_findings.append(f"Nested root cause: {c_type} {c_msg}".strip())

        # Find all stack frames
        for frame_match in STACK_FRAME_REGEX.finditer(logs):
            cls_name = frame_match.group(1).strip()
            method_name = frame_match.group(2).strip()
            file_name = frame_match.group(3)
            line_num = int(frame_match.group(4)) if frame_match.group(4) else None
            is_native = bool(frame_match.group(5))

            loc = f"{file_name}:{line_num}" if file_name and line_num else ("Native Method" if is_native else "Unknown")
            frame_str = f"{cls_name}.{method_name}({loc})"
            frames.append({
                "class": cls_name,
                "method": method_name,
                "file": file_name,
                "line": line_num,
                "formatted": frame_str
            })

        # Identify failure point
        failure_point = None
        top_file = None
        top_line = None

        if frames:
            # Prioritize first application frame (e.g. org.eclipse.*) over standard library reflection
            app_frames = [f for f in frames if not f["class"].startswith(("java.lang.reflect", "sun.reflect", "jdk.internal"))]
            target_frame = app_frames[0] if app_frames else frames[0]

            top_file = target_frame["file"]
            top_line = target_frame["line"]
            failure_point = f"{target_frame['class']}.{target_frame['method']} ({target_frame['file']}:{target_frame['line']})" if target_frame['file'] else f"{target_frame['class']}.{target_frame['method']}"
            technical_findings.append(f"Topmost application failure point identified at: {failure_point}")

        code_paths = [f["formatted"] for f in frames[:15]]

        # Determine parsing status and confidence
        if exception_type or frames:
            status = "analyzed"
            confidence = 0.92 if (exception_type and frames) else 0.78
        else:
            # Check for generic error logs or warnings
            error_count = len(re.findall(r"\b(?:error|fail|failed|fatal|severe)\b", logs, re.I))
            if error_count > 0:
                status = "analyzed"
                confidence = 0.60
                technical_findings.append(f"Identified {error_count} general error markers in log output without Java stack trace.")
            else:
                status = "malformed_logs"
                confidence = 0.50
                technical_findings.append("Supplied log text does not conform to standard stack trace or structured error log format.")

        return {
            "status": status,
            "exception_type": exception_type,
            "error_message": error_message,
            "failure_point": failure_point,
            "file_name": top_file,
            "line_number": top_line,
            "chained_exceptions": chained_exceptions,
            "affected_code_path": code_paths,
            "technical_findings": technical_findings,
            "confidence": confidence,
        }


log_analysis_agent = LogAnalysisAgent()
