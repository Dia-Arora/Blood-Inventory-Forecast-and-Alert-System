"""
Data Engineering Pipeline: MIMIC-IV Blood Demand Extractor
Responsible for extracting real-world blood transfusion events from MIMIC-IV
and converting them into a daily demand time-series.
"""

import pandas as pd
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# MIMIC-IV ITEMIDs for Blood Products
# Reference: MIMIC-IV d_items table
BLOOD_ITEM_IDS = {
    225168: 'Packed Red Blood Cells',
    220996: 'Fresh Frozen Plasma',
    225170: 'Platelets',
    225171: 'Cryoprecipitate'
}

def extract_daily_demand(inputevents_path: Path, output_path: Path):
    """
    Reads the MIMIC-IV inputevents table (or a chunk of it),
    filters for blood transfusions, and aggregates into daily demand.
    """
    logger.info(f"Loading clinical data from {inputevents_path}...")
    
    # In a real environment, read in chunks due to MIMIC-IV size
    try:
        df = pd.read_csv(inputevents_path, usecols=['subject_id', 'starttime', 'itemid', 'amount'])
    except FileNotFoundError:
        logger.error(f"File not found: {inputevents_path}. Ensure you have MIMIC-IV access.")
        return
    
    # 1. Filter for only blood products
    df_blood = df[df['itemid'].isin(BLOOD_ITEM_IDS.keys())].copy()
    
    # 2. Map item IDs to human-readable names
    df_blood['blood_product'] = df_blood['itemid'].map(BLOOD_ITEM_IDS)
    
    # 3. Convert timestamps to daily dates
    df_blood['date'] = pd.to_datetime(df_blood['starttime']).dt.date
    
    # 4. Aggregate daily demand
    # Since MIMIC records amounts in ml, we can normalize to "units" (approx 300ml per unit)
    df_blood['units_used'] = df_blood['amount'] / 300.0
    
    daily_demand = df_blood.groupby(['date', 'blood_product'])['units_used'].sum().reset_index()
    
    # 5. Pivot to have products as columns
    daily_demand_pivot = daily_demand.pivot(index='date', columns='blood_product', values='units_used').fillna(0)
    
    # Save the real-world dataset
    daily_demand_pivot.to_csv(output_path)
    logger.info(f"Successfully generated real-world demand dataset at {output_path}")
    return daily_demand_pivot

if __name__ == "__main__":
    # Example usage for the Data Lead
    INPUT_PATH = Path("../datasets/mimic_iv/icu/inputevents.csv")
    OUTPUT_PATH = Path("../datasets/demand/mimic_real_demand.csv")
    
    # extract_daily_demand(INPUT_PATH, OUTPUT_PATH)
    print("MIMIC-IV Extraction pipeline base ready.")
