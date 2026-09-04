from typing import Tuple, Dict, Any

def calculate_risk_score(impact: int, likelihood: int, control_effectiveness: int) -> Tuple[int, str]:
    """
    Calculate deterministic risk score.
    Methodology: risk_score = impact * likelihood * (6 - control_effectiveness)
    All inputs scale 1-5.
    Level: LOW (1-24), MEDIUM (25-49), HIGH (50-74), CRITICAL (75-125)
    """
    score = impact * likelihood * (6 - control_effectiveness)
    
    if score < 25:
        level = "LOW"
    elif score < 50:
        level = "MEDIUM"
    elif score < 75:
        level = "HIGH"
    else:
        level = "CRITICAL"
        
    return score, level

def assign_severity(control_id: str, exception_data: Dict[str, Any]) -> str:
    """Assigns severity based on data characteristics."""
    if exception_data.get("exception_type") == "DATA_AVAILABILITY":
        return "LOW"
    sev = exception_data.get("severity")
    if sev in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
        return sev
    return "MEDIUM"

def score_exception(exception_data: Dict[str, Any]) -> Tuple[int, str, Dict[str, Any]]:
    """Returns full breakdown of the exception score."""
    # Data availability / insufficient evidence handling
    if exception_data.get("exception_type") == "DATA_AVAILABILITY" or exception_data.get("is_data_unavailable"):
        return 0, "INSUFFICIENT_EVIDENCE", {
            "impact": 1,
            "likelihood": 1,
            "control_effectiveness": 3,
            "formula": "N/A - Insufficient Evidence / Data Unavailable",
            "risk_status": "INSUFFICIENT_EVIDENCE",
        }

    severity = exception_data.get("severity", "MEDIUM")
    if severity == "CRITICAL":
        impact, likelihood, ce = 5, 4, 2
    elif severity == "HIGH":
        impact, likelihood, ce = 4, 3, 2  # 4 * 3 * 4 = 48 (MEDIUM) or 4 * 4 * 3 = 48
    elif severity == "LOW":
        impact, likelihood, ce = 2, 2, 4
    else:
        impact, likelihood, ce = 3, 3, 3

    score, level = calculate_risk_score(impact, likelihood, ce)
    breakdown = {
        "impact": impact,
        "likelihood": likelihood,
        "control_effectiveness": ce,
        "formula": "impact * likelihood * (6 - control_effectiveness)",
        "risk_status": level,
    }
    return score, level, breakdown
