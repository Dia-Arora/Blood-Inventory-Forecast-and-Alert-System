# BloodIQ, Explained in Plain English

This document explains, in full detail, what this project actually does: every dataset it uses, every machine learning model it trains, how those models' outputs get turned into a simulated blood inventory, and how that all becomes the dashboard you see in the browser. It's written for someone with no prior context on this codebase.

---

## 1. The one-sentence version

BloodIQ takes two real-world datasets (how much blood a hospital system used historically, and how many people donated blood by blood type), trains machine learning models on them to forecast the future, then runs a simulated day-by-day blood inventory through those forecasts to answer four questions for each blood type (A, B, AB, O): **how much will be needed, how much will come in, is a shortage brewing, and is blood about to be wasted from expiring unused?**

---

## 2. The two datasets

Everything in this project is grounded in exactly two real, downloadable datasets. No other data source is used anywhere in the running system.

### 2.1 The demand dataset — `backend/data/blood_demand.csv`

**Where it's from:** A public Kaggle dataset of blood demand records.

**What one row looks like:**

```
Date,DayOfWeek,Month,Population,Events,HistoricalBloodUsage,HospitalAdmissions,BloodDonorsAvailable,Temperature,PredictedBloodDemand
2020-01-02,3,1,196867,0,187,71,55,21.590135995172037,197
```

