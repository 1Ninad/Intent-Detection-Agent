#!/bin/bash

# Check if deployment is ready

PROJECT_ID="intent-detection-agent"
REGION="asia-south1"

echo "=========================================="
echo "Deployment Readiness Check"
echo "=========================================="
echo ""

# Check gcloud auth
echo "1. Checking Google Cloud authentication..."
ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null)
if [ -z "$ACCOUNT" ]; then
    echo "   ❌ Not authenticated. Run: gcloud auth login"
    exit 1
else
    echo "   ✅ Authenticated as: $ACCOUNT"
fi

# Check project
echo ""
echo "2. Checking project configuration..."
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
if [ "$CURRENT_PROJECT" != "$PROJECT_ID" ]; then
    echo "   ⚠️  Current project: $CURRENT_PROJECT"
    echo "   Setting to: $PROJECT_ID"
    gcloud config set project $PROJECT_ID
else
    echo "   ✅ Project: $PROJECT_ID"
fi

# Check APIs
echo ""
echo "3. Checking required APIs..."
REQUIRED_APIS=(
    "run.googleapis.com"
    "cloudbuild.googleapis.com"
    "artifactregistry.googleapis.com"
    "secretmanager.googleapis.com"
)

for api in "${REQUIRED_APIS[@]}"; do
    if gcloud services list --enabled --filter="name:$api" --format="value(name)" | grep -q "$api"; then
        echo "   ✅ $api"
    else
        echo "   ❌ $api (not enabled)"
        echo "      Enable with: gcloud services enable $api"
    fi
done

# Check secrets
echo ""
echo "4. Checking secrets..."
REQUIRED_SECRETS=(
    "OPENAI_API_KEY"
    "PPLX_API_KEY"
)

OPTIONAL_SECRETS=(
    "NEO4J_URI"
    "NEO4J_PASSWORD"
    "QDRANT_HOST"
    "QDRANT_API_KEY"
)

for secret in "${REQUIRED_SECRETS[@]}"; do
    if gcloud secrets describe $secret &>/dev/null; then
        echo "   ✅ $secret"
    else
        echo "   ❌ $secret (missing)"
    fi
done

echo ""
echo "   Database secrets (optional for local testing):"
for secret in "${OPTIONAL_SECRETS[@]}"; do
    if gcloud secrets describe $secret &>/dev/null; then
        echo "   ✅ $secret"
    else
        echo "   ⚠️  $secret (not set - required for production)"
    fi
done

# Check Docker files
echo ""
echo "5. Checking Dockerfiles..."
if [ -f "Dockerfile.backend" ]; then
    echo "   ✅ Dockerfile.backend"
else
    echo "   ❌ Dockerfile.backend (missing)"
fi

if [ -f "Dockerfile.frontend" ]; then
    echo "   ✅ Dockerfile.frontend"
else
    echo "   ❌ Dockerfile.frontend (missing)"
fi

# Summary
echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="
echo ""

MISSING_DB_SECRETS=0
for secret in "${OPTIONAL_SECRETS[@]}"; do
    if ! gcloud secrets describe $secret &>/dev/null; then
        MISSING_DB_SECRETS=$((MISSING_DB_SECRETS + 1))
    fi
done

if [ $MISSING_DB_SECRETS -gt 0 ]; then
    echo "⚠️  Database secrets missing. You need:"
    echo ""
    echo "1. Neo4j Aura (https://neo4j.com/cloud/aura/)"
    echo "   - Create free instance"
    echo "   - Get connection URI and password"
    echo ""
    echo "2. Qdrant Cloud (https://cloud.qdrant.io/)"
    echo "   - Create free cluster"
    echo "   - Get host and API key"
    echo ""
    echo "Then create secrets with:"
    echo "   ./deploy-cloudrun.sh"
    echo ""
else
    echo "✅ All secrets configured!"
    echo ""
    echo "Ready to deploy. Run:"
    echo "   ./deploy-automated.sh"
    echo ""
fi
