"""
Feature Engineering Pipeline
==============================
Member 1 — Data Engineering Lead

Takes the raw daily demand CSV from mimic_extractor.py and engineers
the full feature matrix required by the Hybrid GRU-LightGBM model.

Features Engineered
-------------------
Temporal:
    lag_7, lag_14, lag_30     — Demand N days ago (captures weekly patterns)
    rolling_mean_7, _14       — Smoothed trend signal
    rolling_std_7             — Volatility measure (important for emergencies)
    day_of_week, month, etc.  — Already added by extractor

Domain-Specific (Novel):
    demand_spike_flag         — Binary: was yesterday's demand >2σ from 7-day mean?
    days_since_last_spike     — How recently did a demand spike occur?
    product_mix_ratio         — PRBC as fraction of total (blood type mix signal)

Splits:
    Outputs three CSVs: train.csv, val.csv, test.csv (chronological 70/15/15)
"""

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

INPUT_PATH  = Path("data/mimic_real_demand.csv")
OUTPUT_DIR  = Path("data")

TRAIN_RATIO = 0.70
VAL_RATIO   = 0.15
# Test = remaining 0.15

LAG_DAYS        = [7, 14, 30]
ROLLING_WINDOWS = [7, 14]
TARGET_COL      = "total_units"


# ---------------------------------------------------------------------------
# Feature builders
# ---------------------------------------------------------------------------

def add_lag_features(df: pd.DataFrame, col: str = TARGET_COL) -> pd.DataFrame:
    for lag in LAG_DAYS:
        df[f"lag_{lag}"] = df[col].shift(lag)
    return df


def add_rolling_features(df: pd.DataFrame, col: str = TARGET_COL) -> pd.DataFrame:
    for window in ROLLING_WINDOWS:
        df[f"rolling_mean_{window}"] = df[col].shift(1).rolling(window).mean()
    df["rolling_std_7"] = df[col].shift(1).rolling(7).std()
    return df


def add_domain_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Novel domain-specific features for blood demand forecasting.
    These are NOT in standard ML papers — they embed blood supply chain
    domain knowledge directly into the feature space.
    """
    # 1. Demand spike flag: yesterday's demand > mean + 2*std over past 7 days
    rolling_mean = df[TARGET_COL].shift(1).rolling(7).mean()
    rolling_std  = df[TARGET_COL].shift(1).rolling(7).std().fillna(1.0)
    df["demand_spike_flag"] = ((df[TARGET_COL].shift(1)) > (rolling_mean + 2 * rolling_std)).astype(int)

    # 2. Days since last spike (captures post-event recovery windows)
    spike_indices = df.index[df["demand_spike_flag"] == 1].tolist()
    days_since = []
    for i in df.index:
        past = [s for s in spike_indices if s < i]
        days_since.append(i - past[-1] if past else 999)
    df["days_since_last_spike"] = days_since

    # 3. Product mix ratio: PRBC as share of total demand
    if "prbc_units" in df.columns:
        df["prbc_mix_ratio"] = df["prbc_units"] / (df["total_units"].replace(0, np.nan))
        df["prbc_mix_ratio"].fillna(0.0, inplace=True)

    return df


# ---------------------------------------------------------------------------
# Chronological split (NO shuffle — time-series must stay ordered)
# ---------------------------------------------------------------------------

def chronological_split(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    n = len(df)
    train_end = int(n * TRAIN_RATIO)
    val_end   = train_end + int(n * VAL_RATIO)

    train = df.iloc[:train_end].copy()
    val   = df.iloc[train_end:val_end].copy()
    test  = df.iloc[val_end:].copy()

    logger.info(
        "Split: train=%d | val=%d | test=%d", len(train), len(val), len(test)
    )
    return train, val, test


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def build_features(input_path: Path = INPUT_PATH, output_dir: Path = OUTPUT_DIR) -> pd.DataFrame:
    logger.info("Loading demand data from %s", input_path)
    df = pd.read_csv(input_path, parse_dates=["date"])
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)

    logger.info("Engineering features...")
    df = add_lag_features(df)
    df = add_rolling_features(df)
    df = add_domain_features(df)

    # Drop rows with NaN introduced by lag/rolling (first ~30 days)
    before = len(df)
    df.dropna(inplace=True)
    df.reset_index(drop=True, inplace=True)
    logger.info("Dropped %d NaN rows from lag/rolling warmup.", before - len(df))

    # Save full feature set
    output_dir.mkdir(parents=True, exist_ok=True)
    full_path = output_dir / "mimic_real_demand_features.csv"
    df.to_csv(full_path, index=False)
    logger.info("Full feature set → %s  (%d rows, %d cols)", full_path, len(df), len(df.columns))

    # Split and save
    train, val, test = chronological_split(df)
    train.to_csv(output_dir / "train.csv", index=False)
    val.to_csv(output_dir / "val.csv",   index=False)
    test.to_csv(output_dir / "test.csv", index=False)
    logger.info("Train/val/test CSVs saved to %s/", output_dir)

    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    if not INPUT_PATH.exists():
        print(f"[!] Run mimic_extractor.py first to generate {INPUT_PATH}")
        sys.exit(1)
    result = build_features()
    print(f"\n Feature engineering complete — {len(result)} rows, {len(result.columns)} features")
    print(f"   Columns: {result.columns.tolist()}")
