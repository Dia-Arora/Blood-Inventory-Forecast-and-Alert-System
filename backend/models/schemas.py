"""
models/schemas.py
-----------------
Pydantic v2 response models for all FastAPI endpoints.

These schemas define the exact JSON shape returned to API clients.
They are separate from the SQLAlchemy ORM models in database/db.py.
"""

from datetime import date, datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

class InventoryBatchOut(BaseModel):
    """A single blood batch as returned by GET /inventory."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    batch_id: str
    blood_group: str
    units: int
    collection_date: date
    expiry_date: date
    status: str


class InventoryResponse(BaseModel):
    """Response wrapper for GET /inventory."""

    total_batches: int
    stock_summary: Dict[str, int] = Field(
        description="Total available units per blood group."
    )
    batches: List[InventoryBatchOut]


# ---------------------------------------------------------------------------
# Demand forecast
# ---------------------------------------------------------------------------

class DemandForecastItem(BaseModel):
    """One day of demand prediction."""

    model_config = ConfigDict(from_attributes=True)

    forecast_date: date
    predicted_units: float
    created_at: datetime


class DemandForecastResponse(BaseModel):
    """Response wrapper for GET /forecast/demand."""

    days_returned: int
    forecasts: List[DemandForecastItem]


# ---------------------------------------------------------------------------
# Donation forecast
# ---------------------------------------------------------------------------

class DonationForecastItem(BaseModel):
    """One (date, blood_group) donation prediction."""

    model_config = ConfigDict(from_attributes=True)

    forecast_date: date
    blood_group: str
    predicted_units: float
    created_at: datetime


class DonationForecastResponse(BaseModel):
    """Response wrapper for GET /forecast/donation."""

    days_returned: int
    blood_group_filter: Optional[str]
    forecasts: List[DonationForecastItem]


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

class AlertOut(BaseModel):
    """A single risk alert as returned by GET /alerts."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    alert_date: date
    blood_group: str
    alert_type: str
    risk_level: str
    message: str
    recommendation: str
    created_at: datetime


class AlertsResponse(BaseModel):
    """Response wrapper for GET /alerts."""

    total_alerts: int
    alerts: List[AlertOut]


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

class SimulationResponse(BaseModel):
    """Response returned by POST /simulate."""

    sim_date: date = Field(description="The date that was simulated.")
    projected_stock: Dict[str, int] = Field(
        description="AVAILABLE units per blood group after simulation."
    )
    consumed: Dict[str, int] = Field(
        description="Units consumed per group to meet demand."
    )
    donated: Dict[str, int] = Field(
        description="Units added per group from today's donations."
    )
    expired: Dict[str, int] = Field(
        description="Units lost per group due to expiry."
    )
    demand_fulfilled: bool = Field(
        description="Whether all predicted demand could be met from stock."
    )
    unmet_demand: Dict[str, int] = Field(
        description="Units of demand not met due to insufficient stock."
    )
    alerts_generated: int = Field(
        description="Number of MEDIUM/HIGH risk alerts generated."
    )
    alerts: List[AlertOut] = Field(
        description="Alerts generated during this simulation step."
    )
    model_metrics: Optional[Dict] = Field(
        default=None,
        description="Training metrics if models were trained during this call."
    )
