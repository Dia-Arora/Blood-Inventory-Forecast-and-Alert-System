"""
utils/helpers.py
----------------
Reusable utility functions used across the backend.
"""

import logging
from datetime import date, timedelta
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from config.settings import BLOOD_GROUPS
from database.db import ForecastDemand, ForecastDonation, InventoryBatch


logger = logging.getLogger(__name__)


def setup_logging(level: int = logging.INFO) -> None:
    """
    Configure root logger with a consistent format.
    Call once at application startup (in main.py).
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_stock_summary(db: Session) -> Dict[str, int]:
    """
    Return total AVAILABLE units per blood group from the DB.

    Parameters
    ----------
    db : SQLAlchemy Session

    Returns
    -------
    dict[str, int]
        {"A": 120, "B": 80, "AB": 30, "O": 150}
    """
    rows = (
        db.query(InventoryBatch.blood_group, func.sum(InventoryBatch.units))
        .filter(InventoryBatch.status == "AVAILABLE")
        .group_by(InventoryBatch.blood_group)
        .all()
    )
    summary = {g: 0 for g in BLOOD_GROUPS}
    for group, total in rows:
        if group in summary:
            summary[group] = int(total or 0)
    return summary


def get_next_simulation_date(db: Session) -> date:
    """
    Determine the next date to simulate.

    Logic:
    - If forecast_demand table has records, return max(forecast_date) + 1 day.
    - Otherwise return today.

    This ensures simulations advance sequentially without gaps.
    """
    max_date = db.query(func.max(ForecastDemand.forecast_date)).scalar()
    if max_date is None:
        return date.today()
    # Convert to date if needed (SQLite may return string)
    if isinstance(max_date, str):
        from datetime import datetime as dt
        max_date = dt.strptime(max_date, "%Y-%m-%d").date()
    return max_date + timedelta(days=1)


def store_demand_forecasts(
    db: Session,
    forecasts: List[float],
    start_date: Optional[date] = None,
) -> int:
    """
    Persist XGBoost demand predictions to the forecast_demand table.

    If a record already exists for a given date, it is overwritten
    (delete-then-insert) to keep data fresh.

    Parameters
    ----------
    db        : SQLAlchemy Session.
    forecasts : List of predicted demand values (one per day, starting tomorrow).
    start_date: First forecast date. Defaults to tomorrow.

    Returns
    -------
    int
        Number of records inserted.
    """
    from datetime import datetime
    if start_date is None:
        start_date = date.today() + timedelta(days=1)

    forecast_dates = [start_date + timedelta(days=i) for i in range(len(forecasts))]

    # Remove any existing forecasts for these dates to avoid stale duplicates
    db.query(ForecastDemand).filter(
        ForecastDemand.forecast_date.in_(forecast_dates)
    ).delete(synchronize_session=False)

    records = [
        ForecastDemand(
            forecast_date=d,
            predicted_units=max(0.0, float(v)),
            created_at=datetime.utcnow(),
        )
        for d, v in zip(forecast_dates, forecasts)
    ]
    db.bulk_save_objects(records)
    db.commit()

    logger.info(
        "Stored %d demand forecast records (%s → %s).",
        len(records),
        forecast_dates[0],
        forecast_dates[-1],
    )
    return len(records)


def store_donation_forecasts(
    db: Session,
    forecasts_by_group: Dict[str, List[float]],
    start_date: Optional[date] = None,
) -> int:
    """
    Persist Prophet donation predictions to the forecast_donations table.

    Parameters
    ----------
    db                : SQLAlchemy Session.
    forecasts_by_group: dict[group, list[float]] — one list per blood group.
    start_date        : First forecast date. Defaults to tomorrow.

    Returns
    -------
    int
        Number of records inserted.
    """
    from datetime import datetime
    if start_date is None:
        start_date = date.today() + timedelta(days=1)

    n = max(len(v) for v in forecasts_by_group.values())
    forecast_dates = [start_date + timedelta(days=i) for i in range(n)]

    # Remove existing forecasts for these dates + groups
    db.query(ForecastDonation).filter(
        ForecastDonation.forecast_date.in_(forecast_dates)
    ).delete(synchronize_session=False)

    records = []
    for group, values in forecasts_by_group.items():
        if group not in BLOOD_GROUPS:
            continue
        for d, v in zip(forecast_dates, values):
            records.append(
                ForecastDonation(
                    forecast_date=d,
                    blood_group=group,
                    predicted_units=max(0.0, float(v)),
                    created_at=datetime.utcnow(),
                )
            )

    db.bulk_save_objects(records)
    db.commit()

    logger.info(
        "Stored %d donation forecast records across %d groups.",
        len(records), len(forecasts_by_group),
    )
    return len(records)
