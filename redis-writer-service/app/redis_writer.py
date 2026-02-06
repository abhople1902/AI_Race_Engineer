class RedisWriter:
    def __init__(self, redis_client):
        self.redis = redis_client

    
    def write_stint_state(
        self,
        session_id: int,
        driver_number: int,
        stint: dict,
        lap_number: int,
    ):
        key = f"session:{session_id}:driver:{driver_number}:stint"

        self.redis.hset(
            key,
            mapping={
                "stint_number": stint["stint_number"],
                "compound": stint["compound"],
                "stint_lap_start": stint["lap_start"],
                "last_pit_lap": stint["lap_start"] - 1,
                "tyre_age_at_start": stint["tyre_age_at_start"],
            }
        )


    def write_leaderboard(self, event: dict):
        session_id = event.get("session_key")
        if session_id is None:
            raise ValueError("Leaderboard event missing session_key")

        leaderboard_key = f"session:{session_id}:leaderboard"
        meta_key = f"session:{session_id}:meta"

        active_drivers = {
            str(entry["driver_number"])
            for entry in event["standings"]
        }

        pipe = self.redis.pipeline(transaction=True)


        # Handling retired drivers
        existing_drivers = self.redis.zrange(leaderboard_key, 0, -1)
        retired_drivers = set(existing_drivers) - active_drivers

        if retired_drivers:
            pipe.zrem(leaderboard_key, *retired_drivers)

            for driver in retired_drivers:
                pipe.hset(
                    f"session:{session_id}:driver:{driver}",
                    mapping={
                        "status": "RETIRED",
                        "updated_at": event["event_time"],
                    }
                )


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
                    "interval_to_ahead": entry["interval"],
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
