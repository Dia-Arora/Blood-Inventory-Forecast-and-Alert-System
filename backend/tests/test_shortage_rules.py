from simulation.shortage_rules import classify_shortage


def test_critical_at_or_below_three_days_coverage():
    assert classify_shortage(0.0) == "CRITICAL"
    assert classify_shortage(3.0) == "CRITICAL"


def test_warning_between_three_and_seven_days_coverage():
    assert classify_shortage(3.5) == "WARNING"
    assert classify_shortage(7.0) == "WARNING"


def test_safe_above_seven_days_coverage():
    assert classify_shortage(7.5) == "SAFE"
    assert classify_shortage(100.0) == "SAFE"