**What each column means:**
| Column | Meaning |
|---|---|
| `Date` | The calendar day this row describes |
| `DayOfWeek` | Day of the week as a number (0 = Monday) |
| `Month` | Month number (1–12) |
| `Population` | The local population figure for that day/region in the dataset |
| `Events` | A flag (0 or 1) for whether a notable event happened that day (e.g. something that might spike blood demand, like a mass-casualty event or holiday) |
| `HistoricalBloodUsage` | How much blood was actually used the *previous* day (a lagging indicator) |
| `HospitalAdmissions` | How many people were admitted to hospital that day |
| `BloodDonorsAvailable` | How many donors were available/registered that day |
| `Temperature` | The day's temperature |
| `PredictedBloodDemand` | **This is the target/label column** — the actual number of blood units demanded that day. (The name is a little confusing — despite being called "Predicted," in the dataset itself this is the real historical number we're training the model to reproduce, not a pre-computed prediction.) |

**Scale of the data:** 1,827 rows, one per day, covering **2020-01-01 to 2024-12-31** (5 years). Averaged across all those days, demand is **~184 units per day**.

**The critical limitation:** this is a **single national/aggregate number per day**. There is no column anywhere that says how many of those units were blood type A vs. O vs. anything else. This one fact shapes a large part of the rest of the system (see §4, "the disaggregation problem," below).

### 2.2 The supply dataset — `backend/data/blood_donations.csv`

**Where it's from:** Malaysia's government open-data portal (`data.gov.my`), a real public blood-donation dataset.

**What one row looks like:**

```
date,blood_type,donations
2006-01-01,a,152
2006-01-01,o,194
```

**What each column means:**
| Column | Meaning |
|---|---|
| `date` | The calendar day |
| `blood_type` | One of `a`, `b`, `ab`, `o` (lowercase), or the special value `all` which is just the sum of the other four for that day — the code always filters this row out before using the data |
| `donations` | How many units of that blood type were donated that day, nationally |

**Scale of the data:** 7,490 rows *per blood type* (so ~30,000 rows total), covering **2006-01-01 to 2026-07-04** — about 20 years. Averaged across the whole period:

| Blood type | Average donations/day | Share of total |
|---|---|---|
| O | ~543.5 | **41.8%** |
| B | ~353.4 | **27.2%** |
| A | ~322.5 | **24.8%** |
| AB | ~79.8 | **6.1%** |

**Why this matters:** this is the *only* place in either dataset where blood-type-level detail exists at all. Every "per blood type" number the dashboard shows for demand ultimately traces back to these four ratios.

### 2.3 A hard constraint this creates

Neither dataset has:
- **Hospital or regional breakdowns** — both are national aggregates.
- **Rh factor (+/-)** — the donation data only has A/B/AB/O, no positive/negative split.

Because of this, the whole project is deliberately scoped to **national-level forecasting across exactly 4 blood types (A, B, AB, O)** — not 8 types, not per-hospital. Anywhere you might expect "O+" or "AB-", this system only ever produces "O" or "AB".

---

## 3. Machine Learning Model #1 — Demand Forecasting (LightGBM)

**File:** `backend/ml/train_demand.py`, used via `backend/ml/inference.py`

**What it is:** LightGBM is a "gradient boosted decision tree" model — a widely-used, fast, and accurate machine learning technique for tabular (spreadsheet-like) data. It builds hundreds of small decision trees in sequence, where each new tree tries to correct the mistakes of the trees before it.

**What it's trained to do:** predict the single number `PredictedBloodDemand` (total national blood demand for that day) using the other columns in the demand dataset as inputs (its "features").

**The exact features it uses:**
- Calendar-derived: `DayOfWeek`, `Month`, `Quarter`, `DayOfYear`, `DayOfMonth`, `WeekOfYear` (all computed automatically from the `Date` column — the model never sees the raw date, only these derived numbers, since a raw date isn't something a tree-based model can use directly)
- From the dataset directly: `Population`, `Events`, `HospitalAdmissions`, `Temperature`

**How it's trained:**
- The dataset is sorted by date and split so the model trains on all but the last 30 days, and is tested against those last 30 days it never saw during training (this is called a time-series train/test split — it mimics the real situation of predicting days you haven't seen yet).
- Model settings: 500 trees maximum, learning rate 0.05, tree depth capped at 6, and it uses "early stopping" — if the model stops improving on the held-out 30 test days for 50 rounds in a row, training halts early to avoid overfitting.
- After training, it's evaluated with two standard error metrics: MAE (Mean Absolute Error — average size of the mistake, in blood units) and RMSE (Root Mean Squared Error — similar, but penalizes big mistakes more heavily).
- The finished model is saved to disk as `backend/ml/demand_model.pkl` using `joblib` (a standard way to save trained Python ML models to a file so they don't need to be retrained every time the server restarts).

**How it's used to predict the *future*:** This is a subtlety worth understanding. To predict tomorrow's demand, the model needs values for *all* its input features for tomorrow — but we don't actually know tomorrow's real `HospitalAdmissions`, `Events`, or `Temperature` yet (those are only known in real data *after* the fact). So `predict_demand()` in `inference.py` **synthesizes plausible future values** for those columns:
- `Population` is fixed at a constant (180,000)
- `Events` is randomly 0 or 1 with a 90%/10% split (mimicking how rare "event" days actually are in the training data)
- `HospitalAdmissions` is drawn from a random normal distribution centered at 70
- `Temperature` is drawn from a random normal distribution centered at 28

This means: the *demand model itself* is real and properly trained on real historical data, but every time you ask it to forecast "the next 30 days," the day-to-day wiggle in the forecast is partly driven by these randomly-sampled stand-in covariates, not a real weather or admissions forecast. This is an honest, necessary simplification — nobody has a real 30-day-ahead hospital admissions forecast to plug in — but it's worth knowing that the forecast's *shape* (trend, seasonality) is real and learned, while its *day-to-day jitter* has some randomness baked in from these synthetic inputs.

**Output:** a list of `{date, predicted_demand}` pairs — one aggregate (all blood types combined) number per day for the requested number of days (default 30).

---

## 4. Machine Learning Model #2 — Supply/Donation Forecasting (Prophet)

**File:** `backend/ml/train_supply.py`, used via `backend/ml/inference.py`

**What it is:** Prophet is a forecasting tool originally built by Facebook/Meta, designed specifically for time series with strong seasonal patterns (weekly cycles, yearly cycles, holiday effects) — exactly what donation data looks like (donations dip on weekends, vary by season, etc.).

**What it's trained to do:** Unlike the demand model (one model predicting one aggregate number), this trains **four separate, independent Prophet models — one per blood type (A, B, AB, O)**. Each one only ever sees the donation history for its own blood type.

**How each one is trained:**
- The donation data is filtered down to just that blood type's rows (e.g. only rows where `blood_type == 'a'`).
- Renamed to the column names Prophet requires: `ds` (the date) and `y` (the value to predict — in this case, `donations`).
- Filtered to only data after 2019-01-01 (about 5 recent years) — old data from 2006 is less representative of current donation patterns, so it's dropped to keep the model relevant.
- Each model is configured with: yearly seasonality on, weekly seasonality on, daily seasonality off (donations don't have a meaningful within-day pattern in this data), and a "changepoint prior scale" of 0.05 (this controls how flexible Prophet is allowed to be about the *trend* changing direction over time — a lower number means it assumes the long-term trend is fairly stable and won't overreact to short-term wiggles).
- Malaysian public holidays are added via `model.add_country_holidays(country_name='MY')`, so the model can learn that donation numbers dip or spike around real Malaysian holidays.
- All four trained models are saved together in a single file, `backend/ml/supply_models.pkl` (a Python dictionary of `{blood_type: trained_model}`).

**How it predicts the future:** Prophet has a built-in mechanism for this — you ask it to build a "future dataframe" extending some number of days past its training data, and it produces a forecast (called `yhat`) for each of those future days, based on the seasonal and trend patterns it learned. Negative predictions (which Prophet can occasionally produce, since it doesn't inherently know donations can't be negative) are clipped to zero.

**Output:** a dictionary keyed by blood type (`{"A": [...], "B": [...], "AB": [...], "O": [...]}`), each holding a list of `{date, predicted_supply}` pairs for the requested number of days.

**Why this one doesn't need synthetic covariates like the demand model does:** Prophet is a different kind of model — it only needs *time* as an input (it learns patterns purely from how the target value moved over time), so there's no equivalent problem of "we don't know tomorrow's weather" here. This makes the supply forecast more purely "real" than the demand forecast.

---

## 5. The disaggregation problem, and how it's solved

**File:** `backend/ml/demand_split.py`

Here's the core tension: the demand *model* only produces one number per day (total demand, no blood-type breakdown), but the whole point of this project is to show shortage/wastage risk **per blood type**. So how do you get a per-type demand number out of a model that was never taught blood types?

**The answer: `compute_type_ratios()` and `split_by_type()`.**

1. `compute_type_ratios()` reads the *real* donation dataset (`blood_donations.csv`), sums up all historical donations per blood type across all ~20 years of data, and computes what fraction of total donations each type represents. As shown in §2.2 above, this comes out to roughly O=41.8%, B=27.2%, A=24.8%, AB=6.1% (these are computed live from the real CSV every time, not hardcoded — if the dataset changes, the ratios automatically update).

2. `split_by_type()` takes the LightGBM model's one aggregate demand number for a given day, and multiplies it by each of those four ratios. So if the model predicts 200 units of total demand tomorrow, the disaggregated numbers become roughly: O ≈ 84, B ≈ 54, A ≈ 50, AB ≈ 12.

**Is this a real per-type demand forecast?** No — and this is important to be upfront about. This is a **documented approximation**: it assumes that the demand for each blood type is always in the same fixed proportion as its *donation* volume nationally. In reality, demand proportions and donation proportions aren't necessarily identical (donation supply reflects population blood-type distribution, while demand can be skewed by e.g. trauma cases needing O-negative specifically). But given that the demand dataset has *no* type breakdown at all, this is the most honest, data-grounded way to produce a "per type" number — it's not invented from nothing, it's derived from real donation-mix data, but it should be understood as an approximation, not an independently-learned prediction.

---

## 6. The simulation engine — turning forecasts into an inventory

**File:** `backend/simulation/engine.py`

Once you have (a) a demand forecast per blood type and (b) a supply forecast per blood type, you still don't have an "inventory" — you have two separate number lines. The simulation engine is what turns those into an actual simulated stock of blood bags, day by day, for each blood type independently.

**This is a pure Python simulation — no machine learning here, just deterministic bookkeeping logic.** It runs entirely in memory, fresh, every time someone calls the `/api/simulate` endpoint. There is no database anywhere in this project — nothing is persisted between requests.

Here's what happens for **one blood type**, for each simulated day, in order:

1. **A starting stock is seeded.** On day zero, before anything else happens, the simulation assumes there's already some blood on the shelf — set to 7 days' worth of that type's first day of forecasted demand (`INITIAL_STOCK_COVERAGE_DAYS = 7` in `backend/config.py`). This initial batch is deliberately "seeded" as already half-aged (21 days into its 42-day shelf life) rather than brand new — a simplification so it doesn't unrealistically all expire on the exact same day later.

2. **Donations arrive.** That day's forecasted supply number becomes a brand-new "batch" of blood units, starting at a full 42-day shelf life (`SHELF_LIFE_DAYS = 42` — the real medical standard shelf life for red blood cells stored at 1–6°C).

3. **Demand consumes stock, oldest-first (FEFO).** FEFO stands for "First-Expired, First-Out" — the standard real-world blood bank practice of always using the soonest-to-expire units first, to minimize waste. The simulation sorts all current batches by days-left-until-expiry and consumes from the batch closest to expiring first, working through however many batches it takes to meet that day's demand. If there isn't enough stock to meet demand, whatever's left over is recorded as `unmet_demand` (a real shortfall) rather than pretending demand was magically satisfied.

4. **Everything ages by one day.** Every remaining batch (including the one that arrived today) has its "days until expiry" reduced by one.

5. **Anything that hits zero shelf life left is expired and removed.** The total units removed this way are recorded as that day's `expired` count — this is literal wasted blood, discarded because it wasn't used in time.

6. **The day is scored for risk** (see §7 below) and a full record is saved: date, that day's demand, that day's supply, how much was actually consumed, how much demand went unmet, how much expired, the resulting stock level, and the two risk classifications.

This entire 6-step process repeats once per simulated day (default 30 days), independently for each of the 4 blood types, and the results are collected into one response.

---

## 7. The two rule-based classifiers

Neither of these use machine learning — they're simple, transparent, explainable rules applied to numbers the simulation engine already computed. This was a deliberate choice: shortage and wastage risk are meant to be easy to understand and audit, not a "black box."

### 7.1 Shortage classification — `backend/simulation/shortage_rules.py`

**The input:** "days of coverage" — current stock divided by the trailing 7-day average demand for that blood type. In plain terms: *at the current rate of use, how many more days would this stock last if nothing else came in?*

**The rule:**
| Days of coverage | Classification |
|---|---|
| ≤ 3 days | **CRITICAL** |
| ≤ 7 days (but > 3) | **WARNING** |
| > 7 days | **SAFE** |

These exact thresholds (3 and 7 days) were chosen to match the same convention already used elsewhere in the project's inventory-status UI, so the numbers mean the same thing everywhere in the system.

### 7.2 Wastage classification — `backend/simulation/wastage_rules.py`

**The input:** "near-expiry ratio" — of the blood currently in stock, what fraction is within 3 days of expiring (`WASTAGE_NEAR_EXPIRY_WINDOW_DAYS = 3`)?

**The rule:**
| Near-expiry ratio | Classification |
|---|---|
| > 40% | **HIGH** |
| 15%–40% | **MED** |
| < 15% | **LOW** |

In plain terms: if almost half your current stock of a blood type is about to expire in the next 3 days, that's a HIGH wastage risk — you likely won't be able to use it all before it has to be thrown away.

---

## 8. The API — how it all gets served

**File:** `backend/api/main.py` (a FastAPI web server)

The important endpoints:

- **`POST /api/train/demand`** — runs the LightGBM training process from scratch and saves the model to disk.
- **`POST /api/train/supply`** — runs the 4 Prophet trainings from scratch and saves them to disk.
- **`GET /api/forecast/demand?days=30`** — returns just the aggregate LightGBM demand forecast.
- **`GET /api/forecast/supply?days=30`** — returns just the 4 Prophet supply forecasts.
- **`GET /api/simulate?days=30`** — the main endpoint the dashboard actually uses. In one call, this:
  1. Calls the demand model and disaggregates it by type (§5)
  2. Calls the 4 supply models
  3. Runs the full day-by-day simulation (§6) for all 4 blood types
  4. Classifies every day for shortage and wastage risk (§7)
  5. Returns everything as one JSON response: `{"A": [...30 day-records...], "B": [...], "AB": [...], "O": [...]}`

Nothing is cached or stored — every call retrains nothing (models are loaded from the `.pkl` files saved during training) but re-runs the forecasting and simulation fresh, so the numbers reflect "today" as the starting point every time you call it.

---

## 9. The frontend — the "Boss Health Bar" dashboard

**Files:** `frontend/src/pages/Dashboard.jsx`, `frontend/src/components/HealthBarCard.jsx`, `frontend/src/components/AlertStream.jsx`, `frontend/src/lib/api.js`

The dashboard calls `/api/simulate?days=30` exactly once when the page loads, getting back the full 30-day simulated future for all 4 blood types in one shot. Everything you see and interact with afterward is just replaying and filtering that one response client-side — there's no additional server communication as you click around.

### 9.1 The four Health Bar cards

Named after the health/HP bars in video games, one card per blood type (A, B, AB, O):
- A fill bar showing current simulated stock, colored **green (Safe) / amber (Warning) / red, pulsing (Critical)** based directly on that day's shortage classification from the backend — never hardcoded, always reflecting the real computed risk.
- A brief "shake" animation plays on any day where that blood type had units expire (a visual "ouch" moment for wastage).
- **Level A (always visible):** a small readout under the bar showing that day's exact demand, supply, shortage risk label, and wastage risk label as text.
- **Level B (click to expand):** clicking a card expands it into a line chart showing demand vs. supply as two lines across the *entire* 30-day window (not just today), plus a row of small colored ticks — one per day — showing at a glance which days were risky.

### 9.2 The day-by-day scrubber

A "Next Day" button and an "Auto-play" toggle let you step through the pre-computed 30-day simulation one day at a time (or watch it play automatically), updating all four cards, the KPI numbers, and the alert feed in sync — again, using only the one already-fetched response, no new network calls per day.

### 9.3 The Alert Stream

A real-time-feeling feed of events, but every single entry is derived directly from the actual simulation data (there is no random/fake alert generation anywhere in this component): a CRITICAL shortage on a given day for a given type becomes an alert entry, as does any day where units expired. It's filterable by severity (All / Critical / Warning / Expiry).

### 9.4 Visual design

The whole gamified interaction (fill bars, color-by-risk, shake animation, day scrubber) deliberately reuses the site's existing design system — the same rose/blush color palette and "Outfit" typography used elsewhere on the site — rather than introducing a new visual style just for this feature.

---

## 10. What this project deliberately does NOT do

To be fully transparent about scope, here's what was explicitly left out, and why:

- **No hospital-level or regional breakdown.** Neither dataset has this information; adding it would mean inventing data.
- **No Rh factor (+/-), only 4 blood types (A/B/AB/O).** Same reason — the data doesn't support an 8-way split.
- **No database.** Every simulation is computed fresh, in memory, from the saved trained models and the two CSV files. Nothing about a specific simulation run is saved anywhere.
- **No inter-location transfer recommendations** (e.g. "move 20 units of O- from Hospital A to Hospital B") — this would require real multi-location data that doesn't exist here.
- **No deep-learning hybrid model.** An earlier version of this project's plans mentioned a fancier neural-network-based model (a GRU combined with LightGBM). That was dropped in favor of the simpler, real, working LightGBM + Prophet combination described above, which is what's actually trained and running.

---

## 11. Quick reference — file map

| File | Role |
|---|---|
| `backend/data/blood_demand.csv` | Real Kaggle demand dataset |
| `backend/data/blood_donations.csv` | Real Malaysian donation dataset |
| `backend/ml/train_demand.py` | Trains the LightGBM demand model |
| `backend/ml/train_supply.py` | Trains the 4 Prophet supply models |
| `backend/ml/demand_split.py` | Disaggregates aggregate demand into per-type demand |
| `backend/ml/inference.py` | Loads trained models and produces forecasts |
| `backend/config.py` | Shared constants (blood types, shelf life, thresholds) |
| `backend/simulation/engine.py` | Day-by-day FEFO stock simulation |
| `backend/simulation/shortage_rules.py` | Shortage risk classifier |
| `backend/simulation/wastage_rules.py` | Wastage risk classifier |
| `backend/api/main.py` | The web server tying everything together |
| `frontend/src/lib/api.js` | Fetches the simulation data from the backend |
| `frontend/src/components/HealthBarCard.jsx` | One blood-type's gamified status card |
| `frontend/src/components/AlertStream.jsx` | The real-data-driven alert feed |
| `frontend/src/pages/Dashboard.jsx` | The page that ties it all together |
