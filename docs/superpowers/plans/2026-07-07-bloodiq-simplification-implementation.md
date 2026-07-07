# BloodIQ Simplification & Gamified Simulation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Strip the repo down to exactly what's needed for four capabilities (per-blood-type supply forecast, demand forecast, rule-based shortage classification, rule-based wastage prediction) built on the two real datasets already in the repo, and ship a "Boss Health Bar" gamified dashboard that visualizes all four per blood type, reusing the existing rose/blush design system.

**Architecture:** A trimmed FastAPI backend (`backend/api/main.py` + `backend/ml/` + new `backend/simulation/`) computes an in-memory, day-by-day FEFO stock simulation per blood type from two real ML forecasts (LightGBM demand, Prophet supply) and returns one JSON payload per `/api/simulate` call. The existing React dashboard (`frontend/src/pages/Dashboard.jsx`) is rebuilt to render that payload as four animated health-bar cards plus a real-data-driven alert feed, replacing all client-side `Math.random()` data. No database, no multi-hospital concept, no 8-way Rh blood types — 4 ABO types only.

**Tech Stack:** FastAPI, LightGBM, Prophet, pandas, pytest, httpx (backend, Python 3.13, existing venv at `backend/.venv`); React 18, Vite, Tailwind v4, Recharts, lucide-react (frontend, existing).

**Spec:** `docs/superpowers/specs/2026-07-07-bloodiq-simplification-design.md`

---

## Phase 0 — Remove junk

### Task 1: Delete redundant member workspaces and their shared config

**Files:**
- Delete: `member_1_data_engineering/`, `member_2_ml_models/`, `member_3_digital_twin/`, `member_4_fullstack/`, `shared/`

- [ ] **Step 1: Confirm nothing outside these directories imports from them**

Run: `grep -rln "shared.config\|member_1_data_engineering\|member_2_ml_models\|member_3_digital_twin\|member_4_fullstack" --include="*.py" --include="*.jsx" --include="*.js" /Users/aarushluthra/blood | grep -v -E "^/Users/aarushluthra/blood/(member_|shared/)"`

Expected: no output (empty). If anything outside `member_*/` or `shared/` shows up, stop and investigate before deleting.

- [ ] **Step 2: Delete the directories**

```bash
cd /Users/aarushluthra/blood
git rm -r member_1_data_engineering member_2_ml_models member_3_digital_twin member_4_fullstack shared
```

- [ ] **Step 3: Commit**

```bash
git commit -m "$(cat <<'EOF'
chore: remove redundant member workspaces and shared MIMIC-IV column contract

These were parallel, never-integrated individual workspaces built around
MIMIC-IV data. The project now uses two real datasets (Kaggle demand,
Malaysia donations) wired directly into backend/.
EOF
)"
```

---

### Task 2: Delete MIMIC-IV data generation, placeholder datasets, and unrelated design file

**Files:**
- Delete: `backend/data_generation/`, `backend/datasets/`, `DESIGN-sentry.md`

- [ ] **Step 1: Confirm nothing imports from backend/data_generation**

Run: `grep -rln "data_generation" /Users/aarushluthra/blood/backend --include="*.py"`

Expected: no output.

- [ ] **Step 2: Delete**

```bash
cd /Users/aarushluthra/blood
git rm -r backend/data_generation DESIGN-sentry.md
# backend/datasets/ is gitignored (untracked) - remove from disk directly
rm -rf backend/datasets
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
chore: remove MIMIC-IV pipeline, placeholder datasets, and stray design file

MIMIC-IV extraction/synthetic data generation is replaced by the two real
datasets in backend/data/. DESIGN-sentry.md was an unrelated, unreferenced
design-token file for a different brand.
EOF
)"
```

---

### Task 3: Delete the original orchestrator backend

**Files:**
- Delete: `backend/main.py`, `backend/services/`, `backend/forecasting/`, `backend/inventory/`, `backend/inventory_simulation/`, `backend/database/`, `backend/models/`, `backend/config/` (old directory), `backend/utils/`, `backend/decision_engine/`, `backend/api/routes.py`, `backend/blood_inventory.db`, `backend/trained_models/`

- [ ] **Step 1: Confirm the surviving backend files have zero dependency on any of this**

Run: `grep -rn "from config\|import config\|from utils\|from decision_engine\|from database\|from models\.\|from services\|from inventory\|from forecasting" /Users/aarushluthra/blood/backend/api/main.py /Users/aarushluthra/blood/backend/ml/*.py /Users/aarushluthra/blood/backend/run.py`

Expected: no output. (Already verified during planning — this step re-confirms before deleting.)

- [ ] **Step 2: Delete tracked files/directories**

```bash
cd /Users/aarushluthra/blood
git rm -r backend/main.py backend/services backend/forecasting backend/inventory backend/inventory_simulation backend/database backend/models backend/config backend/utils backend/decision_engine backend/api/routes.py
```

- [ ] **Step 3: Remove untracked local artifacts**

```bash
rm -f /Users/aarushluthra/blood/backend/blood_inventory.db
rm -rf /Users/aarushluthra/blood/backend/trained_models
find /Users/aarushluthra/blood/backend -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
```

- [ ] **Step 4: Verify `backend/api/main.py` still imports cleanly (expect an error about missing `ml.demand_split` — that's fine, it's created in Task 7; this just confirms the deletions above didn't break anything else)**

Run: `cd /Users/aarushluthra/blood/backend && .venv/bin/python -c "import api.main"`
Expected: succeeds (no import errors) — `demand_split`/`simulation` aren't imported yet at this point in the plan.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
chore: remove original orchestrator backend

Removes the SQL-backed, multi-hospital-oriented backend (main.py,
services/orchestrator.py, forecasting/, inventory/, inventory_simulation/,
database/, models/, old config/, utils/, decision_engine/) built around
synthetic data. Superseded by backend/api + backend/ml + new
backend/simulation, which use the two real datasets and no database.
EOF
)"
```

---

### Task 4: Delete orphaned frontend file, fake tests, and unused dependency

**Files:**
- Delete: `frontend/src/BloodIQDashboard.jsx`, `tests/test_models.py`, `tests/test_data_pipeline.py`, `tests/` (directory, now empty)
- Modify: `frontend/package.json:10-17` (remove unused `axios`)

- [ ] **Step 1: Confirm BloodIQDashboard.jsx is unreferenced**

Run: `grep -rln "BloodIQDashboard" /Users/aarushluthra/blood/frontend/src`

Expected: only the file itself shows up (no importer).

- [ ] **Step 2: Confirm axios is unused**

Run: `grep -rln "axios" /Users/aarushluthra/blood/frontend/src`

Expected: no output.

- [ ] **Step 3: Delete files**

```bash
cd /Users/aarushluthra/blood
git rm frontend/src/BloodIQDashboard.jsx tests/test_models.py tests/test_data_pipeline.py
rmdir tests 2>/dev/null || true
```

- [ ] **Step 4: Remove axios from package.json**

Edit `frontend/package.json` — remove this line from `dependencies`:
```json
    "axios": "^1.6.0",
