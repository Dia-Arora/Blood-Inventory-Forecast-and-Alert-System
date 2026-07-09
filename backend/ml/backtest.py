"""
Held-out accuracy evaluation for the demand and supply models, exposed via
/api/backtest so the frontend can show actual-vs-predicted charts instead of
only asserting the models are accurate.

Demand: the production LightGBM models (demand_models.pkl) are already
trained on all-but-the-last-30-days per blood type (see train_demand.py), so
we can reuse them directly against that held-out tail -- no retraining.

Supply: the production Prophet models are trained on the full history with
no holdout, so a fair backtest needs its own train-only-on-the-earlier-part
fit. This fit is used only for this evaluation and never saved over
supply_models.pkl.
"""
import os
import warnings

import numpy as np
import pandas as pd
from prophet import Prophet
from sklearn.metrics import mean_absolute_error, mean_squared_error

from config import HOSPITAL_SCALE_FACTOR
from ml.inference import get_demand_models
from ml.train_demand import BLOOD_TYPES, DATA_PATH as DEMAND_DATA_PATH, create_features

SUPPLY_DATA_PATH = os.path.join(os.path.dirname(__file__), '../data/blood_donations.csv')
HOLDOUT_DAYS = 30
FEATURES = ['DayOfWeek', 'Month', 'Quarter', 'DayOfYear', 'DayOfMonth', 'WeekOfYear']

_cache = None


def backtest_demand():
    models = get_demand_models()
    if not models:
        raise Exception("Demand models not trained yet.")

    df = pd.read_csv(DEMAND_DATA_PATH)
    df['date'] = pd.to_datetime(df['date'])

    results = {}
    for bt in BLOOD_TYPES:
        df_bt = df[df['blood_type'] == bt].copy()
        df_bt.set_index('date', inplace=True)
        df_bt.sort_index(inplace=True)
        df_bt = create_features(df_bt)
        test_df = df_bt.iloc[-HOLDOUT_DAYS:]

        preds = models[bt].predict(test_df[FEATURES]) * HOSPITAL_SCALE_FACTOR
        actual = test_df['demand'].to_numpy(dtype=float) * HOSPITAL_SCALE_FACTOR

        results[bt.upper()] = {
            "dates": [d.strftime('%Y-%m-%d') for d in test_df.index],
            "actual": [round(v, 1) for v in actual],
            "predicted": [round(float(v), 1) for v in preds],
            "mae": round(float(mean_absolute_error(actual, preds)), 2),
            "rmse": round(float(np.sqrt(mean_squared_error(actual, preds))), 2),
        }
    return results


def backtest_supply():
    warnings.filterwarnings("ignore")
    df = pd.read_csv(SUPPLY_DATA_PATH)

    results = {}
    for bt in BLOOD_TYPES:
        df_bt = df[df['blood_type'] == bt].copy()
        df_bt = df_bt.rename(columns={'date': 'ds', 'donations': 'y'})
        df_bt['ds'] = pd.to_datetime(df_bt['ds'])
        df_bt = df_bt[df_bt['ds'] > '2019-01-01'].sort_values('ds').reset_index(drop=True)

        train_df = df_bt.iloc[:-HOLDOUT_DAYS]
        test_df = df_bt.iloc[-HOLDOUT_DAYS:]

        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            changepoint_prior_scale=0.05
        )
        model.add_country_holidays(country_name='MY')
        model.fit(train_df)

        forecast = model.predict(test_df[['ds']])
        preds = forecast['yhat'].to_numpy(dtype=float) * HOSPITAL_SCALE_FACTOR
        actual = test_df['y'].to_numpy(dtype=float) * HOSPITAL_SCALE_FACTOR

        results[bt.upper()] = {
            "dates": [d.strftime('%Y-%m-%d') for d in test_df['ds']],
            "actual": [round(v, 1) for v in actual],
            "predicted": [round(float(v), 1) for v in preds],
            "mae": round(float(mean_absolute_error(actual, preds)), 2),
            "rmse": round(float(np.sqrt(mean_squared_error(actual, preds))), 2),
        }
    return results


def run_backtest():
    """Cached in-memory: supply's Prophet refit is expensive, and the
    historical data it evaluates against never changes at runtime."""
    global _cache
    if _cache is None:
        _cache = {"demand": backtest_demand(), "supply": backtest_supply()}
    return _cache
