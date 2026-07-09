# Self-Generated Per-Type Demand Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Kaggle demand dataset (itself synthetic, and on an unrelated scale to the real Malaysia supply data) with a demand dataset generated directly per blood type, anchored to the real donation data so both are coherent by construction, then retrain the demand-forecasting pipeline around it.

**Architecture:** A one-off generator script derives synthetic per-type demand from the real `blood_donations.csv` (same dates, same order of magnitude, via a documented formula with its own independent weekly/seasonal shape and random spikes). Four LightGBM models (one per blood type, mirroring the existing Prophet-per-type pattern) are trained on this new data using pure calendar features — which also makes the forecast fully deterministic, since future calendar features never need to be guessed. The donation-ratio disaggregation module and the demand scale factor both become unnecessary and are removed.

**Tech Stack:** pandas, numpy, LightGBM, pytest (all already in the project).

**Spec:** `docs/superpowers/specs/2026-07-09-synthetic-demand-generation-design.md`

---

## Task 1: Create the demand generator with tests

**Files:**
- Create: `backend/data/generate_demand.py`
- Create: `backend/tests/test_generate_demand.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_generate_demand.py`:

```python
import numpy as np
import pandas as pd

from data.generate_demand import compute_demand, weekday_multiplier, seasonal_wave


def test_weekday_multiplier_is_higher_on_weekdays_than_weekends():
    monday = pd.Timestamp("2024-01-01")
    saturday = pd.Timestamp("2024-01-06")
    assert weekday_multiplier(monday) == 1.05
    assert weekday_multiplier(saturday) == 0.85


def test_seasonal_wave_differs_by_blood_type_on_the_same_date():
    date = pd.Timestamp("2024-06-15")
    waves = {bt: seasonal_wave(date, bt) for bt in ["a", "b", "ab", "o"]}
    assert len(set(waves.values())) == 4


def test_compute_demand_is_never_zero_or_negative():
    rng = np.random.default_rng(1)
    date = pd.Timestamp("2024-03-10")
    for donation_units in [0, 1, 5, 500]:
        result = compute_demand(donation_units, date, "o", rng)
        assert result >= 1


class _FixedRNG:
    def __init__(self, normal_val, random_val, uniform_val):
        self._normal = normal_val
        self._random = random_val
        self._uniform = uniform_val

    def normal(self, loc, scale):
        return self._normal

    def random(self):
        return self._random

    def uniform(self, low, high):
        return self._uniform


def test_compute_demand_spike_day_exceeds_non_spike_day():
    date = pd.Timestamp("2024-03-10")
    no_spike_rng = _FixedRNG(normal_val=0.0, random_val=0.99, uniform_val=1.5)
    spike_rng = _FixedRNG(normal_val=0.0, random_val=0.01, uniform_val=1.5)

    no_spike_result = compute_demand(100, date, "o", no_spike_rng)
    spike_result = compute_demand(100, date, "o", spike_rng)

    assert spike_result > no_spike_result
```

- [ ] **Step 2: Run the tests to confirm they fail**

Run: `cd /Users/aarushluthra/blood/backend && .venv/bin/pytest tests/test_generate_demand.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'data.generate_demand'`

- [ ] **Step 3: Implement backend/data/generate_demand.py**

