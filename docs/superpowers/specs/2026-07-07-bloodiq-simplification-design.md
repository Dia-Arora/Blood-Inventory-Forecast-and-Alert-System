# BloodIQ Simplification & Gamified Simulation — Design

## Purpose

The repo has accumulated multiple parallel, partially-overlapping implementations
(an orchestrator-based backend built on synthetic/MIMIC-IV-oriented data, a
newer lightweight backend trained on real data, four redundant per-teammate
workspaces, an orphaned hybrid model, an unused LP transfer optimizer, and a
frontend dashboard that renders random client-side numbers instead of calling
any backend).

This spec scopes the project down to exactly what's needed to build four
things, using exactly two real datasets already present in the repo:

1. Supply (donation) forecasting per blood type
2. Demand forecasting per blood type
3. Shortage classification per blood type (rule-based)
4. Wastage prediction per blood type (rule-based)

...and to remove everything that isn't in service of those four things.

## Data sources (the only two used)

- `backend/data/blood_demand.csv` — Kaggle, national aggregate, daily,
  2020-01-01 to 2024-12-31 (1,827 rows). Columns: `Date, DayOfWeek, Month,
  Population, Events, HistoricalBloodUsage, HospitalAdmissions,
  BloodDonorsAvailable, Temperature, PredictedBloodDemand`. No blood-type
  breakdown.
- `backend/data/blood_donations.csv` — Malaysia government data, daily,
  per blood type, 2006-01-01 to 2026-07-04 (7,490 rows per type). Columns:
  `date, blood_type, donations`. Types present: `a, b, ab, o` (plus an `all`
  aggregate row). **No Rh factor (+/-) in the data.**

## Explicit scope decision: 4 ABO blood types, not 8

Neither dataset carries Rh factor. The project targets **A, B, AB, O only**.
Any existing UI/mockups implying 8 types (with +/-) are considered stale and
will be corrected. This was confirmed with the user during design review.

## What gets removed and why

| Path | Reason |
|---|---|
| `member_1_data_engineering/`, `member_2_ml_models/`, `member_3_digital_twin/`, `member_4_fullstack/` | Parallel individual workspaces, MIMIC-IV-oriented, never integrated, irrelevant to the chosen datasets |
| `shared/` | Column contract used only by the member folders being removed |
| `backend/data_generation/` | MIMIC-IV extractor + synthetic Indian-hospital generator — not our datasets |
| `backend/datasets/` | Placeholder synthetic CSVs generated to unblock an earlier demo; superseded by real `backend/data/` |
| `DESIGN-sentry.md` | Unrelated design-token file for a different brand; unreferenced anywhere |
| `backend/forecasting/demand/hybrid_model.py` | Orphaned GRU+LightGBM code, never wired in, not part of the 4 target capabilities |
| `backend/decision_engine/optimizer.py` | Inter-hospital transfer LP solver — out of scope, no transfer feature requested, no real multi-hospital data |
| `backend/main.py`, `backend/services/orchestrator.py`, `backend/forecasting/demand/demand_model.py`, `backend/forecasting/donation/donation_model.py`, `backend/inventory/`, `backend/inventory_simulation/`, `backend/database/`, `backend/models/schemas.py`, old `backend/api/routes.py` | Original orchestrator backend built around synthetic data, SQL persistence, and multi-hospital concepts not used going forward. Superseded by new modules below. |
| `frontend/src/BloodIQDashboard.jsx` | Orphaned single-file dashboard, no longer routed to |
| `tests/test_models.py`, `tests/test_data_pipeline.py` | Test random numbers, not real logic; replaced |

## What survives as the foundation

`backend/api/main.py`, `backend/ml/train_demand.py`, `backend/ml/train_supply.py`,
`backend/ml/inference.py`, `backend/data/*.csv` — already trained on the two
real datasets. Extended, not replaced.

## New backend structure

```
backend/
  data/                        (unchanged)
    blood_demand.csv
    blood_donations.csv
    README.md
  ml/
    train_demand.py            (existing — LightGBM, aggregate demand)
    train_supply.py            (existing — Prophet x 4 blood types)
    demand_split.py            (NEW — disaggregates aggregate demand forecast into per-type demand)
    inference.py                (extended — add predict_demand_by_type)
  simulation/                  (NEW)
    engine.py                  (day-by-day per-type stock ledger; FEFO aging; in-memory, no DB)
    shortage_rules.py          (rule-based: days-of-coverage -> SAFE/WARNING/CRITICAL)
    wastage_rules.py           (rule-based: near-expiry ratio -> LOW/MED/HIGH)
  config.py                    (NEW — blood types, shelf-life=42d, safety-stock thresholds, starting stock per type)
  api/
    main.py                    (extended: /forecast/demand, /forecast/supply, /simulate, /train/*)
  requirements.txt             (trimmed: fastapi, uvicorn, pandas, numpy, lightgbm, prophet, scikit-learn, joblib)
  run.py                       (unchanged)
```

## New frontend structure

```
frontend/src/
  App.jsx, main.jsx, index.css, components/Navbar.jsx, pages/Home.jsx   (unchanged)
  pages/Dashboard.jsx           (rebuilt — Boss Health Bar UI, calls real backend, no more Math.random() data)
  lib/api.js                   (NEW — fetch/axios wrapper around backend endpoints)
```

