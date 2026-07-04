"""
Data Engineering Pipeline: MIMIC-IV Blood Demand Extractor
===========================================================
Member 1 — Data Engineering Lead

Responsibility:
    Convert raw MIMIC-IV clinical transfusion events into a clean,
    analysis-ready daily time-series suitable for the Hybrid GRU-LightGBM model.

Data Source:
    MIMIC-IV (Medical Information Mart for Intensive Care IV)
    Beth Israel Deaconess Medical Center — PhysioNet
    Access: https://physionet.org/content/mimiciv/

Reference:
    Johnson, A. et al. (2023). MIMIC-IV, a freely accessible electronic health
    record dataset. Scientific Data, 10(1), 1.

Pipeline:
    1. Load inputevents.csv from MIMIC-IV ICU module.
    2. Filter for blood product ITEMIDs (verified against d_items table).
    3. Normalise amounts (mL → units, 1 unit ≈ 300 mL for PRBC).
    4. Aggregate to daily totals per product type.
    5. Join with calendar features (day-of-week, holidays, seasonal flags).
    6. Output a clean CSV for model training.

Usage:
    python -m backend.data_generation.mimic_extractor
"""

import logging
from pathlib import Path

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MIMIC-IV blood product ITEMIDs
# Verified from MIMIC-IV d_items table (carevue + metavision)
# Reference: https://mimic.mit.edu/docs/iv/modules/icu/inputevents/
# ---------------------------------------------------------------------------
BLOOD_ITEM_IDS: dict[int, str] = {
    225168: "Packed Red Blood Cells",
    220996: "Fresh Frozen Plasma",
    225170: "Platelets",
    225171: "Cryoprecipitate",
    226368: "OR Packed RBC Intake",   # Operating-room variant
    226370: "OR FFP Intake",
    226372: "OR Platelets Intake",
}

# Approximate mL per clinical unit (standard transfusion medicine reference)
ML_PER_UNIT: dict[str, float] = {
    "Packed Red Blood Cells":  300.0,
    "OR Packed RBC Intake":    300.0,
    "Fresh Frozen Plasma":     250.0,
    "OR FFP Intake":           250.0,
    "Platelets":               300.0,
    "OR Platelets Intake":     300.0,
    "Cryoprecipitate":          15.0,
}

# Canonical output column names (used by downstream hybrid model)
OUTPUT_COLUMNS = [
    "date",
    "prbc_units",        # Packed Red Blood Cells
    "ffp_units",         # Fresh Frozen Plasma
    "platelet_units",    # Platelets
    "cryo_units",        # Cryoprecipitate
    "total_units",       # Sum across all products
    "day_of_week",       # 0 = Monday … 6 = Sunday
    "is_weekend",
    "month",
    "quarter",
    "day_of_year",
    "week_of_year",
    "is_holiday_us",     # US federal holidays (approximate, can localise)
]

PRODUCT_TO_COLUMN = {
    "Packed Red Blood Cells": "prbc_units",
    "OR Packed RBC Intake":   "prbc_units",
    "Fresh Frozen Plasma":    "ffp_units",
    "OR FFP Intake":          "ffp_units",
    "Platelets":              "platelet_units",
    "OR Platelets Intake":    "platelet_units",
    "Cryoprecipitate":        "cryo_units",
}


# ---------------------------------------------------------------------------
# Step 1 — Raw extraction
# ---------------------------------------------------------------------------

def load_inputevents(path: Path, chunksize: int = 500_000) -> pd.DataFrame:
    """
    Load MIMIC-IV inputevents, keeping only relevant columns and rows.

    Uses chunked reading to handle the ~3GB raw file without OOM errors
    on a standard laptop.
    """
    logger.info("Loading MIMIC-IV inputevents from %s ...", path)

    chunks = []
    reader = pd.read_csv(
        path,
        usecols=["subject_id", "hadm_id", "starttime", "itemid", "amount", "amountuom"],
        chunksize=chunksize,
        low_memory=False,
    )

    for i, chunk in enumerate(reader):
        filtered = chunk[chunk["itemid"].isin(BLOOD_ITEM_IDS.keys())]
        if not filtered.empty:
            chunks.append(filtered)
        if (i + 1) % 10 == 0:
            logger.debug("Processed %d chunks...", i + 1)

    if not chunks:
        raise ValueError(
            "No blood transfusion events found. "
            "Check that the correct MIMIC-IV inputevents.csv is provided."
        )

    df = pd.concat(chunks, ignore_index=True)
    logger.info("Extracted %d raw blood transfusion events.", len(df))
    return df


# ---------------------------------------------------------------------------
# Step 2 — Normalise and filter
# ---------------------------------------------------------------------------

