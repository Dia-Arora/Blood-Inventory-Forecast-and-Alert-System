import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib
import os

def create_features(df):
    """Create time series features based on time series index."""
    df = df.copy()
    df['DayOfWeek'] = df.index.dayofweek
    df['Month'] = df.index.month
    df['Quarter'] = df.index.quarter
    df['DayOfYear'] = df.index.dayofyear
    df['DayOfMonth'] = df.index.day
    df['WeekOfYear'] = df.index.isocalendar().week.astype(int)
    return df

def train():
    data_path = os.path.join(os.path.dirname(__file__), '../data/blood_demand.csv')
    df = pd.read_csv(data_path)
    
    # Preprocessing
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    df.sort_index(inplace=True)
    
    # Feature Engineering
    df = create_features(df)
    
    # Features and Target
    # We predict 'PredictedBloodDemand' based on historical covariates
    target = 'PredictedBloodDemand'
    # We only use features that would be available or forecastable in reality
    # Note: If we don't have future HospitalAdmissions, we might use lags, but for this dataset we'll use the provided features
    features = ['DayOfWeek', 'Month', 'Quarter', 'DayOfYear', 'DayOfMonth', 'WeekOfYear', 
                'Population', 'Events', 'HospitalAdmissions', 'Temperature']
    
    # Train/Test Split (Time Series Split: last 30 days for testing)
    train_df = df.iloc[:-30]
    test_df = df.iloc[-30:]
    
    X_train = train_df[features]
    y_train = train_df[target]
    
    X_test = test_df[features]
    y_test = test_df[target]
    
    # Model Training (SOTA LightGBM)
    model = lgb.LGBMRegressor(
        n_estimators=500,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42
    )
    
    print("Training LightGBM model for Blood Demand...")
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        callbacks=[lgb.early_stopping(stopping_rounds=50)]
    )
    
    # Evaluation
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    print(f"Test MAE: {mae:.2f}")
    print(f"Test RMSE: {rmse:.2f}")
    
    # Save Model
    model_path = os.path.join(os.path.dirname(__file__), 'demand_model.pkl')
    joblib.dump(model, model_path)
    print(f"Model saved to {model_path}")

if __name__ == "__main__":
    train()
