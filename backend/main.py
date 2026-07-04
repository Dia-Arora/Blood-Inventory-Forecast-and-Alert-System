"""
main.py
-------
FastAPI application entry point for the Blood Inventory Forecasting System.

Startup sequence
----------------
1. Configure logging.
2. Create database tables (idempotent).
3. Instantiate the Orchestrator and attach to app.state.
4. Run InventoryGenerator + model loading/training via Orchestrator.initialize().

Running the server
------------------
From the `backend/` directory:

    uvicorn main:app --reload --port 8000

API documentation is available at:
    http://localhost:8000/docs      (Swagger UI)
    http://localhost:8000/redoc     (ReDoc)
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from database.db import SessionLocal, init_db
from services.orchestrator import Orchestrator
from utils.helpers import setup_logging

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    On startup:
      - Initialise DB schema.
      - Create and initialise the Orchestrator (seeds inventory, loads/trains models).

    On shutdown:
      - Log clean exit.
    """
    logger.info("=" * 60)
    logger.info("Blood Inventory Forecasting System — starting up")
    logger.info("=" * 60)

    # 1. Initialise DB schema
    init_db()

    # 2. Create Orchestrator and store in app state (accessible via request.app.state)
    orchestrator = Orchestrator()
    app.state.orchestrator = orchestrator

    # 3. Seed inventory + load/train models
    db = SessionLocal()
    try:
        orchestrator.initialize(db)
    finally:
        db.close()

    logger.info("Startup complete. API is ready.")
    logger.info("Swagger UI: http://localhost:8000/docs")

    yield

    # Shutdown
    logger.info("Blood Inventory Forecasting System — shutting down.")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AI-Based Blood Inventory Forecasting & Shortage Alert System",
    description=(
        "A production-quality backend that combines XGBoost demand forecasting, "
        "Facebook Prophet donation forecasting, deterministic inventory simulation "
        "(FEFO), and rule-based shortage/wastage alert generation.\n\n"
        "**Blood groups supported:** A, B, AB, O\n\n"
        "**POST /simulate** to run one simulation day and generate alerts."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS (permissive for development; restrict origins in production)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
app.include_router(router, prefix="")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["System"], summary="Health check")
def health_check():
    """Simple liveness probe. Returns 200 if the server is running."""
    return {"status": "ok", "system": "Blood Inventory Forecasting System"}


# ---------------------------------------------------------------------------
# Development entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
