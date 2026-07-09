import os

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

DATA_PATH = os.path.join(os.path.dirname(__file__), '../data/blood_demand.csv')
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'demand_models.pkl')
BLOOD_TYPES = ['a', 'b', 'ab', 'o']


def create_features(df):
    """Create time series features based on the DataFrame's date index."""
    df = df.copy()
    df['DayOfWeek'] = df.index.dayofweek
    df['Month'] = df.index.month
    df['Quarter'] = df.index.quarter
    df['DayOfYear'] = df.index.dayofyear
    df['DayOfMonth'] = df.index.day
    df['WeekOfYear'] = df.index.isocalendar().week.astype(int)
    return df


def train():
    df = pd.read_csv(DATA_PATH)
    df['date'] = pd.to_datetime(df['date'])

    features = ['DayOfWeek', 'Month', 'Quarter', 'DayOfYear', 'DayOfMonth', 'WeekOfYear']
    models = {}

    for bt in BLOOD_TYPES:
        print(f"Training LightGBM model for Blood Demand: {bt.upper()}...")
        df_bt = df[df['blood_type'] == bt].copy()
        df_bt.set_index('date', inplace=True)
        df_bt.sort_index(inplace=True)
        df_bt = create_features(df_bt)

        train_df = df_bt.iloc[:-30]
        test_df = df_bt.iloc[-30:]

        X_train, y_train = train_df[features], train_df['demand']
        X_test, y_test = test_df[features], test_df['demand']

        model = lgb.LGBMRegressor(
            n_estimators=500,
            learning_rate=0.05,
            max_depth=6,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42
        )
        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            callbacks=[lgb.early_stopping(stopping_rounds=50)]
        )

        preds = model.predict(X_test)
        mae = mean_absolute_error(y_test, preds)
        rmse = np.sqrt(mean_squared_error(y_test, preds))
        print(f"{bt.upper()} Test MAE: {mae:.2f}")
        print(f"{bt.upper()} Test RMSE: {rmse:.2f}")

        models[bt] = model

    joblib.dump(models, MODEL_PATH)
    print(f"All demand models saved to {MODEL_PATH}")


if __name__ == "__main__":
    train()
