# Self-Generated Per-Type Demand Data — Design

## Purpose

The demand dataset (`backend/data/blood_demand.csv`, sourced from Kaggle) is
itself synthetic — its `PredictedBloodDemand` column name is a giveaway that
it was generated for a machine-learning practice exercise, not sourced from
real hospital records. Worse, it comes from an unrelated country/scale to
the real Malaysia supply dataset, which caused a structural mismatch:
supply always dwarfed demand regardless of any scale-factor tuning, because
the two datasets had no real relationship to each other.

This spec replaces the Kaggle demand dataset with a demand dataset we
generate ourselves, **directly per blood type**, anchored to the real
Malaysia donation data so the two are coherent by construction — same
dates, same order of magnitude — while still having its own independent
shape so it can organically diverge above and below supply (producing real
shortage and wastage moments, not a repeat of the earlier mismatch).

## What gets removed

| Path | Reason |
|---|---|
| `backend/data/blood_demand.csv` (old Kaggle file) | Replaced by a newly generated file of the same name, new schema |
| `backend/ml/demand_split.py` + `backend/tests/test_demand_split.py` | Donation-ratio disaggregation is no longer needed — demand is generated per type natively |
| `DEMAND_SCALE_FACTOR` in `backend/config.py` | No longer needed — the new generator is calibrated correctly from the start |
| The old single-model `predict_demand()` / synthetic-future-covariates logic in `backend/ml/inference.py` | Replaced by a per-type prediction path mirroring `predict_supply()` |

## New demand data schema

Matches `blood_donations.csv`'s shape exactly — same columns, so both
datasets are structurally parallel:

```
date,blood_type,demand
2019-01-01,a,290
2019-01-01,b,410
...
```

