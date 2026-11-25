import logging
import re
from typing import Dict, Any, List, Optional
from .schemas import TriageOutput
from .gemini_service import gemini_service

logger = logging.getLogger("defectiq.triage")

# Documented mapping between historical Eclipse labels and DEFECTIQ enterprise categories
HISTORICAL_SEVERITY_MAPPING = {
    "blocker": "Critical",
    "critical": "Critical",
    "major": "High",
    "normal": "Medium",
    "minor": "Low",
    "trivial": "Low",
    "enhancement": "Low",
}

# Domain-specific keyword signatures for defect severity analysis
CRITICAL_INDICATORS = [
    r"\b(?:crash|crashed|crashing|fatal|segmentation fault|segfault|sigsegv)\b",
    r"\b(?:data loss|corrupt|corruption|deadlock|system hang|jvm crash|freeze)\b",
    r"\b(?:security vulnerability|cve|rce|privilege escalation)\b",
    r"\b(?:unusable|completely broken|cannot start|startup failure|blocking release)\b",
]

HIGH_INDICATORS = [
    r"\b(?:nullpointerexception|npe|illegalstateexception|arrayindexoutofboundsexception)\b",
    r"\b(?:swtexception|vmdisconnectedexception|classnotfoundexception|nosuchmethoderror)\b",
    r"\b(?:stackoverflowerror|outofmemoryerror|oom|compiler error|internal compiler error)\b",
    r"\b(?:regression|fails to compile|compilation failure|broken build)\b",
    r"\b(?:severe failure|unexpected error|cannot save|import failed|parsing error)\b",
]

MEDIUM_INDICATORS = [
    r"\b(?:incorrect|unexpected behaviour|wrong result|missing option|slow performance)\b",
    r"\b(?:warning|deprecated|misaligned|inconsistent|workaround)\b",
    r"\b(?:validation error|failed check|timeout|intermittent)\b",
]

LOW_INDICATORS = [
    r"\b(?:typo|spelling|cosmetic|font|color|spacing|padding|icon|tooltip)\b",
    r"\b(?:minor layout|documentation|doc error|readme|enhancement|cleanup)\b",
]

COMPONENT_SIGNATURES = {
    "Core": [
        r"\borg\.eclipse\.jdt\.core\b", r"\bcompiler\b", r"\bast\b", r"\bparser\b",
        r"\btypebinding\b", r"\blookup\b", r"\bbatch compiler\b", r"\bcode assist\b",
        r"\bdom\b", r"\bindexer\b", r"\bjavamodel\b"
    ],
    "UI": [
        r"\borg\.eclipse\.jdt\.ui\b", r"\borg\.eclipse\.swt\b", r"\borg\.eclipse\.jface\b",
        r"\beditor\b", r"\bview\b", r"\bdialog\b", r"\bwizard\b", r"\bmenu\b",
        r"\bperspective\b", r"\bhover\b", r"\boutline\b", r"\bquick fix\b"
    ],
    "Debug": [
        r"\borg\.eclipse\.jdt\.debug\b", r"\bbreakpoint\b", r"\bdebugger\b", r"\bstepping\b",
        r"\bstack frame\b", r"\bjdi\b", r"\blaunch\b", r"\bvm attach\b", r"\bthread suspension\b"
    ],
    "Text": [
        r"\borg\.eclipse\.jface\.text\b", r"\bsyntax highlight\b", r"\bformatting\b",
        r"\breconciler\b", r"\bcontent assist\b", r"\bhyperlink\b", r"\bword wrap\b"
    ],
    "APT": [
        r"\borg\.eclipse\.jdt\.apt\b", r"\bannotation processor\b", r"\bapt\b"
    ],
}


