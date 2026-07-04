"""
MIMIC-IV Blood Demand Extractor
=================================
Member 1 -- Data Engineering Lead

Extracts real-world blood transfusion events from the MIMIC-IV clinical
database and produces a clean, analysis-ready daily time-series CSV.

Data Source:
    MIMIC-IV (Medical Information Mart for Intensive Care IV)
    Beth Israel Deaconess Medical Center -- PhysioNet
    Access: https://physionet.org/content/mimiciv/
    Citation: Johnson AEW et al. (2023). Scientific Data, 10(1), 1.

Output columns (defined in shared/config/columns.py):
    date, prbc_units, ffp_units, platelet_units, cryo_units, total_units,
    day_of_week, is_weekend, month, quarter, day_of_year, week_of_year,
    is_holiday_us

Usage:
    python mimic_extractor.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MIMIC-IV blood product ITEMIDs
# Source: MIMIC-IV d_items table (verified against metavision)
# https://mimic.mit.edu/docs/iv/modules/icu/inputevents/
# ---------------------------------------------------------------------------
BLOOD_ITEM_IDS: dict[int, str] = {
    225168: "Packed Red Blood Cells",
    220996: "Fresh Frozen Plasma",
    225170: "Platelets",
    225171: "Cryoprecipitate",
    226368: "Packed Red Blood Cells",   # OR variant
    226370: "Fresh Frozen Plasma",      # OR variant
    226372: "Platelets",               # OR variant
}

# mL per clinical unit (AABB Technical Manual, 20th Edition)
ML_PER_UNIT: dict[str, float] = {
    "Packed Red Blood Cells": 300.0,
    "Fresh Frozen Plasma":    250.0,
    "Platelets":              300.0,
    "Cryoprecipitate":         15.0,
}

# MIMIC product name -> output column name (must match shared/config/columns.py)
PRODUCT_TO_COLUMN: dict[str, str] = {
    "Packed Red Blood Cells": "prbc_units",
    "Fresh Frozen Plasma":    "ffp_units",
    "Platelets":              "platelet_units",
    "Cryoprecipitate":        "cryo_units",
}

# Approximate US federal holidays (month, day) as a proxy
# TODO: replace with Indian public holidays for production deployment
_US_HOLIDAYS: set[tuple[int, int]] = {
    (1, 1), (1, 15), (2, 19), (5, 27), (7, 4),
    (9, 2), (11, 11), (11, 28), (12, 25), (12, 31),
}


# ---------------------------------------------------------------------------
# Step 1 -- Raw extraction (chunked for memory efficiency)
# ---------------------------------------------------------------------------

def load_inputevents(path: Path, chunksize: int = 500_000) -> pd.DataFrame:
    """
    Load MIMIC-IV inputevents.csv filtering only blood product rows.
    Uses chunked reading to handle the ~3 GB file on 8 GB RAM machines.
    """
    required_cols = ["subject_id", "hadm_id", "starttime", "itemid", "amount", "amountuom"]

    logger.info("Loading MIMIC-IV inputevents from %s ...", path)
    chunks = []

    try:
        reader = pd.read_csv(
            path,
            usecols=required_cols,
            chunksize=chunksize,
            low_memory=False,
        )
    except ValueError as e:
        raise ValueError(
            f"inputevents.csv is missing expected columns. "
            f"Ensure you are using the MIMIC-IV ICU module (not MIMIC-III). "
            f"Original error: {e}"
        ) from e

    for i, chunk in enumerate(reader):
        filtered = chunk[chunk["itemid"].isin(BLOOD_ITEM_IDS.keys())]
        if not filtered.empty:
            chunks.append(filtered)
        if (i + 1) % 20 == 0:
            logger.debug("Processed %d chunks...", i + 1)

    if not chunks:
        raise ValueError(
            "No blood transfusion events found in inputevents.csv. "
            "Verify that BLOOD_ITEM_IDS match your MIMIC-IV version's d_items table."
        )

    df = pd.concat(chunks, ignore_index=True)
    logger.info("Extracted %d raw transfusion events.", len(df))
    return df


# ---------------------------------------------------------------------------
# Step 2 -- Normalise to clinical units
# ---------------------------------------------------------------------------

def normalise_to_units(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert mL amounts to clinical units and map to output column names.
    Drops rows where amountuom is not mL (logged as a warning).
    """
    df = df.copy()
    df["blood_product"] = df["itemid"].map(BLOOD_ITEM_IDS)
    df["ml_per_unit"]   = df["blood_product"].map(ML_PER_UNIT)
    df["output_col"]    = df["blood_product"].map(PRODUCT_TO_COLUMN)

    # Split mL vs non-mL
    is_ml = df["amountuom"].str.lower().isin(["ml", "milliliters", "milliliter"])
    df_ml   = df[is_ml].copy()
    df_other = df[~is_ml]

    if not df_other.empty:
        logger.warning(
            "%d rows dropped: non-mL amountuom values %s",
            len(df_other),
            df_other["amountuom"].unique().tolist()[:5],
        )

    df_ml["units_used"] = df_ml["amount"] / df_ml["ml_per_unit"]

    # Remove zero/negative amounts (data quality)
    before = len(df_ml)
    df_ml = df_ml[df_ml["units_used"] > 0].copy()
    logger.info(
        "Normalised %d events to clinical units (%d dropped as zero/negative).",
        len(df_ml), before - len(df_ml),
    )
    return df_ml


