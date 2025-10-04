# Deploy Frontend to Vercel

## Option 1: Via Vercel CLI (Recommended)

1. **Login to Vercel:**
   ```bash
   cd services/frontend
   vercel login
   ```

2. **Deploy:**
   ```bash
   vercel --prod --yes
   ```

3. **Set environment variable (if prompted):**
   - `NEXT_PUBLIC_API_BASE_URL=https://intent-backend-584414482857.asia-south1.run.app`

## Option 2: Via Vercel Web Dashboard

1. Go to [vercel.com](https://vercel.com) and sign in
2. Click **"Add New Project"**
3. Import your Git repository (push to GitHub first if not already)
4. **Important:** Set **Root Directory** to `services/frontend`
5. Framework Preset: Next.js (auto-detected)
6. Add Environment Variable:
   - Name: `NEXT_PUBLIC_API_BASE_URL`
   - Value: `https://intent-backend-584414482857.asia-south1.run.app`
7. Click **"Deploy"**

## After Deployment

### 1. Get your Vercel URL
After deployment, you'll get a URL like: `https://your-project.vercel.app`

### 2. Update Backend CORS (Optional)
The backend already allows all origins (`*`), but for better security, add your Vercel URL:

```bash
# Edit services/orchestrator/app.py and add:
"https://your-project.vercel.app",  # Vercel frontend

# Then redeploy backend:
cd /Users/ninadkale/Developer/VIT/EDI5/Intent-Detection-Agents
gcloud builds submit \
  --tag gcr.io/intent-detection-agent/intent-backend:latest \
  --timeout=20m \
  -f Dockerfile.backend \
  .

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
  --set-secrets="OPENAI_API_KEY=OPENAI_API_KEY:latest,PPLX_API_KEY=PPLX_API_KEY:latest" \
  --set-env-vars="NEO4J_USER=neo4j,NEO4J_DATABASE=neo4j,EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2,VECTOR_DIMENSION=384,LLM_MODEL=gpt-4o-mini" \
  --project=intent-detection-agent
```

## Test

Visit your Vercel URL and test the application!

## Backend URL
Your backend is running at: `https://intent-backend-584414482857.asia-south1.run.app`

Test backend health:
```bash
curl https://intent-backend-584414482857.asia-south1.run.app/
```

Should return: `{"status":"ok"}`
