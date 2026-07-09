"""
Shared constants for the BloodIQ simulation and rule engines.
No database -- one simulated blood bank across the 4 ABO blood types
present in the real datasets.
"""

BLOOD_TYPES = ["A", "B", "AB", "O"]

# Neither real dataset has hospital-level detail -- both are national
# totals for Malaysia. To simulate a single typical hospital blood bank
# rather than the whole country, forecasted demand and supply are scaled
# down by this factor before the simulation runs. Malaysia has on the
# order of ~100 hospitals with blood banks nationally, so 1/100 of the
# national volume approximates one typical hospital's share. This is a
# documented approximation (like the demand generation itself), not a
# real per-hospital measurement -- there is no dataset that provides one.
HOSPITAL_SCALE_FACTOR = 0.01

# Red blood cells: standard shelf life at 1-6 C.
SHELF_LIFE_DAYS = 42

# How many days of starting stock to seed the simulation with, sized off
# each type's first forecasted demand day.
INITIAL_STOCK_COVERAGE_DAYS = 7

# Shortage classification thresholds (days of coverage = stock / trailing
# average demand). Matches the thresholds already used by the dashboard's
# existing inventory cards.
SHORTAGE_CRITICAL_COVERAGE_DAYS = 3
SHORTAGE_WARNING_COVERAGE_DAYS = 7

# Wastage classification thresholds (near-expiry ratio = units expiring
# within the window below, divided by current stock).
WASTAGE_NEAR_EXPIRY_WINDOW_DAYS = 3
WASTAGE_HIGH_RATIO = 0.4
WASTAGE_MED_RATIO = 0.15
