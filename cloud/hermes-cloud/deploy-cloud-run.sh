#!/usr/bin/env bash
set -euo pipefail

: "${GCP_PROJECT:?Set GCP_PROJECT}"
: "${REGION:=europe-north1}"
: "${SERVICE:=occ-hermes}"
: "${OCC_EXTENSION_ORIGIN:?Set OCC_EXTENSION_ORIGIN=chrome-extension://<id>}"

IMAGE="${REGION}-docker.pkg.dev/${GCP_PROJECT}/occ/hermes:latest"
gcloud config set project "$GCP_PROJECT"
gcloud artifacts repositories describe occ --location "$REGION" >/dev/null 2>&1 || \
  gcloud artifacts repositories create occ --repository-format=docker --location "$REGION"
gcloud builds submit --tag "$IMAGE" .

gcloud run deploy "$SERVICE" \
  --image "$IMAGE" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --concurrency 4 \
  --timeout 3600 \
  --min-instances 0 \
  --max-instances 1 \
  --port 8080 \
  --set-env-vars "API_SERVER_ENABLED=true,API_SERVER_HOST=0.0.0.0,API_SERVER_PORT=8080,API_SERVER_CORS_ORIGINS=${OCC_EXTENSION_ORIGIN}" \
  --set-secrets "API_SERVER_KEY=occ-hermes-api-key:latest"

echo "Hermes deployed. Put the returned HTTPS service URL into OCC Agent Relay."
echo "The secret occ-hermes-api-key must already exist in Google Secret Manager."
