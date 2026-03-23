#!/bin/bash

# Dino Backend Deployment Script for Google Cloud Run
# This script deploys the backend to Cloud Run using Application Default Credentials

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVICE_NAME="${SERVICE_NAME:-dino-system}"
REGION="${REGION:-us-central1}"
PROJECT_ID="${PROJECT_ID:-edl-idaas-ddev-platform-daad}"
MEMORY="${MEMORY:-512Mi}"
CPU="${CPU:-1}"
MAX_INSTANCES="${MAX_INSTANCES:-10}"
MIN_INSTANCES="${MIN_INSTANCES:-0}"
CONCURRENCY="${CONCURRENCY:-80}"
TIMEOUT="${TIMEOUT:-300}"
ALLOW_UNAUTHENTICATED="${ALLOW_UNAUTHENTICATED:-false}"
DATABASE_NAME="${DATABASE_NAME:-job-manager-jm9}"

# Prepare environment variables
ENV_VARS="DEBUG=False,ENVIRONMENT=production,PROJECT_ID=${PROJECT_ID},DATABASE_NAME=${DATABASE_NAME}"


# Deploy command
  gcloud run deploy ${SERVICE_NAME} \
  --image us-central1-docker.pkg.dev/edl-idaas-ddev-platform-daad/job-manager-artifacts/job-manager-api-wiz2 \
  --platform managed \
  --service-account svc-ddev-idaas-data-munge@edl-idaas-ddev-platform-daad.iam.gserviceaccount.com \
  --no-allow-unauthenticated \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --memory 2G \
  --cpu 1 \
  --concurrency 20 \
  --max-instances 40 \
  --timeout 900 \
  --ingress all \
  --set-env-vars "${ENV_VARS}"