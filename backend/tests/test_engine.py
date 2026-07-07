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
