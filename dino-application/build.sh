#!/bin/bash
DIR="$( cd "$(dirname "$0")" ; pwd -P )"
. ${DIR}/env.sh.${PROJECT}

echo "PROJECT: ${PROJECT}"

gcloud builds submit . --tag us-central1-docker.pkg.dev/edl-idaas-ddev-platform-daad/job-manager-artifacts/job-manager-api-wiz2