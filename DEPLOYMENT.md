# Cloud Run Deployment Guide

This guide explains how to deploy the Intent Detection Agent to Google Cloud Run.

## Prerequisites

1. Google Cloud Project: `intent-detection-agent`
2. Enabled APIs:
   - Cloud Run Admin API
   - Cloud Build API
   - Artifact Registry API
   - Secret Manager API
3. Cloud Databases (required):
   - Neo4j Aura (free tier available at https://neo4j.com/cloud/aura/)
   - Qdrant Cloud (free tier available at https://cloud.qdrant.io/)

## Step 1: Set Up Cloud Databases

### Neo4j Aura Setup
1. Go to https://neo4j.com/cloud/aura/
2. Create a free AuraDB instance
3. Note down:
   - Connection URI (e.g., `neo4j+s://xxxxx.databases.neo4j.io`)
   - Username (usually `neo4j`)
   - Password

### Qdrant Cloud Setup
1. Go to https://cloud.qdrant.io/
2. Create a free cluster
3. Note down:
   - Host (e.g., `xxxxx-xxxxx.cloud.qdrant.io`)
   - API Key

## Step 2: Create Secrets in Google Secret Manager

Run these commands to create secrets:

```bash
# Already created (API keys from .env)
# OPENAI_API_KEY - already exists
# PPLX_API_KEY - already exists

# Create database secrets
echo -n "neo4j+s://your-instance.databases.neo4j.io" | gcloud secrets create NEO4J_URI --data-file=-
echo -n "your-neo4j-password" | gcloud secrets create NEO4J_PASSWORD --data-file=-
echo -n "your-qdrant-host.cloud.qdrant.io" | gcloud secrets create QDRANT_HOST --data-file=-
echo -n "your-qdrant-api-key" | gcloud secrets create QDRANT_API_KEY --data-file=-
```

## Step 3: Deploy to Cloud Run

### Option A: Full Deployment with Databases

Edit and run:
```bash
./deploy-cloudrun.sh
```

This script will:
- Prompt for database credentials
- Create/update secrets
- Build and deploy backend
- Build and deploy frontend
- Output deployment URLs

### Option B: Quick Deployment (if secrets exist)

```bash
./deploy-automated.sh
```

This uses existing secrets and deploys both services.

## Step 4: Update CORS Configuration

After deployment, update backend CORS to include production frontend URL:

1. Edit `services/orchestrator/app.py`
2. Add your frontend URL to allowed origins:
   ```python
   allow_origins=[
       "http://localhost:3000",
       "http://localhost:8501",
       "https://your-frontend-url.run.app",  # Add this
   ]
   ```
3. Redeploy backend:
   ```bash
   gcloud builds submit --tag gcr.io/intent-detection-agent/intent-backend:latest -f Dockerfile.backend .
   gcloud run deploy intent-backend --image gcr.io/intent-detection-agent/intent-backend:latest --region asia-south1
   ```

## Step 5: Configure Custom Domain (Optional)

To use a custom domain like `intent-detection-agent.com`:

1. Verify domain ownership in Google Cloud Console
2. Create domain mapping:
   ```bash
   gcloud run domain-mappings create \
     --service intent-frontend \
     --domain your-domain.com \
     --region asia-south1
   ```
3. Update DNS records as instructed by Google Cloud

## Architecture on Cloud Run

```
User → Frontend (Cloud Run)
         ↓
       Backend (Cloud Run)
         ↓
    Neo4j Aura (Cloud)
    Qdrant Cloud
```

## Environment Variables

### Backend Service
- `OPENAI_API_KEY` (from Secret Manager)
- `PPLX_API_KEY` (from Secret Manager)
- `NEO4J_URI` (from Secret Manager)
- `NEO4J_PASSWORD` (from Secret Manager)
- `QDRANT_HOST` (from Secret Manager)
- `QDRANT_API_KEY` (from Secret Manager)
- `NEO4J_USER=neo4j`
- `NEO4J_DATABASE=neo4j`
- `LLM_MODEL=gpt-4o-mini`
- `EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2`

### Frontend Service
- `NEXT_PUBLIC_API_BASE_URL` (backend Cloud Run URL)

## Resource Configuration

### Backend
- Memory: 2Gi
- CPU: 2
- Timeout: 300s
- Max instances: 10
- Port: 8004

### Frontend
- Memory: 512Mi
- CPU: 1
- Timeout: 60s
- Max instances: 10
- Port: 3000

## Cost Estimate

Free Tier (monthly):
- Cloud Run: 2 million requests, 360,000 GB-seconds
- Neo4j Aura: Free tier (50MB storage)
- Qdrant Cloud: Free tier (1GB storage)

Expected monthly cost (low usage): $0-10

## Troubleshooting

### Backend won't start
- Check Cloud Run logs: `gcloud run services logs read intent-backend --region asia-south1`
- Verify all secrets exist: `gcloud secrets list`
- Check database connectivity from Cloud Shell

### Frontend can't reach backend
- Verify CORS settings in backend
- Check backend URL is correct in frontend env
- Test backend: `curl https://your-backend-url.run.app/`

### Database connection errors
- Verify Neo4j Aura is running and URI is correct
- Check Qdrant Cloud cluster is active
- Ensure secrets are properly mounted

## Manual Deployment Commands

### Build Images
```bash
# Backend
gcloud builds submit --tag gcr.io/intent-detection-agent/intent-backend:latest -f Dockerfile.backend .

# Frontend
gcloud builds submit --tag gcr.io/intent-detection-agent/intent-frontend:latest -f Dockerfile.frontend services/frontend
```

### Deploy Services
```bash
# Backend
gcloud run deploy intent-backend \
  --image gcr.io/intent-detection-agent/intent-backend:latest \
  --region asia-south1 \
  --allow-unauthenticated \
  --port 8004 \
  --memory 2Gi \
  --cpu 2 \
  --set-secrets="OPENAI_API_KEY=OPENAI_API_KEY:latest,PPLX_API_KEY=PPLX_API_KEY:latest,NEO4J_URI=NEO4J_URI:latest,NEO4J_PASSWORD=NEO4J_PASSWORD:latest,QDRANT_HOST=QDRANT_HOST:latest,QDRANT_API_KEY=QDRANT_API_KEY:latest"

# Frontend
gcloud run deploy intent-frontend \
  --image gcr.io/intent-detection-agent/intent-frontend:latest \
  --region asia-south1 \
  --allow-unauthenticated \
  --port 3000 \
  --memory 512Mi \
  --set-env-vars="NEXT_PUBLIC_API_BASE_URL=https://your-backend-url.run.app"
```

## Next Steps

1. Set up monitoring and alerts
2. Configure custom domain
3. Enable Cloud Armor for DDoS protection
4. Set up CI/CD with Cloud Build triggers
5. Implement authentication (Firebase Auth, Auth0, etc.)
