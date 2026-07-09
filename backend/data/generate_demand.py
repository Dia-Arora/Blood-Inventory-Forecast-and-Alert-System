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
