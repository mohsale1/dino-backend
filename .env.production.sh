#!/bin/bash
# Dino E-Menu Backend Production Environment
# Updated: 2025-11-22
# All environment variables actually used in the codebase

# =============================================================================
# ENVIRONMENT & BASIC CONFIG
# =============================================================================
export ENVIRONMENT=production
export DEBUG=false
export LOG_LEVEL=INFO
export PORT=8080

# =============================================================================
# SECURITY - JWT & Authentication
# =============================================================================
export SECRET_KEY=Y8npVmKu/qrRjgl6hISI8d66FxFPjFYZAiax9WDpXh0=
export ALGORITHM=HS256
export ACCESS_TOKEN_EXPIRE_MINUTES=60
export REFRESH_TOKEN_EXPIRE_DAYS=7

# Security Settings
export BCRYPT_ROUNDS=12
export MAX_LOGIN_ATTEMPTS=5
export LOCKOUT_DURATION_MINUTES=2
export REQUIRE_STRONG_PASSWORDS=true
export JWT_AUTH=true

# Client-side password hashing
export CLIENT_PASSWORD_SALT=dino-default-salt-2024-secure-hashing

# =============================================================================
# CORS CONFIGURATION
# =============================================================================
export CORS_ORIGINS=*
export CORS_ALLOW_CREDENTIALS=true
export CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,PATCH,OPTIONS
export CORS_ALLOW_HEADERS=*

# =============================================================================
# GOOGLE CLOUD PLATFORM
# =============================================================================
export GCP_PROJECT_ID=edl-idaas-fdev-platform-2c85
export GCP_REGION=us-central1

# =============================================================================
# FIRESTORE DATABASE
# =============================================================================
export DATABASE_NAME=jm-dino

# =============================================================================
# CLOUD STORAGE
# =============================================================================
export GCS_BUCKET_NAME=edl-idaas-fdev-platform-2c85-dino-storage
export DINO_MENU_BUCKET=edl-idaas-fdev-platform-2c85-dino-storage
export GCS_BUCKET_REGION=us-central1
export GCS_IMAGES_FOLDER=images
export GCS_DOCUMENTS_FOLDER=documents
export GCS_QR_CODES_FOLDER=qr-codes
export GCS_SIGNED_URL_EXPIRATION=3600

# =============================================================================
# FILE UPLOAD CONFIGURATION
# =============================================================================
export MAX_FILE_SIZE=5242880
export MAX_IMAGE_SIZE_MB=5
export MAX_DOCUMENT_SIZE_MB=10
export ALLOWED_IMAGE_TYPES=image/jpeg,image/png,image/webp,image/gif

# =============================================================================
# APPLICATION FEATURES
# =============================================================================
export QR_CODE_BASE_URL=https://yourdomain.com/menu
export DEFAULT_CURRENCY=INR
export PAYMENT_GATEWAY=razorpay
export RATE_LIMIT_PER_MINUTE=300

# =============================================================================
# FEATURE FLAGS
# =============================================================================
export ENABLE_DATABASE_LOGGING=false
export ENABLE_ENHANCED_LOGGING=true
export ENABLE_PERFORMANCE_MONITORING=false
export ENABLE_AUDIT_LOGGING=true

# =============================================================================
# CLOUD RUN CONFIGURATION
# =============================================================================
export CLOUD_RUN_SERVICE_NAME=dino-backend-api
export CLOUD_RUN_IMAGE_NAME=us-central1-docker.pkg.dev/edl-idaas-fdev-platform-2c85/job-manager-artifacts/dino-backend-api
export CLOUD_RUN_REGION=us-central1
export CLOUD_RUN_MEMORY=512Mi
export CLOUD_RUN_CPU=1
export CLOUD_RUN_MAX_INSTANCES=10
export CLOUD_RUN_MIN_INSTANCES=0

# =============================================================================
# PYTHON CONFIGURATION
# =============================================================================
export PYTHONUNBUFFERED=1