class TriageAgent:
    """Enterprise AI Triage Agent responsible for classifying severity, priority, and component."""

    def classify(
        self,
        title: str,
        description: str,
        logs: str = "",
        component: str = "",
        historical_matches: Optional[List[Dict[str, Any]]] = None
    ) -> TriageOutput:
        """Run classification pipeline combining deterministic heuristics with grounded AI."""
        historical_matches = historical_matches or []
        combined_text = f"{title}\n{description}\n{logs}".lower()

        # Step 1: Deterministic Expert Heuristic Evaluation
        det_severity, det_reasoning, det_evidence, det_conf = self._evaluate_severity(combined_text)
        det_component = self._evaluate_component(combined_text, user_component=component)
        det_priority = self._estimate_priority(det_severity, combined_text)

        # Step 2: Leverage Historical Retrieval Evidence if present
        if historical_matches:
            top_match = historical_matches[0]
            hist_sev_raw = top_match.get("severity", "").lower()
            mapped_hist_sev = HISTORICAL_SEVERITY_MAPPING.get(hist_sev_raw)
            if mapped_hist_sev and top_match.get("similarity_score", 0.0) >= 0.70:
                det_evidence.append(
                    f"Strong historical precedent JDT-{top_match.get('source_id')} with severity '{hist_sev_raw}' (mapped to '{mapped_hist_sev}')"
                )
                # Boost confidence with strong historical backing
                det_conf = min(0.95, det_conf + 0.10)

        # Step 3: If Gemini is available, enhance with grounded reasoning
        if gemini_service.is_configured:
            gemini_result = gemini_service.triage_defect(
                title=title,
                description=description,
                logs=logs,
                component=det_component,
                historical_evidence=historical_matches
            )
            if gemini_result:
                return TriageOutput(
                    severity=gemini_result.get("severity", det_severity),
                    priority=gemini_result.get("priority", det_priority),
                    affected_component=gemini_result.get("affected_component", det_component),
                    confidence=float(gemini_result.get("confidence", det_conf)),
                    reasoning=gemini_result.get("reasoning", det_reasoning),
                    evidence=gemini_result.get("evidence", det_evidence),
                    historical_mapping=HISTORICAL_SEVERITY_MAPPING,
                    classification_source="gemini_grounded",
                )

        # Return deterministic expert classification
        return TriageOutput(
            severity=det_severity,
            priority=det_priority,
            affected_component=det_component,
            confidence=det_conf,
            reasoning=det_reasoning,
            evidence=det_evidence,
            historical_mapping=HISTORICAL_SEVERITY_MAPPING,
            classification_source="deterministic_expert",
        )

    def _evaluate_severity(self, text: str) -> tuple[str, str, list[str], float]:
        """Determine severity level, justification, evidence items, and confidence."""
        # Check Critical
        for pattern in CRITICAL_INDICATORS:
            match = re.search(pattern, text)
            if match:
                evidence = [f"Critical keyword detected: '{match.group(0)}' indicating catastrophic failure or crash"]
                reasoning = (
                    f"Classified as Critical due to detected failure pattern '{match.group(0)}'. "
                    "System crashes, unhandled deadlocks, and fatal corruptions require immediate escalation."
                )
                return "Critical", reasoning, evidence, 0.92

        # Check High
        for pattern in HIGH_INDICATORS:
            match = re.search(pattern, text)
            if match:
                evidence = [f"High-severity exception/failure pattern: '{match.group(0)}'"]
                reasoning = (
                    f"Classified as High severity due to exception signature '{match.group(0)}'. "
                    "Core functional breakage impairs developer workflow without total system crash."
                )
                return "High", reasoning, evidence, 0.88

        # Check Low
        for pattern in LOW_INDICATORS:
            match = re.search(pattern, text)
            if match:
                evidence = [f"Cosmetic/low-impact indicator: '{match.group(0)}'"]
                reasoning = (
                    f"Classified as Low severity based on pattern '{match.group(0)}'. "
                    "Issue represents cosmetic, typo, or minor enhancement with no functional impact."
                )
                return "Low", reasoning, evidence, 0.85

        # Check Medium
        for pattern in MEDIUM_INDICATORS:
            match = re.search(pattern, text)
            if match:
                evidence = [f"Medium impact indicator: '{match.group(0)}'"]
                reasoning = (
                    f"Classified as Medium severity. Observed behavior '{match.group(0)}' represents a standard defect "
                    "with localized impact where workaround or alternative paths exist."
                )
                return "Medium", reasoning, evidence, 0.80

        # Default fallback: standard medium bug, lower confidence
        return (
            "Medium",
            "Classified as Medium severity by standard default rule. No catastrophic crash or purely cosmetic indicators detected.",
            ["Default baseline classification applied"],
            0.65
        )

    def _evaluate_component(self, text: str, user_component: str = "") -> str:
        """Infer affected component from stack traces, class names, or text."""
        if user_component and user_component.strip():
            # Validate user provided component
            for comp in COMPONENT_SIGNATURES:
                if user_component.strip().lower() == comp.lower():
                    return comp

        # Check stack traces and package references
        for comp, patterns in COMPONENT_SIGNATURES.items():
            for pat in patterns:
                if re.search(pat, text):
                    return comp

        return "Core"  # Default component for Eclipse JDT

    def _estimate_priority(self, severity: str, text: str) -> str:
        """Estimate operational priority based on severity and urgency indicators."""
        if severity == "Critical":
            return "P1"
        if severity == "High":
            # If blocking a release or widespread, escalate to P1
            if re.search(r"\b(?:blocker|urgent|showstopper|production)\b", text):
                return "P1"
            return "P2"
        if severity == "Medium":
            if re.search(r"\b(?:regression|frequent|blocking)\b", text):
                return "P2"
            return "P3"
        return "P4"


triage_agent = TriageAgent()
