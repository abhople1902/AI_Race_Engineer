# Running main.py with Virtual Environment

## Quick Start (Using Script)

Simply run:
```bash
./run_local.sh
```

## Manual Setup

If you prefer to set it up manually:

### 1. Create and activate virtual environment

```bash
cd extractor-service
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Set environment variables (optional)

The app uses default values, but you can override them:

```bash
export MEETING_KEY=1273
export SESSION_KEY=9869
export POLL_INTERVAL_SEC=10
export PROJECT_ID=your-project-id
export PUBSUB_TOPIC=race_snapshots
```

Or create a `.env` file in the `extractor-service` directory:
```
MEETING_KEY=1273
SESSION_KEY=9869
POLL_INTERVAL_SEC=10
PROJECT_ID=your-project-id
PUBSUB_TOPIC=race_snapshots
```

### 4. Run the application

```bash
cd app
python main.py
```

Or from the extractor-service directory:
```bash
cd app && python main.py
```

## Notes

- The script runs from the `app` directory to ensure relative imports work correctly
- Press `Ctrl+C` to stop the application
- The application will poll OpenF1 API continuously based on `POLL_INTERVAL_SEC`