# ---------------------------------------------------------------------------
# Step 3 -- Daily aggregation
# ---------------------------------------------------------------------------

def aggregate_daily(df: pd.DataFrame) -> pd.DataFrame:
    """
    Group transfusion events by calendar day and output column.
    Fills missing calendar days with zero (no demand = 0 units, not NaN).
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["starttime"]).dt.normalize()  # midnight

    daily = (
        df.groupby(["date", "output_col"])["units_used"]
        .sum()
        .unstack(fill_value=0.0)
        .reset_index()
    )

    # Ensure all product columns exist even if never recorded
    for col in ["prbc_units", "ffp_units", "platelet_units", "cryo_units"]:
        if col not in daily.columns:
            logger.warning("Column %s absent from data -- filling with 0.", col)
            daily[col] = 0.0

    daily["total_units"] = (
        daily["prbc_units"] + daily["ffp_units"] +
        daily["platelet_units"] + daily["cryo_units"]
    )

    # Fill complete calendar range (no gaps)
    daily.sort_values("date", inplace=True)
    full_range = pd.date_range(daily["date"].min(), daily["date"].max(), freq="D")
    daily = (
        daily.set_index("date")
        .reindex(full_range, fill_value=0.0)
        .rename_axis("date")
        .reset_index()
    )

    # Recalculate total_units after reindex (fill_value may overwrite it)
    daily["total_units"] = (
        daily["prbc_units"] + daily["ffp_units"] +
        daily["platelet_units"] + daily["cryo_units"]
    )

    logger.info(
        "Daily aggregation: %d days (%s to %s).",
        len(daily),
        daily["date"].min().date(),
        daily["date"].max().date(),
    )
    return daily


# ---------------------------------------------------------------------------
# Step 4 -- Calendar feature engineering
# ---------------------------------------------------------------------------

def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add temporal features consumed by Member 2's GRU and LightGBM models.
    Column names must match shared/config/columns.py::CALENDAR_COLS exactly.
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])

    df["day_of_week"]  = df["date"].dt.dayofweek              # 0=Monday
    df["is_weekend"]   = (df["date"].dt.dayofweek >= 5).astype(int)
    df["month"]        = df["date"].dt.month
    df["quarter"]      = df["date"].dt.quarter
    df["day_of_year"]  = df["date"].dt.dayofyear
    df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)
    df["is_holiday_us"] = df["date"].apply(
        lambda d: int((d.month, d.day) in _US_HOLIDAYS)
    )
    return df


# ---------------------------------------------------------------------------
# Step 5 -- Output validation
# ---------------------------------------------------------------------------

def validate_output(df: pd.DataFrame) -> None:
    """
    Verify the extraction output satisfies the shared column contract.
    Raises ValueError if any required column is missing or has invalid dtype.
    """
    from pathlib import Path as _Path
    import sys as _sys
    # Inline required columns to avoid import path issues
    required = [
        "date", "prbc_units", "ffp_units", "platelet_units", "cryo_units",
        "total_units", "day_of_week", "is_weekend", "month", "quarter",
        "day_of_year", "week_of_year", "is_holiday_us",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Output is missing required columns: {missing}")

    # Numeric sanity checks
    for col in ["prbc_units", "ffp_units", "platelet_units", "cryo_units", "total_units"]:
        if (df[col] < 0).any():
            raise ValueError(f"Negative values found in column '{col}'.")

    # total_units must equal sum of products
    recomputed = df["prbc_units"] + df["ffp_units"] + df["platelet_units"] + df["cryo_units"]
    if not np.allclose(df["total_units"], recomputed, atol=0.01):
        raise ValueError("total_units does not equal sum of product columns.")

    # No missing dates (full calendar range)
    date_range = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
    if len(df) != len(date_range):
        raise ValueError(
            f"Date gaps detected: expected {len(date_range)} days, got {len(df)}."
        )

    logger.info("Output validation passed: %d rows, %d cols.", len(df), len(df.columns))


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def extract_daily_demand(
    inputevents_path: Path,
    output_path: Path,
    chunksize: int = 500_000,
) -> pd.DataFrame:
    """
    Full extraction pipeline: MIMIC-IV inputevents.csv -> clean daily demand CSV.

    Args:
        inputevents_path: Path to MIMIC-IV icu/inputevents.csv
        output_path:      Destination CSV (e.g. data/mimic_real_demand.csv)
        chunksize:        Rows per read chunk (tune for available RAM)

    Returns:
        Validated DataFrame ready for feature_engineering.py
    """
    df_raw   = load_inputevents(inputevents_path, chunksize)
    df_norm  = normalise_to_units(df_raw)
    df_day   = aggregate_daily(df_norm)
    df_feat  = add_calendar_features(df_day)

    # Enforce column order from shared contract
    col_order = [
        "date", "prbc_units", "ffp_units", "platelet_units", "cryo_units",
        "total_units", "day_of_week", "is_weekend", "month", "quarter",
        "day_of_year", "week_of_year", "is_holiday_us",
    ]
    df_feat = df_feat[col_order]

    validate_output(df_feat)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_feat.to_csv(output_path, index=False)
    logger.info("Saved validated demand dataset -> %s", output_path)
    return df_feat


# ---------------------------------------------------------------------------
# CLI runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="%(levelname)s %(name)s: %(message)s",
    )

    INPUT  = Path("data/raw/inputevents.csv")
    OUTPUT = Path("data/mimic_real_demand.csv")

    if not INPUT.exists():
        print(
            f"\n[!] File not found: {INPUT}\n\n"
            "    To use real MIMIC-IV data:\n"
            "    1. Complete training at https://physionet.org/\n"
            "    2. Sign the MIMIC-IV Data Use Agreement\n"
            "    3. Download inputevents.csv from the ICU module\n"
            "    4. Place it at: member_1_data_engineering/data/raw/inputevents.csv\n"
        )
        sys.exit(1)

    result = extract_daily_demand(INPUT, OUTPUT)
    print(f"\n[OK] Extraction complete: {len(result)} days -> {OUTPUT}")
    print(f"     Date range : {result['date'].min().date()} to {result['date'].max().date()}")
    print(f"     Avg daily total units: {result['total_units'].mean():.1f}")
    print(f"\n     Next step: python feature_engineering.py")
