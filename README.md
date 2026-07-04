# BloodIQ — Blood Inventory Forecast & Alert System

> **IEEE Research Project | B.Tech AI-ML | 2025–2026**
> A Prescriptive Digital Twin for Blood Inventory Management using Hybrid GRU-LightGBM and MIMIC-IV clinical data.

---

##  Project Architecture

```
Blood-Inventory-Forecast-and-Alert-System/
├── backend/                        # Core Python backend
│   ├── config/                     # Central settings (paths, blood groups, params)
│   ├── data_generation/            # MIMIC-IV extraction & feature engineering
│   ├── datasets/                   # Place MIMIC-IV derived CSVs here (NOT committed)
│   ├── decision_engine/            # Prescriptive optimization solver (Linear Programming)
│   ├── forecasting/
│   │   ├── demand/                 # Hybrid GRU + LightGBM demand forecasting model
│   │   └── donation/               # Prophet-based donation forecasting
│   ├── inventory_simulation/       # FEFO-compliant simulation engine
│   ├── services/                   # Orchestrator wiring all components together
│   ├── trained_models/             # Serialized models (NOT committed — use .gitignore)
│   └── main.py                     # FastAPI entry point
├── frontend/                       # React dashboard for live visualization
├── tests/                          # Unit and integration tests
├── docs/                           # Research plan, architecture diagrams
├── paper.tex                       # IEEE paper LaTeX source
├── Makefile                        # One-command runner for training & serving
└── requirements.txt                # Top-level pinned dependencies
```

---

##  Methodology

### Data Source
Real-world clinical transfusion data extracted from **MIMIC-IV** (Medical Information Mart for Intensive Care IV), the de-identified, publicly available database from Beth Israel Deaconess Medical Center. We aggregate daily blood product demand from raw patient-level `inputevents`.

### Model Architecture (Novel Contribution)
We propose a **Hybrid GRU-LightGBM Digital Twin** architecture:
1. **Gated Recurrent Unit (GRU):** Captures temporal sequential patterns in blood demand (trauma seasonality, week-over-week trends). *(Ref: IIETA 2025)*
2. **LightGBM:** Handles non-linear categorical features (day of week, holidays, hospital admissions). *(Ref: IJACSA 2026)*
3. **Prescriptive Solver:** A Linear Programming layer converts the demand forecast into actionable hospital-level transfer policies to minimize FEFO wastage.

### Key Literature (2024–2026)
- Comparative study on ARIMA vs. ANN for blood transfusion demand (2026).
- Hybrid SVR+LGBM for spatial heterogeneity in blood supply (IJACSA, 2026).
- GRU for temporal blood demand forecasting (IIETA, 2025).
- ML for donor return behavior prediction: CatBoost/XGBoost (NIH PubMed, 2025).

---

##  Team & Responsibilities

| Member | Role | Focus |
|--------|------|-------|
| **Member 1** | Data Engineering Lead | `backend/data_generation/` — MIMIC-IV pipeline |
| **Member 2** | ML Lead | `backend/forecasting/demand/` — Hybrid GRU-LightGBM |
| **Member 3** | Operations Research Lead | `backend/decision_engine/` — Prescriptive solver |
| **Member 4** | Full-Stack Lead | `frontend/` + `backend/main.py` — Dashboard & API |

Detailed role breakdown: [`docs/BloodIQ_Team_Project_Plan.pdf`](docs/BloodIQ_Team_Project_Plan.pdf)

---

##  Quick Start

```bash
# Install all dependencies
pip install -r backend/requirements.txt

# Run the backend API
cd backend && uvicorn main:app --reload

# Run the frontend dashboard
cd frontend && npm install && npm run dev
```

---

##  Data Access

This project uses MIMIC-IV. To access the dataset:
1. Complete the required training at https://physionet.org/
2. Sign the data use agreement.
3. Download `inputevents.csv` from the MIMIC-IV ICU module.
4. Place it at `backend/datasets/mimic_iv/icu/inputevents.csv`.

---

*Research supervised under B.Tech AI-ML Program, 2025–2026.*