```

- [ ] **Step 5: Reinstall to sync package-lock.json**

```bash
cd /Users/aarushluthra/blood/frontend && npm install
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
chore: remove orphaned dashboard file, fake tests, and unused axios dependency

BloodIQDashboard.jsx was replaced by pages/Dashboard.jsx and no longer
routed to. The old tests exercised random numbers, not real logic — real
tests land in backend/tests/ in Phase 1-2. axios was never imported.
EOF
)"
```

---

### Task 5: Fix stale root-level tooling

**Files:**
- Delete: `requirements.txt` (root)
- Modify: `Makefile` (full rewrite)

- [ ] **Step 1: Confirm the root requirements.txt and Makefile don't match anything in the repo**

Run: `ls /Users/aarushluthra/blood/src /Users/aarushluthra/blood/api 2>&1`

Expected: `No such file or directory` for both — confirms the root Makefile's targets (`src/data/make_dataset.py`, `api/main.py`) reference a structure that doesn't exist. It's stale boilerplate; `backend/requirements.txt` is the real one.

- [ ] **Step 2: Delete the stale root requirements.txt**

```bash
cd /Users/aarushluthra/blood
git rm requirements.txt
```

- [ ] **Step 3: Rewrite the root Makefile to match the real structure**

Replace the full contents of `/Users/aarushluthra/blood/Makefile` with:

```makefile
.PHONY: install train-demand train-supply api test clean

install:
	cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

train-demand:
	cd backend && .venv/bin/python -c "from ml.train_demand import train; train()"

train-supply:
	cd backend && .venv/bin/python -c "from ml.train_supply import train; train()"

api:
	cd backend && .venv/bin/uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

test:
	cd backend && .venv/bin/pytest tests/ -v

clean:
	find backend -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find backend -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

all: install train-demand train-supply test
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
chore: remove stale root requirements.txt, rewrite Makefile to match reality

The old Makefile referenced src/ and api/main.py paths that don't exist
in this repo. Rewritten with targets that match backend/'s real layout.
EOF
)"
```

---

## Phase 1 — Backend foundation: config and demand disaggregation

### Task 6: Create backend/config.py

**Files:**
- Create: `backend/config.py`

- [ ] **Step 1: Write the file**

```python
"""
Shared constants for the BloodIQ simulation and rule engines.
No database, no per-hospital config — one national-level simulation
across the 4 ABO blood types present in the real datasets.
"""

BLOOD_TYPES = ["A", "B", "AB", "O"]

# Red blood cells: standard shelf life at 1-6 C.
SHELF_LIFE_DAYS = 42

# How many days of starting stock to seed the simulation with, sized off
# each type's first forecasted demand day.
INITIAL_STOCK_COVERAGE_DAYS = 7

# Shortage classification thresholds (days of coverage = stock / trailing
# average demand). Matches the thresholds already used by the dashboard's
# existing inventory cards.
SHORTAGE_CRITICAL_COVERAGE_DAYS = 3
SHORTAGE_WARNING_COVERAGE_DAYS = 7

# Wastage classification thresholds (near-expiry ratio = units expiring
# within the window below, divided by current stock).
WASTAGE_NEAR_EXPIRY_WINDOW_DAYS = 3
WASTAGE_HIGH_RATIO = 0.4
WASTAGE_MED_RATIO = 0.15
```

- [ ] **Step 2: Verify it imports**

Run: `cd /Users/aarushluthra/blood/backend && .venv/bin/python -c "import config; print(config.BLOOD_TYPES)"`
Expected: `['A', 'B', 'AB', 'O']`

- [ ] **Step 3: Commit**

```bash
cd /Users/aarushluthra/blood
git add backend/config.py
git commit -m "feat: add shared config constants for simulation and rules"
```

---

### Task 7: Create backend/ml/demand_split.py with tests

**Files:**
- Create: `backend/ml/demand_split.py`
- Create: `backend/conftest.py`
- Create: `backend/tests/test_demand_split.py`

- [ ] **Step 1: Add backend/conftest.py so tests can import backend packages regardless of cwd**

```python
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
```

- [ ] **Step 2: Install pytest so the test can run**

Add `pytest` and `httpx` to `backend/requirements.txt` (append, don't touch existing lines):

```
pytest
httpx
```

Run: `cd /Users/aarushluthra/blood/backend && .venv/bin/pip install pytest httpx`

- [ ] **Step 3: Write the failing test**

Create `backend/tests/test_demand_split.py`:

```python
from ml.demand_split import compute_type_ratios, split_by_type


def test_ratios_sum_to_one_and_cover_all_types():
    ratios = compute_type_ratios()
    assert set(ratios.keys()) == {"A", "B", "AB", "O"}
    assert abs(sum(ratios.values()) - 1.0) < 1e-6


def test_split_by_type_sums_back_to_original_total():
    total_demand = [
        {"date": "2024-01-01", "predicted_demand": 100.0},
        {"date": "2024-01-02", "predicted_demand": 200.0},
    ]
    split = split_by_type(total_demand)
    assert set(split.keys()) == {"A", "B", "AB", "O"}
    for i in range(len(total_demand)):
        day_total = sum(split[bt][i]["predicted_demand"] for bt in split)
        assert abs(day_total - total_demand[i]["predicted_demand"]) < 1e-6
        assert split["A"][i]["date"] == total_demand[i]["date"]
```

- [ ] **Step 4: Run it to confirm it fails**

Run: `cd /Users/aarushluthra/blood/backend && .venv/bin/pytest tests/test_demand_split.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ml.demand_split'`

- [ ] **Step 5: Implement backend/ml/demand_split.py**

```python
"""
Disaggregates the single aggregate demand forecast (Kaggle dataset has no
blood-type breakdown) into per-ABO-type demand, using each type's historical
share of real Malaysian donation volume as a proxy ratio. This is a
documented approximation, not independently-learned per-type demand -- the
demand dataset doesn't support that.
"""
import os

import pandas as pd

DONATIONS_PATH = os.path.join(os.path.dirname(__file__), "../data/blood_donations.csv")


def compute_type_ratios():
    """Returns {type: ratio} for A/B/AB/O, summing to 1.0."""
    df = pd.read_csv(DONATIONS_PATH)
    df = df[df["blood_type"] != "all"]
    totals = df.groupby("blood_type")["donations"].sum()
    totals.index = totals.index.str.upper()
    ratios = (totals / totals.sum()).to_dict()
    return ratios


def split_by_type(total_demand):
    """
    total_demand: list of {"date": str, "predicted_demand": float}
    Returns: {type: [{"date": str, "predicted_demand": float}, ...]}
    """
    ratios = compute_type_ratios()
    result = {}
    for bt, ratio in ratios.items():
        result[bt] = [
            {"date": d["date"], "predicted_demand": d["predicted_demand"] * ratio}
            for d in total_demand
        ]
    return result
```

