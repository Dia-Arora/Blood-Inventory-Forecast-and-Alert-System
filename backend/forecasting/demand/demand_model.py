"""
forecasting/demand/demand_model.py
-----------------------------------
XGBoost-based blood demand forecasting model.

Responsibilities
----------------
* Load and preprocess the demand CSV.
* Engineer time-based and lag features.
* Train an XGBoost regressor on `HistoricalBloodUsage` (NOT PredictedBloodDemand).
* Evaluate with MAE, RMSE, R².
* Iteratively forecast the next N days.
* Persist and reload the trained model via joblib.
"""

import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor

from config.settings import (
    DEMAND_DATA_PATH,
    DEMAND_MODEL_PATH,
    TRAINED_MODELS_DIR,
    TRAIN_TEST_SPLIT_RATIO,
    XGBOOST_PARAMS,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Feature column names (defined once, used consistently)
# ---------------------------------------------------------------------------
_TARGET_COL = "HistoricalBloodUsage"

# Columns dropped before training (non-features or leakage)
_DROP_COLS = [
    "PredictedBloodDemand",   # explicitly excluded per project spec
    "Date",                    # replaced by engineered time features
]

# Lag / rolling window sizes
_LAG_DAYS = [7, 14, 30]
_ROLLING_WINDOWS = [7, 14]


# ---------------------------------------------------------------------------
# Preprocessing & feature engineering
# ---------------------------------------------------------------------------

def _load_and_preprocess(path: Path) -> pd.DataFrame:
    """
    Load the demand CSV and prepare a clean, feature-rich DataFrame.

    Steps
    -----
    1. Parse `Date` column as datetime.
    2. Drop `PredictedBloodDemand` immediately (never used).
    3. Sort chronologically.
    4. Add time-based features.
    5. Add lag and rolling-mean features on the target.
    6. Drop rows with NaN (introduced by lag/rolling operations at the start).
    """
    logger.info("Loading demand dataset from %s", path)
    df = pd.read_csv(path)

    # 1. Validate required columns are present
    required = {_TARGET_COL, "Date", "DayOfWeek", "Month", "Events",
                "Population", "HospitalAdmissions", "BloodDonorsAvailable", "Temperature"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Demand dataset missing columns: {missing}")

    # 2. Explicitly parse Date column (newer pandas Arrow backend may skip parse_dates)
    df["Date"] = pd.to_datetime(df["Date"], format="mixed", dayfirst=False)

    # 3. Sort chronologically BEFORE dropping Date
    df.sort_values("Date", inplace=True)
    df.reset_index(drop=True, inplace=True)

    # 4. Engineer time-based features from Date BEFORE dropping it
    df["Year"]        = df["Date"].dt.year
    df["Quarter"]     = df["Date"].dt.quarter
    df["DayOfYear"]   = df["Date"].dt.dayofyear
    df["WeekOfYear"]  = df["Date"].dt.isocalendar().week.astype(int)
    df["IsWeekend"]   = (df["Date"].dt.dayofweek >= 5).astype(int)

    # 5. Now drop forbidden columns (PredictedBloodDemand + Date)
    for col in _DROP_COLS:
        if col in df.columns:
            df.drop(columns=[col], inplace=True)

    # 6. Lag features on the target (blood usage N days ago)
    for lag in _LAG_DAYS:
        df[f"lag_{lag}"] = df[_TARGET_COL].shift(lag)

    # 7. Rolling mean features on the target
    for window in _ROLLING_WINDOWS:
        df[f"rolling_mean_{window}"] = (
            df[_TARGET_COL].shift(1).rolling(window=window).mean()
        )

    # 7. Drop NaN rows created by lag / rolling operations
    n_before = len(df)
    df.dropna(inplace=True)
    df.reset_index(drop=True, inplace=True)
    logger.info(
        "Demand preprocessing: %d rows in, %d rows after lag/rolling NA drop.",
        n_before, len(df),
    )

    return df


def _get_feature_columns(df: pd.DataFrame) -> List[str]:
    """Return the ordered list of feature columns (everything except Date & target)."""
    exclude = {_TARGET_COL, "Date"}
    # Preserve stable ordering for reproducibility
    return [c for c in df.columns if c not in exclude]


# ---------------------------------------------------------------------------
# DemandForecaster
# ---------------------------------------------------------------------------

class DemandForecaster:
    """
    Trains and serves an XGBoost model for blood demand forecasting.

    Attributes
    ----------
    model : XGBRegressor or None
        Populated after calling `train()` or `load()`.
    feature_cols : list[str]
        Feature column names used during training (needed for prediction).
    last_known_row : dict
        The most recent row of features from the training data, used as
        the starting point for iterative future prediction.
    """

    def __init__(self) -> None:
        self.model: Optional[XGBRegressor] = None
        self.feature_cols: List[str] = []
        self.last_known_row: Optional[Dict] = None
        self._training_df: Optional[pd.DataFrame] = None  # retained for iterative forecast

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(self) -> Dict[str, float]:
        """
        Load data, engineer features, train XGBoost, evaluate, and save model.

        Returns
        -------
        dict
            Evaluation metrics: MAE, RMSE, R² on the held-out test set.
        """
        df = _load_and_preprocess(DEMAND_DATA_PATH)
        self.feature_cols = _get_feature_columns(df)
        self._training_df = df.copy()

        X = df[self.feature_cols].values
        y = df[_TARGET_COL].values

        # Chronological split (no shuffle)
        split_idx = int(len(df) * TRAIN_TEST_SPLIT_RATIO)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]

        logger.info(
            "Training XGBoost demand model — %d train samples, %d test samples.",
            len(X_train), len(X_test),
        )

        self.model = XGBRegressor(**XGBOOST_PARAMS)
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False,
        )

        # Evaluate
        y_pred = self.model.predict(X_test)
        metrics = {
            "mae":  float(mean_absolute_error(y_test, y_pred)),
            "rmse": float(np.sqrt(mean_squared_error(y_test, y_pred))),
            "r2":   float(r2_score(y_test, y_pred)),
        }
        logger.info(
            "Demand model evaluation — MAE: %.2f | RMSE: %.2f | R²: %.4f",
            metrics["mae"], metrics["rmse"], metrics["r2"],
        )

        # Store the last known feature row for iterative forecasting
        self._update_last_known_row(df)

        # Persist model
        TRAINED_MODELS_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "model": self.model,
                "feature_cols": self.feature_cols,
                "last_known_row": self.last_known_row,
                "last_target_history": df[_TARGET_COL].tolist(),
            },
            DEMAND_MODEL_PATH,
        )
        logger.info("Demand model saved to %s", DEMAND_MODEL_PATH)

        return metrics

    def _update_last_known_row(self, df: pd.DataFrame) -> None:
        """Extract the last row of feature values from the training DataFrame."""
        last = df.iloc[-1]
        self.last_known_row = {col: float(last[col]) for col in self.feature_cols}
        # Also store the target history for rolling lag computation
        self._target_history: List[float] = df[_TARGET_COL].tolist()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def load(self) -> bool:
        """
        Load a previously trained model from disk.

        Returns
        -------
        bool
            True if the model file exists and was loaded successfully.
        """
        if not DEMAND_MODEL_PATH.exists():
            logger.warning("Demand model file not found at %s.", DEMAND_MODEL_PATH)
            return False

        saved = joblib.load(DEMAND_MODEL_PATH)
        self.model = saved["model"]
        self.feature_cols = saved["feature_cols"]
        self.last_known_row = saved["last_known_row"]
        self._target_history = saved["last_target_history"]
        logger.info("Demand model loaded from %s.", DEMAND_MODEL_PATH)
        return True

    def is_trained(self) -> bool:
        """Return True if a model is loaded and ready to predict."""
        return self.model is not None

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict_next_days(self, n: int = 30) -> List[float]:
        """
        Iteratively predict the next `n` days of blood demand.

        The approach:
        1. Start from the last known feature row.
        2. Predict day D, then slide the lag/rolling windows forward
           using the predicted value as a proxy for the actual value.
        3. Repeat for D+1 … D+n-1.

        Parameters
        ----------
        n : int
            Number of days to forecast.

        Returns
        -------
        list of float
            Predicted demand (units) for each of the next n days.
        """
        if not self.is_trained():
            raise RuntimeError("DemandForecaster: model not trained. Call train() or load() first.")

        predictions: List[float] = []
        # Working copy of the feature row — will be mutated each step
        current_row = dict(self.last_known_row)
        # Target history for computing lags/rolling means
        target_history: List[float] = list(self._target_history)

        # Identify which feature columns are lag / rolling columns
        lag_cols    = {f"lag_{lag}": lag for lag in _LAG_DAYS}
        roll_cols   = {f"rolling_mean_{w}": w for w in _ROLLING_WINDOWS}

        # Last known date values (to advance time-based features)
        last_day_of_year = int(current_row.get("DayOfYear", 1))
        last_week_of_year = int(current_row.get("WeekOfYear", 1))
        last_month = int(current_row.get("Month", 1))
        last_quarter = int(current_row.get("Quarter", 1))
        last_dow = int(current_row.get("DayOfWeek", 0))

        # Compute from a reference date (last date + 1)
        # We use today as reference since we don't store the actual last date
        # in the feature row; time fields are inferred from offsets.
        reference_date = date.today()

        for step in range(n):
            forecast_date = reference_date + timedelta(days=step + 1)

            # 1. Update time-based features
            current_row["Year"]       = forecast_date.year
            current_row["Month"]      = forecast_date.month
            current_row["Quarter"]    = (forecast_date.month - 1) // 3 + 1
            current_row["DayOfYear"]  = forecast_date.timetuple().tm_yday
            current_row["WeekOfYear"] = forecast_date.isocalendar()[1]
            current_row["DayOfWeek"]  = forecast_date.weekday()
            current_row["IsWeekend"]  = int(forecast_date.weekday() >= 5)
            # Events default to 0 for future days (no event data available)
            current_row["Events"] = 0.0

            # 2. Update lag features from target history
            for col, lag in lag_cols.items():
                if len(target_history) >= lag:
                    current_row[col] = target_history[-lag]
                # else: leave as-is (edge case for very small history)

            # 3. Update rolling mean features
            for col, window in roll_cols.items():
                if len(target_history) >= window:
                    current_row[col] = float(np.mean(target_history[-window:]))

            # 4. Assemble feature vector in training order
            feature_vector = np.array(
                [current_row.get(col, 0.0) for col in self.feature_cols],
                dtype=float,
            ).reshape(1, -1)

            # 5. Predict and clip to non-negative
            pred = float(self.model.predict(feature_vector)[0])
            pred = max(pred, 0.0)
            predictions.append(pred)

            # 6. Append prediction to history so next step's lags are correct
            target_history.append(pred)

        logger.info("Demand forecast generated: %d days, range %.1f–%.1f units.",
                    n, min(predictions), max(predictions))
        return predictions
