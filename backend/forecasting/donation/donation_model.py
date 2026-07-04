"""
forecasting/donation/donation_model.py
---------------------------------------
Facebook Prophet-based blood donation forecasting.

Four independent Prophet models are trained — one per ABO blood group
(A, B, AB, O) — using only the rows where blood_type matches that group.

The ``all`` rows are filtered out immediately at load time and are never
used for training or evaluation.

Output format
-------------
predict_next_days(n) returns a dict:
    {
        "A":  [float, ...],   # n values
        "B":  [float, ...],
        "AB": [float, ...],
        "O":  [float, ...],
    }
"""

import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import joblib
import pandas as pd
from prophet import Prophet

from config.settings import (
    BLOOD_GROUPS,
    DONATION_DATA_PATH,
    PROPHET_PARAMS,
    TRAINED_MODELS_DIR,
    donation_model_path,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

def _load_group_dataframe(path: Path, blood_group: str) -> pd.DataFrame:
    """
    Load and filter the donation CSV for a single blood group.

    Steps
    -----
    1. Read CSV, parse dates.
    2. Filter to rows where blood_type == blood_group (case-insensitive).
       The ``all`` aggregate rows are excluded because they don't match any
       specific group string.
    3. Rename to Prophet-required column names: ``ds`` and ``y``.
    4. Sort chronologically and drop duplicates.
    5. Clip negative donation values to 0 (data quality guard).

    Parameters
    ----------
    blood_group : str
        One of {"A", "B", "AB", "O"} (uppercase).

    Returns
    -------
    pd.DataFrame
        Columns: ds (datetime), y (float donations).
    """
    df = pd.read_csv(path)

    # Explicitly parse date column (Arrow backend may not auto-convert with parse_dates)
    df["date"] = pd.to_datetime(df["date"], format="mixed", dayfirst=False)

    # Filter for this blood group (the CSV stores lowercase: 'a', 'b', 'ab', 'o')
    mask = df["blood_type"].str.strip().str.lower() == blood_group.lower()
    df_group = df[mask][["date", "donations"]].copy()

    if df_group.empty:
        raise ValueError(
            f"No donation records found for blood group '{blood_group}' in {path}. "
            f"Available types: {df['blood_type'].unique().tolist()}"
        )

    # Rename to Prophet convention
    df_group.rename(columns={"date": "ds", "donations": "y"}, inplace=True)

    # Sort and deduplicate
    df_group.sort_values("ds", inplace=True)
    df_group.drop_duplicates(subset="ds", inplace=True)
    df_group.reset_index(drop=True, inplace=True)

    # Clip negatives
    df_group["y"] = df_group["y"].clip(lower=0)

    logger.info(
        "Group %s donation data: %d records, %s → %s",
        blood_group,
        len(df_group),
        df_group["ds"].min().date(),
        df_group["ds"].max().date(),
    )

    return df_group


# ---------------------------------------------------------------------------
# DonationForecaster
# ---------------------------------------------------------------------------

class DonationForecaster:
    """
    Trains and serves four independent Prophet models for donation forecasting.

    One model per ABO blood group: A, B, AB, O.
    Models are trained on the per-group historical donation rows only.
    The ``all`` rows from the CSV are never used.

    Attributes
    ----------
    models : dict[str, Prophet]
        Keyed by blood group string. Populated by train() or load().
    """

    def __init__(self) -> None:
        self.models: Dict[str, Prophet] = {}

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(self) -> Dict[str, Dict[str, float]]:
        """
        Train a separate Prophet model for each blood group.

        Returns
        -------
        dict
            Keyed by blood group; values are evaluation dicts with
            ``mean_absolute_error`` on the last 10% of training data.
        """
        TRAINED_MODELS_DIR.mkdir(parents=True, exist_ok=True)
        metrics: Dict[str, Dict[str, float]] = {}

        for group in BLOOD_GROUPS:
            logger.info("Training Prophet model for blood group %s...", group)
            df_group = _load_group_dataframe(DONATION_DATA_PATH, group)

            # Suppress Prophet's verbose output by suppressing its internal logger
            _silence_prophet_logging()

            model = Prophet(**PROPHET_PARAMS)
            model.fit(df_group)

            # In-sample evaluation on the last 10% of the data
            eval_metrics = _evaluate_prophet(model, df_group)
            metrics[group] = eval_metrics
            logger.info(
                "Group %s — MAE: %.2f | RMSE: %.2f",
                group, eval_metrics["mae"], eval_metrics["rmse"],
            )

            # Save model
            model_path = donation_model_path(group)
            joblib.dump(model, model_path)
            logger.info("Prophet model for group %s saved to %s", group, model_path)

            self.models[group] = model

        return metrics

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def load(self) -> bool:
        """
        Load all four Prophet models from disk.

        Returns
        -------
        bool
            True if all four models were found and loaded.
            False if any model file is missing (caller should retrain).
        """
        all_loaded = True
        for group in BLOOD_GROUPS:
            path = donation_model_path(group)
            if path.exists():
                self.models[group] = joblib.load(path)
                logger.info("Prophet model for group %s loaded from %s.", group, path)
            else:
                logger.warning(
                    "Prophet model for group %s not found at %s.", group, path
                )
                all_loaded = False

        return all_loaded

    def is_trained(self) -> bool:
        """Return True only if all four group models are loaded."""
        return len(self.models) == len(BLOOD_GROUPS) and all(
            g in self.models for g in BLOOD_GROUPS
        )

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict_next_days(self, n: int = 30) -> Dict[str, List[float]]:
        """
        Forecast donations for each blood group over the next ``n`` days.

        Parameters
        ----------
        n : int
            Number of days to forecast (starting from tomorrow).

        Returns
        -------
        dict[str, list[float]]
            Keys: "A", "B", "AB", "O".
            Values: list of n non-negative predicted donation counts.
        """
        if not self.is_trained():
            raise RuntimeError(
                "DonationForecaster: models not trained. Call train() or load() first."
            )

        results: Dict[str, List[float]] = {}

        for group in BLOOD_GROUPS:
            model = self.models[group]

            # Prophet requires a future DataFrame with column 'ds'
            future_dates = _make_future_dates(n)
            future_df = pd.DataFrame({"ds": future_dates})

            forecast = model.predict(future_df)

            # ``yhat`` is the point estimate; clip negatives (Prophet can produce them)
            values = forecast["yhat"].clip(lower=0).tolist()
            results[group] = [float(v) for v in values]

        logger.info(
            "Donation forecast generated: %d days per group. "
            "Totals — A: %.0f, B: %.0f, AB: %.0f, O: %.0f",
            n,
            sum(results["A"]),
            sum(results["B"]),
            sum(results["AB"]),
            sum(results["O"]),
        )

        return results

    def predict_single_day(self, target_date: date) -> Dict[str, float]:
        """
        Forecast donations for each blood group for a specific single date.

        Parameters
        ----------
        target_date : date

        Returns
        -------
        dict[str, float]
            {"A": float, "B": float, "AB": float, "O": float}
        """
        if not self.is_trained():
            raise RuntimeError("DonationForecaster: models not trained.")

        result: Dict[str, float] = {}
        future_df = pd.DataFrame({"ds": [pd.Timestamp(target_date)]})

        for group in BLOOD_GROUPS:
            forecast = self.models[group].predict(future_df)
            val = float(forecast["yhat"].clip(lower=0).iloc[0])
            result[group] = val

        return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_future_dates(n: int) -> List[pd.Timestamp]:
    """Return a list of n Timestamps starting from tomorrow."""
    start = date.today() + timedelta(days=1)
    return [pd.Timestamp(start + timedelta(days=i)) for i in range(n)]


def _evaluate_prophet(model: Prophet, df: pd.DataFrame) -> Dict[str, float]:
    """
    Compute in-sample MAE and RMSE on the last 10% of the training data.

    Prophet is refitted on the first 90% then evaluated on the final 10%.
    This avoids data leakage while still giving an approximation of model quality.
    """
    import numpy as np

    split_idx = int(len(df) * 0.90)
    train_df = df.iloc[:split_idx].copy()
    test_df  = df.iloc[split_idx:].copy()

    _silence_prophet_logging()
    eval_model = Prophet(**PROPHET_PARAMS)
    eval_model.fit(train_df)

    forecast = eval_model.predict(test_df[["ds"]])
    y_true = test_df["y"].values
    y_pred = forecast["yhat"].clip(lower=0).values

    mae  = float(np.mean(np.abs(y_true - y_pred)))
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

    return {"mae": mae, "rmse": rmse}


def _silence_prophet_logging() -> None:
    """Suppress Prophet's (and cmdstanpy's) verbose output."""
    import logging as _logging
    _logging.getLogger("prophet").setLevel(_logging.WARNING)
    _logging.getLogger("cmdstanpy").setLevel(_logging.WARNING)
