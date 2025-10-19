#!/bin/bash

# Production Deployment Script for Dino Backend
# This script validates configuration and deploys to Cloud Run

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=${1:-""}
SECRET_KEY=${2:-""}
FRONTEND_URL=${3:-""}

echo -e "${BLUE}🚀 Dino Backend Production Deployment${NC}"
echo "=================================================="

# Validate inputs
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}❌ Error: PROJECT_ID is required${NC}"
    echo "Usage: $0 <PROJECT_ID> [SECRET_KEY] [FRONTEND_URL]"
    echo "Example: $0 my-gcp-project-id"
    exit 1
fi

echo -e "${GREEN}✅ Project ID: $PROJECT_ID${NC}"

# Generate SECRET_KEY if not provided
if [ -z "$SECRET_KEY" ]; then
    echo -e "${YELLOW}⚠️ No SECRET_KEY provided, generating secure key...${NC}"
    SECRET_KEY=$(openssl rand -base64 48 | tr -d "=+/" | cut -c1-32)
    echo -e "${GREEN}✅ Generated SECRET_KEY (length: ${#SECRET_KEY})${NC}"
else
    echo -e "${GREEN}✅ Using provided SECRET_KEY (length: ${#SECRET_KEY})${NC}"
    
    # Validate SECRET_KEY length
    if [ ${#SECRET_KEY} -lt 32 ]; then
        echo -e "${RED}❌ Error: SECRET_KEY must be at least 32 characters long${NC}"
        exit 1
    fi
fi

# Set default FRONTEND_URL if not provided
if [ -z "$FRONTEND_URL" ]; then
    FRONTEND_URL="https://dino-frontend-$PROJECT_ID.us-central1.run.app"
    echo -e "${YELLOW}⚠️ No FRONTEND_URL provided, using default: $FRONTEND_URL${NC}"
else
    echo -e "${GREEN}✅ Using provided FRONTEND_URL: $FRONTEND_URL${NC}"
fi

# Validate GCP authentication
echo -e "${BLUE}🔐 Validating GCP authentication...${NC}"
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${RED}❌ Error: No active GCP authentication found${NC}"
    echo "Please run: gcloud auth login"
    exit 1
fi

ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
echo -e "${GREEN}✅ Authenticated as: $ACTIVE_ACCOUNT${NC}"

# Set project
echo -e "${BLUE}🔧 Setting GCP project...${NC}"
gcloud config set project $PROJECT_ID

# Validate project exists
if ! gcloud projects describe $PROJECT_ID >/dev/null 2>&1; then
    echo -e "${RED}❌ Error: Project $PROJECT_ID not found or no access${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Project $PROJECT_ID is accessible${NC}"

# Check required APIs
echo -e "${BLUE}🔍 Checking required APIs...${NC}"
REQUIRED_APIS=(
    "cloudbuild.googleapis.com"
    "run.googleapis.com"
    "artifactregistry.googleapis.com"
    "firestore.googleapis.com"
    "storage.googleapis.com"
)

for api in "${REQUIRED_APIS[@]}"; do
    if gcloud services list --enabled --filter="name:$api" --format="value(name)" | grep -q "$api"; then
        echo -e "${GREEN}✅ $api is enabled${NC}"
    else
        echo -e "${YELLOW}⚠️ Enabling $api...${NC}"
        gcloud services enable $api
    fi
done

# Check if Artifact Registry repository exists
echo -e "${BLUE}🏗️ Checking Artifact Registry...${NC}"
REPO_NAME="dino-repo"
REGION="us-central1"

if ! gcloud artifacts repositories describe $REPO_NAME --location=$REGION >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️ Creating Artifact Registry repository...${NC}"
    gcloud artifacts repositories create $REPO_NAME \
        --repository-format=docker \
        --location=$REGION \
        --description="Dino Backend Docker Repository"
else
    echo -e "${GREEN}✅ Artifact Registry repository exists${NC}"
fi

# Check service account
echo -e "${BLUE}👤 Checking service account...${NC}"
SERVICE_ACCOUNT="dino-backend-sa@$PROJECT_ID.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe $SERVICE_ACCOUNT >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️ Creating service account...${NC}"
    gcloud iam service-accounts create dino-backend-sa \
        --display-name="Dino Backend Service Account" \
        --description="Service account for Dino Backend Cloud Run service"
    
    # Grant necessary roles
    echo -e "${YELLOW}⚠️ Granting IAM roles...${NC}"
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/datastore.user"
    
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/storage.objectAdmin"
else
    echo -e "${GREEN}✅ Service account exists${NC}"
fi

# Validate Firestore database
echo -e "${BLUE}🗄️ Checking Firestore database...${NC}"
if ! gcloud firestore databases describe --database="jm-dino" >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️ Firestore database 'jm-dino' not found${NC}"
    echo -e "${YELLOW}   Please create it manually in the GCP Console or use '(default)'${NC}"
    echo -e "${YELLOW}   Continuing with deployment...${NC}"
else
    echo -e "${GREEN}✅ Firestore database 'jm-dino' exists${NC}"
fi

# Start Cloud Build
echo -e "${BLUE}🏗️ Starting Cloud Build deployment...${NC}"
echo "Configuration:"
echo "  - Project: $PROJECT_ID"
echo "  - SECRET_KEY: [HIDDEN] (length: ${#SECRET_KEY})"
echo "  - Frontend URL: $FRONTEND_URL"
echo "  - Database: jm-dino"

# Submit build with substitution variables
gcloud builds submit \
    --config=cloudbuild.yaml \
    --substitutions="_SECRET_KEY=$SECRET_KEY,_FRONTEND_URL=$FRONTEND_URL" \
    .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
    echo ""
    echo "Service URL: https://dino-backend-$PROJECT_ID.a.run.app"
    echo "Health Check: https://dino-backend-$PROJECT_ID.a.run.app/health"
    echo ""
    echo -e "${YELLOW}📝 Next Steps:${NC}"
    echo "1. Test the health endpoint"
    echo "2. Update your frontend CORS configuration"
    echo "3. Test API endpoints"
    echo "4. Monitor logs: gcloud logs tail --service=dino-backend"
else
    echo -e "${RED}❌ Deployment failed!${NC}"
    echo "Check the Cloud Build logs for details"
    exit 1
fi