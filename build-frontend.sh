#!/bin/bash
set -e

PROJECT_ID="intent-detection-agent"
REGION="asia-south1"
BACKEND_URL="https://intent-backend-584414482857.asia-south1.run.app"

echo "Building frontend with backend URL: $BACKEND_URL"

# Build using Cloud Build with substitutions
gcloud builds submit \
  --project=$PROJECT_ID \
  --substitutions=_BACKEND_URL=$BACKEND_URL \
  --config=- << EOF
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-t'
      - 'gcr.io/$PROJECT_ID/intent-frontend:latest'
      - '-f'
      - 'Dockerfile.frontend'
      - '--build-arg'
      - 'NEXT_PUBLIC_API_BASE_URL=\$_BACKEND_URL'
      - '.'
images: ['gcr.io/$PROJECT_ID/intent-frontend:latest']
timeout: '1200s'
EOF

echo ""
echo "Deploying to Cloud Run..."
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
  --project=$PROJECT_ID

echo ""
echo "Deployment complete!"
echo "Frontend URL: https://intent-frontend-584414482857.asia-south1.run.app"
