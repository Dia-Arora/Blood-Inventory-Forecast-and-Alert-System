"""
inventory/inventory_generator.py
---------------------------------
Generates the initial realistic blood inventory in the database.

Design rules
------------
* Idempotent: runs only if the inventory_batches table is empty.
* Quantities are grounded in relative ABO blood group frequency, not random noise.
* Collection dates are spread across the last (shelf_life // 2) days to simulate
  a realistic mix of fresh and ageing stock.
* Expiry date = collection_date + BLOOD_SHELF_LIFE_DAYS (from config).
* All batch IDs are UUIDs.
"""

import logging
import uuid
from datetime import date, timedelta
from typing import List

from sqlalchemy.orm import Session

from config.settings import (
    BLOOD_GROUPS,
    BLOOD_SHELF_LIFE_DAYS,
    INITIAL_BATCHES_PER_GROUP,
    SAFETY_STOCK_PER_GROUP,
)
from database.db import InventoryBatch

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Realistic unit ranges per blood group
# ---------------------------------------------------------------------------
# Ranges are proportional to typical hospital procurement volumes and
# reflect relative ABO frequency: O is most common, AB is rarest.
_UNIT_RANGES = {
    "O":  (60, 120),
    "A":  (50, 100),
    "B":  (30,  70),
    "AB": (15,  35),
}

# Spread collection dates across this window (days before today).
_DATE_SPREAD_DAYS = BLOOD_SHELF_LIFE_DAYS // 2  # 21 days


def _build_batches(today: date) -> List[InventoryBatch]:
    """
    Build a list of InventoryBatch objects covering all four blood groups.

    Each group receives INITIAL_BATCHES_PER_GROUP batches with collection dates
    evenly distributed over the last _DATE_SPREAD_DAYS days.
    """
    batches: List[InventoryBatch] = []

    for group in BLOOD_GROUPS:
        low, high = _UNIT_RANGES[group]
        n = INITIAL_BATCHES_PER_GROUP

        # Evenly spread n collection dates across the window.
        # Step = window / (n - 1) so first date = today - window, last = today.
        step = _DATE_SPREAD_DAYS // max(n - 1, 1)

        for i in range(n):
            # Collection date: start from oldest, step forward.
            days_ago = _DATE_SPREAD_DAYS - i * step
            collection_date = today - timedelta(days=days_ago)
            expiry_date = collection_date + timedelta(days=BLOOD_SHELF_LIFE_DAYS)

            # Units: distribute evenly across batches so total ≈ midpoint × n.
            # Use a deterministic linear ramp (not random) for reproducibility.
            fraction = i / max(n - 1, 1)          # 0.0 → 1.0
            units = int(low + fraction * (high - low))
            # Ensure units never falls below the safety stock threshold for auditability.
            units = max(units, SAFETY_STOCK_PER_GROUP.get(group, 20) // n)

            batch = InventoryBatch(
                batch_id=str(uuid.uuid4()),
                blood_group=group,
                units=units,
                collection_date=collection_date,
                expiry_date=expiry_date,
                status="AVAILABLE",
            )
            batches.append(batch)

    return batches


class InventoryGenerator:
    """
    Responsible for seeding the initial blood inventory.

    Usage
    -----
    Call ``run(db)`` once at application startup. The method checks whether
    any inventory already exists and exits immediately if so (idempotent).
    """

    def run(self, db: Session) -> bool:
        """
        Seed the initial inventory if the table is empty.

        Parameters
        ----------
        db : SQLAlchemy Session

        Returns
        -------
        bool
            True  → inventory was seeded now (first run).
            False → inventory already existed; nothing changed.
        """
        existing_count = db.query(InventoryBatch).count()
        if existing_count > 0:
            logger.info(
                "Inventory already seeded (%d batches found). Skipping generator.",
                existing_count,
            )
            return False

        today = date.today()
        batches = _build_batches(today)

        db.bulk_save_objects(batches)
        db.commit()

        logger.info(
            "Initial inventory seeded: %d batches across %d blood groups "
            "(shelf life = %d days).",
            len(batches),
            len(BLOOD_GROUPS),
            BLOOD_SHELF_LIFE_DAYS,
        )

        # Log a summary per group for transparency.
        for group in BLOOD_GROUPS:
            group_batches = [b for b in batches if b.blood_group == group]
            total_units = sum(b.units for b in group_batches)
            logger.info(
                "  Group %s: %d batches, %d total units",
                group,
                len(group_batches),
                total_units,
            )

        return True
