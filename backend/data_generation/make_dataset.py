import os
import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime, timedelta

# ==========================================
# 1. Configuration & Setup
# ==========================================
np.random.seed(42)
Faker.seed(42)
fake = Faker('en_IN') # Indian context for hospital names

START_DATE = '2021-01-01'
END_DATE = '2023-12-31'
N_HOSPITALS = 5

# Indian Population Blood Group Distribution Approx
# O+: 37%, B+: 32%, A+: 22%, AB+: 7%, Negatives ~2% (0.5% each to sum to ~100%)
BLOOD_GROUPS = {
    'O+': 0.37, 'A+': 0.22, 'B+': 0.32, 'AB+': 0.07,
    'O-': 0.005, 'A-': 0.005, 'B-': 0.005, 'AB-': 0.005
}

# Base daily demand across a hospital
BASE_HOSPITAL_DEMAND_MEAN = 100 

# Holidays for simulated seasonal spikes (Ramadan, Diwali, Christmas variations)
# Simplified list for 2021-2023
HOLIDAYS = pd.to_datetime([
    '2021-11-04', '2021-12-25', '2021-05-13', # Diwali, Christmas, Eid
    '2022-10-24', '2022-12-25', '2022-05-03',
    '2023-11-12', '2023-12-25', '2023-04-22'
])

