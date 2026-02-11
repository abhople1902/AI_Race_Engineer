from redis import Redis
from snapshot_builder import AISnapshotBuilder
from strategy_engine import StrategyEngine
import json

# Redis
redis = Redis(host="localhost", port=6379, decode_responses=True)

# Build snapshot
builder = AISnapshotBuilder(redis)
drivers = [1, 12]

snapshot = builder.build_snapshot(
    session_id=9869,
    driver_numbers=drivers,
)

# Strategy engine (OpenRouter model)
engine = StrategyEngine(
    model_name="mistralai/mistral-7b-instruct",
    temperature=0.2,
)

# Predict
result = engine.predict(
    snapshot=snapshot,
    driver_numbers=drivers,
)

print(json.dumps(result, indent=2))