- [ ] **Step 6: Run the test again to confirm it passes**

Run: `cd /Users/aarushluthra/blood/backend && .venv/bin/pytest tests/test_demand_split.py -v`
Expected: `2 passed`

- [ ] **Step 7: Commit**

```bash
cd /Users/aarushluthra/blood
git add backend/conftest.py backend/tests/test_demand_split.py backend/ml/demand_split.py backend/requirements.txt
git commit -m "feat: add per-type demand disaggregation from real donation ratios"
```

---

### Task 8: Extend backend/ml/inference.py with predict_demand_by_type

**Files:**
- Modify: `backend/ml/inference.py` (append)
- Create: `backend/tests/test_inference.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_inference.py`:

```python
from ml import inference


def test_predict_demand_by_type_splits_the_aggregate(monkeypatch):
    fake_total = [{"date": "2024-01-01", "predicted_demand": 100.0}]
    monkeypatch.setattr(inference, "predict_demand", lambda days: fake_total)

    result = inference.predict_demand_by_type(1)

    assert set(result.keys()) == {"A", "B", "AB", "O"}
    day_total = sum(result[bt][0]["predicted_demand"] for bt in result)
    assert abs(day_total - 100.0) < 1e-6
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd /Users/aarushluthra/blood/backend && .venv/bin/pytest tests/test_inference.py -v`
Expected: FAIL with `AttributeError: module 'ml.inference' has no attribute 'predict_demand_by_type'`

- [ ] **Step 3: Append to backend/ml/inference.py**

Add this import near the top (with the other imports) and this function at the end of the file:

```python
from ml.demand_split import split_by_type
```

```python
def predict_demand_by_type(days=30):
    """
    Per-blood-type demand: forecasts the aggregate total (LightGBM) and
    disaggregates it via ml.demand_split (see that module for the method).
    """
    total_demand = predict_demand(days)
    return split_by_type(total_demand)
```

- [ ] **Step 4: Run the test again to confirm it passes**

Run: `cd /Users/aarushluthra/blood/backend && .venv/bin/pytest tests/test_inference.py -v`
Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
cd /Users/aarushluthra/blood
git add backend/ml/inference.py backend/tests/test_inference.py
git commit -m "feat: add predict_demand_by_type to inference module"
```

---

## Phase 2 — Simulation engine and rule-based classifiers

### Task 9: Create backend/simulation/shortage_rules.py with tests

**Files:**
- Create: `backend/simulation/shortage_rules.py`
- Create: `backend/tests/test_shortage_rules.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_shortage_rules.py`:

```python
from simulation.shortage_rules import classify_shortage


def test_critical_at_or_below_three_days_coverage():
    assert classify_shortage(0.0) == "CRITICAL"
    assert classify_shortage(3.0) == "CRITICAL"


def test_warning_between_three_and_seven_days_coverage():
    assert classify_shortage(3.5) == "WARNING"
    assert classify_shortage(7.0) == "WARNING"


def test_safe_above_seven_days_coverage():
    assert classify_shortage(7.5) == "SAFE"
    assert classify_shortage(100.0) == "SAFE"
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd /Users/aarushluthra/blood/backend && .venv/bin/pytest tests/test_shortage_rules.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'simulation'`

- [ ] **Step 3: Implement backend/simulation/shortage_rules.py**

```python
"""Rule-based shortage classification from days-of-coverage."""
from config import SHORTAGE_CRITICAL_COVERAGE_DAYS, SHORTAGE_WARNING_COVERAGE_DAYS


def classify_shortage(coverage_days):
    """coverage_days = current stock / trailing average daily demand."""
    if coverage_days <= SHORTAGE_CRITICAL_COVERAGE_DAYS:
        return "CRITICAL"
    if coverage_days <= SHORTAGE_WARNING_COVERAGE_DAYS:
        return "WARNING"
    return "SAFE"
```

- [ ] **Step 4: Run the test again to confirm it passes**

Run: `cd /Users/aarushluthra/blood/backend && .venv/bin/pytest tests/test_shortage_rules.py -v`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
cd /Users/aarushluthra/blood
git add backend/simulation/shortage_rules.py backend/tests/test_shortage_rules.py
git commit -m "feat: add rule-based shortage classifier"
```

---

### Task 10: Create backend/simulation/wastage_rules.py with tests

**Files:**
- Create: `backend/simulation/wastage_rules.py`
- Create: `backend/tests/test_wastage_rules.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_wastage_rules.py`:

```python
from simulation.wastage_rules import classify_wastage


def test_high_when_near_expiry_ratio_above_point_four():
    assert classify_wastage(0.41) == "HIGH"
    assert classify_wastage(1.0) == "HIGH"


def test_med_when_near_expiry_ratio_between_point_15_and_point_4():
    assert classify_wastage(0.15) == "MED"
    assert classify_wastage(0.4) == "MED"


def test_low_when_near_expiry_ratio_at_or_below_point_15():
    assert classify_wastage(0.0) == "LOW"
    assert classify_wastage(0.1) == "LOW"
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd /Users/aarushluthra/blood/backend && .venv/bin/pytest tests/test_wastage_rules.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'simulation.wastage_rules'`

- [ ] **Step 3: Implement backend/simulation/wastage_rules.py**

```python
"""Rule-based wastage classification from near-expiry stock ratio."""
from config import WASTAGE_HIGH_RATIO, WASTAGE_MED_RATIO


def classify_wastage(near_expiry_ratio):
    """near_expiry_ratio = units expiring within the window / current stock."""
    if near_expiry_ratio > WASTAGE_HIGH_RATIO:
        return "HIGH"
    if near_expiry_ratio > WASTAGE_MED_RATIO:
        return "MED"
    return "LOW"
```

- [ ] **Step 4: Run the test again to confirm it passes**

Run: `cd /Users/aarushluthra/blood/backend && .venv/bin/pytest tests/test_wastage_rules.py -v`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
cd /Users/aarushluthra/blood
git add backend/simulation/wastage_rules.py backend/tests/test_wastage_rules.py
git commit -m "feat: add rule-based wastage classifier"
```

---

### Task 11: Create backend/simulation/engine.py with tests

**Files:**
- Create: `backend/simulation/engine.py`
- Create: `backend/tests/test_engine.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_engine.py`:

```python
from config import INITIAL_STOCK_COVERAGE_DAYS
from simulation.engine import simulate_single_type, run_simulation


def _series(values, key):
    return [{"date": f"2024-01-{i+1:02d}", key: v} for i, v in enumerate(values)]


