"""
Risk Classification Engine
============================
Member 3 -- Digital Twin Lead

Classifies shortage and wastage risk levels for each blood product
based on the FEFO simulation state and the demand forecast.

Risk levels:
    HIGH   -- Immediate action required
    MEDIUM -- Monitor closely; preventive action needed
    LOW    -- Within safe thresholds, no alert generated

This module is consumed by:
    - run_twin.py (local simulation)
    - member_4_fullstack/api/ (FastAPI response body)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Dict, List

logger = logging.getLogger(__name__)

# Safety stock thresholds (units) -- align with simulation/fefo_engine.py
SAFETY_STOCK: dict[str, float] = {
    "Packed Red Blood Cells": 60.0,
    "Fresh Frozen Plasma":    30.0,
    "Platelets":              15.0,
    "Cryoprecipitate":         5.0,
}

WASTAGE_WINDOW_DAYS: int = 3   # flag batches expiring within this many days


@dataclass
class RiskAlert:
    """A single risk event for one blood product on one simulation day."""
    date:           date
    product:        str
    alert_type:     str   # "SHORTAGE" | "WASTAGE"
    risk_level:     str   # "HIGH" | "MEDIUM" | "LOW"
    message:        str
    recommendation: str


class RiskEngine:
    """
    Evaluates post-simulation inventory state and emits RiskAlert objects.

    Inputs:
        current_stock   -- Dict[product, units_available]
        expiring_soon   -- Dict[product, units_expiring_within_3_days]
        forecast_demand -- Dict[product, predicted_units_tomorrow]

    Output:
        List[RiskAlert] -- only MEDIUM and HIGH alerts returned
    """

    def evaluate(
        self,
        sim_date: date,
        current_stock:   Dict[str, float],
        expiring_soon:   Dict[str, float],
        forecast_demand: Dict[str, float],
    ) -> List[RiskAlert]:
        alerts: List[RiskAlert] = []

        for product, safety in SAFETY_STOCK.items():
            stock    = current_stock.get(product, 0.0)
            expiring = expiring_soon.get(product, 0.0)
            demand   = forecast_demand.get(product, 0.0)

            shortage_alert = self._shortage(sim_date, product, stock, safety)
            if shortage_alert.risk_level != "LOW":
                alerts.append(shortage_alert)

            wastage_alert = self._wastage(sim_date, product, stock, expiring, demand)
            if wastage_alert.risk_level != "LOW":
                alerts.append(wastage_alert)

        logger.info(
            "%s -- %d alert(s) raised (%d HIGH, %d MEDIUM)",
            sim_date,
            len(alerts),
            sum(1 for a in alerts if a.risk_level == "HIGH"),
            sum(1 for a in alerts if a.risk_level == "MEDIUM"),
        )
        return alerts

    # ------------------------------------------------------------------
    # Shortage logic
    # ------------------------------------------------------------------

    def _shortage(
        self, sim_date: date, product: str, stock: float, safety: float
    ) -> RiskAlert:
        half = safety / 2

        if stock < half:
            level = "HIGH"
            msg  = (
                f"{product}: critically low at {stock:.1f} units "
                f"(safety threshold: {safety:.0f})."
            )
            rec  = (
                f"URGENT -- contact regional blood bank for emergency transfer. "
                f"Minimum {safety - stock:.0f} units needed within 24 hours."
            )
        elif stock < safety:
            shortfall = safety - stock
            level = "MEDIUM"
            msg  = (
                f"{product}: below safety stock ({stock:.1f}/{safety:.0f} units). "
                f"Shortfall: {shortfall:.1f} units."
            )
            rec  = (
                f"Schedule donation campaign within 5 days. "
                f"Consider procuring {shortfall:.0f} units from partner facility."
            )
        else:
            level = "LOW"
            msg  = f"{product}: stock {stock:.1f} units -- within safe range."
            rec  = "No action required."

        return RiskAlert(
            date=sim_date, product=product, alert_type="SHORTAGE",
            risk_level=level, message=msg, recommendation=rec,
        )

    # ------------------------------------------------------------------
    # Wastage logic
    # ------------------------------------------------------------------

    def _wastage(
        self,
        sim_date: date,
        product: str,
        stock: float,
        expiring: float,
        incoming_demand: float,
    ) -> RiskAlert:
        if expiring <= 0:
            return RiskAlert(
                date=sim_date, product=product, alert_type="WASTAGE",
                risk_level="LOW",
                message=f"{product}: no near-expiry stock.",
                recommendation="No action required.",
            )

        ratio = expiring / max(stock, 1.0)   # proportion of stock about to expire

        if ratio > 0.5 and incoming_demand < expiring:
            level = "HIGH"
            msg  = (
                f"{product}: {expiring:.1f} units expiring within {WASTAGE_WINDOW_DAYS} days "
                f"({ratio*100:.0f}% of total stock). Forecast demand ({incoming_demand:.1f}) "
                f"insufficient to consume near-expiry units."
            )
            rec  = (
                f"Prescriptive action: transfer {expiring - incoming_demand:.0f} units "
                f"of {product} to a partner hospital immediately. "
                f"Prioritise FEFO transfusions for all elective procedures today."
            )
        elif ratio > 0.25:
            level = "MEDIUM"
            msg  = (
                f"{product}: {expiring:.1f} units expiring within {WASTAGE_WINDOW_DAYS} days "
                f"({ratio*100:.0f}% of total stock). Moderate wastage risk."
            )
            rec  = (
                f"Review {product} transfusion schedule -- prioritise near-expiry batches. "
                f"Notify clinicians to prefer {product} in upcoming elective procedures."
            )
        else:
            level = "LOW"
            msg  = f"{product}: wastage risk low ({expiring:.1f} near-expiry units)."
            rec  = "No action required."

        return RiskAlert(
            date=sim_date, product=product, alert_type="WASTAGE",
            risk_level=level, message=msg, recommendation=rec,
        )
