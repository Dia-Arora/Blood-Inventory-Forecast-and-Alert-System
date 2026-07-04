# Member 3 — Operations Research & Digital Twin Lead

## Your Responsibility
Build the **Prescriptive AI** layer — the system that takes Member 2's demand forecast and produces concrete, actionable recommendations. This is the **novel contribution** that distinguishes our work from all existing blood inventory ML papers.

## Your Workspace
```
member_3_digital_twin/
├── simulation/
│   └── fefo_engine.py      ← FEFO simulation: tracks individual blood bag batches
├── optimization/
│   └── optimizer.py        ← LP solver: prescribes inter-location blood transfers
├── risk_engine.py          ← Classifies shortage/wastage risk levels (HIGH/MED/LOW)
├── run_twin.py             ← Entry point: runs a full Digital Twin simulation day
└── requirements.txt
```

## Quick Start
```bash
cd member_3_digital_twin
pip install -r requirements.txt

# IMPORTANT: Member 2 must have generated predictions first.
# Provide a forecast CSV or run with sample data:
python run_twin.py --forecast_csv sample_forecast.csv
```

## What You Hand Off
- `risk_engine.py` functions → imported by Member 4's API
- `optimizer.py` → imported by Member 4's API to return transfer recommendations
- Paper figures: wastage reduction chart, transfer policy table

## Key Decisions You Own
- Safety stock thresholds per blood product
- FEFO batch expiry tracking logic
- LP objective function formulation (minimize wastage AND shortage simultaneously)

## Paper Section You Write
**Section III-C: Prescriptive Optimization Framework**
**Section V: Digital Twin Evaluation** (wastage % reduction vs baseline)
