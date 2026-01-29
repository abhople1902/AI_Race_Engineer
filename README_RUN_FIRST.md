# Extractor Service – F1 Analytics

This microservice polls OpenF1 API on a hybrid schedule to extract real-time race data to further structure it and analyze it or passing it to an AI model.

---

## 🔧 Components

- Polls `intervals`, `laps`, `pit`, `positions` `race_control`, etc.
- Emits full snapshots:
  - Every 10 seconds
  - When leader finishes a lap
  - On pit stops, flags, or other race events
- Publishes to Pub/Sub topic `race_snapshots`

---

## 🐳 Running Locally (Docker)

1. Create `.env` file from template
2. Build & run:

```bash
docker-compose up --build
