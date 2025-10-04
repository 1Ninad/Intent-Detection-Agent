# Deployment Guide - Intent Detection Agent

## Current Deployment URLs

- **Backend**: https://intent-backend-584414482857.asia-south1.run.app
- **Frontend**: https://intent-frontend-584414482857.asia-south1.run.app

## 1. Testing the Application

### Local Testing
```bash
# Terminal 1 - Start backend
python -m uvicorn services.orchestrator.app:app --host 0.0.0.0 --port 8004

# Terminal 2 - Start frontend
cd services/frontend
npm run dev
```

Access at: http://localhost:3000

### Production Testing
Open: https://intent-frontend-584414482857.asia-south1.run.app

The frontend connects to the backend at: https://intent-backend-584414482857.asia-south1.run.app

## 2. Custom Domain Setup

### Option A: Using Google Cloud Domain Mapping

1. **Verify domain ownership** in Google Search Console:
   ```bash
   # Go to: https://search.google.com/search-console
   # Add your domain and verify ownership
   ```

2. **Map domain to Cloud Run**:
   ```bash
   # For frontend
   gcloud run domain-mappings create \
     --service intent-frontend \
     --domain your-domain.com \
     --region asia-south1

   # For backend (API subdomain)
   gcloud run domain-mappings create \
     --service intent-backend \
     --domain api.your-domain.com \
     --region asia-south1
   ```

3. **Update DNS records** (in your domain registrar):
   - The command above will show DNS records to add
   - Typically: CNAME or A records pointing to ghs.googlehosted.com

4. **Update frontend environment variable**:
   ```bash
   # Redeploy frontend with new backend URL
   cd services/frontend
   gcloud run deploy intent-frontend \
     --source . \
     --region asia-south1 \
     --set-env-vars="NEXT_PUBLIC_API_BASE_URL=https://api.your-domain.com"
   ```

### Option B: Using Cloudflare (Recommended for easier SSL)

1. Add your domain to Cloudflare
2. Point DNS to Cloud Run services:
   - `your-domain.com` → CNAME to `intent-frontend-584414482857.asia-south1.run.app`
   - `api.your-domain.com` → CNAME to `intent-backend-584414482857.asia-south1.run.app`
3. Enable SSL/TLS in Cloudflare (Full mode)
4. Update frontend to use `https://api.your-domain.com`

## 3. Deploying Code Changes

### Frontend Changes Only

```bash
cd services/frontend

# Deploy using Cloud Run buildpacks (automatic)
gcloud run deploy intent-frontend \
  --source . \
  --region asia-south1 \
  --set-env-vars="NEXT_PUBLIC_API_BASE_URL=https://intent-backend-584414482857.asia-south1.run.app"
```

Time: ~3-5 minutes

### Backend Changes Only

```bash
# From project root directory

# 1. Build Docker image
gcloud builds submit --config=cloudbuild.backend.yaml .

# 2. Deploy to Cloud Run
gcloud run deploy intent-backend \
  --image gcr.io/intent-detection-agent/intent-backend:latest \
  --platform managed \
  --region asia-south1 \
  --allow-unauthenticated \
  --port 8004 \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10 \
  --set-secrets="OPENAI_API_KEY=OPENAI_API_KEY:latest,PPLX_API_KEY=PPLX_API_KEY:latest,NEO4J_URI=NEO4J_URI:latest,NEO4J_PASSWORD=NEO4J_PASSWORD:latest,QDRANT_HOST=QDRANT_HOST:latest,QDRANT_API_KEY=QDRANT_API_KEY:latest" \
  --set-env-vars="NEO4J_USER=neo4j,NEO4J_DATABASE=neo4j,QDRANT_PORT=6333,EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2,LLM_MODEL=gpt-4o-mini"
```

Time: ~10-12 minutes (build takes 8-10 mins)

### Both Frontend and Backend Changes

```bash
# Deploy backend first (from project root)
gcloud builds submit --config=cloudbuild.backend.yaml .
gcloud run deploy intent-backend \
  --image gcr.io/intent-detection-agent/intent-backend:latest \
  --region asia-south1 \
  --set-secrets="OPENAI_API_KEY=OPENAI_API_KEY:latest,PPLX_API_KEY=PPLX_API_KEY:latest,NEO4J_URI=NEO4J_URI:latest,NEO4J_PASSWORD=NEO4J_PASSWORD:latest,QDRANT_HOST=QDRANT_HOST:latest,QDRANT_API_KEY=QDRANT_API_KEY:latest" \
  --set-env-vars="NEO4J_USER=neo4j,NEO4J_DATABASE=neo4j,QDRANT_PORT=6333,EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2,LLM_MODEL=gpt-4o-mini"

# Then deploy frontend
cd services/frontend
gcloud run deploy intent-frontend \
  --source . \
  --region asia-south1 \
  --set-env-vars="NEXT_PUBLIC_API_BASE_URL=https://intent-backend-584414482857.asia-south1.run.app"
```

Time: ~13-15 minutes total

## 4. Quick Deployment Script

Create `deploy.sh` in project root:

