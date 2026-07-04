"""
Feature Engineering Pipeline
==============================
Member 1 -- Data Engineering Lead

Takes the raw daily demand CSV from mimic_extractor.py and engineers
the full feature matrix required by the Hybrid GRU-LightGBM model (Member 2)
and the Digital Twin (Member 3).

All output column names are defined in shared/config/columns.py.
DO NOT add columns here without updating that contract file.

Features Engineered
-------------------
Lag features (temporal memory):
    lag_7, lag_14, lag_30        -- total_units N days ago

Rolling statistics (trend + volatility):
    rolling_mean_7, rolling_mean_14  -- smoothed trend signal
    rolling_std_7                    -- demand volatility

Domain-specific (novel contribution):
    demand_spike_flag       -- 1 if yesterday > rolling_mean + 2*sigma
    days_since_last_spike   -- calendar days since last spike (not row index)
    prbc_mix_ratio          -- PRBC share of total demand
    ffp_mix_ratio           -- FFP share of total demand
    platelet_mix_ratio      -- Platelet share of total demand

Outputs:
    data/mimic_real_demand_features.csv  -- full feature set
    data/train.csv                       -- 70% chronological split
    data/val.csv                         -- 15% chronological split
    data/test.csv                        -- 15% chronological split

Usage:
    python feature_engineering.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
INPUT_PATH = Path("data/mimic_real_demand.csv")
OUTPUT_DIR = Path("data")

# ---------------------------------------------------------------------------
# Shared contract (column names must match shared/config/columns.py)
# ---------------------------------------------------------------------------
TARGET_COL       = "total_units"
LAG_DAYS         = [7, 14, 30]
ROLLING_WINDOWS  = [7, 14]
TRAIN_RATIO      = 0.70
VAL_RATIO        = 0.15

# All features Member 2's model expects to find in train.csv / val.csv / test.csv
REQUIRED_OUTPUT_COLS = [
    # From extractor
    "date", "prbc_units", "ffp_units", "platelet_units", "cryo_units", "total_units",
    "day_of_week", "is_weekend", "month", "quarter", "day_of_year", "week_of_year", "is_holiday_us",
    # Lag
    "lag_7", "lag_14", "lag_30",
    # Rolling
    "rolling_mean_7", "rolling_mean_14", "rolling_std_7",
    # Domain
    "demand_spike_flag", "days_since_last_spike",
    "prbc_mix_ratio", "ffp_mix_ratio", "platelet_mix_ratio",
]


# ---------------------------------------------------------------------------
# Feature builders
# ---------------------------------------------------------------------------

def add_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """Lag of total_units at 7, 14, 30 days (shift=1 so no leakage)."""
    df = df.copy()
    for lag in LAG_DAYS:
        df[f"lag_{lag}"] = df[TARGET_COL].shift(lag)
    return df


def add_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    """Rolling mean and std -- shifted by 1 to prevent target leakage."""
    df = df.copy()
    for window in ROLLING_WINDOWS:
        df[f"rolling_mean_{window}"] = (
            df[TARGET_COL].shift(1).rolling(window, min_periods=1).mean()
        )
    df["rolling_std_7"] = (
        df[TARGET_COL].shift(1).rolling(7, min_periods=2).std()
    )
    return df


def add_domain_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Novel domain-specific features that encode blood supply chain knowledge.

    These are absent from standard time-series ML papers and form part of
    the novel contribution documented in the IEEE paper.
    """
    df = df.copy()

    # 1. Demand spike flag
    rolling_mean = df[TARGET_COL].shift(1).rolling(7, min_periods=2).mean()
    rolling_std  = df[TARGET_COL].shift(1).rolling(7, min_periods=2).std().fillna(1.0)
    df["demand_spike_flag"] = (
        (df[TARGET_COL].shift(1)) > (rolling_mean + 2.0 * rolling_std)
    ).astype(int)

    # 2. Days since last spike -- uses actual calendar dates, not row indices
    #    This correctly handles any gaps in the date range.
    spike_dates = df.loc[df["demand_spike_flag"] == 1, "date"].tolist()
    spike_dates_dt = pd.to_datetime(spike_dates)

    def _days_since(current_date: pd.Timestamp) -> int:
        past = spike_dates_dt[spike_dates_dt < current_date]
        if len(past) == 0:
            return 999
        return int((current_date - past.max()).days)

    df["days_since_last_spike"] = df["date"].apply(_days_since)

    # 3. Product mix ratios (what share of demand is each product?)
    total = df[TARGET_COL].replace(0, np.nan)
    df["prbc_mix_ratio"]     = (df["prbc_units"]     / total).fillna(0.0).round(4)
    df["ffp_mix_ratio"]      = (df["ffp_units"]      / total).fillna(0.0).round(4)
    df["platelet_mix_ratio"] = (df["platelet_units"] / total).fillna(0.0).round(4)

    # Sanity: mix ratios must sum to <= 1 (cryo is excluded but minor)
    mix_sum = df["prbc_mix_ratio"] + df["ffp_mix_ratio"] + df["platelet_mix_ratio"]
    if (mix_sum > 1.01).any():
        logger.warning(
            "Mix ratios exceed 1.0 on %d rows -- check product column values.",
            (mix_sum > 1.01).sum(),
        )

    return df


