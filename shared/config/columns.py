"""
shared/config/columns.py
=========================
Canonical column contract shared across ALL members.

This is the single source of truth for:
  - Column names produced by Member 1
  - Column names consumed by Member 2 (ML model)
  - Column names consumed by Member 3 (Digital Twin)
  - Column names served by Member 4 (API)

NEVER define feature lists inline in individual member files.
Always import from here.
"""

# ---------------------------------------------------------------------------
# Target variable
# ---------------------------------------------------------------------------
TARGET_COL = "total_units"

# ---------------------------------------------------------------------------
# Raw product columns (output by mimic_extractor.py)
# ---------------------------------------------------------------------------
PRODUCT_COLS = [
    "prbc_units",       # Packed Red Blood Cells
    "ffp_units",        # Fresh Frozen Plasma
    "platelet_units",   # Platelets
    "cryo_units",       # Cryoprecipitate
    "total_units",      # Sum of all products (the forecast target)
]

# ---------------------------------------------------------------------------
# Calendar features (output by mimic_extractor.py)
# ---------------------------------------------------------------------------
CALENDAR_COLS = [
    "day_of_week",      # 0=Monday ... 6=Sunday
    "is_weekend",       # 1 if Saturday or Sunday
    "month",
    "quarter",
    "day_of_year",
    "week_of_year",
    "is_holiday_us",    # 1 on approximate US federal holidays (proxy for Indian holidays)
]

# ---------------------------------------------------------------------------
# Engineered features (output by feature_engineering.py)
# ---------------------------------------------------------------------------
LAG_COLS = [
    "lag_7",            # total_units 7 days ago
    "lag_14",           # total_units 14 days ago
    "lag_30",           # total_units 30 days ago
]

ROLLING_COLS = [
    "rolling_mean_7",   # 7-day rolling mean of total_units
    "rolling_mean_14",  # 14-day rolling mean of total_units
    "rolling_std_7",    # 7-day rolling std of total_units (volatility)
]

DOMAIN_COLS = [
    "demand_spike_flag",        # 1 if yesterday's demand exceeded mean + 2*sigma
    "days_since_last_spike",    # Days elapsed since last demand spike
    "prbc_mix_ratio",           # PRBC fraction of total demand
    "ffp_mix_ratio",            # FFP fraction of total demand
    "platelet_mix_ratio",       # Platelet fraction of total demand
]

# ---------------------------------------------------------------------------
# Full feature matrix column order (all columns in the output CSV)
# ---------------------------------------------------------------------------
ALL_FEATURE_COLS = (
    ["date"]
    + PRODUCT_COLS
    + CALENDAR_COLS
    + LAG_COLS
    + ROLLING_COLS
    + DOMAIN_COLS
)

# ---------------------------------------------------------------------------
# Member 2 (ML model) — feature subsets
# ---------------------------------------------------------------------------

# Sequential features fed to the GRU as a sliding window (temporal signal)
SEQUENCE_FEATURES = [
    "total_units",
    "prbc_units",
    "ffp_units",
    "platelet_units",
    "is_weekend",
    "is_holiday_us",
    "demand_spike_flag",
]

# Static features fed to LightGBM (tabular, no ordering required)
STATIC_FEATURES = [
    "day_of_week",
    "is_weekend",
    "month",
    "quarter",
    "day_of_year",
    "week_of_year",
    "is_holiday_us",
    "lag_7",
    "lag_14",
    "lag_30",
    "rolling_mean_7",
    "rolling_mean_14",
    "rolling_std_7",
    "demand_spike_flag",
    "days_since_last_spike",
    "prbc_mix_ratio",
    "ffp_mix_ratio",
    "platelet_mix_ratio",
]

# ---------------------------------------------------------------------------
# Member 3 (Digital Twin) — product name mapping
# Product column names (Member 1) -> full product names (Member 3 FEFO engine)
# ---------------------------------------------------------------------------
COLUMN_TO_PRODUCT = {
    "prbc_units":     "Packed Red Blood Cells",
    "ffp_units":      "Fresh Frozen Plasma",
    "platelet_units": "Platelets",
    "cryo_units":     "Cryoprecipitate",
}

PRODUCT_TO_COLUMN = {v: k for k, v in COLUMN_TO_PRODUCT.items()}

# Mix ratio columns -> product column they describe
MIX_RATIO_TO_PRODUCT_COL = {
    "prbc_mix_ratio":     "prbc_units",
    "ffp_mix_ratio":      "ffp_units",
    "platelet_mix_ratio": "platelet_units",
}

# ---------------------------------------------------------------------------
# Split ratios (kept here so all members use identical splits)
# ---------------------------------------------------------------------------
TRAIN_RATIO = 0.70
VAL_RATIO   = 0.15
# TEST_RATIO  = 0.15 (implicit)

GRU_SEQUENCE_WINDOW = 30  # Days of history per GRU input sample
