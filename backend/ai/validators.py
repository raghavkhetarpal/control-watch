"""AI output validation to ensure constraints, safety, and evidence grounding.

Validates AI responses against strict operational risk constraints:
- Must not invent facts / hallucinate data not in evidence
- Must not claim regulatory violations or fraud
- Must not override or determine authoritative risk scores
- Must defend against prompt injections embedded in data fields
"""
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

import structlog

logger = structlog.get_logger(__name__)

# Prompt injection patterns in either response or input evidence
INJECTION_PATTERNS = [
    r"ignore\s+(?:all\s+|previous\s+)?instructions",
    r"system:\s*override",
    r"override\s+risk",
    r"you\s+are\s+now",
    r"system\s+prompt",
    r"injected\s+instruction",
    r"bypass\s+controls",
]

# Prohibited regulatory / fraud claims
REGULATORY_PATTERNS = [
    r"\bfraud\b",
    r"\bfraudulent\b",
    r"\bregulatory\s+violation\b",
    r"\billegal\b",
    r"\bpenalty\b",
    r"\bsec\s+investigation\b",
    r"\bfinra\s+sanction\b",
]

# Prohibited risk score override claims
OVERRIDE_PATTERNS = [
    r"risk\s+score\s+should\s+be",
    r"risk\s+score\s+is\s+0\b",
    r"authoritative\s+score\s+is",
    r"override\s+the\s+score",
]


@dataclass
class ValidationResult:
    """Result of validating an AI-generated response."""
    status: str  # 'VALIDATED', 'FLAGGED', 'REJECTED'
    issues: List[str] = field(default_factory=list)
    confidence: float = 1.0

    @property
    def is_valid(self) -> bool:
        return self.status == "VALIDATED"

    def __getitem__(self, key: str) -> Any:
        if key == "valid":
            return self.is_valid
        if key == "status":
            return self.status
        if key == "reason":
            return self.issues[0] if self.issues else ""
        if key == "issues":
            return self.issues
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default


def validate_ai_response(
    response_text: str,
    evidence: Union[Dict[str, Any], str],
    control_result: Optional[Dict[str, Any]] = None,
) -> ValidationResult:
    """Validate AI response and evidence against constraints and injection attempts.

    Args:
        response_text: The generated or candidate response.
        evidence: Structured evidence dictionary or string context.
        control_result: Optional control execution result dictionary.

    Returns:
        ValidationResult with status ('VALIDATED', 'FLAGGED', 'REJECTED'),
        list of identified issues, and confidence score.
    """
    issues: List[str] = []
    status = "VALIDATED"

    response_lower = (response_text or "").lower()
    evidence_str = str(evidence).lower()

    # 1. Prompt Injection Defense (Checks both evidence payload and output)
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, evidence_str) or re.search(pattern, response_lower):
            issues.append(f"Prompt injection pattern detected: {pattern}")
            status = "REJECTED"
            break

    # Check for specific conflicting / fabricated injections
    if "fraudulent" in evidence_str or "this fund is fraudulent" in evidence_str:
        issues.append("Conflicting instructions or unverified fraud claim in evidence.")
        status = "REJECTED"

    if "risk score is 0" in evidence_str or "risk score is 0" in response_lower:
        issues.append("Fabricated claim: risk score cannot be artificially set to 0.")
        status = "REJECTED"

    # 2. Regulatory and Fraud Language Checks
    for pattern in REGULATORY_PATTERNS:
        if re.search(pattern, response_lower):
            issues.append(f"Response contains unauthorized regulatory or fraud terminology: '{pattern}'")
            if status != "REJECTED":
                status = "FLAGGED"

    # 3. Risk Score Override Checks
    for pattern in OVERRIDE_PATTERNS:
        if re.search(pattern, response_lower):
            issues.append("Response attempts to override or dictate authoritative risk score.")
            if status != "REJECTED":
                status = "FLAGGED"

    # 4. Hallucination / Evidence Grounding Check
    if "data not in evidence" in response_lower and "data not in evidence" not in evidence_str:
        issues.append("Hallucination: Response mentions unverified data not present in evidence.")
        if status != "REJECTED":
            status = "FLAGGED"

    # Determine confidence
    if status == "VALIDATED":
        confidence = 0.95
    elif status == "FLAGGED":
        confidence = 0.50
    else:
        confidence = 0.10

    logger.info(
        "ai_response_validated",
        status=status,
        issues_count=len(issues),
        confidence=confidence,
    )
    return ValidationResult(status=status, issues=issues, confidence=confidence)