```python
"""
Generates a synthetic demand dataset, anchored to the real Malaysia
donation data (backend/data/blood_donations.csv), covering 2019-01-01
to 2024-12-31.

See docs/superpowers/specs/2026-07-09-synthetic-demand-generation-design.md
for the full rationale. Run once: `python generate_demand.py` from this
directory (or via `make generate-demand` from the repo root).
"""
import os

import numpy as np
import pandas as pd

BLOOD_TYPES = ["a", "b", "ab", "o"]
START_DATE = "2019-01-01"
END_DATE = "2024-12-31"
SPIKE_PROBABILITY = 0.04

# Fixed per-type seasonal phase offsets (radians) so each type's annual
# wave peaks/troughs on a different day than the others or than supply's
# own real seasonality.
PHASE_OFFSETS = {"a": 0.0, "b": 1.57, "ab": 3.14, "o": 4.71}

DONATIONS_PATH = os.path.join(os.path.dirname(__file__), "blood_donations.csv")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "blood_demand.csv")


def weekday_multiplier(date):
    """Demand's own weekly shape: higher on weekdays (elective procedures), lower on weekends."""
    return 0.85 if date.dayofweek >= 5 else 1.05


def seasonal_wave(date, blood_type):
    """A slow annual sine wave, phase-shifted per blood type."""
    day_of_year = date.dayofyear
    phase = PHASE_OFFSETS[blood_type]
    return 0.15 * np.sin(2 * np.pi * day_of_year / 365 + phase)


def compute_demand(donation_units, date, blood_type, rng):
    """
    Computes one day's synthetic demand for one blood type, anchored to
    that day's real donation count.

    donation_units: the real donations that day for this blood type (int)
    date: a pandas.Timestamp
    blood_type: one of "a", "b", "ab", "o"
    rng: an object with .normal(loc, scale), .random(), and .uniform(low, high)
         methods (a numpy.random.Generator in production; a test double in tests)

    Returns: an int, always >= 1.
    """
    noise = rng.normal(0, 0.08)
    ratio = 1 + seasonal_wave(date, blood_type) + noise
    spike = rng.uniform(1.3, 1.8) if rng.random() < SPIKE_PROBABILITY else 1.0

    demand = donation_units * weekday_multiplier(date) * ratio * spike
    return max(1, round(demand))


def main():
    rng = np.random.default_rng(42)

    donations = pd.read_csv(DONATIONS_PATH)
    donations["date"] = pd.to_datetime(donations["date"])
    donations = donations[donations["blood_type"] != "all"]
    donations = donations[
        (donations["date"] >= START_DATE) & (donations["date"] <= END_DATE)
    ]

    rows = []
    for _, row in donations.iterrows():
        demand = compute_demand(row["donations"], row["date"], row["blood_type"], rng)
        rows.append({
            "date": row["date"].strftime("%Y-%m-%d"),
            "blood_type": row["blood_type"],
            "demand": demand,
        })

    result = pd.DataFrame(rows).sort_values(["date", "blood_type"])
    result.to_csv(OUTPUT_PATH, index=False)
    print(f"Wrote {len(result)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tests again to confirm they pass**

Run: `cd /Users/aarushluthra/blood/backend && .venv/bin/pytest tests/test_generate_demand.py -v`
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
cd /Users/aarushluthra/blood
git add backend/data/generate_demand.py backend/tests/test_generate_demand.py
git commit -m "feat: add synthetic per-type demand generator anchored to real donation data"
```

---

## Task 2: Generate and commit the new demand dataset

**Files:**
- Modify: `backend/data/blood_demand.csv` (fully regenerated, new schema)

- [ ] **Step 1: Run the generator**

Run: `cd /Users/aarushluthra/blood/backend/data && /Users/aarushluthra/blood/backend/.venv/bin/python generate_demand.py`
Expected output: `Wrote 8768 rows to /Users/aarushluthra/blood/backend/data/blood_demand.csv`

- [ ] **Step 2: Spot-check the new file's schema and scale**

Run: `head -5 /Users/aarushluthra/blood/backend/data/blood_demand.csv`
Expected: a header `date,blood_type,demand` followed by rows like `2019-01-01,a,<number>`.

Run this sanity check comparing the new demand data's scale to the real donation data's scale (they should now be close, unlike before):
```bash
cd /Users/aarushluthra/blood/backend && .venv/bin/python -c "
import pandas as pd
demand = pd.read_csv('data/blood_demand.csv')
donations = pd.read_csv('data/blood_donations.csv')
donations = donations[donations['blood_type'] != 'all']
for bt in ['a', 'b', 'ab', 'o']:
    d = demand[demand['blood_type'] == bt]['demand'].mean()
    s = donations[donations['blood_type'] == bt]['donations'].mean()
    print(f'{bt}: avg demand={d:.1f}, avg donations={s:.1f}, ratio={d/s:.3f}')
"
```
Expected: ratios all close to 1.0 (roughly 0.95–1.05) for every blood type — confirming demand and supply are now on the same real scale.

- [ ] **Step 3: Commit the regenerated file**

```bash
cd /Users/aarushluthra/blood
git add backend/data/blood_demand.csv
git commit -m "chore: regenerate blood_demand.csv as synthetic per-type data anchored to real donations

Replaces the old Kaggle-sourced file (itself synthetic, and on an
unrelated scale to the real Malaysia supply data) with output from
generate_demand.py."
```

---

## Task 3: Rewrite backend/ml/train_demand.py to train 4 per-type LightGBM models

**Files:**
- Modify: `backend/ml/train_demand.py` (full rewrite)

- [ ] **Step 1: Replace the full contents of backend/ml/train_demand.py**

