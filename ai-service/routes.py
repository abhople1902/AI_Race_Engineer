import os
import traceback

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.ai_service import AIStrategyService
from app.strategy_engine import StrategyEngine


app = FastAPI(title="F1 Strategy AI")

REDIS_WRITER_BASE_URL = os.getenv(
    "REDIS_WRITER_BASE_URL",
    "http://localhost:8001",
)
MODEL_NAME = os.getenv(
    "MODEL_NAME",
    "mistralai/mistral-7b-instruct",
)
MODEL_TEMPERATURE = float(os.getenv("MODEL_TEMPERATURE", "0.2"))

engine = StrategyEngine(
    model_name=MODEL_NAME,
    temperature=MODEL_TEMPERATURE,
)

service = AIStrategyService(REDIS_WRITER_BASE_URL, engine)


class PredictionRequest(BaseModel):
    session_id: int
    drivers: list[int]
    simulation_id: Optional[str] = None


@app.post("/predict")
def predict(req: PredictionRequest):
    if len(req.drivers) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least two drivers must be provided",
        )

    try:
        result = service.predict(
            session_id=req.session_id,
            driver_numbers=req.drivers,
            simulation_id=req.simulation_id,
        )
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )
