"""
Adds realistic day-to-day and week-to-week randomness on top of the
underlying demand/supply forecasts, so the simulation can show genuine
CRITICAL shortage and HIGH wastage moments -- not just smooth trends.

Real trauma surges, donation-drive successes, and donation shortfalls are
fundamentally unpredictable in advance (a forecasting model can only ever
learn the *expected* pattern from calendar features, never a specific
future shock) -- so this layer models "what actually happens" on top of
"what was expected", the same way a Monte-Carlo scenario would.

Deterministic: every (blood_type, date) pair always produces the same
shock. Uses a stable SHA-256-based seed rather than Python's built-in
hash(), which is randomized per-process and would silently break
determinism across server restarts.

Named scenarios (see simulation/scenarios.py) can override this default
random behavior for specific day windows of the simulation -- e.g. "the
first two simulated days see a guaranteed demand surge" -- instead of the
always-on random chance. When a scenario has no override for a given day
(including the "default" scenario, which never overrides anything), the
exact original random logic runs unchanged, so existing behavior and tests
are unaffected by this parameter's existence.
"""
import hashlib

import numpy as np

from simulation.scenarios import SCENARIOS


def _seeded_rng(*parts):
    key = "-".join(str(p) for p in parts).encode("utf-8")
    seed = int(hashlib.sha256(key).hexdigest(), 16) % (2**32)
    return np.random.default_rng(seed)


def _scenario_override(scenario, side, day_index):
    if day_index is None:
        return None
    config = SCENARIOS.get(scenario)
    if not config:
        return None
    windows = config.get(f"{side}_override")
    if not windows:
        return None
    for window in windows:
        if window["start_day"] <= day_index < window["end_day"]:
            return window["range"]
    return None


def demand_shock_multiplier(blood_type, date, day_index=None, scenario="default"):
    """
    Daily jitter (+/- ~15%) plus occasional multi-day demand surges
    (~6% of weeks, 1.8-2.6x) representing trauma clusters or local
    outbreaks that no calendar-based forecast could have predicted --
    unless `scenario` overrides this day with a preset multiplier.
    """
    date_str = date.strftime("%Y-%m-%d")
    daily_rng = _seeded_rng(blood_type, date_str, "demand-daily")
    daily_noise = daily_rng.normal(0, 0.15)

    override_range = _scenario_override(scenario, "demand", day_index)
    if override_range is not None:
        override_rng = _seeded_rng(blood_type, date_str, scenario, "demand-scenario")
        mult = override_rng.uniform(*override_range)
        return max(0.1, (1 + daily_noise) * mult)

    iso_year, iso_week, _ = date.isocalendar()
    week_rng = _seeded_rng(blood_type, iso_year, iso_week, "demand-surge")
    is_surge = week_rng.random() < 0.06
    surge_mult = week_rng.uniform(1.8, 2.6) if is_surge else 1.0

    return max(0.1, (1 + daily_noise) * surge_mult)


def supply_shock_multiplier(blood_type, date, day_index=None, scenario="default"):
    """
    Daily jitter (+/- ~15%) plus occasional multi-day supply swings:
    ~5% of weeks are a donation shortfall (0.4-0.6x, e.g. holidays or bad
    weather suppressing turnout), ~5% are a donation-drive glut
    (1.6-2.2x) that can outpace demand enough to risk wastage -- unless
    `scenario` overrides this day with a preset multiplier.
    """
    date_str = date.strftime("%Y-%m-%d")
    daily_rng = _seeded_rng(blood_type, date_str, "supply-daily")
    daily_noise = daily_rng.normal(0, 0.15)

    override_range = _scenario_override(scenario, "supply", day_index)
    if override_range is not None:
        override_rng = _seeded_rng(blood_type, date_str, scenario, "supply-scenario")
        mult = override_rng.uniform(*override_range)
        return max(0.1, (1 + daily_noise) * mult)

    iso_year, iso_week, _ = date.isocalendar()
    week_rng = _seeded_rng(blood_type, iso_year, iso_week, "supply-swing")
    roll = week_rng.random()
    if roll < 0.05:
        swing_mult = week_rng.uniform(0.4, 0.6)
    elif roll < 0.10:
        swing_mult = week_rng.uniform(1.6, 2.2)
    else:
        swing_mult = 1.0

    return max(0.1, (1 + daily_noise) * swing_mult)
