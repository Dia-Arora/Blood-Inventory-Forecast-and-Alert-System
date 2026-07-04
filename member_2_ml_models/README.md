# Member 2 — ML Lead

## Your Responsibility
Build and train the **Hybrid GRU + LightGBM** ensemble demand forecasting model. Benchmark it against baselines. Save the trained model artifacts for Member 3 and Member 4 to consume.

## Your Workspace
```
member_2_ml_models/
├── hybrid_model.py     ← Core GRU + LightGBM architecture (PyTorch)
├── train.py            ← Full training pipeline: loads data, trains, saves model
├── evaluate.py         ← Benchmark vs ARIMA, XGBoost, plain LSTM baselines
├── models/             ← Saved model weights (ignored by git)
│   ├── gru_model.pt
│   └── lgb_model.pkl
├── outputs/            ← Evaluation results, plots
│   ├── metrics_table.csv
│   └── predicted_vs_actual.png
└── requirements.txt
```

## Quick Start
```bash
cd member_2_ml_models
pip install -r requirements.txt

# IMPORTANT: Member 1 must have run their pipeline first.
# Copy their output here:
cp ../member_1_data_engineering/data/train.csv data/
cp ../member_1_data_engineering/data/val.csv   data/
cp ../member_1_data_engineering/data/test.csv  data/

# Train the hybrid model
python train.py

# Evaluate and benchmark
python evaluate.py
```

## What You Hand Off
- `models/gru_model.pt` and `models/lgb_model.pkl` → to Member 3 and Member 4
- `outputs/metrics_table.csv` → for the paper's results table

## Key Decisions You Own
- GRU hidden dimension and number of layers
- LightGBM hyperparameters (n_estimators, learning_rate, etc.)
- Ensemble weighting (GRU weight vs LightGBM weight)
- Sequence window size for the GRU (default: 30 days)

## Paper Section You Write
**Section III-B: Predictive Model Architecture**
**Section IV: Experimental Results** (Table II — Performance Metrics)
