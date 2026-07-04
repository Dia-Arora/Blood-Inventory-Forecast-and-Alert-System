"""
Digital Twin Orchestrator
==========================
Member 3 -- Digital Twin Lead

Entry point for running a complete Digital Twin simulation day.
Wires together:
    1. FEFOEngine    -- Batch-level inventory simulation
    2. RiskEngine    -- Shortage and wastage risk classification
    3. Optimizer     -- Prescriptive LP transfer recommendations

Usage:
    python run_twin.py

Or import for use by Member 4's API:
    from run_twin import DigitalTwin
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from simulation.fefo_engine import FEFOEngine, DaySimulationResult, SHELF_LIFE_DAYS, SAFETY_STOCK
from risk_engine import RiskEngine, RiskAlert
from optimization.optimizer import PrescriptiveOptimizer, BloodStockState, PrescriptiveAction

logger = logging.getLogger(__name__)

PRODUCTS = list(SHELF_LIFE_DAYS.keys())


@dataclass
class TwinDayResult:
    """Full output of one Digital Twin simulation day."""
    sim_date:    date
    sim_results: Dict[str, DaySimulationResult]
    alerts:      List[RiskAlert]
    actions:     List[PrescriptiveAction]
    summary:     Dict[str, float] = field(default_factory=dict)


class DigitalTwin:
    """
    The core Digital Twin for blood inventory management.

    Simulates N days of operations using:
    - FEFO inventory mechanics
    - AI-generated demand forecast (from Member 2)
    - Prescriptive LP optimization (transfer recommendations)
    """

    def __init__(self):
        self.fefo    = FEFOEngine()
        self.risk    = RiskEngine()
        self.opt     = PrescriptiveOptimizer(safety_stock={
            p: int(v) for p, v in SAFETY_STOCK.items()
        })
        self._seeded = False

    def seed(self, units_per_product: Optional[Dict[str, float]] = None):
        """Seed starting inventory. Call once before simulating."""
        defaults = {p: SAFETY_STOCK[p] * 1.2 for p in PRODUCTS}
        stock = units_per_product or defaults
        for product, units in stock.items():
            self.fefo.seed_inventory(product, units, days_offset=-15)
        self._seeded = True
        logger.info("Inventory seeded for %d products.", len(PRODUCTS))

    def step(
        self,
        sim_date: date,
        demand_forecast: Dict[str, float],
        donation_forecast: Dict[str, float],
        location_id: str = "Hospital_1",
    ) -> TwinDayResult:
        """
        Run one simulation day.

        Args:
            sim_date:          The date being simulated.
            demand_forecast:   Dict[product, predicted_units_needed]
            donation_forecast: Dict[product, predicted_units_arriving]
            location_id:       Hospital identifier (for optimizer context)

        Returns:
            TwinDayResult with FEFO results, risk alerts, and prescriptive actions.
        """
        if not self._seeded:
            self.seed()

        # 1. Receive donations first (new stock arrives)
        for product, units in donation_forecast.items():
            if units > 0:
                self.fefo.receive_donation(product, units, sim_date)

        # 2. Run FEFO simulation for each product
        sim_results: Dict[str, DaySimulationResult] = {}
        for product in PRODUCTS:
            demand = demand_forecast.get(product, 0.0)
            result = self.fefo.simulate_day(product, demand, sim_date)
            result.donations = donation_forecast.get(product, 0.0)
            sim_results[product] = result

        # 3. Assess risk
        current_stock  = {p: r.closing_stock for p, r in sim_results.items()}
        expiring_soon  = {
            p: self.fefo.stock_expiring_within(p, 3, sim_date) for p in PRODUCTS
        }
        alerts = self.risk.evaluate(sim_date, current_stock, expiring_soon, demand_forecast)

        # 4. Prescriptive optimization
        stock_states = [
            BloodStockState(
                location_id=location_id,
                blood_group=p,
                units_available=current_stock[p],
                units_expiring_in_3_days=expiring_soon[p],
            )
            for p in PRODUCTS
        ]
        actions = self.opt.optimize_transfers(stock_states, {location_id: sum(demand_forecast.values())})

        # 5. Summary stats
        summary = {
            "total_demand":    sum(r.demand for r in sim_results.values()),
            "total_fulfilled": sum(r.fulfilled for r in sim_results.values()),
            "total_expired":   sum(r.expired_units for r in sim_results.values()),
            "total_unmet":     sum(r.unmet_demand for r in sim_results.values()),
            "fill_rate_%":     round(
                100 * sum(r.fulfilled for r in sim_results.values()) /
                max(sum(r.demand for r in sim_results.values()), 1), 2
            ),
        }

        return TwinDayResult(
            sim_date=sim_date,
            sim_results=sim_results,
            alerts=alerts,
            actions=actions,
            summary=summary,
        )


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    twin = DigitalTwin()
    twin.seed()

    today = date.today()

    # Simulate 7 days with dummy forecasts
    for i in range(7):
        sim_date = today + timedelta(days=i)
        demand   = {p: 18.0 for p in PRODUCTS}
        donation = {p: 10.0 for p in PRODUCTS}

        result = twin.step(sim_date, demand, donation)

        high_alerts = [a for a in result.alerts if a.risk_level == "HIGH"]
        print(
            f"Day {i+1} ({sim_date}): "
            f"fill_rate={result.summary['fill_rate_%']}% | "
            f"expired={result.summary['total_expired']:.1f} | "
            f"HIGH alerts={len(high_alerts)} | "
            f"actions={len(result.actions)}"
        )
