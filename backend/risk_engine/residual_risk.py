from typing import Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
from dataclasses import dataclass

@dataclass
class RiskAssessment:
    fund_id: str
    period_date: str
    inherent_risk: float
    control_effectiveness: float
    residual_risk: float
    risk_level: str

def calculate_residual_risk(inherent_risk: float, control_effectiveness: float) -> Tuple[float, str]:
    """
    inherent_risk = impact * likelihood (1-25)
    control_effectiveness from KCI (0-1)
    residual_risk = inherent_risk * (1 - control_effectiveness)
    """
    residual = round(inherent_risk * (1 - control_effectiveness), 2)
    if residual <= 6:
        level = "LOW"
    elif residual <= 12:
        level = "MEDIUM"
    elif residual <= 18:
        level = "HIGH"
    else:
        level = "CRITICAL"
    return residual, level

def calculate_fund_risk(session: Session, fund_id: str, period_date: str) -> RiskAssessment:
    """Calculates risk, creates risk_assessments record, and returns it."""
    # Stub values for illustrative analytical thresholds
    inherent_risk = 15.0
    ce = 0.8 # Derived from execution_rate * pass_rate
    
    residual, level = calculate_residual_risk(inherent_risk, ce)
    
    # Insert record
    session.execute(
        text("""
            INSERT INTO risk_assessments (fund_id, period_date, inherent_risk, control_effectiveness, residual_risk, risk_level)
            VALUES (:f, :pd, :ir, :ce, :rr, :rl)
        """),
        {"f": fund_id, "pd": period_date, "ir": inherent_risk, "ce": ce, "rr": residual, "rl": level}
    )
    session.commit()
    
    return RiskAssessment(fund_id, period_date, inherent_risk, ce, residual, level)
