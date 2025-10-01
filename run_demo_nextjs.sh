#!/bin/bash
# Complete system startup with Next.js frontend

echo "========================================"
echo "Starting Intent Detection System"
echo "with Next.js Frontend"
echo "========================================"
echo ""

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if databases are running
echo "Checking databases..."
if ! docker ps | grep -q neo4j; then
    echo "Starting databases..."
    docker-compose up -d
    echo "Waiting 10 seconds for databases to initialize..."
    sleep 10
fi

# Start orchestrator in background
echo ""
echo "Starting orchestrator API on port 8004..."
python -m uvicorn services.orchestrator.app:app --host 0.0.0.0 --port 8004 > /tmp/orchestrator.log 2>&1 &
ORCH_PID=$!
echo "Orchestrator PID: $ORCH_PID"

# Wait for orchestrator to be ready
echo "Waiting for orchestrator to be ready..."
sleep 5
until curl -s http://localhost:8004/ > /dev/null 2>&1; do
    echo "Waiting for orchestrator..."
    sleep 2
done
echo "✓ Orchestrator is ready"

# Start Next.js frontend
echo ""
echo "Starting Next.js frontend on port 3000..."
cd services/frontend

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Create .env.local if it doesn't exist
if [ ! -f ".env.local" ]; then
    cp .env.example .env.local
fi

npm run dev &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

cd ../..

echo ""
echo "========================================"
echo "✓ System is ready!"
echo "========================================"
echo ""
echo "Services running:"
echo "  • Neo4j:        http://localhost:7474"
echo "  • Qdrant:       http://localhost:6333/dashboard"
echo "  • Orchestrator: http://localhost:8004"
echo "  • Frontend:     http://localhost:3000"
echo ""
echo "Open http://localhost:3000 in your browser to start"
echo ""
echo "To stop all services, press Ctrl+C"
echo ""

# Wait for both processes
wait $ORCH_PID $FRONTEND_PID