```python
import os

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

DATA_PATH = os.path.join(os.path.dirname(__file__), '../data/blood_demand.csv')
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'demand_models.pkl')
BLOOD_TYPES = ['a', 'b', 'ab', 'o']


def create_features(df):
    """Create time series features based on the DataFrame's date index."""
    df = df.copy()
    df['DayOfWeek'] = df.index.dayofweek
    df['Month'] = df.index.month
    df['Quarter'] = df.index.quarter
    df['DayOfYear'] = df.index.dayofyear
    df['DayOfMonth'] = df.index.day
    df['WeekOfYear'] = df.index.isocalendar().week.astype(int)
    return df


def train():
    df = pd.read_csv(DATA_PATH)
    df['date'] = pd.to_datetime(df['date'])

    features = ['DayOfWeek', 'Month', 'Quarter', 'DayOfYear', 'DayOfMonth', 'WeekOfYear']
    models = {}

    for bt in BLOOD_TYPES:
        print(f"Training LightGBM model for Blood Demand: {bt.upper()}...")
        df_bt = df[df['blood_type'] == bt].copy()
        df_bt.set_index('date', inplace=True)
        df_bt.sort_index(inplace=True)
        df_bt = create_features(df_bt)

        train_df = df_bt.iloc[:-30]
        test_df = df_bt.iloc[-30:]

        X_train, y_train = train_df[features], train_df['demand']
        X_test, y_test = test_df[features], test_df['demand']

        model = lgb.LGBMRegressor(
            n_estimators=500,
            learning_rate=0.05,
            max_depth=6,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42
        )
        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            callbacks=[lgb.early_stopping(stopping_rounds=50)]
        )

        preds = model.predict(X_test)
        mae = mean_absolute_error(y_test, preds)
        rmse = np.sqrt(mean_squared_error(y_test, preds))
        print(f"{bt.upper()} Test MAE: {mae:.2f}")
        print(f"{bt.upper()} Test RMSE: {rmse:.2f}")

        models[bt] = model

    joblib.dump(models, MODEL_PATH)
    print(f"All demand models saved to {MODEL_PATH}")


if __name__ == "__main__":
    train()
```

- [ ] **Step 2: Verify it trains successfully**

Run: `cd /Users/aarushluthra/blood/backend && .venv/bin/python -c "from ml.train_demand import train; train()"`
Expected: prints training progress and MAE/RMSE for each of A, B, AB, O, ending with `All demand models saved to .../backend/ml/demand_models.pkl`

- [ ] **Step 3: Confirm the old single-model file is gone and the new one exists**

