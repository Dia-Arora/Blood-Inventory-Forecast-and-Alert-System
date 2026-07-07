from simulation.wastage_rules import classify_wastage


def test_high_when_near_expiry_ratio_above_point_four():
    assert classify_wastage(0.41) == "HIGH"
    assert classify_wastage(1.0) == "HIGH"


def test_med_when_near_expiry_ratio_between_point_15_and_point_4():
    assert classify_wastage(0.15) == "MED"
    assert classify_wastage(0.4) == "MED"


def test_low_when_near_expiry_ratio_at_or_below_point_15():
    assert classify_wastage(0.0) == "LOW"
    assert classify_wastage(0.1) == "LOW"
