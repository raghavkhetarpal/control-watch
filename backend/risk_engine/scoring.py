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
    """Assigns severity based on data characteristics. Placeholder logic."""
    return "MEDIUM"

def score_exception(exception_data: Dict[str, Any]) -> Tuple[int, str, Dict[str, Any]]:
    """Returns full breakdown of the exception score."""
    # Dummy illustrative deterministic parameters
    impact = 3
    likelihood = 3
    ce = 3
    score, level = calculate_risk_score(impact, likelihood, ce)
    breakdown = {
        "impact": impact,
        "likelihood": likelihood,
        "control_effectiveness": ce,
        "formula": "impact * likelihood * (6 - control_effectiveness)"
    }
    return score, level, breakdown