def test_simulate_single_type_conserves_units_day_by_day():
    demand_series = _series([8, 3, 6, 10, 4], "predicted_demand")
    supply_series = _series([2, 7, 1, 3, 5], "predicted_supply")

    records = simulate_single_type(demand_series, supply_series, days=5)

    assert len(records) == 5
    # Computed the same way engine.py seeds it - independent of the
    # records being asserted on, so this isn't a tautology.
    initial_stock = round(demand_series[0]["predicted_demand"] * INITIAL_STOCK_COVERAGE_DAYS)
    for i, r in enumerate(records):
        supply_today = supply_series[i]["predicted_supply"]
        prev_stock = initial_stock if i == 0 else records[i - 1]["stock"]
        expected_stock = prev_stock + supply_today - r["consumed"] - r["expired"]
        assert abs(r["stock"] - expected_stock) < 1e-6
        assert r["stock"] >= 0
        assert r["shortage_risk"] in {"SAFE", "WARNING", "CRITICAL"}
        assert r["wastage_risk"] in {"LOW", "MED", "HIGH"}


def test_run_simulation_returns_all_four_blood_types():
    demand_by_type = {
        bt: _series([20, 20, 20], "predicted_demand") for bt in ["A", "B", "AB", "O"]
    }
    supply_by_type = {
        bt: _series([10, 10, 10], "predicted_supply") for bt in ["A", "B", "AB", "O"]
    }

    result = run_simulation(demand_by_type, supply_by_type, days=3)

    assert set(result.keys()) == {"A", "B", "AB", "O"}
    for bt in result:
        assert len(result[bt]) == 3
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd /Users/aarushluthra/blood/backend && .venv/bin/pytest tests/test_engine.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'simulation.engine'`

- [ ] **Step 3: Implement backend/simulation/engine.py**

```python
"""
Day-by-day, in-memory, per-blood-type FEFO stock simulation. No database --
computed fresh for every /api/simulate call from the demand and supply
forecasts already produced by backend/ml.
"""
from config import BLOOD_TYPES, INITIAL_STOCK_COVERAGE_DAYS, SHELF_LIFE_DAYS
from simulation.shortage_rules import classify_shortage
from simulation.wastage_rules import classify_wastage


