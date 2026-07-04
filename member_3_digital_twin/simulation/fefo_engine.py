"""
FEFO Simulation Engine
=======================
Member 3 — Digital Twin Lead

Implements a First-Expire, First-Out (FEFO) blood inventory simulation.
This is the core physics of the Digital Twin — it mirrors how a real
blood bank operates, tracking individual batches of blood bags with
specific collection dates and expiry dates.

Biology Reference:
    Packed Red Blood Cells (PRBC): shelf life 42 days at 1–6°C
    (AABB Technical Manual, 20th Edition)

Novel Aspect:
    Standard ML papers ignore FEFO mechanics and just track total units.
    Our Digital Twin tracks EACH BATCH individually, enabling precise
    wastage prediction and FEFO-compliant prescription.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Blood product shelf lives (days from collection)
# ---------------------------------------------------------------------------
SHELF_LIFE_DAYS: dict[str, int] = {
    "Packed Red Blood Cells": 42,
    "Fresh Frozen Plasma":    365,   # When frozen
    "Platelets":               5,    # Most perishable — 5 days
    "Cryoprecipitate":        365,
}

# Safety stock thresholds (units) — tune based on hospital capacity
SAFETY_STOCK: dict[str, float] = {
    "Packed Red Blood Cells": 60.0,
    "Fresh Frozen Plasma":    30.0,
    "Platelets":              15.0,
    "Cryoprecipitate":         5.0,
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class BloodBatch:
    """
    Represents a single batch of blood units collected on one day.
    This is the atomic unit of the FEFO simulation.
    """
    batch_id: str
    product:  str
    units:    float
    collection_date: date
    expiry_date:     date
    status: str = "AVAILABLE"   # AVAILABLE | USED | EXPIRED

    @classmethod
    def create(cls, product: str, units: float, collection_date: date) -> "BloodBatch":
        shelf_life = SHELF_LIFE_DAYS.get(product, 42)
        expiry     = collection_date + timedelta(days=shelf_life)
        batch_id   = f"{product[:4].upper()}_{collection_date.isoformat()}"
        return cls(
            batch_id=batch_id,
            product=product,
            units=units,
            collection_date=collection_date,
            expiry_date=expiry,
        )

    @property
    def days_to_expiry(self) -> int:
        return (self.expiry_date - date.today()).days

    @property
    def is_expired(self) -> bool:
        return date.today() >= self.expiry_date and self.status == "AVAILABLE"


@dataclass
class DaySimulationResult:
    """Output of a single simulation day."""
    sim_date:        date
    product:         str
    opening_stock:   float
    donations:       float
    demand:          float
    fulfilled:       float
    unmet_demand:    float
    expired_units:   float
    closing_stock:   float
    batches_expired: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# FEFO Engine
# ---------------------------------------------------------------------------

class FEFOEngine:
    """
    Maintains a live inventory of blood batches and simulates daily operations.

    Usage:
        engine = FEFOEngine()
        engine.receive_donation("Packed Red Blood Cells", units=20, on_date=today)
        result = engine.simulate_day("Packed Red Blood Cells", demand=15, on_date=today)
    """

    def __init__(self):
        # Inventory: product → list of batches sorted by expiry (FEFO order)
        self._inventory: Dict[str, List[BloodBatch]] = {
            p: [] for p in SHELF_LIFE_DAYS
        }

    def seed_inventory(self, product: str, units: float, days_offset: int = -20):
        """
        Seed starting inventory — useful for simulation warmup.
        Creates a batch collected `days_offset` days ago.
        """
        collection = date.today() + timedelta(days=days_offset)
        batch = BloodBatch.create(product, units, collection)
        self._add_batch(batch)

    def receive_donation(self, product: str, units: float, on_date: date):
        """Register incoming blood donation as a new batch."""
        batch = BloodBatch.create(product, units, on_date)
        self._add_batch(batch)
        logger.debug("Received %.1f units of %s (expires %s)", units, product, batch.expiry_date)

    def _add_batch(self, batch: BloodBatch):
        """Insert batch and re-sort by expiry (FEFO order)."""
        self._inventory[batch.product].append(batch)
        self._inventory[batch.product].sort(key=lambda b: b.expiry_date)

    def simulate_day(self, product: str, demand: float, on_date: date) -> DaySimulationResult:
        """
        Run one simulation day for a given product.

        Steps:
        1. Expire any batches past their expiry date.
        2. Fulfill demand using FEFO order (oldest first).
        3. Compute closing stock and unmet demand.
        """
        batches = self._inventory[product]
        opening_stock = sum(b.units for b in batches if b.status == "AVAILABLE")

        # --- Step 1: Expire batches ---
        expired_units = 0.0
        expired_ids   = []
        for batch in batches:
            if batch.status == "AVAILABLE" and on_date >= batch.expiry_date:
                expired_units += batch.units
                expired_ids.append(batch.batch_id)
                batch.status = "EXPIRED"
                logger.warning(
                    "EXPIRED: %s — %.1f units of %s", batch.batch_id, batch.units, product
                )

        # --- Step 2: Fulfill demand (FEFO — use oldest available first) ---
        remaining_demand = demand
        fulfilled        = 0.0
        for batch in batches:
            if batch.status != "AVAILABLE" or remaining_demand <= 0:
                continue
            take = min(batch.units, remaining_demand)
            batch.units      -= take
            fulfilled        += take
            remaining_demand -= take
            if batch.units <= 0:
                batch.status = "USED"

        unmet_demand  = max(remaining_demand, 0.0)
        closing_stock = sum(b.units for b in batches if b.status == "AVAILABLE")

        return DaySimulationResult(
            sim_date=on_date,
            product=product,
            opening_stock=opening_stock,
            donations=0.0,          # Filled by caller after receive_donation()
            demand=demand,
            fulfilled=fulfilled,
            unmet_demand=unmet_demand,
            expired_units=expired_units,
            closing_stock=closing_stock,
            batches_expired=expired_ids,
        )

    def stock_expiring_within(self, product: str, days: int, from_date: date) -> float:
        """Returns total units expiring within `days` from `from_date`."""
        window_end = from_date + timedelta(days=days)
        return sum(
            b.units
            for b in self._inventory[product]
            if b.status == "AVAILABLE" and from_date <= b.expiry_date <= window_end
        )

    def total_available(self, product: str) -> float:
        return sum(b.units for b in self._inventory[product] if b.status == "AVAILABLE")


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    today = date.today()
    engine = FEFOEngine()

    # Seed and run a 3-day smoke test
    engine.seed_inventory("Packed Red Blood Cells", units=50, days_offset=-30)
    engine.receive_donation("Packed Red Blood Cells", units=20, on_date=today)

    for i in range(3):
        sim_date = today + timedelta(days=i)
        result = engine.simulate_day("Packed Red Blood Cells", demand=18.0, on_date=sim_date)
        print(f"Day {i+1}: closing={result.closing_stock:.1f} | expired={result.expired_units:.1f} | unmet={result.unmet_demand:.1f}")
