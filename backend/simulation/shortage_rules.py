"""Rule-based shortage classification from days-of-coverage."""
from config import SHORTAGE_CRITICAL_COVERAGE_DAYS, SHORTAGE_WARNING_COVERAGE_DAYS


def classify_shortage(coverage_days):
    """coverage_days = current stock / trailing average daily demand."""
    if coverage_days <= SHORTAGE_CRITICAL_COVERAGE_DAYS:
        return "CRITICAL"
    if coverage_days <= SHORTAGE_WARNING_COVERAGE_DAYS:
        return "WARNING"
    return "SAFE"