def main():
    # ==========================================
    # 2. Base Grid Generation
    # ==========================================
    date_range = pd.date_range(start=START_DATE, end=END_DATE, freq='D')
    hospitals = [f"{fake.company()} Hospital" for _ in range(N_HOSPITALS)]

    # Create Cartesian Product for Date x Hospital x Blood Group
    grid = [(d, h, bg, prob) for d in date_range for h in hospitals for bg, prob in BLOOD_GROUPS.items()]
    df = pd.DataFrame(grid, columns=['date', 'hospital_id', 'blood_group', 'bg_probability'])

    # Time-based features
    df['month'] = df['date'].dt.month
    df['day_of_week'] = df['date'].dt.weekday
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    df['is_holiday'] = df['date'].isin(HOLIDAYS).astype(int)

    # ==========================================
    # 3. Simulate Time-Series & Inventory Dynamics
    # ==========================================
    # We process each (hospital, blood_group) as an independent time series
    series_results = []

    for (h_id, bg), group_df in df.groupby(['hospital_id', 'blood_group']):
        group_df = group_df.sort_values('date').copy()
        n_days = len(group_df)
        bg_prob = group_df['bg_probability'].iloc[0]
        
        # Expected daily volume for this specific blood group
        avg_vol = BASE_HOSPITAL_DEMAND_MEAN * bg_prob
        
        # Arrays to track state
        collected = np.zeros(n_days)
        used = np.zeros(n_days)
        expired = np.zeros(n_days)
        stock = np.zeros(n_days)
        avg_expiry_days = np.zeros(n_days)
        near_exp_ratio = np.zeros(n_days)
        
        # Initial stock (~7 days of buffer)
        current_inventory = int(avg_vol * 7)
        
        for i in range(n_days):
            is_we = group_df['is_weekend'].iloc[i]
            is_hol = group_df['is_holiday'].iloc[i]
            
            # --- 1. Collection Logic ---
            # Weekend drop ~20%
            weekend_multiplier = 0.8 if is_we else 1.0
            # Add controlled Gaussian noise (sigma=0.05)
            noise_col = np.random.normal(0, 0.05)
            
            daily_collection = max(0, int(avg_vol * weekend_multiplier * (1 + noise_col)))
            
            # --- 2. Demand Logic ---
            # Holiday emergency spikes ~15%
            holiday_multiplier = 1.15 if is_hol else 1.0
            noise_dem = np.random.normal(0, 0.05)
            
            daily_demand = max(0, int(avg_vol * holiday_multiplier * (1 + noise_dem)))
            
            # Evaluate ability to meet demand
            actual_used = min(current_inventory + daily_collection, daily_demand)
            
            # --- 3. Expiry and State Update ---
            if current_inventory > 0:
                expire_chance = np.random.uniform(0.01, 0.04)
                daily_expired = int(current_inventory * expire_chance)
            else:
                daily_expired = 0
                
            # Update stock
            current_inventory = current_inventory + daily_collection - actual_used - daily_expired
            current_inventory = max(0, current_inventory)
            
            # Inventory Health Metrics
            avg_exp = np.random.normal(21, 5) if current_inventory > 0 else 0
            avg_exp = np.clip(avg_exp, 0, 42)
            
            if current_inventory > 0:
                base_near_exp_ratio = max(0, (21 - avg_exp) / 21 * 0.5 + 0.1) # approx logic
                ner = np.clip(base_near_exp_ratio + np.random.normal(0, 0.05), 0, 1)
            else:
                ner = 0.0
                
            # Record keeping
            collected[i] = daily_collection
            used[i] = actual_used
            expired[i] = daily_expired
            stock[i] = current_inventory
            avg_expiry_days[i] = round(avg_exp, 1)
            near_exp_ratio[i] = round(ner, 3)

        # Assign generated values back to the group dataframe
        group_df['units_collected'] = collected.astype(int)
        group_df['units_used'] = used.astype(int)
        group_df['units_expired'] = expired.astype(int)
        group_df['current_stock'] = stock.astype(int)
        group_df['days_to_expiry'] = avg_expiry_days
        group_df['near_expiry_ratio'] = near_exp_ratio
        
        series_results.append(group_df)

    # Combine all generated series back together
    final_df = pd.concat(series_results, ignore_index=True)
    final_df = final_df.sort_values(by=['hospital_id', 'blood_group', 'date']).reset_index(drop=True)

    # ==========================================
    # 4. Lag, Rolling Features, & Targets
    # ==========================================
    final_df['demand_lag_1'] = final_df.groupby(['hospital_id', 'blood_group'])['units_used'].shift(1)
    final_df['demand_lag_7'] = final_df.groupby(['hospital_id', 'blood_group'])['units_used'].shift(7)
    final_df['demand_rolling_7d_avg'] = final_df.groupby(['hospital_id', 'blood_group'])['units_used'].transform(
        lambda x: x.rolling(window=7, min_periods=1).mean()
    ).round(2)

    # Backfill initial NaNs induced by shift
    for col in ['demand_lag_1', 'demand_lag_7']:
        final_df[col] = final_df[col].bfill()

    # Target Feature 1: Stock Coverage
    safe_demand = final_df['demand_rolling_7d_avg'].replace(0, 1)
    final_df['stock_coverage_days'] = (final_df['current_stock'] / safe_demand).round(2)

    # Shortage Flag: Triggered when coverage < 3 days
    final_df['shortage_flag'] = (final_df['stock_coverage_days'] < 3.0).astype(int)

    # Target Feature 2: Expiry Risk
    final_df['expiry_risk_flag'] = (final_df['near_expiry_ratio'] > 0.4).astype(int)

    # Clean up temporary columns
    final_df = final_df.drop(columns=['bg_probability'])

    # Rearrange columns exactly as requested
    final_columns = [
        'date', 'hospital_id', 'blood_group', 'units_collected', 'units_used', 
        'units_expired', 'current_stock', 'days_to_expiry', 'is_holiday', 
        'is_weekend', 'month', 'day_of_week', 'demand_lag_1', 'demand_lag_7', 
        'demand_rolling_7d_avg', 'stock_coverage_days', 'near_expiry_ratio', 
        'shortage_flag', 'expiry_risk_flag'
    ]
    final_df = final_df[final_columns]

    # ==========================================
    # 5. Export and Output Summary Stats
    # ==========================================
    # Set up standard data folder relative to root (assuming src/data runs from root-ish workspace)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    output_dir = os.path.join(project_root, 'data', 'raw')
    os.makedirs(output_dir, exist_ok=True)
    
    csv_name = os.path.join(output_dir, 'blood_inventory_dataset.csv')
    final_df.to_csv(csv_name, index=False)

    print("="*50)
    print(f"Dataset generated successfully -> {csv_name}")
    print("="*50)
    print(f"Shape: {final_df.shape}\n")
    print(f"Missing Values:\n{final_df.isnull().sum()}\n")

    print("Class Balance - Shortage Flag:")
    print(final_df['shortage_flag'].value_counts(normalize=True).round(4) * 100)
    print("\nClass Balance - Expiry Risk Flag:")
    print(final_df['expiry_risk_flag'].value_counts(normalize=True).round(4) * 100)
    print("\nBlood Group Distribution (Row counts should be perfectly equal by design):")
    print(final_df['blood_group'].value_counts())
    print("="*50)

if __name__ == "__main__":
    main()
