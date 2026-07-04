# AI-Based Blood Inventory Forecasting and Shortage Alert System

This is a production-quality backend decision-support system designed for hospitals and blood banks to proactively predict blood demand and donation, simulate inventory evolution, and generate actionable shortage/wastage alerts.

---

## Project Objective

The system bridges machine learning predictions with deterministic clinical inventory rules:
1. **Demand Forecasting**: Trains an **XGBoost Regressor** on historical blood usage data to forecast future daily hospital demand.
2. **Donation Forecasting**: Trains **four independent Facebook Prophet models** (one for each ABO blood group: `A`, `B`, `AB`, `O`) on historical donations to predict incoming supply per group.
3. **Inventory Simulation Engine**: A deterministic engine that uses **FEFO (First Expire, First Out)** logic to consume inventory, handles daily batch expiries, adds new daily donation batches, and updates persistent SQLite storage.
4. **Decision Engine**: A rule-based engine that evaluates projected stock levels against safety stock thresholds to flag shortage risk, checks upcoming expiries against demand to flag wastage risk, and outputs human-readable recommendations.

---

## System Architecture & Workflow

```
       Historical Demand Data
                 │
                 ▼
          [ XGBoost Model ]
                 │
                 ▼
       Predicted Total Demand
                 │
                 ▼
     [ Simulation Engine ]  ◄── Proportional split based on Safety Stock weights
                 │
                 ▼
     FEFO Consumption on Stock
                 │
                 ▼
     Updated Inventory State
                 │
                 ▼
        [ Decision Engine ] ────► Shortage Alerts (HIGH/MEDIUM/LOW)
                                ► Wastage Alerts (HIGH/MEDIUM/LOW)
                                ► Actionable Recommendations
```

```
       Historical Donation Data
                 │
                 ▼
     [ 4x Prophet Models (A,B,AB,O) ]
                 │
                 ▼
      Predicted Donations Group
                 │
                 ▼
     [ Simulation Engine ] ────► New Inventory Batches (42-day Shelf Life)
```

---

## Project Structure

```
backend/
├── api/
│   └── routes.py             # FastAPI REST endpoints
├── config/
│   └── settings.py           # Config variables (shelf-life, safety stock, paths)
├── database/
│   └── db.py                 # SQLite ORM schema & session setup
├── datasets/
│   ├── demand/               # demand/synthetic_blood_demand_data.csv
│   └── supply/               # supply/blood_donations.csv
├── decision_engine/
│   └── engine.py             # Rule-based risk & recommendation generator
├── forecasting/
│   ├── demand/
│   │   └── demand_model.py   # XGBoost demand regressor & preprocessing
│   └── donation/
│       └── donation_model.py # 4x Prophet donation models & preprocessing
├── inventory/
│   └── inventory_generator.py# Seeder for generating realistic initial inventory
├── inventory_simulation/
│   └── simulation_engine.py  # FEFO-based deterministic simulator
├── models/
│   └── schemas.py            # Pydantic v2 validation and API response models
├── services/
│   └── orchestrator.py       # Pipeline orchestrator
├── trained_models/           # Saved model weights (.joblib files)
├── utils/
│   └── helpers.py            # Logger config, forecasting db wrappers, etc.
├── main.py                   # App lifecycle, startup seeder, FastAPI wrapper
└── requirements.txt          # Pinned project dependencies
```

---

## Getting Started

### Prerequisites
- Python 3.10 to 3.14
- Git

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Dia-Arora/Blood-Inventory-Forecast-and-Alert-System.git
   cd Blood-Inventory-Forecast-and-Alert-System/backend
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Server

Start the FastAPI application:
```bash
python main.py
```
*Note: On the first run, the system will automatically seed an initial inventory database and perform lazy training of all 5 Machine Learning models (1x XGBoost and 4x Prophet models). This step creates checkpoints under `trained_models/` so subsequent server startups are instantaneous.*

Once running, the API interactive documentation is available at:
👉 **[http://localhost:8000/docs](http://localhost:8000/docs)** (Swagger UI)

---

## Database Schemas (SQLite)

The system keeps data normalized using four primary tables:
- **`inventory_batches`**: Tracks physical blood bags. Fields: `batch_id`, `blood_group` (A/B/AB/O), `units`, `collection_date`, `expiry_date`, `status` (AVAILABLE / CONSUMED / EXPIRED).
- **`forecast_demand`**: Stores daily total forecasted hospital demand.
- **`forecast_donations`**: Stores forecasted incoming donations per group.
- **`risk_alerts`**: Log of all generated alerts. Fields: `alert_date`, `blood_group`, `alert_type` (SHORTAGE/WASTAGE), `risk_level` (HIGH/MEDIUM), `message`, `recommendation`.

---

## FastAPI REST Endpoints

### 1. GET `/inventory`
Returns the current stock state. Can be filtered by `blood_group` (A, B, AB, O) or `status` (AVAILABLE, CONSUMED, EXPIRED). Returns a total units summary per group.

### 2. POST `/simulate`
Runs one simulation day (advances the simulated timeline). It:
1. Marks expired batches as `EXPIRED`.
2. Generates demand and donation predictions for the target day.
3. Performs FEFO consumption of available stock based on predicted demand.
4. Generates new inventory batches from predicted donations.
5. Invokes the Decision Engine to produce risk alerts and recommendations.
6. Returns the updated state.

### 3. GET `/forecast/demand`
Returns demand forecast records for the next $N$ days.

### 4. GET `/forecast/donation`
Returns donation forecast records per blood group for the next $N$ days.

### 5. GET `/alerts`
Returns safety risk alerts. Filters by `risk_level` (HIGH/MEDIUM/LOW), `blood_group`, and `alert_type`.
