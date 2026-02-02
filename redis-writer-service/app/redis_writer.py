class RedisWriter:
    def __init__(self, redis_client):
        self.redis = redis_client

    def write_leaderboard(self, event: dict):
        session_id = event.get("session_key")
        if session_id is None:
            raise ValueError("Leaderboard event missing session_key")

        leaderboard_key = f"session:{session_id}:leaderboard"
        meta_key = f"session:{session_id}:meta"

        pipe = self.redis.pipeline(transaction=True)

        for entry in event["standings"]:
            driver_number = str(entry["driver_number"])

            pipe.zadd(
                leaderboard_key,
                {driver_number: entry["position"]}
            )

            driver_key = f"session:{session_id}:driver:{driver_number}"
            pipe.hset(
                driver_key,
                mapping={
                    "position": entry["position"],
                    "gap_to_leader": entry["gap_to_leader"],
                    "lap_number": event["lap_number"],
                    "status": "RUNNING",
                    "updated_at": event["event_time"],
                }
            )

        pipe.hset(
            meta_key,
            mapping={
                "lap": event["lap_number"],
                "leader_driver_number": event["leader_driver_number"],
                "last_event_ts": event["event_time"],
                "cars_running": len(event["standings"]),
            }
        )

        pipe.execute()
