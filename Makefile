# Makefile for Intent Detection Agents

.PHONY: up down run test clean logs

# Start infrastructure (Neo4j + Qdrant)
up:
	docker-compose up -d

# Stop all containers
down:
	docker-compose down

# Start all services
run:
	@echo "Starting all services..."
	@cd services/collector && python -m uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload &
	@cd services/classifier && python -m uvicorn src.main:app --host 0.0.0.0 --port 8002 --reload &
	@cd services/ranker && python -m uvicorn src.main:app --host 0.0.0.0 --port 8003 --reload &
	@cd services/orchestrator && python -m uvicorn src.main:app --host 0.0.0.0 --port 8004 --reload &
	@cd services/app && streamlit run src/app.py --server.port 8501 --server.address 0.0.0.0 &
	@echo "All services started. Access UI at http://localhost:8501"

# Run tests
test:
	@echo "Running tests..."
	@python -m pytest tests/ -v

# View logs
logs:
	docker-compose logs -f

# Clean up
clean:
	@echo "Cleaning up..."
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@find . -type d -name "*.egg-info" -exec rm -rf {} +
	@echo "Cleanup complete"

# Install dependencies
install:
	@echo "Installing dependencies..."
	@pip install -r requirements.txt

# Setup development environment
setup: install
	@echo "Setting up development environment..."
	@cp env.example .env
	@echo "Please edit .env with your configuration"
	@make up
	@echo "Development environment ready!"
