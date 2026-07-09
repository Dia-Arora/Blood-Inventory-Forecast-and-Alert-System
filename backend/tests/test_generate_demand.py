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
