from datetime import datetime, timedelta

from simulation.scenario_shocks import demand_shock_multiplier, supply_shock_multiplier


def test_demand_shock_is_deterministic_for_same_inputs():
    date = datetime(2026, 3, 10)
    assert demand_shock_multiplier("o", date) == demand_shock_multiplier("o", date)


def test_demand_shock_ignores_time_of_day():
    # Regression test: predict_demand_by_type() builds its dates from
    # datetime.now(), which carries the current time-of-day, not just the
    # date. The shock must depend only on the calendar day, or calling
    # the API at two different times of the same day would silently
    # produce different "daily" shocks -- reintroducing the exact
    # non-determinism bug already fixed once in inference.py.
    midnight = datetime(2026, 3, 10, 0, 0, 0)
    afternoon = datetime(2026, 3, 10, 15, 42, 7, 123456)
    assert demand_shock_multiplier("o", midnight) == demand_shock_multiplier("o", afternoon)


def test_supply_shock_ignores_time_of_day():
    midnight = datetime(2026, 5, 1, 0, 0, 0)
    evening = datetime(2026, 5, 1, 23, 59, 59)
    assert supply_shock_multiplier("ab", midnight) == supply_shock_multiplier("ab", evening)


def test_demand_shock_differs_by_blood_type_on_same_date():
    date = datetime(2026, 3, 10)
    values = {bt: demand_shock_multiplier(bt, date) for bt in ["a", "b", "ab", "o"]}
    assert len(set(values.values())) > 1


def test_demand_shock_is_always_positive():
    date = datetime(2026, 3, 10)
    for bt in ["a", "b", "ab", "o"]:
        assert demand_shock_multiplier(bt, date) > 0


def test_supply_shock_is_deterministic_for_same_inputs():
    date = datetime(2026, 5, 1)
    assert supply_shock_multiplier("ab", date) == supply_shock_multiplier("ab", date)


def test_supply_shock_is_always_positive():
    date = datetime(2026, 5, 1)
    for bt in ["a", "b", "ab", "o"]:
        assert supply_shock_multiplier(bt, date) > 0


def test_demand_surges_actually_occur_across_a_year():
    # With a 6%-per-week-per-type surge chance, it would be a near
    # statistical impossibility for none of 4 types to ever surge across
    # 52 weeks. Guards against a broken/always-1.0 implementation.
    found_surge = False
    start = datetime(2026, 1, 5)
    for week_offset in range(52):
        date = start + timedelta(weeks=week_offset)
        for bt in ["a", "b", "ab", "o"]:
            if demand_shock_multiplier(bt, date) > 1.5:
                found_surge = True
    assert found_surge


def test_supply_shortfalls_actually_occur_across_a_year():
    found_shortfall = False
    start = datetime(2026, 1, 5)
    for week_offset in range(52):
        date = start + timedelta(weeks=week_offset)
        for bt in ["a", "b", "ab", "o"]:
            if supply_shock_multiplier(bt, date) < 0.7:
                found_shortfall = True
    assert found_shortfall


def test_supply_gluts_actually_occur_across_a_year():
    found_glut = False
    start = datetime(2026, 1, 5)
    for week_offset in range(52):
        date = start + timedelta(weeks=week_offset)
        for bt in ["a", "b", "ab", "o"]:
            if supply_shock_multiplier(bt, date) > 1.4:
                found_glut = True
    assert found_glut
