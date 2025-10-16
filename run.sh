#!/bin/bash

# Simple script to run the entire Intent Detection project
# Usage: ./run.sh

set -e

echo "=========================================="
echo "Intent Detection Agents - Startup Script"
echo "=========================================="
echo ""

# Check if PostgreSQL is running
echo "Checking PostgreSQL..."
if ! brew services list | grep postgresql@15 | grep started > /dev/null 2>&1; then
    echo "Starting PostgreSQL..."
    brew services start postgresql@15
    sleep 3
else
    echo "PostgreSQL is already running"
fi

# Check if database exists
echo "Checking database..."
if ! /opt/homebrew/opt/postgresql@15/bin/psql -lqt | cut -d \| -f 1 | grep -qw sales_prospects; then
    echo "Creating database..."
    /opt/homebrew/opt/postgresql@15/bin/createdb sales_prospects
fi

# Check environment file
if [ ! -f .env ]; then
    echo ""
    echo "ERROR: .env file not found!"
    echo "Please copy ' env.example' to '.env' and add your API keys:"
    echo "  cp ' env.example' .env"
    echo "  # Then edit .env with your OPENAI_API_KEY and PPLX_API_KEY"
    echo ""
    exit 1
fi

# Check for API keys
if ! grep -q "sk-" .env 2>/dev/null || ! grep -q "pplx-" .env 2>/dev/null; then
    echo ""
    echo "WARNING: API keys may not be configured in .env"
    echo "Make sure you have set:"
    echo "  - OPENAI_API_KEY"
    echo "  - PPLX_API_KEY"
    echo ""
fi

echo ""
echo "Starting backend API server..."
echo "Backend will be available at: http://localhost:8000"
echo ""
echo "To test the API:"
echo "  curl -X POST http://localhost:8000/run \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"freeText\": \"Fintech companies hiring engineers\", \"topK\": 3}'"
echo ""
echo "Or run the test script:"
echo "  python test_pipeline.py"
echo ""
echo "=========================================="
echo ""

# Start the FastAPI server
python -m uvicorn services.orchestrator.app:app --reload --port 8000
