# BloodIQ — Blood Demand, Supply, Shortage & Wastage Intelligence

BloodIQ forecasts blood demand and donations per blood type (A, B, AB, O),
runs a day-by-day simulated inventory, and classifies shortage and wastage
risk per type — visualized as a gamified "health bar" dashboard.

## Scope

Built on two real, freely available datasets:

- **Demand:** [Kaggle blood demand dataset](https://www.kaggle.com/datasets/rishi2003das/blood-demand-dataset) — national daily aggregate.
- **Supply:** [Malaysia government blood donation data](https://data.gov.my/data-catalogue/blood_donations) — daily, per blood type.

Neither dataset has hospital-level detail or Rh factor (+/-), so BloodIQ
targets national-level A/B/AB/O forecasting and simulation only — see
`docs/superpowers/specs/2026-07-07-bloodiq-simplification-design.md` for
the full rationale.

## Quick start

```bash
# Backend
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -c "from ml.train_demand import train; train()"
.venv/bin/python -c "from ml.train_supply import train; train()"
.venv/bin/uvicorn api.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Then open `http://localhost:5173/dashboard`.

## Architecture

See `docs/ARCHITECTURE.md`.

## Tests

```bash
cd backend && .venv/bin/pytest tests/ -v
```
