"""
inventory_simulation/simulation_engine.py
------------------------------------------
Deterministic inventory simulation engine.

This module contains ZERO machine learning.
All logic is rule-based and reproducible given the same inputs.

Workflow per simulation day
---------------------------
1. Expire batches whose expiry_date < sim_date.
2. Fetch predicted demand total and per-group donations from DB.
3. Distribute total demand across groups proportionally.
4. Consume stock using FEFO (First Expire, First Out) per group.
5. Add new donation batches for the simulation day.
6. Persist all changes.
7. Return a SimulationResult dataclass.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, Optional

from sqlalchemy.orm import Session

from config.settings import (
    BLOOD_GROUPS,
    BLOOD_SHELF_LIFE_DAYS,
    SAFETY_STOCK_PER_GROUP,
)
from database.db import ForecastDemand, ForecastDonation, InventoryBatch

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class SimulationResult:
    """
    Summary of one simulation day's outcome.

    Attributes
    ----------
    sim_date        : The date for which the simulation was run.
    projected_stock : Units available per group after the simulation.
    consumed        : Units consumed per group to meet predicted demand.
    donated         : Units added per group from predicted donations.
    expired         : Units lost per group due to expiry.
    demand_fulfilled: Whether predicted demand could be fully met from stock.
    unmet_demand    : Units of demand not fulfilled (stock ran out), per group.
    """
    sim_date: date
    projected_stock: Dict[str, int] = field(default_factory=dict)
    consumed: Dict[str, int] = field(default_factory=dict)
    donated: Dict[str, int] = field(default_factory=dict)
    expired: Dict[str, int] = field(default_factory=dict)
    demand_fulfilled: bool = True
    unmet_demand: Dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Demand distribution helper
# ---------------------------------------------------------------------------

def _distribute_demand(
    total_demand: float,
    safety_stock: Dict[str, int],
    blood_groups: list,
) -> Dict[str, int]:
    """
    Split a total demand figure across blood groups proportionally.

    Proportions are derived from the SAFETY_STOCK_PER_GROUP config values,
    which encode the relative importance/frequency of each group.

    Parameters
    ----------
    total_demand : float
        XGBoost-predicted total blood demand for the day.
    safety_stock : dict
        Per-group safety stock thresholds (used as proportion weights).
    blood_groups : list
        Ordered list of blood group strings.

    Returns
    -------
    dict[str, int]
        Integer demand per group (rounded, sums ≈ total_demand).
    """
    total_weight = sum(safety_stock.values())
    if total_weight == 0:
        # Fallback: equal distribution
        per_group = int(total_demand / len(blood_groups))
        return {g: per_group for g in blood_groups}

    demand_by_group: Dict[str, int] = {}
    remainder = int(round(total_demand))

    for i, group in enumerate(blood_groups):
        weight = safety_stock.get(group, 1)
        if i == len(blood_groups) - 1:
            # Assign all remaining units to the last group to avoid rounding loss
            demand_by_group[group] = max(0, remainder - sum(demand_by_group.values()))
        else:
            share = int(round(total_demand * weight / total_weight))
            demand_by_group[group] = max(0, share)

    return demand_by_group


# ---------------------------------------------------------------------------
# SimulationEngine
# ---------------------------------------------------------------------------

class SimulationEngine:
    """
    Runs one simulation day:

    1. Expire old batches.
    2. Read forecasts from DB.
    3. Consume stock (FEFO).
    4. Add new donation batches.
    5. Persist all changes.
    6. Return SimulationResult.
    """

    def run_simulation_day(self, db: Session, sim_date: date) -> SimulationResult:
        """
        Execute one full simulation cycle for ``sim_date``.

        Parameters
        ----------
        db       : Active SQLAlchemy session.
        sim_date : The date being simulated.

        Returns
        -------
        SimulationResult
        """
        logger.info("=== Simulation day: %s ===", sim_date)

        # Step 1: Expire batches
        expired_by_group = self._expire_batches(db, sim_date)

        # Step 2: Fetch forecasts
        demand_total = self._get_demand_forecast(db, sim_date)
        donation_by_group = self._get_donation_forecast(db, sim_date)

        if demand_total is None:
            logger.warning(
                "No demand forecast found for %s. Defaulting to 0.", sim_date
            )
            demand_total = 0.0

        if not donation_by_group:
            logger.warning(
                "No donation forecast found for %s. Defaulting to 0 per group.", sim_date
            )
            donation_by_group = {g: 0.0 for g in BLOOD_GROUPS}

        # Step 3: Distribute demand across groups
        demand_by_group = _distribute_demand(
            demand_total, SAFETY_STOCK_PER_GROUP, BLOOD_GROUPS
        )
        logger.info(
            "Total demand: %.1f → distributed: %s", demand_total, demand_by_group
        )

        # Step 4: Add new donation batches BEFORE consumption
        # (Donations collected today are available for today's use)
        donated_by_group = self._add_donation_batches(db, sim_date, donation_by_group)

        # Step 5: FEFO consumption
        consumed_by_group, unmet_demand, demand_fulfilled = self._consume_stock_fefo(
            db, demand_by_group
        )

        # Commit all changes to the DB
        db.commit()

        # Step 6: Compute projected stock per group
        projected_stock = self._compute_projected_stock(db)

        result = SimulationResult(
            sim_date=sim_date,
            projected_stock=projected_stock,
            consumed=consumed_by_group,
            donated=donated_by_group,
            expired=expired_by_group,
            demand_fulfilled=demand_fulfilled,
            unmet_demand=unmet_demand,
        )

        logger.info(
            "Simulation complete — Stock: %s | Consumed: %s | Donated: %s | Expired: %s",
            projected_stock, consumed_by_group, donated_by_group, expired_by_group,
        )

        return result

    # ------------------------------------------------------------------
    # Step 1: Expire batches
    # ------------------------------------------------------------------

    def _expire_batches(self, db: Session, sim_date: date) -> Dict[str, int]:
        """
        Mark as EXPIRED any AVAILABLE batch whose expiry_date < sim_date.

        Returns
        -------
        dict[str, int]
            Units expired per blood group.
        """
        expired_by_group: Dict[str, int] = {g: 0 for g in BLOOD_GROUPS}

        expired_batches = (
            db.query(InventoryBatch)
            .filter(
                InventoryBatch.status == "AVAILABLE",
                InventoryBatch.expiry_date < sim_date,
            )
            .all()
        )

        for batch in expired_batches:
            expired_by_group[batch.blood_group] = (
                expired_by_group.get(batch.blood_group, 0) + batch.units
            )
            batch.status = "EXPIRED"
            logger.debug(
                "Expired batch %s (%s, %d units, expired %s)",
                batch.batch_id, batch.blood_group, batch.units, batch.expiry_date,
            )

        if expired_batches:
            logger.info(
                "Expired %d batches: %s",
                len(expired_batches), expired_by_group,
            )

        return expired_by_group

    # ------------------------------------------------------------------
    # Step 2: Fetch forecasts
    # ------------------------------------------------------------------

    def _get_demand_forecast(
        self, db: Session, sim_date: date
    ) -> Optional[float]:
        """Retrieve the demand forecast for sim_date from the DB."""
        record = (
            db.query(ForecastDemand)
            .filter(ForecastDemand.forecast_date == sim_date)
            .order_by(ForecastDemand.created_at.desc())
            .first()
        )
        return record.predicted_units if record else None

    def _get_donation_forecast(
        self, db: Session, sim_date: date
    ) -> Dict[str, float]:
        """Retrieve per-group donation forecasts for sim_date from the DB."""
        records = (
            db.query(ForecastDonation)
            .filter(ForecastDonation.forecast_date == sim_date)
            .all()
        )
        return {r.blood_group: r.predicted_units for r in records}

    # ------------------------------------------------------------------
    # Step 4: Add donation batches
    # ------------------------------------------------------------------

    def _add_donation_batches(
        self,
        db: Session,
        sim_date: date,
        donation_by_group: Dict[str, float],
    ) -> Dict[str, int]:
        """
        Create one new AVAILABLE batch per blood group from today's donations.

        Each batch:
        - collection_date = sim_date
        - expiry_date     = sim_date + BLOOD_SHELF_LIFE_DAYS
        - units           = round(donation_by_group[group])
        - status          = AVAILABLE

        Returns
        -------
        dict[str, int]
            Integer units donated per group.
        """
        donated_by_group: Dict[str, int] = {}

        for group in BLOOD_GROUPS:
            raw_units = donation_by_group.get(group, 0.0)
            units = max(0, int(round(raw_units)))
            donated_by_group[group] = units

            if units == 0:
                logger.debug("Group %s: 0 donation units predicted; skipping batch.", group)
                continue

            batch = InventoryBatch(
                batch_id=str(uuid.uuid4()),
                blood_group=group,
                units=units,
                collection_date=sim_date,
                expiry_date=sim_date + timedelta(days=BLOOD_SHELF_LIFE_DAYS),
                status="AVAILABLE",
            )
            db.add(batch)

        logger.info("Donation batches added: %s", donated_by_group)
        return donated_by_group

    # ------------------------------------------------------------------
    # Step 5: FEFO consumption
    # ------------------------------------------------------------------

    def _consume_stock_fefo(
        self, db: Session, demand_by_group: Dict[str, int]
    ) -> tuple[Dict[str, int], Dict[str, int], bool]:
        """
        Consume blood units using FEFO (First Expire, First Out).

        For each group:
        - Fetch AVAILABLE batches ordered by expiry_date ASC.
        - Consume from the soonest-to-expire batch first.
        - A partially consumed batch has its units reduced in place.
        - A fully consumed batch is marked CONSUMED.

        Parameters
        ----------
        demand_by_group : dict[str, int]
            Units to consume per blood group.

        Returns
        -------
        tuple of:
          consumed_by_group : dict[str, int]  — units actually consumed
          unmet_demand      : dict[str, int]  — units not fulfilled (shortfall)
          demand_fulfilled  : bool             — True if all demand was met
        """
        consumed_by_group: Dict[str, int] = {g: 0 for g in BLOOD_GROUPS}
        unmet_demand: Dict[str, int] = {g: 0 for g in BLOOD_GROUPS}
        demand_fulfilled = True

        for group in BLOOD_GROUPS:
            needed = demand_by_group.get(group, 0)
            if needed <= 0:
                continue

            # FEFO: sort by earliest expiry first
            batches = (
                db.query(InventoryBatch)
                .filter(
                    InventoryBatch.blood_group == group,
                    InventoryBatch.status == "AVAILABLE",
                )
                .order_by(InventoryBatch.expiry_date.asc())
                .all()
            )

            remaining_demand = needed

            for batch in batches:
                if remaining_demand <= 0:
                    break

                if batch.units <= remaining_demand:
                    # Consume the entire batch
                    consumed_by_group[group] += batch.units
                    remaining_demand -= batch.units
                    batch.units = 0
                    batch.status = "CONSUMED"
                    logger.debug(
                        "Consumed batch %s (%s, all %d units)",
                        batch.batch_id, group, consumed_by_group[group],
                    )
                else:
                    # Partial consumption
                    batch.units -= remaining_demand
                    consumed_by_group[group] += remaining_demand
                    remaining_demand = 0
                    logger.debug(
                        "Partially consumed batch %s (%s, %d units remaining)",
                        batch.batch_id, group, batch.units,
                    )

            if remaining_demand > 0:
                unmet_demand[group] = remaining_demand
                demand_fulfilled = False
                logger.warning(
                    "Group %s: demand shortfall of %d units.", group, remaining_demand
                )

        return consumed_by_group, unmet_demand, demand_fulfilled

    # ------------------------------------------------------------------
    # Step 6: Projected stock
    # ------------------------------------------------------------------

    def _compute_projected_stock(self, db: Session) -> Dict[str, int]:
        """
        Query the DB for total AVAILABLE units per blood group after the simulation.

        Returns
        -------
        dict[str, int]
        """
        from sqlalchemy import func

        rows = (
            db.query(InventoryBatch.blood_group, func.sum(InventoryBatch.units))
            .filter(InventoryBatch.status == "AVAILABLE")
            .group_by(InventoryBatch.blood_group)
            .all()
        )

        stock = {g: 0 for g in BLOOD_GROUPS}
        for group, total in rows:
            if group in stock:
                stock[group] = int(total or 0)

        return stock
