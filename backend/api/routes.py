"""
api/routes.py
-------------
FastAPI route definitions for all 5 endpoints.

Endpoints
---------
GET  /inventory            — Current inventory with stock summary.
GET  /forecast/demand      — Latest demand forecasts from DB.
GET  /forecast/donation    — Latest donation forecasts from DB (per group).
POST /simulate             — Run one simulation day.
GET  /alerts               — Latest risk alerts with optional filtering.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from config.settings import BLOOD_GROUPS
from database.db import (
    ForecastDemand,
    ForecastDonation,
    InventoryBatch,
    RiskAlert,
    get_db,
)
from models.schemas import (
    AlertOut,
    AlertsResponse,
    DemandForecastItem,
    DemandForecastResponse,
    DonationForecastItem,
    DonationForecastResponse,
    InventoryBatchOut,
    InventoryResponse,
    SimulationResponse,
)
from utils.helpers import get_stock_summary

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# GET /inventory
# ---------------------------------------------------------------------------

@router.get(
    "/inventory",
    response_model=InventoryResponse,
    summary="Get current blood inventory",
    description=(
        "Returns all inventory batches with optional filtering by blood group "
        "or status. Includes a stock summary (total AVAILABLE units per group)."
    ),
)
def get_inventory(
    blood_group: Optional[str] = Query(
        default=None,
        description=f"Filter by blood group. One of: {BLOOD_GROUPS}",
    ),
    status: Optional[str] = Query(
        default=None,
        description="Filter by batch status: AVAILABLE, CONSUMED, EXPIRED.",
    ),
    db: Session = Depends(get_db),
):
    # Validate blood_group filter
    if blood_group and blood_group.upper() not in BLOOD_GROUPS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid blood_group '{blood_group}'. Must be one of {BLOOD_GROUPS}.",
        )

    query = db.query(InventoryBatch)

    if blood_group:
        query = query.filter(InventoryBatch.blood_group == blood_group.upper())

    if status:
        status_upper = status.upper()
        if status_upper not in ("AVAILABLE", "CONSUMED", "EXPIRED"):
            raise HTTPException(
                status_code=400,
                detail="Invalid status. Must be AVAILABLE, CONSUMED, or EXPIRED.",
            )
        query = query.filter(InventoryBatch.status == status_upper)

    batches = query.order_by(
        InventoryBatch.blood_group,
        InventoryBatch.expiry_date.asc(),
    ).all()

    stock_summary = get_stock_summary(db)

    return InventoryResponse(
        total_batches=len(batches),
        stock_summary=stock_summary,
        batches=[InventoryBatchOut.model_validate(b) for b in batches],
    )


# ---------------------------------------------------------------------------
# GET /forecast/demand
# ---------------------------------------------------------------------------

@router.get(
    "/forecast/demand",
    response_model=DemandForecastResponse,
    summary="Get latest blood demand forecast",
    description="Returns the most recent XGBoost demand predictions stored in the DB.",
)
def get_demand_forecast(
    days: int = Query(
        default=7,
        ge=1,
        le=90,
        description="Number of forecast days to return.",
    ),
    db: Session = Depends(get_db),
):
    records = (
        db.query(ForecastDemand)
        .order_by(ForecastDemand.forecast_date.asc())
        .limit(days)
        .all()
    )

    if not records:
        raise HTTPException(
            status_code=404,
            detail="No demand forecasts found. Run POST /simulate first.",
        )

    return DemandForecastResponse(
        days_returned=len(records),
        forecasts=[DemandForecastItem.model_validate(r) for r in records],
    )


# ---------------------------------------------------------------------------
# GET /forecast/donation
# ---------------------------------------------------------------------------

@router.get(
    "/forecast/donation",
    response_model=DonationForecastResponse,
    summary="Get latest blood donation forecast",
    description=(
        "Returns Prophet donation forecasts per blood group. "
        "Optionally filter by a single blood group."
    ),
)
def get_donation_forecast(
    days: int = Query(
        default=7,
        ge=1,
        le=90,
        description="Number of forecast days to return per group.",
    ),
    blood_group: Optional[str] = Query(
        default=None,
        description=f"Filter by blood group. One of: {BLOOD_GROUPS}",
    ),
    db: Session = Depends(get_db),
):
    if blood_group and blood_group.upper() not in BLOOD_GROUPS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid blood_group '{blood_group}'. Must be one of {BLOOD_GROUPS}.",
        )

    query = db.query(ForecastDonation)

    if blood_group:
        query = query.filter(ForecastDonation.blood_group == blood_group.upper())

    records = (
        query
        .order_by(
            ForecastDonation.forecast_date.asc(),
            ForecastDonation.blood_group.asc(),
        )
        .limit(days * len(BLOOD_GROUPS) if not blood_group else days)
        .all()
    )

    if not records:
        raise HTTPException(
            status_code=404,
            detail="No donation forecasts found. Run POST /simulate first.",
        )

    return DonationForecastResponse(
        days_returned=len(records),
        blood_group_filter=blood_group.upper() if blood_group else None,
        forecasts=[DonationForecastItem.model_validate(r) for r in records],
    )


# ---------------------------------------------------------------------------
# POST /simulate
# ---------------------------------------------------------------------------

@router.post(
    "/simulate",
    response_model=SimulationResponse,
    summary="Run one simulation day",
    description=(
        "Advances the simulation by one day. On the first call, ML models are "
        "trained if not already present. Returns updated inventory state and alerts."
    ),
)
def run_simulation(
    request: "Request",
    db: Session = Depends(get_db),
):
    orchestrator = request.app.state.orchestrator
    try:
        result = orchestrator.run_simulation(db)
    except Exception as exc:
        logger.exception("Simulation failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Simulation error: {exc}") from exc

    return result


# ---------------------------------------------------------------------------
# GET /alerts
# ---------------------------------------------------------------------------

@router.get(
    "/alerts",
    response_model=AlertsResponse,
    summary="Get latest risk alerts",
    description=(
        "Returns shortage and wastage alerts generated by the Decision Engine. "
        "Optionally filter by risk_level or blood_group."
    ),
)
def get_alerts(
    risk_level: Optional[str] = Query(
        default=None,
        description="Filter by risk level: LOW, MEDIUM, HIGH.",
    ),
    blood_group: Optional[str] = Query(
        default=None,
        description=f"Filter by blood group. One of: {BLOOD_GROUPS}",
    ),
    alert_type: Optional[str] = Query(
        default=None,
        description="Filter by type: SHORTAGE or WASTAGE.",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of alerts to return.",
    ),
    db: Session = Depends(get_db),
):
    # Validate filters
    if risk_level and risk_level.upper() not in ("LOW", "MEDIUM", "HIGH"):
        raise HTTPException(
            status_code=400,
            detail="Invalid risk_level. Must be LOW, MEDIUM, or HIGH.",
        )
    if blood_group and blood_group.upper() not in BLOOD_GROUPS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid blood_group '{blood_group}'. Must be one of {BLOOD_GROUPS}.",
        )
    if alert_type and alert_type.upper() not in ("SHORTAGE", "WASTAGE"):
        raise HTTPException(
            status_code=400,
            detail="Invalid alert_type. Must be SHORTAGE or WASTAGE.",
        )

    query = db.query(RiskAlert)

    if risk_level:
        query = query.filter(RiskAlert.risk_level == risk_level.upper())
    if blood_group:
        query = query.filter(RiskAlert.blood_group == blood_group.upper())
    if alert_type:
        query = query.filter(RiskAlert.alert_type == alert_type.upper())

    alerts = (
        query
        .order_by(RiskAlert.alert_date.desc(), RiskAlert.risk_level.desc())
        .limit(limit)
        .all()
    )

    return AlertsResponse(
        total_alerts=len(alerts),
        alerts=[AlertOut.model_validate(a) for a in alerts],
    )
