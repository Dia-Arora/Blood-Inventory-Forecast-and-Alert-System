# Architecture Overview

BloodIQ is scoped to four capabilities, built on two real datasets, with no
database and no per-hospital modeling:

1. Supply (donation) forecasting per blood type
2. Demand forecasting per blood type
3. Rule-based shortage classification per blood type
4. Rule-based wastage prediction per blood type

## Data

- `backend/data/blood_demand.csv` — Kaggle, national aggregate daily demand,
  2020-2024. No blood-type breakdown.
- `backend/data/blood_donations.csv` — Malaysian government daily donations,
  broken down by blood type (A, B, AB, O), 2006-2026.

## Backend (`backend/`)

```
backend/
  data/                 Real datasets (see above)
  ml/
    train_demand.py     LightGBM on aggregate demand
    train_supply.py     Prophet x4, one per blood type, on real donations
    demand_split.py      Disaggregates the aggregate demand forecast into
                          per-type demand, using each type's historical
                          share of donations as a proxy ratio
    inference.py          predict_demand / predict_supply / predict_demand_by_type
  simulation/
    engine.py             Day-by-day, in-memory, per-type FEFO stock ledger
    shortage_rules.py     Days-of-coverage -> SAFE / WARNING / CRITICAL
    wastage_rules.py       Near-expiry ratio -> LOW / MED / HIGH
  config.py               Blood types, shelf life, thresholds
  api/main.py              /api/forecast/demand, /api/forecast/supply,
                            /api/simulate, /api/train/*
```

No SQL database — `/api/simulate` computes the full simulation fresh from
the trained models on every call.

## Frontend (`frontend/`)

React + Vite + Tailwind v4. `pages/Dashboard.jsx` calls `/api/simulate` once
per load and renders four `HealthBarCard` components (one per blood type,
"Boss Health Bar" style: a fill bar colored by shortage risk, with a
day-by-day Next Day / Auto-play scrubber) plus an `AlertStream` sidebar
derived from the same response's shortage/wastage classifications.

## Explicitly out of scope

- Hospital-level or regional breakdowns (neither dataset supports this).
- Rh factor / 8 blood types (neither dataset has Rh data — A/B/AB/O only).
- Inter-location transfer recommendations.
- Any database or persistence layer.
- The GRU+LightGBM hybrid model (plain LightGBM + Prophet only).

See `docs/superpowers/specs/2026-07-07-bloodiq-simplification-design.md`
for the full rationale.
