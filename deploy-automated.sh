#!/bin/bash

# Automated Cloud Run deployment script
# Uses existing secrets and environment variables

set -e

PROJECT_ID="intent-detection-agent"
REGION="asia-south1"

echo "=========================================="
echo "Automated Cloud Run Deployment"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "=========================================="

# Set project and region
gcloud config set project $PROJECT_ID
gcloud config set run/region $REGION

# Build backend
echo ""
echo "Building backend image..."
gcloud builds submit \
    --tag gcr.io/$PROJECT_ID/intent-backend:latest \
    --timeout=20m \
    -f Dockerfile.backend \
    .

# Deploy backend
echo ""
echo "Deploying backend to Cloud Run..."
gcloud run deploy intent-backend \
    --image gcr.io/$PROJECT_ID/intent-backend:latest \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --port 8004 \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --max-instances 10 \
    --set-secrets="OPENAI_API_KEY=OPENAI_API_KEY:latest,PPLX_API_KEY=PPLX_API_KEY:latest" \
    --set-env-vars="NEO4J_USER=neo4j,NEO4J_DATABASE=neo4j,EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2,VECTOR_DIMENSION=384,LLM_MODEL=gpt-4o-mini"

# Get backend URL
BACKEND_URL=$(gcloud run services describe intent-backend --region $REGION --format 'value(status.url)')
echo "Backend deployed at: $BACKEND_URL"

# Build frontend
echo ""
echo "Building frontend image..."
gcloud builds submit \
    --tag gcr.io/$PROJECT_ID/intent-frontend:latest \
    --timeout=20m \
    -f Dockerfile.frontend \
    --substitutions="_NEXT_PUBLIC_API_BASE_URL=$BACKEND_URL" \
    services/frontend

# Deploy frontend
echo ""
echo "Deploying frontend to Cloud Run..."
gcloud run deploy intent-frontend \
    --image gcr.io/$PROJECT_ID/intent-frontend:latest \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --port 3000 \
    --memory 512Mi \
    --cpu 1 \
    --timeout 60 \
    --max-instances 10 \
    --set-env-vars="NEXT_PUBLIC_API_BASE_URL=$BACKEND_URL"

# Get frontend URL
FRONTEND_URL=$(gcloud run services describe intent-frontend --region $REGION --format 'value(status.url)')

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo "Backend:  $BACKEND_URL"
echo "Frontend: $FRONTEND_URL"
echo ""
echo "Note: Update backend CORS to include: $FRONTEND_URL"
