"""
Full Training Pipeline: Hybrid GRU + LightGBM
==============================================
Member 2 — ML Lead

Trains the ensemble model on the feature-engineered MIMIC-IV dataset
produced by Member 1. Saves trained model artifacts to models/.

Usage:
    python train.py
"""

import logging
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch

from hybrid_model import HybridDemandForecaster, BloodDemandGRU

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DATA_DIR   = Path("data")
MODEL_DIR  = Path("models")
OUTPUT_DIR = Path("outputs")

SEQUENCE_WINDOW = 30          # Days of history fed to GRU per prediction
TARGET_COL      = "total_units"
GRU_EPOCHS      = 30
GRU_HIDDEN_DIM  = 64
GRU_LAYERS      = 2
GRU_WEIGHT      = 0.60        # Ensemble weighting (based on 2025 literature)

# Features used by LightGBM (static, non-sequential)
STATIC_FEATURES = [
    "day_of_week", "is_weekend", "month", "quarter",
    "day_of_year", "week_of_year", "is_holiday_us",
    "lag_7", "lag_14", "lag_30",
    "rolling_mean_7", "rolling_mean_14", "rolling_std_7",
    "demand_spike_flag", "days_since_last_spike", "prbc_mix_ratio",
]

# Features used by GRU (temporal sequences)
SEQUENCE_FEATURES = [
    "total_units", "prbc_units", "ffp_units", "platelet_units",
    "is_weekend", "is_holiday_us", "demand_spike_flag",
]


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

def load_splits() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train = pd.read_csv(DATA_DIR / "train.csv", parse_dates=["date"])
    val   = pd.read_csv(DATA_DIR / "val.csv",   parse_dates=["date"])
    test  = pd.read_csv(DATA_DIR / "test.csv",  parse_dates=["date"])
    logger.info("Loaded train=%d, val=%d, test=%d rows.", len(train), len(val), len(test))
    return train, val, test


def build_sequences(df: pd.DataFrame, window: int = SEQUENCE_WINDOW):
    """Convert a flat DataFrame into 3-D sequences for the GRU."""
    cols = [c for c in SEQUENCE_FEATURES if c in df.columns]
    values = df[cols].values
    X, y = [], []
    for i in range(len(values) - window):
        X.append(values[i : i + window])
        y.append(df[TARGET_COL].iloc[i + window])
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


def build_static(df: pd.DataFrame, window: int = SEQUENCE_WINDOW):
    """Static features aligned with the sequence target (offset by window)."""
    cols = [c for c in STATIC_FEATURES if c in df.columns]
    return df[cols].iloc[window:].values.astype(np.float32)


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    if not (DATA_DIR / "train.csv").exists():
        print("[!] data/train.csv not found. Run Member 1's pipeline first.")
        sys.exit(1)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    train_df, val_df, test_df = load_splits()

    # --- Prepare sequences ---
    logger.info("Building GRU sequences (window=%d)...", SEQUENCE_WINDOW)
    X_train_seq, y_train = build_sequences(train_df)
    X_val_seq,   y_val   = build_sequences(val_df)

    # --- Prepare static features ---
    X_train_static = build_static(train_df)
    X_val_static   = build_static(val_df)

    # --- Infer input dims ---
    seq_input_dim    = X_train_seq.shape[2]
    static_input_dim = X_train_static.shape[1]
    logger.info("GRU input dim: %d | LightGBM input dim: %d", seq_input_dim, static_input_dim)

    # --- Build & train model ---
    forecaster = HybridDemandForecaster(
        seq_input_dim=seq_input_dim,
        static_input_dim=static_input_dim,
        hidden_dim=GRU_HIDDEN_DIM,
        num_layers=GRU_LAYERS,
    )

    logger.info("=== Training GRU ===")
    forecaster.train_gru(X_train_seq, y_train, epochs=GRU_EPOCHS)

    logger.info("=== Training LightGBM ===")
    forecaster.train_lightgbm(X_train_static, y_train)

    # --- Save artifacts ---
    torch.save(forecaster.gru_model.state_dict(), MODEL_DIR / "gru_model.pt")
    joblib.dump(forecaster.lgb_model, MODEL_DIR / "lgb_model.pkl")
    logger.info("Models saved to %s/", MODEL_DIR)

    # --- Quick validation ---
    val_preds = forecaster.predict(X_val_seq, X_val_static, gru_weight=GRU_WEIGHT)
    mae = float(np.mean(np.abs(val_preds - y_val)))
    rmse = float(np.sqrt(np.mean((val_preds - y_val) ** 2)))
    logger.info("Validation — MAE: %.3f | RMSE: %.3f", mae, rmse)
    print(f"\n Training complete — Val MAE: {mae:.3f} | Val RMSE: {rmse:.3f}")
    print(f"   Artifacts saved to {MODEL_DIR}/")


if __name__ == "__main__":
    train()
