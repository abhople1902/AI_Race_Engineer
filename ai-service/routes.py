from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from redis import Redis

from app.ai_service import AIStrategyService
from app.strategy_engine import StrategyEngine


app = FastAPI(title="F1 Strategy AI")

redis = Redis(host="localhost", port=6379, decode_responses=True)

engine = StrategyEngine(
    model_name="mistralai/mistral-7b-instruct",
    temperature=0.2,
)

service = AIStrategyService(redis, engine)


class PredictionRequest(BaseModel):
    session_id: int
    drivers: list[int]


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
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )
