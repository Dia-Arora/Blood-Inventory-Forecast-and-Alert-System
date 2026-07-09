"""
Shared constants for the BloodIQ simulation and rule engines.
No database, no per-hospital config -- one national-level simulation
across the 4 ABO blood types present in the real datasets.
"""

BLOOD_TYPES = ["A", "B", "AB", "O"]

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

# The demand dataset (Kaggle, ~184 units/day national total) and the supply
# dataset (Malaysia, ~1299 units/day national total across all 4 types) come
# from two different-sized real-world systems -- without reconciling scale,
# supply always dwarfs demand and the simulation never shows a shortage or
# wastage. This factor scales the demand forecast up to be comparable to the
# supply forecast's real scale (computed as avg_total_supply / avg_total_demand
# from the two real CSVs: 1299.2 / 184.0 = 7.0623), rather than fabricating
# new demand numbers from nothing.
DEMAND_SCALE_FACTOR = 7.0623
