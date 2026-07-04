"""
config/settings.py
------------------
Central configuration for the Blood Inventory Forecasting System.

All file paths are resolved relative to the `backend/` directory at runtime
using pathlib so there are no hardcoded absolute paths anywhere in the codebase.
"""

from pathlib import Path
from typing import Dict, List

# ---------------------------------------------------------------------------
# Root resolution
# ---------------------------------------------------------------------------
# This file lives at backend/config/settings.py → parent.parent = backend/
BACKEND_ROOT: Path = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Blood group constants
# ---------------------------------------------------------------------------
# Single source of truth for the four ABO groups used across the entire system.
# All DB columns, forecasting outputs, and API responses use these exact strings.
BLOOD_GROUPS: List[str] = ["A", "B", "AB", "O"]

# ---------------------------------------------------------------------------
# Inventory parameters
# ---------------------------------------------------------------------------
# Red blood cell shelf life in days (standard: 42 days at 1–6 °C).
BLOOD_SHELF_LIFE_DAYS: int = 42

# Minimum safe stock units per blood group.
# Used by the Decision Engine to compute shortage risk levels.
SAFETY_STOCK_PER_GROUP: Dict[str, int] = {
    "A":  50,
    "B":  40,
    "AB": 20,
    "O":  60,
}

# Number of days ahead to look when assessing wastage risk.
WASTAGE_EXPIRY_WINDOW_DAYS: int = 3

# Number of initial batches to generate per blood group during first-run seeding.
INITIAL_BATCHES_PER_GROUP: int = 6

# ---------------------------------------------------------------------------
# Dataset paths (relative to BACKEND_ROOT)
# ---------------------------------------------------------------------------
DEMAND_DATA_PATH: Path = BACKEND_ROOT / "datasets" / "demand" / "synthetic_blood_demand_data.csv"
DONATION_DATA_PATH: Path = BACKEND_ROOT / "datasets" / "supply" / "blood_donations.csv"

# ---------------------------------------------------------------------------
# Trained model paths
# ---------------------------------------------------------------------------
TRAINED_MODELS_DIR: Path = BACKEND_ROOT / "trained_models"

DEMAND_MODEL_PATH: Path = TRAINED_MODELS_DIR / "demand_xgb.joblib"

# Prophet models: one file per blood group, e.g. donation_prophet_A.joblib
def donation_model_path(blood_group: str) -> Path:
    """Return the joblib path for a given blood group's Prophet model."""
    return TRAINED_MODELS_DIR / f"donation_prophet_{blood_group}.joblib"


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# SQLite file placed inside backend/ directory.
DATABASE_URL: str = f"sqlite:///{BACKEND_ROOT / 'blood_inventory.db'}"

# ---------------------------------------------------------------------------
# Simulation / forecasting defaults
# ---------------------------------------------------------------------------
# How many days ahead to forecast and store when /simulate is called.
FORECAST_HORIZON_DAYS: int = 30

# ---------------------------------------------------------------------------
# XGBoost hyperparameters (demand model)
# ---------------------------------------------------------------------------
XGBOOST_PARAMS: Dict = {
    "n_estimators": 300,
    "learning_rate": 0.05,
    "max_depth": 6,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": 42,
    "n_jobs": -1,
}

# Train/test split ratio (chronological)
TRAIN_TEST_SPLIT_RATIO: float = 0.80

# ---------------------------------------------------------------------------
# Prophet hyperparameters (donation models)
# ---------------------------------------------------------------------------
PROPHET_PARAMS: Dict = {
    "yearly_seasonality": True,
    "weekly_seasonality": True,
    "daily_seasonality": False,
    "interval_width": 0.80,
}
