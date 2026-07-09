import pandas as pd
import numpy as np
import joblib
import os
from datetime import datetime, timedelta
from config import DEMAND_SCALE_FACTOR
from ml.demand_split import split_by_type

# Load models safely (they might not exist until training finishes)
DEMAND_MODEL_PATH = os.path.join(os.path.dirname(__file__), 'demand_model.pkl')
SUPPLY_MODELS_PATH = os.path.join(os.path.dirname(__file__), 'supply_models.pkl')

def get_demand_model():
    if os.path.exists(DEMAND_MODEL_PATH):
        return joblib.load(DEMAND_MODEL_PATH)
    return None

def get_supply_models():
    if os.path.exists(SUPPLY_MODELS_PATH):
        return joblib.load(SUPPLY_MODELS_PATH)
    return {}

def predict_demand(days=30):
    """
    Predicts the total blood demand for the next 'days' days.
    Uses LightGBM. Since we need future covariates, we will synthesize realistic
    future features based on historical averages to feed the model.

    The raw model output is multiplied by DEMAND_SCALE_FACTOR (see config.py)
    to reconcile the demand dataset's scale with the real supply dataset's
    much larger scale -- without this, supply always dwarfs demand and the
    simulation never shows a shortage or wastage day.
    """
    model = get_demand_model()
    if not model:
        raise Exception("Demand model not trained yet.")
        
    start_date = datetime.now()
    future_dates = [start_date + timedelta(days=i) for i in range(days)]
    
    # Create future dataframe with synthesized covariates
    df_future = pd.DataFrame({'Date': future_dates})
    df_future.set_index('Date', inplace=True)
    
    # Time features
    df_future['DayOfWeek'] = df_future.index.dayofweek
    df_future['Month'] = df_future.index.month
    df_future['Quarter'] = df_future.index.quarter
    df_future['DayOfYear'] = df_future.index.dayofyear
    df_future['DayOfMonth'] = df_future.index.day
    df_future['WeekOfYear'] = df_future.index.isocalendar().week.astype(int)
    
    # Synthetic covariates based on historical averages from Kaggle dataset
    df_future['Population'] = 180000 
    df_future['Events'] = np.random.choice([0, 1], size=days, p=[0.9, 0.1])
    df_future['HospitalAdmissions'] = np.random.normal(loc=70, scale=15, size=days).astype(int)
    df_future['Temperature'] = np.random.normal(loc=28, scale=5, size=days)
    
    features = ['DayOfWeek', 'Month', 'Quarter', 'DayOfYear', 'DayOfMonth', 'WeekOfYear', 
                'Population', 'Events', 'HospitalAdmissions', 'Temperature']
                
    preds = model.predict(df_future[features])
    
    results = []
    for date, pred in zip(future_dates, preds):
        results.append({
            "date": date.strftime('%Y-%m-%d'),
            "predicted_demand": round(float(pred) * DEMAND_SCALE_FACTOR)
        })
        
    return results


def predict_supply(days=30):
    """
    Predicts blood supply/donations for the next 'days' using Prophet.
    Returns predictions broken down by blood type.
    """
    models = get_supply_models()
    if not models:
        raise Exception("Supply models not trained yet.")
        
    results = {}
    for bt, model in models.items():
        # Prophet future dataframe
        future = model.make_future_dataframe(periods=days)
        # We only want the last 'days'
        forecast = model.predict(future)
        recent_forecast = forecast[['ds', 'yhat']].tail(days)
        
        preds = []
        for _, row in recent_forecast.iterrows():
            preds.append({
                "date": row['ds'].strftime('%Y-%m-%d'),
                "predicted_supply": max(0, round(float(row['yhat'])))
            })
        results[bt.upper()] = preds

    return results


def predict_demand_by_type(days=30):
    """
    Per-blood-type demand: forecasts the aggregate total (LightGBM) and
    disaggregates it via ml.demand_split (see that module for the method).
    """
    total_demand = predict_demand(days)
    return split_by_type(total_demand)
