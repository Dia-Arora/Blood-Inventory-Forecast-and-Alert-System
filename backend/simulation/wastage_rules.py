"""Rule-based wastage classification from near-expiry stock ratio."""
from config import WASTAGE_HIGH_RATIO, WASTAGE_MED_RATIO


def classify_wastage(near_expiry_ratio):
    """near_expiry_ratio = units expiring within the window / current stock."""
    if near_expiry_ratio > WASTAGE_HIGH_RATIO:
        return "HIGH"
    if near_expiry_ratio >= WASTAGE_MED_RATIO:
        return "MED"
    return "LOW"
