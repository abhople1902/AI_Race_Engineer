#!/bin/bash
# Deployment script for Google Cloud Run

set -e

PROJECT_ID=${1:-"your-project-id"}
REGION=${2:-"us-central1"}
SERVICE_NAME="f1-extractor"

echo "Building and deploying $SERVICE_NAME to Cloud Run..."

# Build and push image
echo "Building Docker image..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi \
  --timeout 300 \
  --set-env-vars "F1_YEAR_PREFERRED=2025,F1_EVENT=Mexico,F1_SESSION=R,FASTF1_CACHE=/tmp/f1_cache"

echo "Deployment complete!"
echo "Service URL: $(gcloud run services describe $SERVICE_NAME --format='value(status.url)' --region $REGION)"

