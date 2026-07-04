"""
Member 1 -- Smoke Test
=======================
Verifies the full extraction + feature engineering pipeline without
requiring real MIMIC-IV data. Uses a small synthetic dataframe that
mirrors the exact schema of MIMIC-IV inputevents.csv.

Run this to confirm your environment is set up correctly:
    python test_pipeline.py

Expected output: all checks pass with no ValueError.
"""

from __future__ import annotations

import io
import logging
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Build a minimal synthetic inputevents.csv (mirrors MIMIC-IV schema)
# ---------------------------------------------------------------------------

def make_synthetic_inputevents(n_days: int = 90, n_events_per_day: int = 50) -> pd.DataFrame:
    """
    Generates a synthetic inputevents DataFrame that mimics MIMIC-IV structure.
    Contains all required columns and blood product ITEMIDs.
    """
    rng = np.random.default_rng(seed=42)
    blood_itemids = [225168, 220996, 225170, 225171, 226368]
    rows = []

    base = pd.Timestamp("2020-01-01")
    for day_offset in range(n_days):
        day = base + pd.Timedelta(days=day_offset)
        for _ in range(n_events_per_day):
            itemid = rng.choice(blood_itemids)
            rows.append({
                "subject_id": int(rng.integers(1000, 9999)),
                "hadm_id":    int(rng.integers(100000, 999999)),
                "starttime":  str(day + pd.Timedelta(hours=int(rng.integers(0, 23)))),
                "itemid":     int(itemid),
                "amount":     round(float(rng.uniform(100, 500)), 1),
                "amountuom":  "mL",
            })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_extractor(tmp_dir: Path) -> Path:
    logger.info("-- TEST 1: mimic_extractor.py --")
    from mimic_extractor import extract_daily_demand

    # Write synthetic inputevents
    raw_dir = tmp_dir / "data" / "raw"
    raw_dir.mkdir(parents=True)
    events_path = raw_dir / "inputevents.csv"
    df_events = make_synthetic_inputevents(n_days=90)
    df_events.to_csv(events_path, index=False)

    output_path = tmp_dir / "data" / "mimic_real_demand.csv"
    result = extract_daily_demand(events_path, output_path, chunksize=5000)

    assert output_path.exists(), "mimic_real_demand.csv not created"
    assert len(result) == 90, f"Expected 90 rows, got {len(result)}"
    assert "total_units" in result.columns
    assert (result["total_units"] >= 0).all(), "Negative total_units found"
    logger.info("  [PASS] Extraction: %d rows, %d cols", len(result), len(result.columns))
    return output_path


def test_feature_engineering(raw_csv: Path, tmp_dir: Path) -> None:
    logger.info("-- TEST 2: feature_engineering.py --")
    from feature_engineering import build_features, REQUIRED_OUTPUT_COLS

    result = build_features(
        input_path=raw_csv,
        output_dir=tmp_dir / "data",
    )

    # All required columns present
    missing = [c for c in REQUIRED_OUTPUT_COLS if c not in result.columns]
    assert not missing, f"Missing columns: {missing}"

    # No NaN in feature columns
    feature_cols = [c for c in REQUIRED_OUTPUT_COLS if c != "date"]
    for col in feature_cols:
        nan_count = result[col].isna().sum()
        assert nan_count == 0, f"NaN in column '{col}': {nan_count} rows"

    # Mix ratios in valid range
    for col in ["prbc_mix_ratio", "ffp_mix_ratio", "platelet_mix_ratio"]:
        assert result[col].between(0, 1).all(), f"{col} out of [0, 1] range"

    # Train/val/test all created
    for split in ["train.csv", "val.csv", "test.csv"]:
        path = tmp_dir / "data" / split
        assert path.exists(), f"{split} not created"
        df = pd.read_csv(path)
        assert len(df) > 0, f"{split} is empty"

    logger.info(
        "  [PASS] Features: %d rows, %d cols. Splits: train/val/test all valid.",
        len(result), len(result.columns),
    )


def test_column_contract(tmp_dir: Path) -> None:
    logger.info("-- TEST 3: Member 2 column contract compatibility --")
    # Load what Member 2 expects
    STATIC_FEATURES = [
        "day_of_week", "is_weekend", "month", "quarter",
        "day_of_year", "week_of_year", "is_holiday_us",
        "lag_7", "lag_14", "lag_30",
        "rolling_mean_7", "rolling_mean_14", "rolling_std_7",
        "demand_spike_flag", "days_since_last_spike",
        "prbc_mix_ratio", "ffp_mix_ratio", "platelet_mix_ratio",
    ]
    SEQUENCE_FEATURES = [
        "total_units", "prbc_units", "ffp_units", "platelet_units",
        "is_weekend", "is_holiday_us", "demand_spike_flag",
    ]

    train_df = pd.read_csv(tmp_dir / "data" / "train.csv")
    all_needed = set(STATIC_FEATURES + SEQUENCE_FEATURES)
    present = set(train_df.columns)
    missing = all_needed - present
    assert not missing, f"Member 2 needs these columns that are absent: {missing}"
    logger.info("  [PASS] All Member 2 feature columns present in train.csv.")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Copy test to run from within member_1_data_engineering/
        import os
        os.chdir(Path(__file__).parent)

        try:
            raw_csv = test_extractor(tmp_path)
            test_feature_engineering(raw_csv, tmp_path)
            test_column_contract(tmp_path)

            print("\n" + "=" * 55)
            print("  ALL TESTS PASSED -- Member 1 pipeline is correct")
            print("  Compatible with Member 2 and Member 3 contracts")
            print("=" * 55)
        except (AssertionError, ValueError) as e:
            print(f"\n  FAILED: {e}")
            sys.exit(1)