```bash
#!/bin/bash

# Check argument
if [ "$1" == "frontend" ]; then
    echo "Deploying frontend only..."
    cd services/frontend
    gcloud run deploy intent-frontend \
      --source . \
      --region asia-south1 \
      --set-env-vars="NEXT_PUBLIC_API_BASE_URL=https://intent-backend-584414482857.asia-south1.run.app"

elif [ "$1" == "backend" ]; then
    echo "Deploying backend only..."
    gcloud builds submit --config=cloudbuild.backend.yaml .
    gcloud run deploy intent-backend \
      --image gcr.io/intent-detection-agent/intent-backend:latest \
      --region asia-south1 \
      --set-secrets="OPENAI_API_KEY=OPENAI_API_KEY:latest,PPLX_API_KEY=PPLX_API_KEY:latest,NEO4J_URI=NEO4J_URI:latest,NEO4J_PASSWORD=NEO4J_PASSWORD:latest,QDRANT_HOST=QDRANT_HOST:latest,QDRANT_API_KEY=QDRANT_API_KEY:latest" \
      --set-env-vars="NEO4J_USER=neo4j,NEO4J_DATABASE=neo4j,QDRANT_PORT=6333,EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2,LLM_MODEL=gpt-4o-mini"

elif [ "$1" == "both" ]; then
    echo "Deploying both backend and frontend..."
    # Backend
    gcloud builds submit --config=cloudbuild.backend.yaml .
    gcloud run deploy intent-backend \
      --image gcr.io/intent-detection-agent/intent-backend:latest \
      --region asia-south1 \
      --set-secrets="OPENAI_API_KEY=OPENAI_API_KEY:latest,PPLX_API_KEY=PPLX_API_KEY:latest,NEO4J_URI=NEO4J_URI:latest,NEO4J_PASSWORD=NEO4J_PASSWORD:latest,QDRANT_HOST=QDRANT_HOST:latest,QDRANT_API_KEY=QDRANT_API_KEY:latest" \
      --set-env-vars="NEO4J_USER=neo4j,NEO4J_DATABASE=neo4j,QDRANT_PORT=6333,EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2,LLM_MODEL=gpt-4o-mini"

    # Frontend
    cd services/frontend
    gcloud run deploy intent-frontend \
      --source . \
      --region asia-south1 \
      --set-env-vars="NEXT_PUBLIC_API_BASE_URL=https://intent-backend-584414482857.asia-south1.run.app"

else
    echo "Usage: ./deploy.sh [frontend|backend|both]"
    exit 1
fi
```

Make it executable:
```bash
chmod +x deploy.sh
```

Usage:
```bash
./deploy.sh frontend   # Deploy only frontend
./deploy.sh backend    # Deploy only backend
./deploy.sh both       # Deploy both
```

## 5. Monitoring and Logs

### View Logs
```bash
# Backend logs
gcloud run services logs read intent-backend --region=asia-south1 --limit=50

# Frontend logs
gcloud run services logs read intent-frontend --region=asia-south1 --limit=50

# Stream logs (live)
gcloud run services logs tail intent-backend --region=asia-south1
```

### Check Service Status
```bash
gcloud run services list --region=asia-south1
```

### Check Resource Usage
View in Cloud Console:
https://console.cloud.google.com/run?project=intent-detection-agent

## 6. Cost Optimization

Cloud Run charges only for actual usage:
- Backend: ~$0.024/hour when active (2 vCPU, 2GB RAM)
- Frontend: ~$0.006/hour when active (1 vCPU, 512MB RAM)
- Free tier: 2 million requests/month

To reduce costs:
```bash
# Set max instances lower
gcloud run services update intent-backend \
  --max-instances=5 \
  --region=asia-south1

# Set min instances to 0 (cold starts but no idle costs)
gcloud run services update intent-backend \
  --min-instances=0 \
  --region=asia-south1
```

## 7. Troubleshooting

### Frontend shows "Cannot connect to backend"
1. Check CORS settings in `services/orchestrator/app.py`
2. Verify backend is accessible: `curl https://intent-backend-584414482857.asia-south1.run.app/`
3. Check frontend environment variable has correct backend URL

### Backend deployment fails
1. Check build logs: `gcloud builds list --limit=5`
2. View specific build: `gcloud builds log <BUILD_ID>`
3. Common issues:
   - Missing dependencies in requirements.txt
   - Import errors
   - Database connection issues (check secrets)

### Frontend deployment fails
1. Check that `lib` directory has correct permissions: `chmod 755 services/frontend/lib`
2. Ensure package-lock.json is not in .dockerignore
3. Try rebuilding node_modules: `cd services/frontend && rm -rf node_modules && npm install`

## 8. Updating Environment Variables

### Backend
```bash
gcloud run services update intent-backend \
  --update-env-vars="NEW_VAR=value" \
  --region=asia-south1
```

### Frontend
```bash
cd services/frontend
gcloud run deploy intent-frontend \
  --source . \
  --region=asia-south1 \
  --update-env-vars="NEXT_PUBLIC_NEW_VAR=value"
```

## 9. Rolling Back Deployments

```bash
# List revisions
gcloud run revisions list --service=intent-backend --region=asia-south1

# Rollback to specific revision
gcloud run services update-traffic intent-backend \
  --to-revisions=intent-backend-00003-9vt=100 \
  --region=asia-south1
```
