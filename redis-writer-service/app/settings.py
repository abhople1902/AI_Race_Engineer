import os

KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "kafka:9092"
)

OPENF1_BASE_URL = "https://api.openf1.org/v1/"

LEADERBOARD_TOPIC = os.getenv(
    "LEADERBOARD_TOPIC",
    "f1.leaderboard.events"
)

RACE_CONTROL_TOPIC = os.getenv(
    "RACE_CONTROL_TOPIC",
    "f1.race_control.raw"
)

KAFKA_API_KEY = os.getenv("KAFKA_API_KEY")
KAFKA_API_SECRET = os.getenv("KAFKA_API_SECRET")

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
