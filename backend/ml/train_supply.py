import pandas as pd
from prophet import Prophet
import joblib
import os
import warnings

# Suppress prophet output
warnings.filterwarnings("ignore")

def train():
    data_path = os.path.join(os.path.dirname(__file__), '../data/blood_donations.csv')
    df = pd.read_csv(data_path)
    
    # We want to train a model for each specific blood type (a, b, ab, o), not just 'all'
    blood_types = ['a', 'b', 'ab', 'o']
    models = {}
    
    for bt in blood_types:
        print(f"Training Prophet model for Blood Type: {bt.upper()}...")
        # Filter for specific blood type
        df_bt = df[df['blood_type'] == bt].copy()
        
        # Prophet requires columns 'ds' (date) and 'y' (target)
        df_bt = df_bt.rename(columns={'date': 'ds', 'donations': 'y'})
        df_bt['ds'] = pd.to_datetime(df_bt['ds'])
        
        # Sort and optionally filter to recent years if data is too huge, let's use last 5 years for relevance
        df_bt = df_bt[df_bt['ds'] > '2019-01-01']
        
        # Initialize and train Prophet
        # SOTA for this type of seasonal data
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            changepoint_prior_scale=0.05
        )
        # Adding Malaysian holidays could improve this, but we'll stick to built-in seasonality
        model.add_country_holidays(country_name='MY')
        
        model.fit(df_bt)
        models[bt] = model
        print(f"Finished training for {bt.upper()}")
        
    # Save the dictionary of models
    model_path = os.path.join(os.path.dirname(__file__), 'supply_models.pkl')
    joblib.dump(models, model_path)
    print(f"All supply models saved to {model_path}")

if __name__ == "__main__":
    train()