def simulate_single_type(demand_series, supply_series, days):
    """
    demand_series: list of {"date": str, "predicted_demand": float}, length >= days
    supply_series: list of {"date": str, "predicted_supply": float}, length >= days

    Returns a list of `days` day-records:
      {date, day_index, demand, supply, consumed, unmet_demand, expired,
       stock, shortage_risk, wastage_risk}
    """
    initial_units = round(demand_series[0]["predicted_demand"] * INITIAL_STOCK_COVERAGE_DAYS)
    # Seed as one batch already half-aged, so it doesn't all expire on the
    # same simulated day (a deliberate simplification for a first version).
    batches = [{"units": initial_units, "days_until_expiry": SHELF_LIFE_DAYS // 2}]

    records = []
    recent_demand = []

    for i in range(days):
        demand_today = demand_series[i]["predicted_demand"]
        supply_today = supply_series[i]["predicted_supply"]

        # 1. Donation inflow: a fresh batch at full shelf life.
        batches.append({"units": supply_today, "days_until_expiry": SHELF_LIFE_DAYS})

        # 2. FEFO consumption: oldest (soonest-to-expire) batch first.
        batches.sort(key=lambda b: b["days_until_expiry"])
        remaining_demand = demand_today
        consumed = 0.0
        for batch in batches:
            if remaining_demand <= 0:
                break
            take = min(batch["units"], remaining_demand)
            batch["units"] -= take
            remaining_demand -= take
            consumed += take
        unmet_demand = remaining_demand
        batches = [b for b in batches if b["units"] > 0]

        # 3. Age every remaining batch by one day, then expire anything
        #    that has run out of shelf life.
        for b in batches:
            b["days_until_expiry"] -= 1
        expired = sum(b["units"] for b in batches if b["days_until_expiry"] <= 0)
        batches = [b for b in batches if b["days_until_expiry"] > 0]

        stock = sum(b["units"] for b in batches)

        # 4. Classify shortage risk from a 7-day trailing demand average.
        recent_demand.append(demand_today)
        if len(recent_demand) > 7:
            recent_demand.pop(0)
        avg_demand = sum(recent_demand) / len(recent_demand)
        coverage_days = stock / avg_demand if avg_demand > 0 else float("inf")

        # 5. Classify wastage risk from the near-expiry ratio.
        near_expiry_units = sum(
            b["units"] for b in batches if b["days_until_expiry"] <= 3
        )
        near_expiry_ratio = near_expiry_units / stock if stock > 0 else 0.0

        records.append({
            "date": demand_series[i]["date"],
            "day_index": i,
            "demand": round(demand_today, 1),
            "supply": round(supply_today, 1),
            "consumed": round(consumed, 1),
            "unmet_demand": round(unmet_demand, 1),
            "expired": round(expired, 1),
            "stock": round(stock, 1),
            "shortage_risk": classify_shortage(coverage_days),
            "wastage_risk": classify_wastage(near_expiry_ratio),
        })

    return records


def run_simulation(demand_by_type, supply_by_type, days):
    """
    demand_by_type: {type: [{"date", "predicted_demand"}, ...]}
    supply_by_type: {type: [{"date", "predicted_supply"}, ...]}
    Returns: {type: [day-record, ...]}
    """
    return {
        bt: simulate_single_type(demand_by_type[bt], supply_by_type[bt], days)
        for bt in BLOOD_TYPES
    }
```

- [ ] **Step 4: Run the test again to confirm it passes**

Run: `cd /Users/aarushluthra/blood/backend && .venv/bin/pytest tests/test_engine.py -v`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
cd /Users/aarushluthra/blood
git add backend/simulation/engine.py backend/tests/test_engine.py
git commit -m "feat: add day-by-day FEFO simulation engine"
```

---

## Phase 3 — API wiring and end-to-end verification

### Task 12: Trim backend/requirements.txt

**Files:**
- Modify: `backend/requirements.txt` (full rewrite)

- [ ] **Step 1: Replace the full contents of backend/requirements.txt**

```
fastapi==0.104.1
uvicorn[standard]==0.24.0.post1
pandas
numpy
scikit-learn
lightgbm
prophet
joblib
pytest
httpx
```

(Drops `xgboost`, `darts`, `matplotlib`, `seaborn`, `python-multipart` — none are imported anywhere in `backend/ml`, `backend/simulation`, or `backend/api` after the Phase 0 deletions.)

- [ ] **Step 2: Confirm nothing still imports the dropped packages**

Run: `grep -rln "xgboost\|import darts\|matplotlib\|seaborn\|multipart" /Users/aarushluthra/blood/backend/ml /Users/aarushluthra/blood/backend/api /Users/aarushluthra/blood/backend/simulation /Users/aarushluthra/blood/backend/config.py`

Expected: no output.

- [ ] **Step 3: Install into the existing venv**

Run: `cd /Users/aarushluthra/blood/backend && .venv/bin/pip install -r requirements.txt`
Expected: installs `lightgbm` (new); everything else already present or unaffected.

- [ ] **Step 4: Commit**

```bash
cd /Users/aarushluthra/blood
git add backend/requirements.txt
git commit -m "chore: trim backend requirements to what's actually imported"
```

---

### Task 13: Add /api/simulate endpoint with an end-to-end test

**Files:**
- Modify: `backend/api/main.py`
- Create: `backend/tests/test_api_simulate.py`

- [ ] **Step 1: Write the end-to-end test (it will fail until the endpoint exists)**

Create `backend/tests/test_api_simulate.py`:

```python
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from ml.train_demand import train as train_demand
    from ml.train_supply import train as train_supply

    train_demand()
    train_supply()

    from api.main import app
    return TestClient(app)


def test_simulate_returns_all_four_blood_types_with_valid_labels(client):
    resp = client.get("/api/simulate?days=10")
    assert resp.status_code == 200

    body = resp.json()
    assert body["status"] == "success"

    data = body["data"]
    assert set(data.keys()) == {"A", "B", "AB", "O"}
    for records in data.values():
        assert len(records) == 10
        for r in records:
            assert r["stock"] >= 0
            assert r["shortage_risk"] in {"SAFE", "WARNING", "CRITICAL"}
            assert r["wastage_risk"] in {"LOW", "MED", "HIGH"}
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd /Users/aarushluthra/blood/backend && .venv/bin/pytest tests/test_api_simulate.py -v`
Expected: FAIL — either a training error (if run in isolation before models exist, that's fine and expected to self-heal since the fixture trains first) or a 404/500 on `/api/simulate` because the route doesn't exist yet.

- [ ] **Step 3: Add the endpoint to backend/api/main.py**

Add these imports near the top, alongside the existing `ml.inference` import:

```python
from ml.inference import predict_demand, predict_supply, predict_demand_by_type
from simulation.engine import run_simulation
```

Add this route (anywhere alongside the other `@app.get` routes):

```python
@app.get("/api/simulate")
def simulate(days: int = 30):
    try:
        demand_by_type = predict_demand_by_type(days)
        supply_by_type = predict_supply(days)
        result = run_simulation(demand_by_type, supply_by_type, days)
        return {"status": "success", "data": result}
    except Exception as e:
        logging.error(f"Simulate Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 4: Run the test again to confirm it passes**

Run: `cd /Users/aarushluthra/blood/backend && .venv/bin/pytest tests/test_api_simulate.py -v`
Expected: `1 passed` (this run also trains and saves `backend/ml/demand_model.pkl` and `backend/ml/supply_models.pkl` as a side effect of the fixture — that's intended, see Task 14).

- [ ] **Step 5: Run the full backend test suite to confirm nothing regressed**

Run: `cd /Users/aarushluthra/blood/backend && .venv/bin/pytest tests/ -v`
Expected: all tests pass (demand_split, inference, shortage_rules, wastage_rules, engine, api_simulate).

- [ ] **Step 6: Commit**

```bash
cd /Users/aarushluthra/blood
git add backend/api/main.py backend/tests/test_api_simulate.py
git commit -m "feat: add /api/simulate endpoint wiring demand, supply, and simulation together"
```

---

### Task 14: Manually verify the running API

**Files:** none (verification only)

- [ ] **Step 1: Start the backend**

Run: `cd /Users/aarushluthra/blood/backend && .venv/bin/uvicorn api.main:app --port 8000 &`

(Use the `preview_start` tool with a `backend` launch config if working inside the agent harness, matching the earlier session's setup.)

- [ ] **Step 2: Confirm the root and simulate endpoints respond**

Run: `curl -s http://localhost:8000/`
Expected: `{"status":"BloodIQ Intelligence Engine Running"}`

Run: `curl -s "http://localhost:8000/api/simulate?days=5" | python3 -m json.tool | head -40`
Expected: JSON with `"status": "success"` and a `"data"` object keyed `A`, `B`, `AB`, `O`, each holding 5 day-records with `stock`, `demand`, `supply`, `shortage_risk`, `wastage_risk` fields.

- [ ] **Step 3: Stop the server**

Run: `kill %1` (or use `preview_stop` if using the harness tool)

No commit for this task — verification only.

---

## Phase 4 — Frontend: gamified health bar dashboard

### Task 15: Add frontend/src/lib/api.js

**Files:**
- Create: `frontend/src/lib/api.js`

- [ ] **Step 1: Write the file**

```javascript
const API_BASE = 'http://localhost:8000';

export async function fetchSimulation(days = 30) {
  const res = await fetch(`${API_BASE}/api/simulate?days=${days}`);
  if (!res.ok) {
    throw new Error(`Simulate request failed with status ${res.status}`);
  }
  const json = await res.json();
  if (json.status !== 'success') {
    throw new Error(json.detail || 'Simulate request returned an error');
  }
  return json.data;
}
```

- [ ] **Step 2: Commit**

```bash
cd /Users/aarushluthra/blood
git add frontend/src/lib/api.js
git commit -m "feat: add fetchSimulation API wrapper for the dashboard"
```

---

### Task 16: Add the shake animation to index.css

**Files:**
- Modify: `frontend/src/index.css` (append near the existing `@keyframes`/`.anim-*` block)

- [ ] **Step 1: Append this block after the existing `.anim-fade-in-d3` rule**

```css
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  20% { transform: translateX(-4px); }
  40% { transform: translateX(4px); }
  60% { transform: translateX(-3px); }
  80% { transform: translateX(3px); }
}
.anim-shake { animation: shake 0.4s ease-in-out; }
```

- [ ] **Step 2: Commit**

```bash
cd /Users/aarushluthra/blood
git add frontend/src/index.css
git commit -m "feat: add shake animation for wastage events on health bar cards"
```

---

### Task 17: Create frontend/src/components/HealthBarCard.jsx

**Files:**
- Create: `frontend/src/components/HealthBarCard.jsx`

- [ ] **Step 1: Write the file**

```jsx
import React, { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { ChevronDown, AlertTriangle } from 'lucide-react';

const RISK_STYLES = {
  SAFE: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200/60', bar: 'bg-gradient-to-r from-emerald-400 to-emerald-500', label: 'Safe' },
  WARNING: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200/60', bar: 'bg-gradient-to-r from-amber-400 to-amber-500', label: 'Warning' },
  CRITICAL: { bg: 'bg-rose-50', text: 'text-rose-600', border: 'border-rose-200/60', bar: 'bg-gradient-to-r from-rose-400 to-rose-500', label: 'Critical' },
};

const WASTAGE_STYLES = {
  LOW: { text: 'text-gray-500', label: 'Low' },
  MED: { text: 'text-amber-700', label: 'Medium' },
  HIGH: { text: 'text-rose-600', label: 'High' },
};

export default function HealthBarCard({ bloodType, series, dayIndex }) {
  const [expanded, setExpanded] = useState(false);
  const today = series[dayIndex];
  const maxStock = Math.max(...series.map(d => d.stock), 1);
  const pct = Math.min(100, Math.max(2, (today.stock / maxStock) * 100));
  const st = RISK_STYLES[today.shortage_risk] || RISK_STYLES.SAFE;
  const wst = WASTAGE_STYLES[today.wastage_risk] || WASTAGE_STYLES.LOW;
  const isCritical = today.shortage_risk === 'CRITICAL';
  const justWasted = today.expired > 0;

  return (
    <div
      className={`p-5 rounded-2xl border bg-white transition-all duration-300 cursor-pointer hover:-translate-y-0.5 ${isCritical ? 'border-rose-300' : 'border-gray-200/80 hover:border-rose-300'}`}
      onClick={() => setExpanded(e => !e)}
    >
      <div key={`${bloodType}-${dayIndex}-flash`} className={justWasted ? 'anim-shake' : ''}>
        <div className="flex justify-between items-center mb-3">
          <span className="font-outfit text-[22px] font-normal text-gray-900">{bloodType}</span>
          <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-normal uppercase tracking-wider border ${st.bg} ${st.text} ${st.border} ${isCritical ? 'animate-pulse' : ''}`}>
            {st.label}
          </span>
        </div>

        <div className="flex justify-between items-baseline mb-1.5">
          <span className="font-sans text-[12px] text-gray-400">Current Stock</span>
          <span className="font-outfit text-[16px] font-normal text-gray-800">
            {Math.round(today.stock)} <span className="font-sans text-[12px] text-gray-400">units</span>
          </span>
        </div>

        <div className="h-2.5 w-full bg-gray-100/80 rounded-full my-2 overflow-hidden p-0.5 border border-gray-200/40">
          <div className={`h-full ${st.bar} rounded-full transition-all duration-700 shadow-2xs`} style={{ width: `${pct}%` }} />
        </div>
      </div>

      {/* Level A: always-visible readout */}
      <div className="bg-gray-50/80 rounded-xl p-3 mt-3 border border-gray-100/80 grid grid-cols-2 gap-2 text-[11.5px]">
        <div className="flex flex-col">
          <span className="font-sans text-[11px] text-gray-400">Demand today</span>
          <span className="font-outfit font-normal text-[13px] text-gray-700">{Math.round(today.demand)} units</span>
        </div>
        <div className="flex flex-col">
          <span className="font-sans text-[11px] text-gray-400">Supply today</span>
          <span className="font-outfit font-normal text-[13px] text-gray-700">{Math.round(today.supply)} units</span>
        </div>
        <div className="flex flex-col">
          <span className="font-sans text-[11px] text-gray-400">Shortage risk</span>
          <span className={`font-outfit font-normal text-[13px] ${st.text}`}>{st.label}</span>
        </div>
        <div className="flex flex-col">
          <span className="font-sans text-[11px] text-gray-400">Wastage risk</span>
          <span className={`font-outfit font-normal text-[13px] ${wst.text}`}>{wst.label}</span>
        </div>
      </div>

      {justWasted && (
        <div className="mt-3 flex items-center gap-1.5 text-[11px] font-normal text-rose-600 bg-rose-50/80 border border-rose-200/60 px-3 py-1.5 rounded-xl">
          <AlertTriangle className="w-3.5 h-3.5 text-rose-500" />
          <span>{Math.round(today.expired)} units expired today</span>
        </div>
      )}

      <button
        className="mt-3 flex items-center gap-1 text-[11px] font-normal text-gray-400 hover:text-rose-500 transition-colors"
        onClick={(e) => { e.stopPropagation(); setExpanded(x => !x); }}
      >
        <ChevronDown className={`w-3.5 h-3.5 transition-transform ${expanded ? 'rotate-180' : ''}`} />
        {expanded ? 'Hide 30-day trend' : 'Show 30-day trend'}
      </button>

      {expanded && (
        <div className="mt-3 border-t border-gray-100 pt-3" onClick={(e) => e.stopPropagation()}>
          <div className="h-[160px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={series} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
                <CartesianGrid strokeDasharray="4 4" stroke="#f3f4f6" vertical={false} />
                <XAxis dataKey="date" stroke="#9ca3af" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} minTickGap={30} />
                <YAxis stroke="#9ca3af" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '12px', fontSize: '12px' }} />
                <Line type="monotone" dataKey="demand" stroke="#f43f5e" strokeWidth={2} dot={false} name="Demand" />
                <Line type="monotone" dataKey="supply" stroke="#3b82f6" strokeWidth={2} dot={false} name="Supply" />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="flex gap-[2px] mt-2">
            {series.map((d, i) => (
              <div
                key={i}
                title={`${d.date}: ${d.shortage_risk}${d.expired > 0 ? ' - wastage' : ''}`}
                className={`flex-1 h-2 rounded-sm ${
                  d.shortage_risk === 'CRITICAL' ? 'bg-rose-400' : d.shortage_risk === 'WARNING' ? 'bg-amber-300' : 'bg-emerald-300'
                } ${d.expired > 0 ? 'ring-2 ring-offset-1 ring-gray-700' : ''}`}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd /Users/aarushluthra/blood
git add frontend/src/components/HealthBarCard.jsx
git commit -m "feat: add HealthBarCard component (Boss Health Bar + Level A/B interactivity)"
```

---

### Task 18: Create frontend/src/components/AlertStream.jsx

**Files:**
- Create: `frontend/src/components/AlertStream.jsx`

- [ ] **Step 1: Write the file**

```jsx
import React, { useMemo, useState } from 'react';
import { Bell, CheckCircle2 } from 'lucide-react';

function buildEvents(simulateData, dayIndex) {
  const events = [];
  Object.entries(simulateData).forEach(([bloodType, series]) => {
    for (let i = 0; i <= dayIndex; i++) {
      const day = series[i];
      if (day.shortage_risk === 'CRITICAL') {
        events.push({
          id: `${bloodType}-shortage-${i}`, severity: 'critical', type: 'shortage', group: bloodType, day: i,
          message: `${bloodType} stock at CRITICAL coverage (${Math.round(day.stock)} units).`,
        });
      } else if (day.shortage_risk === 'WARNING') {
        events.push({
          id: `${bloodType}-shortage-${i}`, severity: 'warning', type: 'shortage', group: bloodType, day: i,
          message: `${bloodType} stock coverage running low (${Math.round(day.stock)} units).`,
        });
      }
      if (day.expired > 0) {
        events.push({
          id: `${bloodType}-wastage-${i}`, severity: day.wastage_risk === 'HIGH' ? 'critical' : 'warning', type: 'expiry', group: bloodType, day: i,
          message: `${Math.round(day.expired)} units of ${bloodType} expired unused.`,
        });
      }
    }
  });
  return events.sort((a, b) => b.day - a.day);
}

export default function AlertStream({ simulateData, dayIndex }) {
  const [filter, setFilter] = useState('ALL');
  const events = useMemo(() => buildEvents(simulateData, dayIndex), [simulateData, dayIndex]);
  const filtered = events.filter(e =>
    filter === 'ALL' ? true :
    filter === 'CRITICAL' ? e.severity === 'critical' :
    filter === 'WARNING' ? e.severity === 'warning' :
    e.type === 'expiry'
  );

  return (
    <div className="bg-white border border-gray-200 rounded-2xl p-5 h-[720px] flex flex-col">
      <div className="flex justify-between items-center mb-4">
        <h2 className="font-outfit text-[16px] font-normal text-gray-900 flex items-center gap-2">
          <Bell className="w-4 h-4 text-rose-500" /> <span>Alert Stream</span>
        </h2>
        <span className="text-[11px] font-normal text-gray-400">Day {dayIndex + 1}</span>
      </div>
      <div className="flex gap-1.5 mb-4">
        {['ALL', 'CRITICAL', 'WARNING', 'EXPIRY'].map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className={`text-[11px] font-normal px-2.5 py-1 rounded-lg transition-all ${filter === f ? 'bg-gray-900 text-white shadow-2xs' : 'bg-gray-100 text-gray-500 hover:bg-gray-200/80'}`}>
            {f}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto space-y-2.5 custom-scrollbar">
        {filtered.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <CheckCircle2 className="w-8 h-8 mx-auto mb-2 opacity-40" />
            <p className="font-sans text-[13px]">No active alerts</p>
          </div>
        ) : filtered.map(e => (
          <div key={e.id} className={`p-3.5 rounded-xl border text-[13px] transition-all hover:shadow-2xs ${e.severity === 'critical' ? 'bg-rose-50/60 border-rose-200/80' : 'bg-amber-50/60 border-amber-200/80'}`}>
            <div className="flex justify-between items-start mb-1.5">
              <div className="flex gap-1.5">
                <span className={`px-2 py-0.5 rounded-md text-[9px] font-normal uppercase tracking-wider ${e.severity === 'critical' ? 'bg-rose-500 text-white' : 'bg-amber-500 text-white'}`}>{e.severity}</span>
                <span className="px-2 py-0.5 rounded-md text-[9px] font-normal bg-gray-800 text-white">{e.group}</span>
              </div>
              <span className="text-[10px] text-gray-400 font-outfit">Day {e.day + 1}</span>
            </div>
            <p className="font-sans text-gray-600 leading-relaxed text-[12.5px]">{e.message}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd /Users/aarushluthra/blood
git add frontend/src/components/AlertStream.jsx
git commit -m "feat: add AlertStream component driven by real shortage/wastage data"
```

---

### Task 19: Rebuild frontend/src/pages/Dashboard.jsx

**Files:**
- Modify: `frontend/src/pages/Dashboard.jsx` (full rewrite)

- [ ] **Step 1: Replace the full contents of frontend/src/pages/Dashboard.jsx**

```jsx
import React, { useEffect, useState, useCallback } from 'react';
import { Clock, RefreshCcw, Droplet, AlertTriangle, Calendar, TrendingUp, TrendingDown, Play, Pause, SkipForward } from 'lucide-react';
import { fetchSimulation } from '../lib/api';
import HealthBarCard from '../components/HealthBarCard';
import AlertStream from '../components/AlertStream';

const BLOOD_TYPES = ['A', 'B', 'AB', 'O'];
const SIM_DAYS = 30;

export default function Dashboard() {
  const [simulateData, setSimulateData] = useState(null);
  const [error, setError] = useState(null);
  const [dayIndex, setDayIndex] = useState(0);
  const [autoPlay, setAutoPlay] = useState(false);
  const [lastRefresh, setLastRefresh] = useState(new Date());

  const loadSimulation = useCallback(() => {
    setError(null);
    fetchSimulation(SIM_DAYS)
      .then(data => {
        setSimulateData(data);
        setDayIndex(0);
        setLastRefresh(new Date());
      })
      .catch(err => setError(err.message));
  }, []);

  useEffect(() => { loadSimulation(); }, [loadSimulation]);

  useEffect(() => {
    if (!autoPlay || !simulateData) return;
    const iv = setInterval(() => {
      setDayIndex(d => {
        if (d >= SIM_DAYS - 1) { setAutoPlay(false); return d; }
        return d + 1;
      });
    }, 800);
    return () => clearInterval(iv);
  }, [autoPlay, simulateData]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-md">
          <AlertTriangle className="w-10 h-10 text-rose-400 mx-auto mb-3" />
          <p className="font-outfit text-gray-900 mb-1">Couldn't reach the BloodIQ backend</p>
          <p className="font-sans text-[13px] text-gray-500 mb-4">{error}</p>
          <button onClick={loadSimulation} className="text-[13px] font-normal bg-gray-900 text-white px-4 py-2 rounded-lg hover:bg-gray-800 transition-colors">Retry</button>
        </div>
      </div>
    );
  }

  if (!simulateData) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="font-outfit text-gray-400">Loading simulation...</p>
      </div>
    );
  }

  const totalStock = BLOOD_TYPES.reduce((acc, bt) => acc + simulateData[bt][dayIndex].stock, 0);
  const criticalCount = BLOOD_TYPES.filter(bt => simulateData[bt][dayIndex].shortage_risk === 'CRITICAL').length;
  const expiringToday = BLOOD_TYPES.reduce((acc, bt) => acc + simulateData[bt][dayIndex].expired, 0);
  const suppliedToday = BLOOD_TYPES.reduce((acc, bt) => acc + simulateData[bt][dayIndex].supply, 0);

  return (
    <div className="bg-gray-50 min-h-screen pb-8">
      <div className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between sticky top-16 z-40">
        <div className="flex items-center gap-5">
          <h1 className="font-outfit text-xl font-normal text-gray-900">Dashboard</h1>
          <span className="text-[13px] font-normal text-gray-500 bg-gray-50 px-3 py-1.5 rounded-lg border border-gray-200">
            Day {dayIndex + 1} / {SIM_DAYS} · {simulateData.A[dayIndex].date}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setAutoPlay(p => !p)}
            className="flex items-center gap-1.5 text-[13px] font-normal bg-rose-500 text-white px-3 py-1.5 rounded-lg hover:bg-rose-600 transition-colors"
          >
            {autoPlay ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            {autoPlay ? 'Pause' : 'Auto-play'}
          </button>
          <button
            onClick={() => setDayIndex(d => Math.min(d + 1, SIM_DAYS - 1))}
            disabled={dayIndex >= SIM_DAYS - 1}
            className="flex items-center gap-1.5 text-[13px] font-normal bg-gray-900 text-white px-3 py-1.5 rounded-lg hover:bg-gray-800 transition-colors disabled:opacity-40"
          >
            <SkipForward className="w-3.5 h-3.5" /> Next Day
          </button>
          <div className="flex items-center gap-2 text-[12px] text-gray-400 font-normal ml-1">
            <Clock className="w-3.5 h-3.5" /> {lastRefresh.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            <button onClick={loadSimulation} className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"><RefreshCcw className="w-3.5 h-3.5 text-gray-500" /></button>
          </div>
        </div>
      </div>

      <div className="max-w-[1440px] mx-auto p-6 grid grid-cols-12 gap-5">
        <div className="col-span-12 grid grid-cols-2 md:grid-cols-4 gap-4">
          <KPI title="Total Stock" value={Math.round(totalStock)} unit="units" icon={<Droplet className="w-4 h-4 text-rose-400" />} trend="live" up />
          <KPI title="Critical Shortages" value={criticalCount} unit="blood types" icon={<AlertTriangle className="w-4 h-4 text-rose-500" />} trend={criticalCount > 0 ? 'action needed' : 'all clear'} up={criticalCount === 0} color={criticalCount > 0 ? 'text-rose-600' : 'text-emerald-600'} />
          <KPI title="Expired Today" value={Math.round(expiringToday)} unit="units" icon={<Calendar className="w-4 h-4 text-amber-400" />} trend={expiringToday > 0 ? 'wastage' : 'none'} color="text-amber-600" />
          <KPI title="Donations Today" value={Math.round(suppliedToday)} unit="units" icon={<TrendingUp className="w-4 h-4 text-emerald-500" />} trend="incoming" up />
        </div>

        <div className="col-span-12 lg:col-span-3">
          <AlertStream simulateData={simulateData} dayIndex={dayIndex} />
        </div>

        <div className="col-span-12 lg:col-span-9">
          <div className="bg-white border border-gray-200 rounded-2xl p-6">
            <h2 className="font-outfit text-[18px] font-normal text-gray-900 mb-1">Blood Type Status</h2>
            <p className="font-sans text-[13px] text-gray-500 mb-5">Live stock, demand, supply, shortage & wastage risk per blood type</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {BLOOD_TYPES.map(bt => (
                <HealthBarCard key={bt} bloodType={bt} series={simulateData[bt]} dayIndex={dayIndex} />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function KPI({ title, value, unit, icon, trend, up, color = 'text-gray-900' }) {
  return (
    <div className="bg-gradient-to-b from-white to-gray-50/50 border border-gray-200/80 rounded-2xl p-5 hover:border-rose-200 hover:shadow-lg hover:shadow-rose-500/5 hover:-translate-y-0.5 transition-all duration-300 group">
      <div className="flex justify-between items-start mb-4">
        <span className="font-outfit text-[12px] font-normal text-gray-500 uppercase tracking-wider">{title}</span>
        <div className="w-9 h-9 bg-rose-50/80 border border-rose-100/60 rounded-xl flex items-center justify-center group-hover:scale-105 transition-transform">{icon}</div>
      </div>
      <div className="flex items-baseline gap-1.5 mb-3">
        <span className={`font-outfit text-3xl font-normal ${color}`}>{value}</span>
        <span className="font-sans text-[12px] text-gray-400">{unit}</span>
      </div>
      <div>
        <span className={`inline-flex items-center gap-1 text-[11px] font-normal px-2 py-0.5 rounded-full border ${up ? 'bg-emerald-50 text-emerald-700 border-emerald-100' : 'bg-rose-50 text-rose-600 border-rose-100'}`}>
          {up ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
          <span>{trend}</span>
        </span>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd /Users/aarushluthra/blood
git add frontend/src/pages/Dashboard.jsx
git commit -m "feat: rebuild Dashboard with real /api/simulate data and Boss Health Bar cards

Removes the hospital selector, fake network heatmap, and all
Math.random() data generation. KPIs, alerts, and health bars are now
all derived from one real /api/simulate response."
```

---

### Task 20: Manually verify the full dashboard in the browser

**Files:** none (verification only)

- [ ] **Step 1: Start both servers**

Backend: `cd /Users/aarushluthra/blood/backend && .venv/bin/uvicorn api.main:app --port 8000 &`
Frontend: `cd /Users/aarushluthra/blood/frontend && npm run dev &`

(Use `preview_start` for both if working inside the agent harness.)

- [ ] **Step 2: Load the dashboard and check the console for errors**

Navigate to `http://localhost:5173/dashboard`. Check browser console — expect no errors.

- [ ] **Step 3: Verify the four health-bar cards render with real data**

Confirm 4 cards labeled A, B, AB, O (not 8 Rh-split types), each showing a fill bar, a SAFE/WARNING/CRITICAL badge, and the Level A readout (demand, supply, shortage risk, wastage risk) for day 1.

- [ ] **Step 4: Verify Next Day / Auto-play interactivity**

Click "Next Day" repeatedly — confirm the bars, KPIs, and Alert Stream update. Click "Auto-play" — confirm it steps automatically and stops at day 30.

- [ ] **Step 5: Verify Level B expand**

Click a health-bar card — confirm it expands into a demand-vs-supply line chart plus the day-by-day risk strip, and collapses again on a second click.

- [ ] **Step 6: Verify the wastage shake and Alert Stream**

Step through days until a card shows `expired > 0` — confirm the shake animation plays and a corresponding entry appears in the Alert Stream sidebar.

- [ ] **Step 7: Verify the visual theme is unchanged**

Confirm the page still uses the existing rose/blush palette, Outfit typography, and card/grid conventions — no new color scheme introduced.

No commit for this task — verification only.

---

## Phase 5 — Documentation cleanup

### Task 21: Rewrite docs/ARCHITECTURE.md

**Files:**
- Modify: `docs/ARCHITECTURE.md` (full rewrite)

- [ ] **Step 1: Replace the full contents of docs/ARCHITECTURE.md**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
cd /Users/aarushluthra/blood
git add docs/ARCHITECTURE.md
git commit -m "docs: rewrite ARCHITECTURE.md to match the simplified system"
```

---

### Task 22: Update root README.md

**Files:**
- Modify: `README.md` (full rewrite)

- [ ] **Step 1: Replace the full contents of README.md**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
cd /Users/aarushluthra/blood
git add README.md
git commit -m "docs: rewrite README to reflect the simplified, real-data scope"
```

---

## Self-Review Notes (completed during plan authoring)

- **Spec coverage:** every section of the design spec maps to a task —
  removal table -> Phase 0 (Tasks 1-5); backend structure -> Phase 1-3
  (Tasks 6-14); frontend structure and interactivity levels -> Phase 4
  (Tasks 15-20); out-of-scope items are verified absent, not just unmentioned.
- **Type/name consistency checked:** `simulate_single_type`/`run_simulation`
  (engine.py), `classify_shortage`/`classify_wastage` (rules), field names
  `demand`/`supply`/`stock`/`expired`/`shortage_risk`/`wastage_risk` are used
  identically across `engine.py`, `api/main.py`, `HealthBarCard.jsx`,
  `AlertStream.jsx`, and all tests.
- **No placeholders:** every step above contains complete, runnable code —
  no "TODO", no "add error handling here" without showing the handler.
