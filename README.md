# Intent Detection Agents

A multi-agent system that detects B2B buying intent in real time by combining knowledge graphs, vector databases, and intelligent ranking algorithms.

## Overview

This system identifies companies showing buying intent by analyzing various signals (job postings, RFPs, news, website updates) and ranking them based on relevance and preference indicators.

## Architecture

- **Knowledge Graph (Neo4j)**: Stores companies and signals with relationships
- **Vector DB (Qdrant)**: Stores semantic embeddings for fast discovery
- **Services**: Collector, Classifier, Ranker, and Orchestrator agents
- **Frontend**: Streamlit UI for searching and viewing prospects with evidence

## Quick Start

1. **Setup Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Start Infrastructure**:
   ```bash
   make up
   ```

3. **Run Services**:
   ```bash
   make run
   ```

4. **Access UI**:
   Open http://localhost:8501

## Development

- `make up` - Start Neo4j + Qdrant containers
- `make run` - Start all services
- `make test` - Run tests
- `make down` - Stop all containers

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

For detailed architecture, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
