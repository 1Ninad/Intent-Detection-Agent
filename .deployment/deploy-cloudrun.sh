#!/bin/bash

# Cloud Run deployment script for Intent Detection Agent
# Project: intent-detection-agent
# Region: asia-south1 (Mumbai, India)

set -e

PROJECT_ID="intent-detection-agent"
REGION="asia-south1"

echo "=========================================="
echo "Cloud Run Deployment Script"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Set project and region
echo -e "${YELLOW}Setting up Google Cloud configuration...${NC}"
gcloud config set project $PROJECT_ID
gcloud config set run/region $REGION

# Database configuration - IMPORTANT: UPDATE THESE VALUES
echo ""
echo -e "${RED}IMPORTANT: Database Configuration${NC}"
echo "This deployment requires cloud-hosted databases:"
echo "  1. Neo4j Aura (https://neo4j.com/cloud/aura/) - Get connection URI"
echo "  2. Qdrant Cloud (https://cloud.qdrant.io/) - Get host and API key"
echo ""
echo "Please provide the database connection details:"
echo ""

# Prompt for database URIs if not in environment
if [ -z "$NEO4J_URI" ]; then
    read -p "Neo4j URI (e.g., neo4j+s://xxxxx.databases.neo4j.io): " NEO4J_URI
fi

if [ -z "$NEO4J_PASSWORD" ]; then
    read -sp "Neo4j Password: " NEO4J_PASSWORD
    echo ""
fi

if [ -z "$QDRANT_HOST" ]; then
    read -p "Qdrant Host (e.g., xxxxx.cloud.qdrant.io): " QDRANT_HOST
fi

if [ -z "$QDRANT_API_KEY" ]; then
    read -sp "Qdrant API Key: " QDRANT_API_KEY
    echo ""
fi

# Create/update secrets
echo ""
echo -e "${YELLOW}Creating secrets in Secret Manager...${NC}"

echo -n "$NEO4J_URI" | gcloud secrets create NEO4J_URI --data-file=- 2>/dev/null || \
    echo -n "$NEO4J_URI" | gcloud secrets versions add NEO4J_URI --data-file=-

echo -n "$NEO4J_PASSWORD" | gcloud secrets create NEO4J_PASSWORD --data-file=- 2>/dev/null || \
    echo -n "$NEO4J_PASSWORD" | gcloud secrets versions add NEO4J_PASSWORD --data-file=-

echo -n "$QDRANT_HOST" | gcloud secrets create QDRANT_HOST --data-file=- 2>/dev/null || \
    echo -n "$QDRANT_HOST" | gcloud secrets versions add QDRANT_HOST --data-file=-

echo -n "$QDRANT_API_KEY" | gcloud secrets create QDRANT_API_KEY --data-file=- 2>/dev/null || \
    echo -n "$QDRANT_API_KEY" | gcloud secrets versions add QDRANT_API_KEY --data-file=-

echo -n "gpt-4o-mini" | gcloud secrets create LLM_MODEL --data-file=- 2>/dev/null || \
    echo -n "gpt-4o-mini" | gcloud secrets versions add LLM_MODEL --data-file=-

echo -e "${GREEN}Secrets created successfully${NC}"

# Build backend image
echo ""
echo -e "${YELLOW}Building backend image...${NC}"
gcloud builds submit \
    --tag gcr.io/$PROJECT_ID/intent-backend:latest \
    --timeout=20m \
    -f Dockerfile.backend \
    .

echo -e "${GREEN}Backend image built successfully${NC}"

# Deploy backend to Cloud Run
echo ""
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
    --set-secrets="OPENAI_API_KEY=OPENAI_API_KEY:latest,PPLX_API_KEY=PPLX_API_KEY:latest,NEO4J_URI=NEO4J_URI:latest,NEO4J_PASSWORD=NEO4J_PASSWORD:latest,QDRANT_HOST=QDRANT_HOST:latest,QDRANT_API_KEY=QDRANT_API_KEY:latest,LLM_MODEL=LLM_MODEL:latest" \
    --set-env-vars="NEO4J_USER=neo4j,NEO4J_DATABASE=neo4j,QDRANT_PORT=6333,EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2,VECTOR_DIMENSION=384"

# Get backend URL
BACKEND_URL=$(gcloud run services describe intent-backend --region $REGION --format 'value(status.url)')
echo -e "${GREEN}Backend deployed at: $BACKEND_URL${NC}"

# Build frontend image with backend URL
echo ""
echo -e "${YELLOW}Building frontend image...${NC}"
gcloud builds submit \
    --tag gcr.io/$PROJECT_ID/intent-frontend:latest \
    --timeout=20m \
    -f Dockerfile.frontend \
    --substitutions="_NEXT_PUBLIC_API_BASE_URL=$BACKEND_URL" \
    --build-arg NEXT_PUBLIC_API_BASE_URL=$BACKEND_URL \
    services/frontend

echo -e "${GREEN}Frontend image built successfully${NC}"

# Deploy frontend to Cloud Run
echo ""
echo -e "${YELLOW}Deploying frontend to Cloud Run...${NC}"
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
echo -e "${GREEN}=========================================="
echo "Deployment Complete!"
echo "==========================================${NC}"
echo ""
echo -e "${GREEN}Backend URL:${NC}  $BACKEND_URL"
echo -e "${GREEN}Frontend URL:${NC} $FRONTEND_URL"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Test the backend: curl $BACKEND_URL/"
echo "2. Open frontend in browser: $FRONTEND_URL"
echo "3. Configure custom domain (optional):"
echo "   - Run: gcloud run domain-mappings create --service intent-frontend --domain your-domain.com"
echo ""
echo -e "${YELLOW}To update CORS for backend:${NC}"
echo "Update services/orchestrator/app.py to include production frontend URL"
echo "Then rebuild and redeploy backend"
echo ""
