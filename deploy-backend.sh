#!/bin/bash
# Simple script to redeploy backend to Google Cloud Run
# Run this after making code changes to the backend

set -e

PROJECT_ID="intent-detection-agent"
REGION="asia-south1"

echo "Deploying backend to Google Cloud Run..."

# Build image
gcloud builds submit \
  --tag gcr.io/$PROJECT_ID/intent-backend:latest \
  --timeout=20m \
  -f Dockerfile.backend \
  --project=$PROJECT_ID \
  .

# Deploy to Cloud Run
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
  --set-env-vars="NEO4J_USER=neo4j,NEO4J_DATABASE=neo4j,EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2,VECTOR_DIMENSION=384,LLM_MODEL=gpt-4o-mini" \
  --project=$PROJECT_ID

echo ""
echo "Backend deployed successfully!"
echo "URL: https://intent-backend-584414482857.asia-south1.run.app"