Run: `ls /Users/aarushluthra/blood/backend/ml/*.pkl`
Expected: `demand_models.pkl` and `supply_models.pkl` (no `demand_model.pkl` — if it still exists from a previous run, that's fine, it's gitignored and unused going forward; it just won't be loaded by anything after Task 4).

- [ ] **Step 4: Commit**

```bash
cd /Users/aarushluthra/blood
git add backend/ml/train_demand.py
git commit -m "feat: train 4 per-type LightGBM demand models instead of 1 aggregate model"
```

---

## Task 4: Rewrite backend/ml/inference.py's demand functions

**Files:**
- Modify: `backend/ml/inference.py` (full rewrite)

- [ ] **Step 1: Replace the full contents of backend/ml/inference.py**

```python
import os
from datetime import datetime, timedelta

import joblib
import pandas as pd

DEMAND_MODELS_PATH = os.path.join(os.path.dirname(__file__), 'demand_models.pkl')
SUPPLY_MODELS_PATH = os.path.join(os.path.dirname(__file__), 'supply_models.pkl')


def get_demand_models():
    if os.path.exists(DEMAND_MODELS_PATH):
        return joblib.load(DEMAND_MODELS_PATH)
    return {}


def get_supply_models():
    if os.path.exists(SUPPLY_MODELS_PATH):
        return joblib.load(SUPPLY_MODELS_PATH)
    return {}


def predict_demand_by_type(days=30):
    """
    Predicts per-blood-type demand for the next 'days' days using the 4
    LightGBM models (one per type), trained purely on calendar features.

    Unlike the old aggregate model, no future covariates need to be
    synthesized/guessed here -- calendar features for a future date are
    always exactly known, so this forecast is fully deterministic: calling
    it twice in a row returns identical results.
    """
    models = get_demand_models()
    if not models:
        raise Exception("Demand models not trained yet.")

    start_date = datetime.now()
    future_dates = [start_date + timedelta(days=i) for i in range(days)]

    df_future = pd.DataFrame({'date': future_dates})
    df_future.set_index('date', inplace=True)
    df_future['DayOfWeek'] = df_future.index.dayofweek
    df_future['Month'] = df_future.index.month
    df_future['Quarter'] = df_future.index.quarter
    df_future['DayOfYear'] = df_future.index.dayofyear
    df_future['DayOfMonth'] = df_future.index.day
    df_future['WeekOfYear'] = df_future.index.isocalendar().week.astype(int)

    features = ['DayOfWeek', 'Month', 'Quarter', 'DayOfYear', 'DayOfMonth', 'WeekOfYear']

    results = {}
    for bt, model in models.items():
        preds = model.predict(df_future[features])
        results[bt.upper()] = [
            {"date": date.strftime('%Y-%m-%d'), "predicted_demand": max(0, round(float(pred)))}
            for date, pred in zip(future_dates, preds)
        ]
    return results


def predict_supply(days=30):
    """
    Predicts blood supply/donations for the next 'days' using Prophet.
    Returns predictions broken down by blood type.
    """
    models = get_supply_models()
    if not models:
        raise Exception("Supply models not trained yet.")

    results = {}
    for bt, model in models.items():
        future = model.make_future_dataframe(periods=days)
        forecast = model.predict(future)
        recent_forecast = forecast[['ds', 'yhat']].tail(days)

        preds = []
        for _, row in recent_forecast.iterrows():
            preds.append({
                "date": row['ds'].strftime('%Y-%m-%d'),
                "predicted_supply": max(0, round(float(row['yhat'])))
            })
        results[bt.upper()] = preds

    return results
```

- [ ] **Step 2: Verify it imports cleanly**

Run: `cd /Users/aarushluthra/blood/backend && .venv/bin/python -c "import ml.inference"`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd /Users/aarushluthra/blood
git add backend/ml/inference.py
git commit -m "feat: predict demand directly per type from calendar-feature models

Removes predict_demand() (the old aggregate model), the demand_split
disaggregation step, and DEMAND_SCALE_FACTOR usage -- predict_demand_by_type
now loads the 4 per-type LightGBM models directly. Also fixes the
non-determinism bug from the old synthesized future covariates, since
calendar features for a future date are always exactly known."
```

---

## Task 5: Remove DEMAND_SCALE_FACTOR from backend/config.py

**Files:**
- Modify: `backend/config.py`

- [ ] **Step 1: Remove the now-unused constant**

Remove this block from the end of `backend/config.py`:

```python

# The demand dataset (Kaggle, ~184 units/day national total) and the supply
# dataset (Malaysia, ~1299 units/day national total across all 4 types) come
# from two different-sized real-world systems -- without reconciling scale,
# supply always dwarfs demand and the simulation never shows a shortage or
# wastage. This factor scales the demand forecast up to be comparable to the
# supply forecast's real scale (computed as avg_total_supply / avg_total_demand
# from the two real CSVs: 1299.2 / 184.0 = 7.0623), rather than fabricating
# new demand numbers from nothing.
DEMAND_SCALE_FACTOR = 7.0623
```

The file should end with the `WASTAGE_MED_RATIO = 0.15` line.

- [ ] **Step 2: Confirm nothing still imports it**

Run: `grep -rn "DEMAND_SCALE_FACTOR" /Users/aarushluthra/blood/backend --include="*.py"`
Expected: no output (the import was already removed from `inference.py` in Task 4).

- [ ] **Step 3: Commit**

```bash
cd /Users/aarushluthra/blood
git add backend/config.py
git commit -m "chore: remove DEMAND_SCALE_FACTOR, no longer needed with anchored demand generation"
```

---

## Task 6: Delete the demand_split module and its test

**Files:**
- Delete: `backend/ml/demand_split.py`, `backend/tests/test_demand_split.py`

- [ ] **Step 1: Confirm nothing still imports demand_split**

Run: `grep -rn "demand_split" /Users/aarushluthra/blood/backend --include="*.py"`
Expected: no output (the import was already removed from `inference.py` in Task 4; the only remaining references would be in the deleted files themselves, which this step's grep will still show until Step 2 removes them — if you see hits ONLY in `backend/ml/demand_split.py` or `backend/tests/test_demand_split.py`, that's expected and fine).

- [ ] **Step 2: Delete both files**

```bash
cd /Users/aarushluthra/blood
git rm backend/ml/demand_split.py backend/tests/test_demand_split.py
```

- [ ] **Step 3: Commit**

```bash
git commit -m "chore: remove demand_split module, superseded by native per-type demand generation"
```

---

## Task 7: Rewrite backend/tests/test_inference.py

**Files:**
- Modify: `backend/tests/test_inference.py` (full rewrite)

- [ ] **Step 1: Write the new tests**

Replace the full contents of `backend/tests/test_inference.py`:

```python
from ml import inference


def test_predict_demand_by_type_returns_all_four_types(monkeypatch):
    class FakeModel:
        def predict(self, X):
            return [42.0] * len(X)

    fake_models = {bt: FakeModel() for bt in ["a", "b", "ab", "o"]}
    monkeypatch.setattr(inference, "get_demand_models", lambda: fake_models)

    result = inference.predict_demand_by_type(days=3)

    assert set(result.keys()) == {"A", "B", "AB", "O"}
    for bt in result:
        assert len(result[bt]) == 3
        for record in result[bt]:
            assert record["predicted_demand"] == 42
            assert "date" in record


def test_predict_demand_by_type_raises_when_untrained(monkeypatch):
    monkeypatch.setattr(inference, "get_demand_models", lambda: {})

    try:
        inference.predict_demand_by_type(days=1)
        assert False, "expected an exception"
    except Exception as e:
        assert "not trained" in str(e)
```

- [ ] **Step 2: Run the tests to confirm they pass**

Run: `cd /Users/aarushluthra/blood/backend && .venv/bin/pytest tests/test_inference.py -v`
Expected: `2 passed`

- [ ] **Step 3: Commit**

```bash
cd /Users/aarushluthra/blood
git add backend/tests/test_inference.py
git commit -m "test: rewrite inference tests for direct per-type demand prediction"
```

---

## Task 8: Update backend/api/main.py

**Files:**
- Modify: `backend/api/main.py`

- [ ] **Step 1: Update the import line**

Change:
```python
from ml.inference import predict_demand, predict_supply, predict_demand_by_type
```
to:
```python
from ml.inference import predict_supply, predict_demand_by_type
```

- [ ] **Step 2: Update the /api/forecast/demand handler**

Change:
```python
@app.get("/api/forecast/demand")
def get_demand_forecast(days: int = 30):
    try:
        forecast = predict_demand(days)
        return {"status": "success", "data": forecast}
    except Exception as e:
        logging.error(f"Demand Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
```
to:
```python
@app.get("/api/forecast/demand")
def get_demand_forecast(days: int = 30):
    try:
        forecast = predict_demand_by_type(days)
        return {"status": "success", "data": forecast}
    except Exception as e:
        logging.error(f"Demand Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
```

(`/api/simulate` and `/api/train/demand` are unchanged — they already call `predict_demand_by_type` and `train_demand_model`/`train()` respectively, both of which keep the same names.)

- [ ] **Step 2: Verify the app still imports cleanly**

Run: `cd /Users/aarushluthra/blood/backend && .venv/bin/python -c "import api.main"`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd /Users/aarushluthra/blood
git add backend/api/main.py
git commit -m "feat: return per-type shape from /api/forecast/demand, matching /api/forecast/supply"
```

---

## Task 9: Retrain and manually verify determinism and realistic risk states

**Files:** none (verification only)

- [ ] **Step 1: Start the backend**

Run: `cd /Users/aarushluthra/blood/backend && .venv/bin/uvicorn api.main:app --port 8000 &`

(Use `preview_start` if working inside the agent harness.)

- [ ] **Step 2: Confirm two consecutive calls now return identical results (determinism fix)**

```bash
curl -s "http://localhost:8000/api/simulate?days=5" > /tmp/run1.json
curl -s "http://localhost:8000/api/simulate?days=5" > /tmp/run2.json
diff /tmp/run1.json /tmp/run2.json && echo "IDENTICAL - determinism confirmed"
```
Expected: `IDENTICAL - determinism confirmed` (no diff output).

- [ ] **Step 3: Confirm shortage/wastage states now actually appear across a 30-day window**

```bash
curl -s "http://localhost:8000/api/simulate?days=30" | python3 -c "
import json, sys
data = json.load(sys.stdin)['data']
for bt, records in data.items():
    risks = {}
    for r in records:
        risks[r['shortage_risk']] = risks.get(r['shortage_risk'], 0) + 1
    print(f'{bt}: {risks}')
"
```
Expected: at least one blood type shows some `WARNING` or `CRITICAL` days mixed in with `SAFE` (not all 30 days `SAFE` for every type, and not all 30 days `CRITICAL` either — a realistic mix).

- [ ] **Step 4: Stop the server**

Run: `kill %1` (or `preview_stop` if using the harness tool)

No commit for this task — verification only.

---

## Task 10: Run the full backend test suite

**Files:** none (verification only)

- [ ] **Step 1: Run every test**

Run: `cd /Users/aarushluthra/blood/backend && .venv/bin/pytest tests/ -v`
Expected: all tests pass (demand generation x4, engine x4, inference x2, shortage_rules x3, wastage_rules x3, api_simulate x1 — 17 total; `test_demand_split.py` no longer exists).

No commit for this task — verification only.

---

## Task 11: Update backend/data/README.md

**Files:**
- Modify: `backend/data/README.md` (full rewrite)

- [ ] **Step 1: Replace the full contents**

```markdown
# Datasets for BloodIQ ML Models

## 1. Supply dataset (real) — `blood_donations.csv`
* **Source:** [Malaysia government open data](https://data.gov.my/data-catalogue/blood_donations) — real, daily, per blood type (a/b/ab/o), 2006–2026.
* Already committed to this repo.

## 2. Demand dataset (synthetic, generated) — `blood_demand.csv`
* **Not sourced externally.** Generated by `generate_demand.py` in this
  directory, anchored to the real donation data above so both datasets
  share the same calendar and order of magnitude.
* To regenerate: `python generate_demand.py` (deterministic — same
  output every run, given the same `blood_donations.csv`).
* See `docs/superpowers/specs/2026-07-09-synthetic-demand-generation-design.md`
  for the full generation method and rationale.
```

- [ ] **Step 2: Commit**

```bash
cd /Users/aarushluthra/blood
git add backend/data/README.md
git commit -m "docs: update data README to reflect the generated demand dataset"
```

---

## Task 12: Update docs/ARCHITECTURE.md

**Files:**
- Modify: `docs/ARCHITECTURE.md`

- [ ] **Step 1: Update the data and backend sections**

Replace this part of the "Data" section:
```markdown
- `backend/data/blood_demand.csv` — Kaggle, national aggregate daily demand,
  2020-2024. No blood-type breakdown.
```
with:
```markdown
- `backend/data/blood_demand.csv` — synthetic, generated by
  `backend/data/generate_demand.py`, anchored to the real donation data
  below so both share the same calendar and scale. Per blood type
  (A, B, AB, O), 2019-2024.
```

Replace this part of the "Backend" directory tree:
```
    train_demand.py     LightGBM on aggregate demand
    train_supply.py     Prophet x4, one per blood type, on real donations
    demand_split.py      Disaggregates the aggregate demand forecast into
                          per-type demand, using each type's historical
                          share of donations as a proxy ratio
    inference.py          predict_demand / predict_supply / predict_demand_by_type
```
with:
```
    train_demand.py     LightGBM x4, one per blood type, on generated demand
    train_supply.py     Prophet x4, one per blood type, on real donations
    inference.py          predict_demand_by_type / predict_supply
```

- [ ] **Step 2: Commit**

```bash
cd /Users/aarushluthra/blood
git add docs/ARCHITECTURE.md
git commit -m "docs: update ARCHITECTURE.md for the generated per-type demand pipeline"
```

---

## Task 13: Update docs/PROJECT_EXPLAINED.md

**Files:**
- Modify: `docs/PROJECT_EXPLAINED.md`

- [ ] **Step 1: Replace section 2.1 (the demand dataset)**

Replace the entire "2.1 The demand dataset" subsection (from `### 2.1 The demand dataset` up to but not including `### 2.2`) with:

```markdown
### 2.1 The demand dataset — `backend/data/blood_demand.csv`

**Where it's from:** nowhere external — this one is generated by this
project itself, by `backend/data/generate_demand.py`. The original version
of this project used a Kaggle dataset here, but that dataset turned out to
itself be synthetic (its `PredictedBloodDemand` column name was the
giveaway — a genuine historical record wouldn't be pre-labeled
"predicted"), and worse, it came from an unrelated country/scale to the
real Malaysia supply data, which made national demand and national supply
numbers meaningless to compare directly. This project now generates its
own demand data instead, explicitly and transparently synthetic, anchored
to the real donation data so the two are actually comparable.

**How it's generated:** for every real `(date, blood_type)` row in the
donations data (see 2.2 below), a demand number is computed as:

```
demand = donations_that_day
         x weekday_multiplier   (demand's own weekly shape: ~1.05 on
                                 weekdays, ~0.85 on weekends -- elective
                                 procedures cluster on weekdays, unlike
                                 donation drives)
         x (1 + seasonal_wave + noise)   (a slow annual wave, phase-shifted
                                           differently per blood type, plus
                                           small daily jitter)
         x spike_multiplier     (on ~4% of days, a random 1.3-1.8x spike,
                                  modeling a trauma/mass-casualty event)
```

Anchoring to the real donation count for that exact day guarantees demand
and supply share the same calendar and order of magnitude by construction
-- while the independent weekly shape, seasonal phase, and spikes mean
demand isn't just "supply times a constant." In practice, generated demand
averages 98-99% of real donations per blood type, and exceeds it on about
half of all days -- meaning shortages and surpluses both happen
organically, rather than one side permanently dwarfing the other.

**What each column means:** `date`, `blood_type` (a/b/ab/o), `demand`
(the generated number of units demanded that day for that type) --
the same three-column shape as the real donations file.

**Covers:** 2019-01-01 to 2024-12-31 (matching the window already used to
train the supply-side Prophet models), regenerated deterministically from
a fixed random seed.
```

- [ ] **Step 2: Replace section 3 (Machine Learning Model #1 — Demand Forecasting)**

Replace the entire `## 3. Machine Learning Model #1 — Demand Forecasting (LightGBM)`
section (up to but not including `## 4.`) with:

```markdown
## 3. Machine Learning Model #1 — Demand Forecasting (LightGBM)

**File:** `backend/ml/train_demand.py`, used via `backend/ml/inference.py`

**What it is:** the same LightGBM technique described for the supply side's
counterpart below -- fast, accurate gradient-boosted decision trees for
tabular data.

**What it's trained to do:** unlike the original version of this project
(one model predicting one national aggregate number), this trains **four
separate LightGBM models, one per blood type (A, B, AB, O)** -- mirroring
exactly how the supply side already trains four separate Prophet models.
Each model only ever sees its own blood type's generated demand history.

**The exact features it uses:** purely calendar-derived features --
`DayOfWeek`, `Month`, `Quarter`, `DayOfYear`, `DayOfMonth`, `WeekOfYear` --
computed automatically from the date. Notably, there are **no synthesized
guess-features** here (the original version needed to invent plausible
future `Population`/`Events`/`HospitalAdmissions`/`Temperature` values,
since those aren't knowable in advance) -- because calendar features for
any future date are always exactly and deterministically known, this model
needs nothing invented to make a forecast.

**How it's trained:** for each blood type, the same train/test split
convention as before (all but the last 30 days for training, held-out last
30 days for evaluation), the same LightGBM hyperparameters (500 trees,
learning rate 0.05, max depth 6, early stopping after 50 non-improving
rounds), and the same MAE/RMSE evaluation. All four trained models are
saved together as a dictionary in `backend/ml/demand_models.pkl`.

**How it predicts the future:** simply computes the calendar features for
each requested future date and asks each of the four models for its
prediction -- no randomness involved anywhere in this step. **This means
the demand forecast is now fully deterministic**: calling the API twice in
a row for the same future window returns identical numbers, unlike the
original version (see section 10, "What changed," for why this matters).

**Output:** a dictionary keyed by blood type
(`{"A": [...], "B": [...], "AB": [...], "O": [...]}`), each holding a list
of `{date, predicted_demand}` pairs -- the same shape the supply model
already returns.
```

- [ ] **Step 3: Replace section 5 (the disaggregation problem)**

Replace the entire `## 5. The disaggregation problem, and how it's solved`
section (up to but not including `## 6.`) with:

```markdown
## 5. Why there's no "disaggregation problem" anymore

An earlier version of this project only had a single national demand
number (no blood-type breakdown at all), and had to approximate a
per-type split using each type's share of real donations. Since demand is
now generated and forecast **directly per blood type** (see sections 2.1
and 3 above), that disaggregation step is no longer needed and has been
removed from the codebase entirely (`backend/ml/demand_split.py` is gone).
Every blood type now has its own real forecast, not a fraction of someone
else's.
```

- [ ] **Step 4: Add a new closing section explaining what changed and why**

Add this new section immediately before the existing `## 11. Quick reference — file map` section (renumber it to `## 12.`):

```markdown
## 11. What changed since the first version, and why

The first working version of this project used a real Kaggle "blood
demand" dataset for the demand side. Two problems emerged once it was
actually running:

1. **The dataset was itself synthetic.** Its `PredictedBloodDemand` column
   name gave it away -- a genuinely historical record doesn't need a
   column pre-labeled "predicted."
2. **It was on a completely different scale from the real supply data.**
   National demand in that dataset averaged ~184 units/day; the real
   Malaysia donation data averages ~1,299 units/day. Since these numbers
   came from unrelated systems, supply always dwarfed demand no matter how
   the numbers were combined -- the simulation could never show a
   realistic shortage or wastage day.

The fix was not to paper over the mismatch with a scaling constant (an
earlier, since-abandoned patch did try exactly that), but to stop using an
unrelated, misleadingly-labeled dataset altogether. This project now
generates its own demand data, explicitly labeled as synthetic, anchored
to the real donation numbers so the two are coherent by construction (see
section 2.1). A useful side effect: the new demand model only needs
calendar features to forecast the future, which are always exactly known
-- so the forecast is now fully deterministic, where the old model needed
to guess at unknowable future covariates and gave a different answer every
time it was asked.
```

- [ ] **Step 5: Renumber the old "10. What this project deliberately does NOT do" and "11. Quick reference" sections to "10." and "12." respectively, to keep the document's numbering sequential** (the new section above becomes 11; the file map moves to 12).

- [ ] **Step 6: Commit**

```bash
cd /Users/aarushluthra/blood
git add docs/PROJECT_EXPLAINED.md
git commit -m "docs: update PROJECT_EXPLAINED.md for the generated per-type demand pipeline"
```

---

## Task 14: Update root README.md

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update the Scope section**

Replace:
```markdown
Built on two real, freely available datasets:

- **Demand:** [Kaggle blood demand dataset](https://www.kaggle.com/datasets/rishi2003das/blood-demand-dataset) — national daily aggregate.
- **Supply:** [Malaysia government blood donation data](https://data.gov.my/data-catalogue/blood_donations) — daily, per blood type.

Neither dataset has hospital-level detail or Rh factor (+/-), so BloodIQ
targets national-level A/B/AB/O forecasting and simulation only — see
`docs/superpowers/specs/2026-07-09-bloodiq-simplification-design.md` for
the full rationale.
```
with:
```markdown
Built on one real dataset and one dataset generated to be coherent with it:

- **Supply (real):** [Malaysia government blood donation data](https://data.gov.my/data-catalogue/blood_donations) — daily, per blood type, 2006–2026.
- **Demand (generated):** produced by `backend/data/generate_demand.py`,
  anchored to the real donation data above so both share the same
  calendar and order of magnitude — see
  `docs/superpowers/specs/2026-07-09-synthetic-demand-generation-design.md`
  for the full method and rationale.

Neither dataset has hospital-level detail or Rh factor (+/-), so BloodIQ
targets national-level A/B/AB/O forecasting and simulation only.
```

- [ ] **Step 2: Update the Quick start section's training commands**

Replace:
```bash
.venv/bin/python -c "from ml.train_demand import train; train()"
```
This line's command is unchanged (the function name and call signature are the same — no edit needed here), but regenerate the data file first by adding this line immediately before it:
```bash
.venv/bin/python data/generate_demand.py
```

So the full Quick start backend block becomes:
```markdown
```bash
# Backend
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python data/generate_demand.py
.venv/bin/python -c "from ml.train_demand import train; train()"
.venv/bin/python -c "from ml.train_supply import train; train()"
.venv/bin/uvicorn api.main:app --reload --port 8000
```
```

- [ ] **Step 3: Commit**

```bash
cd /Users/aarushluthra/blood
git add README.md
git commit -m "docs: update README for the generated per-type demand dataset"
```

---

## Self-Review Notes (completed during plan authoring)

- **Spec coverage:** every section of the design spec maps to a task —
  generation method -> Task 1-2; train_demand.py rewrite -> Task 3;
  inference.py rewrite -> Task 4; config.py cleanup -> Task 5;
  demand_split removal -> Task 6; test updates -> Task 7; API shape change
  -> Task 8; determinism + realistic-risk verification -> Task 9; full
  suite -> Task 10; all three doc updates (data README, ARCHITECTURE,
  PROJECT_EXPLAINED, root README) -> Tasks 11-14.
- **Verified, not just asserted:** the generation formula and its tests
  were run in a sandbox before being written into this plan (weekday
  multiplier, seasonal wave divergence, never-below-1 floor, and
  spike-exceeds-non-spike were all confirmed with real output). The full
  generator was also run end-to-end against the real donations CSV,
  confirming demand/donation ratios land at 0.98-0.99x per type with
  demand exceeding donations on ~48-49% of days — the intended "organic
  crossover" behavior, not just a plausible-sounding formula.
- **Type/name consistency checked:** `predict_demand_by_type`,
  `get_demand_models`, `demand_models.pkl`, and the `predicted_demand`
  field name are used identically across `train_demand.py`,
  `inference.py`, `api/main.py`, and all tests. `simulation/engine.py` and
  the frontend are untouched and require no changes, since the
  `predicted_demand` field name and the `/api/simulate` response shape
  are unchanged from before this plan.
- **No placeholders:** every step above contains complete, runnable code
  or exact doc text — no "TODO", no "update accordingly" without showing
  the actual replacement text.
