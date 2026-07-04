# Member 1 — Data Engineering Lead

## Your Responsibility
Transform raw clinical data from **MIMIC-IV** into a clean, structured time-series dataset that the ML team (Member 2) can train models on.

## Your Workspace
```
member_1_data_engineering/
├── mimic_extractor.py      ← MAIN FILE: Extract transfusion events from MIMIC-IV
├── feature_engineering.py  ← Add lag, rolling, and calendar features to the dataset
├── data/                   ← Output CSVs go here (ignored by git)
│   └── mimic_real_demand.csv  ← The final cleaned dataset you produce
└── requirements.txt
```

## Quick Start
```bash
cd member_1_data_engineering
pip install -r requirements.txt

# Step 1: Download MIMIC-IV from PhysioNet and place inputevents.csv in data/raw/
# https://physionet.org/content/mimiciv/

# Step 2: Run extraction
python mimic_extractor.py

# Step 3: Run feature engineering
python feature_engineering.py
```

## What You Hand Off
When done, share `data/mimic_real_demand_features.csv` with Member 2 (ML Lead).  
This CSV must have columns: `date, prbc_units, ffp_units, platelet_units, total_units, day_of_week, is_weekend, month, lag_7, lag_14, rolling_mean_7 ...`

## Key Decisions You Own
- Which MIMIC-IV product item IDs to include (see `mimic_extractor.py` → `BLOOD_ITEM_IDS`)
- How to handle missing days (forward fill vs zero-fill)
- Which external features to engineer (holidays, weather proxy, etc.)

## Paper Section You Write
**Section III-A: Dataset Acquisition and Preprocessing**