## Data flow — one `/simulate?days=N` call

1. `inference.predict_demand(N)` — LightGBM forecast of total daily demand (real model, real data).
2. `demand_split.split_by_type(total_demand)` — breaks the total into A/B/AB/O
   using each type's historical share of donations as a proxy ratio, computed
   from the real Malaysia data (approximately O 41%, B 26%, A 24%, AB 6%).
   This is a documented approximation, not independently-learned per-type
   demand — the dataset doesn't support that, and this is the honest way to
   get a per-type number out of it.
3. `inference.predict_supply(N)` — Prophet forecast of per-type donations
   (real model, real data, already exists).
4. `simulation/engine.py` walks day-by-day per blood type: add forecasted
   donations, consume FEFO against forecasted demand, age all stock by one
   day, expire anything past the 42-day shelf life. Fully in-memory per
   request — no database.
5. `shortage_rules.py` labels each day/type SAFE/WARNING/CRITICAL from
   days-of-coverage. `wastage_rules.py` labels each day/type LOW/MED/HIGH from
   near-expiry ratio.
6. One JSON response returns the full N-day, per-type time series (stock,
   consumed, donated, expired, shortage_risk, wastage_risk).
7. `Dashboard.jsx` renders each blood type as an HP bar (Boss Health Bar
   style — see Frontend design below) and steps through the returned days.

## Frontend design — "Boss Health Bars" (approved option)

- One HP-bar card per blood type (A, B, AB, O — four cards, not eight).
- Bar fill % = current simulated stock / a configured reference "full stock"
  for that type.
- Color and behavior driven directly by `shortage_rules` classification:
  green (SAFE), amber (WARNING), pulsing red with a shake animation
  (CRITICAL) — never hardcoded, always reflects the label from the backend.
- A brief "damage flash" animation plays on any day where `wastage_rules`
  reports units expired for that type.
- A "Next Day" control (or auto-play toggle) steps through the pre-computed
  N-day array returned by one `/simulate` call — the backend is not
  step-wise/stateful; all animation state lives client-side.

### Interactivity levels (approved)

- **Level A (default, always visible):** below each health-bar card, a small
  text/badge readout showing that day's forecasted demand, forecasted supply,
  shortage_risk label, and wastage_risk label. Updates in sync with the
  Next Day / auto-play scrubber — no click required to see it.
- **Level B (click-to-expand, opt-in):** clicking a blood-type card expands
  it into a chart showing demand vs. supply as two lines across all N days
  at once (not just the current day), with a color-coded strip underneath
  marking which days were WARNING/CRITICAL for shortage and which days had
  wastage. Collapses back to the Level A card on a second click.
- Both levels are driven by the same single `/simulate` response — no extra
  API calls needed for the expand interaction.

### Visual theme constraint

The gamified health-bar mechanic (fill %, color-by-risk, shake/flash
animations, Next Day scrubber) is a new **interaction pattern**, not a new
**visual language**. It must be built using the dashboard's existing design
system already in place after the latest pull — the Tailwind v4 setup in
`frontend/src/index.css` (`@theme` block: rose/blush palette, "Outfit"
typography), the existing card/section conventions in
`frontend/src/pages/Dashboard.jsx`, and the existing `Navbar`/`Home`/routing
structure. The dark-navy/red color scheme used in the earlier brainstorming
mockup was illustrative of the *mechanic* only — the shipped version reskins
that mechanic in the current rose/blush theme (e.g., CRITICAL uses the
existing rose-600/rose-700 tones already defined, not a new red). No
redesign of layout, navigation, or color system.

## Error handling

- Calling forecast/simulate endpoints before training → clear error directing
  the user to `/train/demand` and `/train/supply` first (existing pattern in
  `backend/api/main.py`, kept).
- Missing or malformed CSV at training time → fail loudly with a clear
  message. No silent fallback to invented/synthetic data under any
  circumstance — this was the recurring problem in the codebase being fixed.
- Simulated stock is clamped at 0, never negative.

## Testing

- `demand_split`: per-type outputs sum back to the original total; type
  ratios sum to 1.
- `shortage_rules` / `wastage_rules`: known inputs produce the expected
  classification (e.g., stock = 0 -> CRITICAL; all-stock near shelf-life
  limit -> HIGH wastage risk).
- `simulation/engine`: unit conservation over a short synthetic run
  (inflow - outflow - expired = change in stock, no leaks).
- One end-to-end test: train on a truncated slice of the real CSVs, run one
  `/simulate` call, assert the response shape and that all four blood types
  are present with non-negative values.

## Out of scope (explicitly)

- Hospital-level or regional breakdowns (neither dataset supports this).
- Rh factor / 8 blood types (neither dataset supports this).
- Inter-location transfer recommendations / LP optimizer.
- Any database or persistence layer — simulation is computed fresh per
  request from CSVs + saved model artifacts.
- The GRU+LightGBM hybrid model — plain LightGBM (demand) + Prophet (supply)
  only, matching what's actually implemented and trainable on this data.
