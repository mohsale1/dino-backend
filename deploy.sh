#!/bin/bash
. .env.production.sh

echo "🚀 Deploying Dino Backend API to Cloud Run..."
gcloud run deploy dino-backend-prod \
  --image=us-central1-docker.pkg.dev/gcp-dino-prod/cloud-run-source-deploy/dino-backend/dino-backend-prod@sha256:00ccf641624b1b1992a63b183b95769bdf2ac4b197a9da1275e9c9da9d58c602 \
  --platform=managed \
  --no-allow-unauthenticated \
  --region=us-central1 \
  --project=gcp-dino-prod \
  --memory=1G \
  --cpu=1 \
  --concurrency=20 \
  --max-instances=2 \
  --min-instances=0 \
  --timeout=540s \
  --ingress=all \
  --port=8080 \
  --update-env-vars="ENVIRONMENT=production,GCP_PROJECT_ID=gcp-dino-prod,DATABASE_NAME=dino-prod,SECRET_KEY=Y8npVmKu/qrRjgl6hISI8d66FxFPjFYZAiax9WDpXh0=,CORS_ORIGINS=*,PYTHONUNBUFFERED=1"

echo "✅ Deployment completed!"