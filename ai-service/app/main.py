from redis import Redis
from snapshot_builder import AISnapshotBuilder


redis = Redis(host="localhost", port=6379, decode_responses=True)
builder = AISnapshotBuilder(redis)
snapshot = builder.build_snapshot(
    session_id=9869,
    driver_numbers=[4, 30],
)
print(snapshot)
