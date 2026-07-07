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


def test_simulate_single_type_records_unmet_demand_when_demand_spikes():
    # Small day-0 demand keeps the seeded initial stock small (14 units,
    # since INITIAL_STOCK_COVERAGE_DAYS=7 -> round(2*7)=14). Day 1's demand
    # (1000) then vastly exceeds everything on hand (14 initial + 2 + 5
    # supply = 21 units total available across both days), so it can't
    # possibly be fully met.
    demand_series = _series([2, 1000], "predicted_demand")
    supply_series = _series([2, 5], "predicted_supply")

    records = simulate_single_type(demand_series, supply_series, days=2)

    assert records[0]["unmet_demand"] == 0
    assert records[1]["unmet_demand"] > 0
    # 14 (seeded) + 2 (day0 supply) + 5 (day1 supply) - 2 (day0 consumed)
    # = 19 units ever available to day 1; demand of 1000 leaves 981 unmet.
    assert records[1]["unmet_demand"] == 981
    for r in records:
        assert r["stock"] >= 0


def test_simulate_single_type_expires_units_on_the_correct_day():
    # Day-0 demand of 2 seeds an initial batch of round(2*7)=14 units at
    # SHELF_LIFE_DAYS // 2 = 21 days_until_expiry. Day 0 consumes 2 of
    # those units, leaving 12. Zero demand and zero supply for every
    # subsequent day means those 12 units just age untouched: they lose
    # one day of shelf life per simulated day, so they hit
    # days_until_expiry == 0 (and are removed as "expired") on day index
    # 20 (the 21st simulated day: 21 days of aging total, 1 from day 0's
    # own aging step plus 20 more idle days).
    demand_series = _series([2] + [0] * 20, "predicted_demand")
    supply_series = _series([0] * 21, "predicted_supply")

    records = simulate_single_type(demand_series, supply_series, days=21)

    assert len(records) == 21
    # Nothing expires before the batch actually runs out of shelf life.
    for r in records[:20]:
        assert r["expired"] == 0
    # The day before expiry, all 12 surviving units are still counted as
    # stock (not prematurely dropped).
    assert records[19]["stock"] == 12
    # On the expiry day, the units are removed from stock exactly once
    # (not double-counted): expired == 12 and stock drops to 0.
    assert records[20]["expired"] == 12
    assert records[20]["stock"] == 0
