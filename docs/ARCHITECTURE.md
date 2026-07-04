# Architecture Overview

```
Blood-Inventory-Forecast-and-Alert-System/
│
├── backend/                             # Python 3.11+ core application
│   ├── config/
│   │   └── settings.py                 # Central config: paths, blood groups, model params
│   │
│   ├── data_generation/
│   │   ├── mimic_extractor.py          # [Member 1] Real MIMIC-IV clinical data extraction
│   │   └── make_dataset.py             # [Member 1] Feature engineering on extracted data
│   │
│   ├── datasets/                        # Raw & processed CSVs (NOT committed — see .gitignore)
│   │   ├── mimic_iv/                    # Place MIMIC-IV inputevents.csv here
│   │   └── demand/                      # Output of the extraction pipeline
│   │
│   ├── forecasting/
│   │   ├── demand/
│   │   │   ├── hybrid_model.py         # [Member 2] SOTA GRU + LightGBM ensemble
│   │   │   └── demand_model.py         # [Member 2] XGBoost baseline (for benchmarking)
│   │   └── donation/
│   │       └── donation_model.py       # Prophet-based donation supply forecasting
│   │
│   ├── decision_engine/
│   │   ├── optimizer.py                # [Member 3] LP Prescriptive solver (SciPy)
│   │   └── engine.py                   # [Member 3] Rule-based alert generation
│   │
│   ├── inventory_simulation/
│   │   └── simulation_engine.py        # [Member 3] FEFO-compliant batch simulation
│   │
│   ├── services/
│   │   └── orchestrator.py             # Wires together all forecasting & decision services
│   │
│   ├── trained_models/                  # Serialized .joblib / .pt files (NOT committed)
│   ├── blood_inventory.db               # SQLite state (NOT committed)
│   └── main.py                          # [Member 4] FastAPI entry point
│
├── frontend/                            # [Member 4] React + Vite dashboard
│   ├── src/
│   │   ├── BloodIQDashboard.jsx         # Main dashboard UI component
│   │   ├── main.jsx                     # React entry point
│   │   └── index.css                    # Design system tokens
│   ├── index.html
│   ├── package.json
│   └── vite.config.js                  # Proxy to backend at :8000
│
├── tests/                               # Pytest test suite
│   ├── test_data_pipeline.py
│   └── test_models.py
│
├── docs/
│   └── BloodIQ_Team_Project_Plan.pdf   # Team role & task breakdown
│
├── paper.tex                            # IEEE paper LaTeX source
├── Makefile                             # Developer commands
├── README.md
├── .gitignore
└── requirements.txt                     # Pinned top-level Python deps
```

## Data Flow

```
MIMIC-IV inputevents.csv
        │
        ▼
[Member 1] mimic_extractor.py
        │  Aggregates patient transfusions → daily demand signal
        ▼
[Member 2] hybrid_model.py (GRU + LightGBM)
        │  Forecasts next 30 days of blood product demand per location
        ▼
[Member 3] optimizer.py (Linear Programming)
        │  Converts forecast → prescriptive inter-hospital transfer policy
        ▼
[Member 4] FastAPI + React Dashboard
           Live visualization of inventory levels, alerts, and actions
```