(`blood_type` values: `a`, `b`, `ab`, `o` — no `all` aggregate row, unlike
the donations file, since it isn't needed here.)

## Generation method — `backend/data/generate_demand.py`

A one-off script, run once, that reads the real `backend/data/blood_donations.csv`
and writes `backend/data/blood_demand.csv`, covering **2019-01-01 to
2024-12-31** (6 years — matches the window `train_supply.py` already
filters donations to). For each `(date, blood_type)` in that range:

```
demand = donations_that_day
         * weekday_multiplier(date)
         * (1 + seasonal_wave(date, blood_type) + daily_noise())
         * spike_multiplier(date)                  # only on spike days
```

Where:

- **`donations_that_day`** — the real donation count for that exact date
  and blood type, read directly from `blood_donations.csv`. This is the
  anchor that guarantees demand and supply share the same calendar and
  order of magnitude.
- **`weekday_multiplier(date)`** — demand's own weekly shape, independent
  of supply's real weekly dip: `1.05` for Monday–Friday, `0.85` for
  Saturday/Sunday (reflecting that elective procedures cluster on
  weekdays, unlike donation drives).
- **`seasonal_wave(date, blood_type)`** — a slow annual sine wave:
  `0.15 * sin(2*pi * day_of_year/365 + phase_offset)`, where
  `phase_offset` is a fixed, different constant per blood type (so all
  four types don't peak/trough on the same calendar day as each other, or
  as supply's own real seasonality).
- **`daily_noise()`** — `random.normal(0, 0.08)`, independent day-to-day
  jitter.
- **`spike_multiplier(date)`** — on a random ~4% of days (seeded, so
  reproducible), a `random.uniform(1.3, 1.8)` multiplier simulating a
  trauma/mass-casualty demand spike; `1.0` on all other days.

The whole script uses a fixed random seed so re-running it regenerates an
identical file. Output is rounded to the nearest integer and floored at a
minimum of 1 unit (never zero or negative).

The core per-row formula is implemented as a standalone, testable function
(not inlined in a loop), so it can be unit-tested without needing the full
CSV:

```python
def compute_demand(donation_units: int, date: pd.Timestamp, blood_type: str,
                    rng: np.random.Generator) -> int:
    ...
```

## Backend changes

### `backend/ml/train_demand.py` (full rewrite)

Trains **4 separate LightGBM models, one per blood type** — mirroring
`train_supply.py`'s 4-Prophet-model loop exactly. Each model is trained on
purely calendar-derived features (`DayOfWeek`, `Month`, `Quarter`,
`DayOfYear`, `DayOfMonth`, `WeekOfYear`) against that type's `demand`
column, using the same time-series train/test split convention (last 30
days held out) and the same LightGBM hyperparameters already used for the
old aggregate model. Saved as a dict (`{blood_type: model}`) to
`backend/ml/demand_models.pkl` (renamed from `demand_model.pkl`, now
plural to match `supply_models.pkl`'s naming).

### `backend/ml/inference.py`

- `get_demand_model()` → renamed `get_demand_models()`, loads the dict from
  `demand_models.pkl` (mirrors `get_supply_models()`).
- `predict_demand()` and `predict_demand_by_type()` collapse into one
  function, `predict_demand_by_type(days=30)`, which loops over the 4
  loaded models and predicts each type's future demand using **only
  calendar features** — no synthesized `Population`/`Events`/
  `HospitalAdmissions`/`Temperature` needed, since those columns no longer
  exist. This is a deliberate side benefit: calendar features for a future
  date are always exactly known (no guessing), so **the forecast becomes
  fully deterministic** — calling the endpoint twice in a row now returns
  the same numbers, fixing the earlier randomness bug as a side effect of
  this change.
- `predict_supply()` is untouched.

### `backend/api/main.py`

- `/api/forecast/demand` changes response shape from one aggregate list to
  a per-type dict (`{"A": [...], "B": [...], "AB": [...], "O": [...]}`),
  matching `/api/forecast/supply`'s existing shape.
- `/api/train/demand` now calls the rewritten `train_demand.train()`
  (trains 4 models instead of 1) — same endpoint, same trigger, updated
  implementation underneath.
- `/api/simulate` still calls `predict_demand_by_type()` — the route body
  barely changes, since the function keeps the same name and signature;
  only its internal implementation changes (per-type LightGBM models
  instead of one aggregate model plus donation-ratio disaggregation).

### `backend/config.py`

- Remove `DEMAND_SCALE_FACTOR` (no longer needed).
- Everything else (`BLOOD_TYPES`, `SHELF_LIFE_DAYS`,
  `INITIAL_STOCK_COVERAGE_DAYS`, the shortage/wastage thresholds) is
  unaffected.

## Testing

- `generate_demand.py`'s `compute_demand()`: unit tests with fixed inputs
  and a seeded RNG, asserting the output falls within the expected range
  for a known weekday/weekend/spike-day/non-spike-day combination, and
  that it's never zero or negative.
- `train_demand.py`: no new unit tests needed beyond what already exists
  for `train_supply.py`'s pattern (the existing end-to-end
  `test_api_simulate.py` fixture already exercises training for real as
  part of its setup).
- `inference.py`: replace the old `test_predict_demand_by_type_splits_the_aggregate`
  and `test_predict_demand_applies_the_scale_factor` tests (both no longer
  applicable) with a test that monkeypatches `get_demand_models()` to
  return 4 fake per-type models and asserts `predict_demand_by_type()`
  returns all 4 keys with the expected shape.
- `test_demand_split.py`: deleted entirely (module no longer exists).
- `test_api_simulate.py`: unaffected in structure (still trains both
  sides then hits `/api/simulate`), but will now also implicitly verify
  the new demand training path works end-to-end.
- One new manual verification step: call `/api/simulate` twice in a row
  and confirm the two responses are now identical (proving the
  determinism fix works), before and separately from checking that
  shortage/wastage states actually appear across the 30-day window.

## Out of scope (explicitly)

- No change to the supply/donation side (`train_supply.py`,
  `predict_supply()`) — already real, already coherent.
- No change to the simulation engine, rule-based classifiers, or any
  frontend code — this only replaces how the demand numbers are produced,
  not how they're consumed.
- Historical demand data is still fundamentally synthetic (there is no
  real per-type Malaysian demand dataset available) — this design makes
  that synthesis honest and coherent with real supply, it does not make
  demand "real."
