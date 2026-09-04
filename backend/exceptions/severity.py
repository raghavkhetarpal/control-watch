"""
Severity assignment module for exception management.
"""
from typing import Tuple, Dict, Any
import structlog

logger = structlog.get_logger(__name__)

def assign_severity(impact: float, likelihood: float, control_effectiveness: float) -> str:
    """
    Maps risk score to severity: LOW (1-24), MEDIUM (25-49), HIGH (50-74), CRITICAL (75-125)
    Risk score calculation is based on backend.risk_engine.scoring
    """
    # Assuming risk_score is roughly impact * likelihood * (1 - control_effectiveness)
    # Scaled to roughly 1-125 range for simplicity here
    risk_score = impact * likelihood * (1.5 - control_effectiveness) * 5
    
    if risk_score < 25:
        return "LOW"
    elif risk_score < 50:
        return "MEDIUM"
    elif risk_score < 75:
        return "HIGH"
    else:
        return "CRITICAL"

def auto_assign_severity(control_id: str, exception_data: Dict[str, Any]) -> Tuple[str, float, float, float]:
    """
    Assigns default impact/likelihood based on control type and exception characteristics.
    """
    # Simplified logic for defaults
    impact = 3.0
    likelihood = 3.0
    control_eff = 0.5
    
    control_type = exception_data.get("control_type", "UNKNOWN")
    
    if control_type == "RECONCILIATION":
        impact = 4.0
        likelihood = 4.0
    elif control_type == "VALUATION":
        impact = 5.0
        likelihood = 2.0
    elif control_type == "DATA_QUALITY":
        impact = 2.0
        likelihood = 4.0
        
    severity = assign_severity(impact, likelihood, control_eff)
    logger.info("Auto-assigned severity", severity=severity, control_id=control_id)
    return severity, impact, likelihood, control_eff
