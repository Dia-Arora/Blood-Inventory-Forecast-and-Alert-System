# BloodIQ — Blood Demand, Supply, Shortage & Wastage Intelligence

BloodIQ forecasts blood demand and donations per blood type (A, B, AB, O),
runs a day-by-day simulated inventory, and classifies shortage and wastage
risk per type — visualized as a gamified "health bar" dashboard.

## Scope

Built on one real dataset and one dataset generated to be coherent with it:

- **Supply (real):** [Malaysia government blood donation data](https://data.gov.my/data-catalogue/blood_donations) — daily, per blood type, 2006–2026.
- **Demand (generated):** produced by `backend/data/generate_demand.py`,
  anchored to the real donation data above so both share the same
  calendar and order of magnitude — see
  `docs/superpowers/specs/2026-07-09-synthetic-demand-generation-design.md`
  for the full method and rationale.

Neither dataset has hospital-level detail or Rh factor (+/-), so BloodIQ
targets national-level A/B/AB/O forecasting and simulation only.

## Quick start

```bash
# Backend
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python data/generate_demand.py
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
