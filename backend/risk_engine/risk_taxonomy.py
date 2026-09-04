from enum import Enum
from typing import Dict, Tuple

class RiskCategory(Enum):
    DATA_QUALITY = "DATA_QUALITY"
    RECONCILIATION = "RECONCILIATION"
    VALUATION = "VALUATION"
    CONCENTRATION = "CONCENTRATION"
    REPORTING = "REPORTING"
    PROCESS = "PROCESS"
    CONTROL_EFFECTIVENESS = "CONTROL_EFFECTIVENESS"
    TECHNOLOGY = "TECHNOLOGY"

# Mapping control_id -> RiskCategory
CONTROL_RISK_MAPPING: Dict[str, RiskCategory] = {
    "DQ-001": RiskCategory.DATA_QUALITY,
    "DQ-002": RiskCategory.DATA_QUALITY,
    "DQ-003": RiskCategory.DATA_QUALITY,
    "DQ-004": RiskCategory.DATA_QUALITY,
    "REC-001": RiskCategory.RECONCILIATION,
    "REC-002": RiskCategory.RECONCILIATION,
    "VAL-001": RiskCategory.VALUATION,
    "VAL-002": RiskCategory.VALUATION,
    "CONC-001": RiskCategory.CONCENTRATION,
    "CONC-002": RiskCategory.CONCENTRATION,
    "CONC-003": RiskCategory.CONCENTRATION,
    "CONC-004": RiskCategory.CONCENTRATION,
    "LIQ-001": RiskCategory.CONCENTRATION, # Or similar
    "RPT-001": RiskCategory.REPORTING,
    "RPT-002": RiskCategory.REPORTING,
    "CLS-001": RiskCategory.DATA_QUALITY
}

# Default (Impact, Likelihood)
CATEGORY_DEFAULTS: Dict[RiskCategory, Tuple[int, int]] = {
    RiskCategory.DATA_QUALITY: (3, 4),
    RiskCategory.RECONCILIATION: (4, 3),
    RiskCategory.VALUATION: (5, 2),
    RiskCategory.CONCENTRATION: (4, 3),
    RiskCategory.REPORTING: (2, 4)
}
