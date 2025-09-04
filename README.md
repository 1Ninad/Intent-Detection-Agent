# Intent Detection Agents

A multi-agent system that detects B2B buying intent in real time by combining knowledge graphs, vector databases, and ranking algorithms.
This system identifies companies showing buying intent by analyzing various signals (job postings, RFPs, news, website updates) and ranking them based on relevance and preference indicators.

## Architecture

- **Knowledge Graph (Neo4j)**: Stores companies and signals with relationships
- **Vector DB (Qdrant)**: Stores semantic embeddings for fast discovery
- **Services**: Collector, Classifier, Ranker, and Orchestrator agents
- **Frontend**: Streamlit UI for searching and viewing prospects with evidence

## Project Structure

```
intent-detection-agents/
├─ services/collector/     # Data ingestion from sources
├─ services/classifier/    # Signal labeling and scoring
├─ services/ranker/        # Preference and ranking algorithms
├─ services/orchestrator/  # Pipeline coordination
├─ services/app/          # Streamlit frontend
├─ database/neo4j/        # Graph schema and constraints
├─ shared/               # Common utilities
└─ docs/                 # Documentation
```

## How It Works

1. **Collector**: Fetches raw signals → cleans → stores in Neo4j + Qdrant
2. **Classifier**: Assigns labels and fitScores to signals
3. **Ranker**: Builds features and applies contextual bandit ranking
4. **Orchestrator**: Coordinates the pipeline and manages job execution
5. **App**: Provides UI for searching and viewing results



## Steps 1 & 2 Setup (Graph Foundation + Ingestion)

### Quick Start
``````powershell
# Start services
docker-compose up -d

# Install dependencies
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Configure API keys for Step 2
python scripts\setup_validator.py --wizard

# Test Graph API (Step 1)
python services\graph\test_api.py

# Run ingestion (Step 2)  
python services\collector\ingestion_orchestrator.py --mode single

#Services

Neo4j Browser: http://localhost:7474 (username:neo4j/password:password123)
Qdrant Dashboard: http://localhost:6333/dashboard