def normalise_to_units(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalise raw mL amounts to clinical units.
    Drops rows with zero or negative amounts.
    """
    df = df.copy()
    df["blood_product"] = df["itemid"].map(BLOOD_ITEM_IDS)
    df["ml_per_unit"]   = df["blood_product"].map(ML_PER_UNIT)

    # Only keep rows where amount is in mL; flag for manual review if uom != 'mL'
    df_ml = df[df["amountuom"].str.lower().isin(["ml", "milliliters"])].copy()
    df_unit = df[~df["amountuom"].str.lower().isin(["ml", "milliliters"])].copy()
    if not df_unit.empty:
        logger.warning(
            "%d rows with non-mL units dropped (review amountuom field).", len(df_unit)
        )

    df_ml["units_used"] = df_ml["amount"] / df_ml["ml_per_unit"]
    df_ml = df_ml[df_ml["units_used"] > 0]
    df_ml["output_col"] = df_ml["blood_product"].map(PRODUCT_TO_COLUMN)

    logger.info("Normalised %d events to clinical units.", len(df_ml))
    return df_ml


# ---------------------------------------------------------------------------
# Step 3 — Daily aggregation
# ---------------------------------------------------------------------------

def aggregate_daily(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate individual transfusion events into a daily time-series
    with one row per date.
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["starttime"]).dt.date

    # Pivot: sum units per output column per day
    daily = (
        df.groupby(["date", "output_col"])["units_used"]
        .sum()
        .unstack(fill_value=0.0)
        .reset_index()
    )

    # Ensure all product columns present (hospital may never use some products)
    for col in ["prbc_units", "ffp_units", "platelet_units", "cryo_units"]:
        if col not in daily.columns:
            daily[col] = 0.0

    daily["total_units"] = (
        daily["prbc_units"] + daily["ffp_units"] +
        daily["platelet_units"] + daily["cryo_units"]
    )

    # Enforce chronological order and fill any missing calendar days
    daily["date"] = pd.to_datetime(daily["date"])
    daily.sort_values("date", inplace=True)

    full_range = pd.date_range(daily["date"].min(), daily["date"].max(), freq="D")
    daily = daily.set_index("date").reindex(full_range, fill_value=0.0)
    daily.index.name = "date"
    daily.reset_index(inplace=True)

    logger.info(
        "Aggregated %d days of blood demand (from %s to %s).",
        len(daily), daily["date"].min().date(), daily["date"].max().date()
    )
    return daily


# ---------------------------------------------------------------------------
# Step 4 — Calendar feature engineering
# ---------------------------------------------------------------------------

def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Append temporal features required by the GRU and LightGBM models.

    Note: Holiday calendar uses approximate US federal holidays as proxy.
    Replace with India/local holidays for production deployment.
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])

    df["day_of_week"]  = df["date"].dt.dayofweek          # 0 = Mon
    df["is_weekend"]   = (df["date"].dt.dayofweek >= 5).astype(int)
    df["month"]        = df["date"].dt.month
    df["quarter"]      = df["date"].dt.quarter
    df["day_of_year"]  = df["date"].dt.dayofyear
    df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)

    # Approximate major US holidays (month, day) as binary flag
    # TODO: replace with Indian public holidays via pandas-holiday or a CSV
    US_HOLIDAYS = {(1,1),(7,4),(11,11),(12,25),(12,31),(1,15),(2,19),(5,27),(9,2),(11,28)}
    df["is_holiday_us"] = df["date"].apply(
        lambda d: int((d.month, d.day) in US_HOLIDAYS)
    )

    return df


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def extract_daily_demand(
    inputevents_path: Path,
    output_path: Path,
    chunksize: int = 500_000,
) -> pd.DataFrame:
    """
    Full extraction pipeline: raw MIMIC-IV → clean daily demand CSV.

    Args:
        inputevents_path: Path to MIMIC-IV icu/inputevents.csv
        output_path: Where to write the processed demand CSV
        chunksize: Rows per chunk for memory-efficient loading

    Returns:
        Clean DataFrame with calendar features ready for model training.
    """
    df_raw  = load_inputevents(inputevents_path, chunksize=chunksize)
    df_norm = normalise_to_units(df_raw)
    df_day  = aggregate_daily(df_norm)
    df_feat = add_calendar_features(df_day)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_feat.to_csv(output_path, index=False)
    logger.info("Saved processed demand dataset → %s", output_path)
    return df_feat


# ---------------------------------------------------------------------------
# CLI runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    INPUT  = Path("datasets/mimic_iv/icu/inputevents.csv")
    OUTPUT = Path("datasets/demand/mimic_real_demand.csv")

    if not INPUT.exists():
        print(
            f"\n[!] File not found: {INPUT}\n"
            "    Please download MIMIC-IV from PhysioNet and place\n"
            "    inputevents.csv at the path above.\n"
            "    Access: https://physionet.org/content/mimiciv/\n"
        )
        sys.exit(1)

    result = extract_daily_demand(INPUT, OUTPUT)
    print(f"\n Extraction complete — {len(result)} days written to {OUTPUT}")
    print(result.tail())