# ---------------------------------------------------------------------------
# Chronological split -- NO shuffle (time-series order must be preserved)
# ---------------------------------------------------------------------------

def chronological_split(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    n         = len(df)
    train_end = int(n * TRAIN_RATIO)
    val_end   = train_end + int(n * VAL_RATIO)

    train = df.iloc[:train_end].copy()
    val   = df.iloc[train_end:val_end].copy()
    test  = df.iloc[val_end:].copy()

    logger.info(
        "Chronological split: train=%d (%s to %s) | val=%d | test=%d",
        len(train), train["date"].iloc[0].date(), train["date"].iloc[-1].date(),
        len(val), len(test),
    )
    return train, val, test


# ---------------------------------------------------------------------------
# Output validation -- confirms contract with Member 2 and Member 3
# ---------------------------------------------------------------------------

def validate_output(df: pd.DataFrame, split_name: str = "full") -> None:
    """
    Verify that the feature matrix satisfies the shared column contract.
    Raises ValueError if any downstream consumer would fail.
    """
    missing = [c for c in REQUIRED_OUTPUT_COLS if c not in df.columns]
    if missing:
        raise ValueError(
            f"[{split_name}] Missing columns required by Member 2 / Member 3: {missing}"
        )

    # No NaN in features (lag/rolling are NaN before dropna -- should all be gone)
    feature_cols = [c for c in REQUIRED_OUTPUT_COLS if c != "date"]
    nan_cols = [c for c in feature_cols if df[c].isna().any()]
    if nan_cols:
        raise ValueError(
            f"[{split_name}] NaN values found in columns: {nan_cols}. "
            "These will silently corrupt model training."
        )

    # Non-negative demand values
    for col in ["prbc_units", "ffp_units", "platelet_units", "cryo_units", "total_units"]:
        if (df[col] < 0).any():
            raise ValueError(f"[{split_name}] Negative values in '{col}'.")

    # Mix ratios in [0, 1]
    for col in ["prbc_mix_ratio", "ffp_mix_ratio", "platelet_mix_ratio"]:
        if (df[col] < 0).any() or (df[col] > 1.0 + 1e-6).any():
            raise ValueError(f"[{split_name}] '{col}' out of [0, 1] range.")

    logger.info("[%s] Validation passed: %d rows x %d cols.", split_name, len(df), len(df.columns))


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def build_features(
    input_path: Path = INPUT_PATH,
    output_dir: Path = OUTPUT_DIR,
) -> pd.DataFrame:
    """
    Full feature engineering pipeline.

    Args:
        input_path: Path to data/mimic_real_demand.csv (output of mimic_extractor.py)
        output_dir: Directory for output CSVs

    Returns:
        Full feature DataFrame (also saved to output_dir/mimic_real_demand_features.csv)
    """
    logger.info("Loading raw demand data from %s ...", input_path)
    df = pd.read_csv(input_path, parse_dates=["date"])
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    logger.info("Loaded %d days of raw demand.", len(df))

    # Feature engineering
    logger.info("Engineering lag features...")
    df = add_lag_features(df)

    logger.info("Engineering rolling features...")
    df = add_rolling_features(df)

    logger.info("Engineering domain features...")
    df = add_domain_features(df)

    # Drop NaN rows introduced by lag/rolling warmup (first max(LAG_DAYS) rows)
    before = len(df)
    df.dropna(subset=[c for c in REQUIRED_OUTPUT_COLS if c != "date"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    dropped = before - len(df)
    logger.info("Dropped %d warmup rows (lag window). %d rows remain.", dropped, len(df))

    # Enforce column order
    extra_cols = [c for c in df.columns if c not in REQUIRED_OUTPUT_COLS]
    df = df[REQUIRED_OUTPUT_COLS + extra_cols]

    # Validate full dataset
    validate_output(df, "full")

    # Save full feature set
    output_dir.mkdir(parents=True, exist_ok=True)
    full_path = output_dir / "mimic_real_demand_features.csv"
    df.to_csv(full_path, index=False)
    logger.info("Full feature set saved -> %s", full_path)

    # Chronological split + validate each split
    train, val, test = chronological_split(df)
    validate_output(train, "train")
    validate_output(val,   "val")
    validate_output(test,  "test")

    train.to_csv(output_dir / "train.csv", index=False)
    val.to_csv(output_dir / "val.csv",     index=False)
    test.to_csv(output_dir / "test.csv",   index=False)
    logger.info("Splits saved: train.csv | val.csv | test.csv -> %s/", output_dir)

    return df


# ---------------------------------------------------------------------------
# CLI runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if not INPUT_PATH.exists():
        print(
            f"\n[!] File not found: {INPUT_PATH}\n"
            "    Run mimic_extractor.py first to generate this file.\n"
        )
        sys.exit(1)

    result = build_features()

    print(f"\n[OK] Feature engineering complete")
    print(f"     Rows     : {len(result)}")
    print(f"     Columns  : {len(result.columns)}")
    print(f"     Date range: {result['date'].min().date()} to {result['date'].max().date()}")
    print(f"\n     Columns produced:")
    for col in result.columns:
        print(f"       {col}")
    print(f"\n     Next step: copy data/train.csv, val.csv, test.csv to member_2_ml_models/data/")
