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
