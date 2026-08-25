"""
Demand classification — routes each facility-drug pair to the right
forecasting method based on CV and ADI.

Thresholds (Syntetos-Boylan):
    CV < 0.49  and ADI < 1.32  → smooth   → SES
    CV >= 0.49 and ADI < 1.32  → erratic  → SES
    CV < 0.49  and ADI >= 1.32 → intermittent → Croston SBA
    CV >= 0.49 and ADI >= 1.32 → lumpy    → Croston SBA
"""

from typing import List, Literal
import math

DemandClass = Literal["smooth", "erratic", "intermittent", "lumpy"]


def classify_demand(values: List[float]) -> DemandClass:
    """Classify a demand series into one of four classes."""
    non_zero = [v for v in values if v > 0]

    if len(non_zero) < 3:
        return "lumpy"

    mean_nz = sum(non_zero) / len(non_zero)
    if mean_nz == 0:
        return "lumpy"

    variance = sum((x - mean_nz) ** 2 for x in non_zero) / len(non_zero)
    cv = math.sqrt(variance) / mean_nz

    # ADI = total periods / non-zero periods
    adi = len(values) / max(len(non_zero), 1)

    if cv < 0.49 and adi < 1.32:
        return "smooth"
    elif cv >= 0.49 and adi < 1.32:
        return "erratic"
    elif cv < 0.49 and adi >= 1.32:
        return "intermittent"
    else:
        return "lumpy"
