#!/bin/bash

# B2B Intent Detection Agent - Demo Startup Script
# This script starts all required services for the demo

set -e  # Exit on error

echo "======================================"
echo "  B2B Intent Detection Agent Demo"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env file not found!${NC}"
    echo "Please create .env file with required API keys:"
    echo "  - PPLX_API_KEY"
    echo "  - OPENAI_API_KEY"
    echo "  - NEO4J_PASSWORD"
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

echo -e "${YELLOW}🔍 Checking prerequisites...${NC}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker is running${NC}"

# Check Python
if ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Python not found${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python found${NC}"

# Step 1: Start databases
echo ""
echo -e "${YELLOW}📦 Step 1: Starting databases (Neo4j + Qdrant)...${NC}"
docker-compose up -d

echo "Waiting for databases to be ready..."
sleep 10

# Check if Neo4j is up
if curl -f http://localhost:7474 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Neo4j is ready at http://localhost:7474${NC}"
else
    echo -e "${RED}⚠️  Neo4j might not be ready yet. Check docker logs if issues occur.${NC}"
fi

# Check if Qdrant is up
if curl -f http://localhost:6333 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Qdrant is ready at http://localhost:6333${NC}"
else
    echo -e "${RED}⚠️  Qdrant might not be ready yet. Check docker logs if issues occur.${NC}"
fi

# Step 2: Start orchestrator API
echo ""
echo -e "${YELLOW}🚀 Step 2: Starting orchestrator API...${NC}"
python -m uvicorn services.orchestrator.app:app --host 0.0.0.0 --port 8004 > /tmp/orchestrator.log 2>&1 &
ORCHESTRATOR_PID=$!
echo "Orchestrator PID: $ORCHESTRATOR_PID"

# Wait for orchestrator to start
echo "Waiting for orchestrator to start..."
sleep 5

if curl -f http://localhost:8004/ > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Orchestrator API is ready at http://localhost:8004${NC}"
else
    echo -e "${RED}❌ Orchestrator failed to start. Check /tmp/orchestrator.log${NC}"
    kill $ORCHESTRATOR_PID 2>/dev/null || true
    exit 1
fi

# Step 3: Start Streamlit UI
echo ""
echo -e "${YELLOW}🎨 Step 3: Starting Streamlit UI...${NC}"
streamlit run ui/app.py --server.port 8501 --server.address 0.0.0.0 > /tmp/streamlit.log 2>&1 &
STREAMLIT_PID=$!
echo "Streamlit PID: $STREAMLIT_PID"

echo ""
echo -e "${GREEN}======================================"
echo "  ✅ All services started!"
echo "======================================${NC}"
echo ""
echo "📱 Open your browser and go to:"
echo -e "${GREEN}   http://localhost:8501${NC}"
echo ""
echo "🔧 Service URLs:"
echo "   - Streamlit UI:      http://localhost:8501"
echo "   - Orchestrator API:  http://localhost:8004"
echo "   - Neo4j Browser:     http://localhost:7474"
echo "   - Qdrant Dashboard:  http://localhost:6333/dashboard"
echo ""
echo "📝 Logs:"
echo "   - Orchestrator: tail -f /tmp/orchestrator.log"
echo "   - Streamlit:    tail -f /tmp/streamlit.log"
echo "   - Docker:       docker-compose logs -f"
echo ""
echo "🛑 To stop all services:"
echo "   - Press Ctrl+C in this terminal"
echo "   - Or run: docker-compose down"
echo ""

# Save PIDs for cleanup
echo $ORCHESTRATOR_PID > /tmp/orchestrator.pid
echo $STREAMLIT_PID > /tmp/streamlit.pid

# Trap for cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Shutting down services...${NC}"

    # Kill background processes
    if [ -f /tmp/orchestrator.pid ]; then
        kill $(cat /tmp/orchestrator.pid) 2>/dev/null || true
        rm /tmp/orchestrator.pid
    fi

    if [ -f /tmp/streamlit.pid ]; then
        kill $(cat /tmp/streamlit.pid) 2>/dev/null || true
        rm /tmp/streamlit.pid
    fi

    echo -e "${GREEN}✅ Services stopped${NC}"
    echo -e "${YELLOW}💡 Databases are still running. Stop with: docker-compose down${NC}"
}

trap cleanup EXIT INT TERM

# Keep script running
echo -e "${YELLOW}📺 Press Ctrl+C to stop all services${NC}"
wait