from redis import Redis
from app.snapshot_builder import AISnapshotBuilder
from app.strategy_engine import StrategyEngine


class AIStrategyService:
    def __init__(self, redis: Redis, engine: StrategyEngine):
        self.redis = redis
        self.snapshot_builder = AISnapshotBuilder(redis)
        self.engine = engine

    def predict(
        self,
        session_id: int,
        driver_numbers: list[int],
        simulation_id: str | None = None,
    ) -> dict:
        snapshot = self.snapshot_builder.build_snapshot(
            session_id=session_id,
            driver_numbers=driver_numbers,
            simulation_id=simulation_id,
        )

        result = self.engine.predict(
            snapshot=snapshot,
            driver_numbers=driver_numbers,
        )

        return result
