from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ml.inference import predict_supply, predict_demand_by_type
from ml.train_demand import train as train_demand_model
from ml.train_supply import train as train_supply_model
from ml.backtest import run_backtest
from simulation.engine import run_simulation
import logging

app = FastAPI(title="BloodIQ AI Intelligence Engine")

# CORS to allow React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For dev only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "BloodIQ Intelligence Engine Running"}

@app.get("/api/forecast/demand")
def get_demand_forecast(days: int = 30):
    try:
        forecast = predict_demand_by_type(days)
        return {"status": "success", "data": forecast}
    except Exception as e:
        logging.error(f"Demand Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/forecast/supply")
def get_supply_forecast(days: int = 30):
    try:
        forecast = predict_supply(days)
        return {"status": "success", "data": forecast}
    except Exception as e:
        logging.error(f"Supply Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/simulate")
def simulate(days: int = 30):
    try:
        demand_by_type = predict_demand_by_type(days)
        supply_by_type = predict_supply(days)
        result = run_simulation(demand_by_type, supply_by_type, days)
        return {"status": "success", "data": result}
    except Exception as e:
        logging.error(f"Simulate Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/backtest")
def get_backtest():
    try:
        data = run_backtest()
        return {"status": "success", "data": data}
    except Exception as e:
        logging.error(f"Backtest Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/train/demand")
def trigger_demand_training():
    try:
        train_demand_model()
        return {"status": "success", "message": "Demand LightGBM model trained successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/train/supply")
def trigger_supply_training():
    try:
        train_supply_model()
        return {"status": "success", "message": "Supply Prophet models trained successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
