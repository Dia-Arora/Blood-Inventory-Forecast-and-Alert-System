import os
from datetime import datetime, timedelta

import joblib
import pandas as pd

from config import HOSPITAL_SCALE_FACTOR
from simulation.scenario_shocks import demand_shock_multiplier, supply_shock_multiplier

DEMAND_MODELS_PATH = os.path.join(os.path.dirname(__file__), 'demand_models.pkl')
SUPPLY_MODELS_PATH = os.path.join(os.path.dirname(__file__), 'supply_models.pkl')


def get_demand_models():
    if os.path.exists(DEMAND_MODELS_PATH):
        return joblib.load(DEMAND_MODELS_PATH)
    return {}


def get_supply_models():
    if os.path.exists(SUPPLY_MODELS_PATH):
        return joblib.load(SUPPLY_MODELS_PATH)
    return {}


def predict_demand_by_type(days=30):
    """
    Predicts per-blood-type demand for the next 'days' days using the 4
    LightGBM models (one per type), trained purely on calendar features.

    Unlike the old aggregate model, no future covariates need to be
    synthesized/guessed here -- calendar features for a future date are
    always exactly known, so this forecast is fully deterministic: calling
    it twice in a row returns identical results.

    The models are trained on national-scale data; predictions are scaled
    down by HOSPITAL_SCALE_FACTOR (see config.py) to approximate a single
    hospital blood bank rather than the whole country. A deterministic
    scenario-shock layer (see simulation/scenario_shocks.py) is then
    applied on top of the smooth point forecast, since no calendar-based
    model can predict an unforecastable trauma surge -- without this, the
    simulation never shows a real CRITICAL shortage.
    """
    models = get_demand_models()
    if not models:
        raise Exception("Demand models not trained yet.")

    start_date = datetime.now()
    future_dates = [start_date + timedelta(days=i) for i in range(days)]

    df_future = pd.DataFrame({'date': future_dates})
    df_future.set_index('date', inplace=True)
    df_future['DayOfWeek'] = df_future.index.dayofweek
    df_future['Month'] = df_future.index.month
    df_future['Quarter'] = df_future.index.quarter
    df_future['DayOfYear'] = df_future.index.dayofyear
    df_future['DayOfMonth'] = df_future.index.day
    df_future['WeekOfYear'] = df_future.index.isocalendar().week.astype(int)

    features = ['DayOfWeek', 'Month', 'Quarter', 'DayOfYear', 'DayOfMonth', 'WeekOfYear']

    results = {}
    for bt, model in models.items():
        preds = model.predict(df_future[features])
        results[bt.upper()] = [
            {
                "date": date.strftime('%Y-%m-%d'),
                "predicted_demand": max(0, round(float(pred) * HOSPITAL_SCALE_FACTOR * demand_shock_multiplier(bt, date))),
            }
            for date, pred in zip(future_dates, preds)
        ]
    return results


def predict_supply(days=30):
    """
    Predicts blood supply/donations for the next 'days' using Prophet.
    Returns predictions broken down by blood type.

    The models are trained on national-scale data; predictions are scaled
    down by HOSPITAL_SCALE_FACTOR (see config.py) to approximate a single
    hospital blood bank rather than the whole country. A deterministic
    scenario-shock layer (see simulation/scenario_shocks.py) is then
    applied on top of Prophet's smoothed point forecast, since real
    donation shortfalls/gluts are unpredictable in advance -- without
    this, the simulation never shows real wastage risk.
    """
    models = get_supply_models()
    if not models:
        raise Exception("Supply models not trained yet.")

    results = {}
    for bt, model in models.items():
        future = model.make_future_dataframe(periods=days)
        forecast = model.predict(future)
        recent_forecast = forecast[['ds', 'yhat']].tail(days)

        preds = []
        for _, row in recent_forecast.iterrows():
            date_obj = row['ds']
            preds.append({
                "date": date_obj.strftime('%Y-%m-%d'),
                "predicted_supply": max(0, round(float(row['yhat']) * HOSPITAL_SCALE_FACTOR * supply_shock_multiplier(bt, date_obj)))
            })
        results[bt.upper()] = preds

    return results
