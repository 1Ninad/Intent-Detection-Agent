#!/bin/bash

# Deployment script for Intent Detection Agent
# Usage: ./deploy.sh [frontend|backend|both]

set -e  # Exit on error

BACKEND_URL="https://intent-backend-584414482857.asia-south1.run.app"
REGION="asia-south1"
PROJECT_ID="intent-detection-agent"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

deploy_frontend() {
    echo -e "${YELLOW}Deploying frontend...${NC}"
    cd services/frontend

    gcloud run deploy intent-frontend \
      --source . \
      --platform managed \
      --region $REGION \
      --allow-unauthenticated \
      --port 3000 \
      --memory 512Mi \
      --cpu 1 \
      --set-env-vars="NEXT_PUBLIC_API_BASE_URL=$BACKEND_URL"

    echo -e "${GREEN}Frontend deployed successfully!${NC}"
    cd ../..
}

deploy_backend() {
    echo -e "${YELLOW}Building backend Docker image...${NC}"
    gcloud builds submit --config=cloudbuild.backend.yaml .

    echo -e "${YELLOW}Deploying backend to Cloud Run...${NC}"
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
      --set-secrets="OPENAI_API_KEY=OPENAI_API_KEY:latest,PPLX_API_KEY=PPLX_API_KEY:latest,NEO4J_URI=NEO4J_URI:latest,NEO4J_PASSWORD=NEO4J_PASSWORD:latest,QDRANT_HOST=QDRANT_HOST:latest,QDRANT_API_KEY=QDRANT_API_KEY:latest" \
      --set-env-vars="NEO4J_USER=neo4j,NEO4J_DATABASE=neo4j,QDRANT_PORT=6333,EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2,LLM_MODEL=gpt-4o-mini"

    echo -e "${GREEN}Backend deployed successfully!${NC}"
}

# Main script
if [ "$1" == "frontend" ]; then
    deploy_frontend

elif [ "$1" == "backend" ]; then
    deploy_backend

elif [ "$1" == "both" ]; then
    echo -e "${YELLOW}Deploying both backend and frontend...${NC}"
    deploy_backend
    echo ""
    deploy_frontend

else
    echo -e "${RED}Usage: ./deploy.sh [frontend|backend|both]${NC}"
    echo ""
    echo "Examples:"
    echo "  ./deploy.sh frontend   # Deploy only frontend (fast, ~3-5 minutes)"
    echo "  ./deploy.sh backend    # Deploy only backend (slow, ~10-12 minutes)"
    echo "  ./deploy.sh both       # Deploy both (slow, ~13-15 minutes)"
    exit 1
fi

echo ""
echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo ""
echo "Frontend URL: https://intent-frontend-584414482857.asia-south1.run.app"
echo "Backend URL:  https://intent-backend-584414482857.asia-south1.run.app"
echo ""
echo "To view logs:"
echo "  gcloud run services logs tail intent-frontend --region=$REGION"
echo "  gcloud run services logs tail intent-backend --region=$REGION"
