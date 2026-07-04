"""
services/orchestrator.py
-------------------------
Wires together all backend components for the /simulate endpoint.

The Orchestrator is responsible for:
1. Ensuring models are trained (lazy train on first call).
2. Generating and persisting demand + donation forecasts.
3. Running the Inventory Simulation Engine.
4. Running the Decision Engine.
5. Returning a unified SimulationResponse.

Business logic (simulation, decisions) lives in their own modules.
This class only coordinates, not implements.
"""

import logging
from datetime import date, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from config.settings import BLOOD_GROUPS, FORECAST_HORIZON_DAYS
from database.db import RiskAlert
from decision_engine.engine import Alert, DecisionEngine
from forecasting.demand.demand_model import DemandForecaster
from forecasting.donation.donation_model import DonationForecaster
from inventory.inventory_generator import InventoryGenerator
from inventory_simulation.simulation_engine import SimulationEngine, SimulationResult
from models.schemas import AlertOut, SimulationResponse
from utils.helpers import (
    get_next_simulation_date,
    store_demand_forecasts,
    store_donation_forecasts,
)

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Central coordinator for the blood inventory forecasting pipeline.

    Instantiated once at application startup and held in app state.
    Thread safety: FastAPI runs handlers in an async event loop but
    model inference is CPU-bound and synchronous — acceptable for a
    single-server B.Tech deployment. For production scale, wrap in
    a background worker or process pool.
    """

    def __init__(self) -> None:
        self.demand_forecaster = DemandForecaster()
        self.donation_forecaster = DonationForecaster()
        self.simulation_engine = SimulationEngine()
        self.decision_engine = DecisionEngine()
        self._demand_metrics: Optional[Dict] = None
        self._donation_metrics: Optional[Dict] = None

    # ------------------------------------------------------------------
    # Model lifecycle
    # ------------------------------------------------------------------

    def initialize(self, db: Session) -> None:
        """
        Called at application startup.

        1. Seed inventory (idempotent).
        2. Attempt to load pre-trained models from disk.
        3. If models are missing, train them now.
        """
        logger.info("Orchestrator initialising...")

        # Seed inventory (no-op if already seeded)
        InventoryGenerator().run(db)

        # Try loading demand model
        if not self.demand_forecaster.load():
            logger.info("Demand model not found on disk. Training now...")
            self._demand_metrics = self.demand_forecaster.train()

        # Try loading donation models
        if not self.donation_forecaster.load():
            logger.info("Donation models not found on disk. Training now...")
            self._donation_metrics = self.donation_forecaster.train()

        logger.info("Orchestrator ready. Models loaded/trained.")

    def _ensure_models_trained(self) -> Optional[Dict]:
        """
        Guarantee models are trained before simulation.
        Returns training metrics if training was triggered; None otherwise.
        """
        metrics: Dict = {}
        trained_anything = False

        if not self.demand_forecaster.is_trained():
            logger.info("Lazily training demand model...")
            self._demand_metrics = self.demand_forecaster.train()
            metrics["demand"] = self._demand_metrics
            trained_anything = True

        if not self.donation_forecaster.is_trained():
            logger.info("Lazily training donation models...")
            self._donation_metrics = self.donation_forecaster.train()
            metrics["donation"] = self._donation_metrics
            trained_anything = True

        return metrics if trained_anything else None

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def run_simulation(self, db: Session) -> SimulationResponse:
        """
        Execute one full simulation day and return the result.

        Steps
        -----
        1. Ensure models are trained.
        2. Determine the next sim_date.
        3. Generate N-day forecasts (demand + donation) and persist to DB.
        4. Run the simulation engine for sim_date.
        5. Run the decision engine.
        6. Build and return SimulationResponse.

        Parameters
        ----------
        db : Active SQLAlchemy session.

        Returns
        -------
        SimulationResponse
        """
        # Step 1: ensure models ready
        training_metrics = self._ensure_models_trained()

        # Step 2: determine simulation date
        sim_date = get_next_simulation_date(db)
        logger.info("Running simulation for date: %s", sim_date)

        # Step 3: generate and persist forecasts
        demand_forecasts = self.demand_forecaster.predict_next_days(FORECAST_HORIZON_DAYS)
        donation_forecasts = self.donation_forecaster.predict_next_days(FORECAST_HORIZON_DAYS)

        # start_date = sim_date so index 0 aligns with the day we're simulating
        store_demand_forecasts(db, demand_forecasts, start_date=sim_date)
        store_donation_forecasts(db, donation_forecasts, start_date=sim_date)

        # Step 4: run simulation engine
        sim_result: SimulationResult = self.simulation_engine.run_simulation_day(
            db, sim_date
        )

        # Step 5: run decision engine
        # Extract single-day donation forecast for decision engine context
        donation_today: Dict[str, float] = {
            g: donation_forecasts[g][0] for g in BLOOD_GROUPS
        }
        alerts: List[Alert] = self.decision_engine.evaluate(
            db, sim_date, sim_result, donation_today
        )

        # Step 6: build response
        alert_outs = self._build_alert_outs(db, sim_date)

        return SimulationResponse(
            sim_date=sim_date,
            projected_stock=sim_result.projected_stock,
            consumed=sim_result.consumed,
            donated=sim_result.donated,
            expired=sim_result.expired,
            demand_fulfilled=sim_result.demand_fulfilled,
            unmet_demand=sim_result.unmet_demand,
            alerts_generated=len([a for a in alerts if a.risk_level != "LOW"]),
            alerts=alert_outs,
            model_metrics=training_metrics,
        )

    def _build_alert_outs(self, db: Session, alert_date: date) -> List[AlertOut]:
        """Fetch today's persisted alerts and convert to schema objects."""
        db_alerts = (
            db.query(RiskAlert)
            .filter(RiskAlert.alert_date == alert_date)
            .order_by(RiskAlert.risk_level.desc())
            .all()
        )
        return [AlertOut.model_validate(a) for a in db_alerts]
