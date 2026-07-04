"""
Model Evaluation & Benchmarking
================================
Member 2 — ML Lead

Evaluates the Hybrid GRU-LightGBM against standard baselines to quantify
the novel contribution for the IEEE paper.

Baselines compared (based on 2025/2026 literature):
    1. ARIMA (statistical baseline)
    2. XGBoost only
    3. GRU only
    4. Hybrid GRU + LightGBM  ← Our model

Metrics reported (Table II of the paper):
    MAE, RMSE, MAPE, R²

Usage:
    python evaluate.py
"""

import logging
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb

from hybrid_model import HybridDemandForecaster, BloodDemandGRU
from train import (
    load_splits, build_sequences, build_static,
    SEQUENCE_WINDOW, TARGET_COL, STATIC_FEATURES, SEQUENCE_FEATURES,
    GRU_HIDDEN_DIM, GRU_LAYERS, GRU_WEIGHT,
)

logger = logging.getLogger(__name__)

DATA_DIR   = Path("data")
MODEL_DIR  = Path("models")
OUTPUT_DIR = Path("outputs")


def mape(y_true, y_pred):
    mask = y_true != 0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def score(name: str, y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    return {
        "Model": name,
        "MAE":   round(float(mean_absolute_error(y_true, y_pred)), 4),
        "RMSE":  round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 4),
        "MAPE%": round(mape(y_true, y_pred), 4),
        "R²":    round(float(r2_score(y_true, y_pred)), 4),
    }


def evaluate():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    train_df, val_df, test_df = load_splits()

    # Prepare test sequences
    X_test_seq, y_test   = build_sequences(test_df)
    X_test_static        = build_static(test_df)

    # Also need combined val+test for ARIMA-style evaluation
    combined = pd.concat([val_df, test_df]).reset_index(drop=True)

    results = []

    # -----------------------------------------------------------------------
    # Baseline 1: ARIMA (statsmodels)
    # -----------------------------------------------------------------------
    try:
        from statsmodels.tsa.arima.model import ARIMA
        logger.info("Fitting ARIMA(1,1,1)...")
        history = train_df[TARGET_COL].values.tolist()
        arima_preds = []
        for i in range(len(y_test)):
            model = ARIMA(history, order=(1, 1, 1))
            fit   = model.fit()
            pred  = fit.forecast(steps=1)[0]
            arima_preds.append(max(pred, 0.0))
            history.append(test_df[TARGET_COL].iloc[SEQUENCE_WINDOW + i])
        results.append(score("ARIMA(1,1,1)", y_test, np.array(arima_preds)))
    except Exception as e:
        logger.warning("ARIMA skipped: %s", e)

    # -----------------------------------------------------------------------
    # Baseline 2: XGBoost only
    # -----------------------------------------------------------------------
    logger.info("Training XGBoost baseline...")
    cols = [c for c in STATIC_FEATURES if c in train_df.columns]
    xgb_model = xgb.XGBRegressor(n_estimators=300, learning_rate=0.05, max_depth=6, random_state=42)
    xgb_model.fit(
        train_df[cols].values,
        train_df[TARGET_COL].values,
        eval_set=[(val_df[cols].values, val_df[TARGET_COL].values)],
        verbose=False,
    )
    xgb_preds = np.maximum(xgb_model.predict(X_test_static), 0)
    results.append(score("XGBoost (baseline)", y_test, xgb_preds))

    # -----------------------------------------------------------------------
    # Baseline 3: GRU only
    # -----------------------------------------------------------------------
    logger.info("Loading trained GRU for ablation...")
    gru_only = BloodDemandGRU(
        input_dim=X_test_seq.shape[2],
        hidden_dim=GRU_HIDDEN_DIM,
        num_layers=GRU_LAYERS,
    )
    gru_only.load_state_dict(torch.load(MODEL_DIR / "gru_model.pt", map_location="cpu"))
    gru_only.eval()
    with torch.no_grad():
        gru_preds = gru_only(torch.FloatTensor(X_test_seq)).numpy().flatten()
    gru_preds = np.maximum(gru_preds, 0)
    results.append(score("GRU (ablation)", y_test, gru_preds))

    # -----------------------------------------------------------------------
    # Our Model: Hybrid GRU + LightGBM
    # -----------------------------------------------------------------------
    logger.info("Loading Hybrid model...")
    lgb_model = joblib.load(MODEL_DIR / "lgb_model.pkl")
    lgb_preds = np.maximum(lgb_model.predict(X_test_static), 0)
    hybrid_preds = GRU_WEIGHT * gru_preds + (1 - GRU_WEIGHT) * lgb_preds
    hybrid_preds = np.maximum(hybrid_preds, 0)
    results.append(score("Hybrid GRU-LightGBM (ours)", y_test, hybrid_preds))

    # -----------------------------------------------------------------------
    # Print & save Table II
    # -----------------------------------------------------------------------
    metrics_df = pd.DataFrame(results)
    print("\n" + "=" * 65)
    print("TABLE II — MODEL EVALUATION ON MIMIC-IV TEST SET")
    print("=" * 65)
    print(metrics_df.to_string(index=False))
    print("=" * 65)

    metrics_df.to_csv(OUTPUT_DIR / "metrics_table.csv", index=False)
    logger.info("Metrics saved → %s", OUTPUT_DIR / "metrics_table.csv")

    # -----------------------------------------------------------------------
    # Figure: Predicted vs Actual (last 60 days of test set)
    # -----------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(y_test[-60:], label="Actual", color="#111827", linewidth=2.0)
    ax.plot(xgb_preds[-60:],    label="XGBoost",           linestyle="--", color="#f59e0b")
    ax.plot(gru_preds[-60:],    label="GRU (ablation)",     linestyle="-.", color="#3b82f6")
    ax.plot(hybrid_preds[-60:], label="Hybrid GRU-LightGBM (ours)", color="#10b981", linewidth=2.0)
    ax.set_title("Predicted vs Actual Blood Demand — 60-Day Test Window", fontsize=13, fontweight="bold")
    ax.set_xlabel("Day")
    ax.set_ylabel("Total Units Demanded")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "predicted_vs_actual.png", dpi=300)
    logger.info("Figure saved → %s", OUTPUT_DIR / "predicted_vs_actual.png")
    print(f"\n Evaluation complete — results in {OUTPUT_DIR}/")


if __name__ == "__main__":
    evaluate()
