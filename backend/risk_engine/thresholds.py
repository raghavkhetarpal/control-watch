from dataclasses import dataclass
from typing import Any

@dataclass
class ThresholdConfig:
    green: float
    amber: float
    red: float
    
def evaluate_threshold(value: float, config: ThresholdConfig) -> str:
    """
    Returns GREEN, AMBER, or RED based on illustrative analytical thresholds.
    """
    if value >= config.red:
        return "RED"
    elif value >= config.amber:
        return "AMBER"
    return "GREEN"
    
# Defaults for controls, e.g. RPT-001 (60 days amber, 90 red)
DEFAULT_THRESHOLDS = {
    "RPT-001": ThresholdConfig(green=30.0, amber=60.0, red=90.0),
    "CONC-001": ThresholdConfig(green=0.35, amber=0.45, red=0.45) # 35% amber, >45% red
}
