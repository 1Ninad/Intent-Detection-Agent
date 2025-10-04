# B2B Intent Detection Agent

AI system that helps B2B sales teams automatically discover prospect companies showing buying intent based on real-time web signals.

## Overview

The agent analyzes web signals across multiple sources to identify companies in active buying cycles. It uses natural language processing, graph databases, and vector embeddings to find, classify, and rank potential prospects based on their likelihood to purchase.

Sales teams can input their company description and ideal customer profile in plain English, and the system returns a ranked list of companies with evidence-backed buying signals.

## Features

- **Natural Language Input**: Sales teams describe their company and target customers in plain English
- **Real-time Web Search**: Integrates with Perplexity AI to discover fresh signals from across the web
- **Signal Classification**: Automatically categorizes signals into types (hiring, funding, tech adoption, partnerships, leadership changes)
- **Knowledge Graph**: Neo4j stores companies, signals, and relationships with temporal information
- **Semantic Search**: Qdrant vector database enables similarity-based prospect discovery
- **Fit Scoring**: Computes relevance scores based on signal types, recency, volume, and sentiment
- **Evidence-backed Results**: Each prospect includes clickable source links and reasoning

## Architecture

### Technology Stack

- **Backend**: Python, FastAPI, LangGraph
- **Databases**: Neo4j (graph), Qdrant (vectors)
- **AI/ML**: Perplexity API, SentenceTransformers

### System Components

1. **Web Search Service**: Perplexity AI integration for discovering companies and signals
2. **Ingestion Layer**: Processes web signals, extracts companies, generates embeddings
3. **Classification Service**: OpenAI-powered signal type classification with fallback rules
4. **Scoring Engine**: Computes fit scores using weighted features (tech signals 35%, volume 25%, executive changes 20%, sentiment 10%, funding 10%)
5. **Orchestrator**: LangGraph-based pipeline coordinating the workflow
6. **UI**: Next.js frontend with real-time API integration

### Data Model

**Neo4j Graph Schema:**
```
Company {id, name, domain, industry, geo}
Signal {id, type, text, source, url, publishedAt, confidence}
(Company)-[:HAS_SIGNAL]->(Signal)
```

**Qdrant Collections:**
- Signal embeddings with metadata (company, type, source, timestamp)
- 384-dimensional vectors using sentence-transformers/all-MiniLM-L6-v2

## Installation

### Prerequisites

- Python 3.11+
- Node.js 18+ (for Next.js frontend)
- Docker and Docker Compose
- API keys for: OpenAI, Perplexity AI

### Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd Intent-Detection-Agents
```

2. **Install dependencies**
```bash
python -m venv .venv
source .venv/bin/activate  
pip install -r requirements.txt
```

3. **Configure environment variables**
```bash
cp env.example .env
# Edit .env:
# OPENAI_API_KEY=sk-...
# PPLX_API_KEY=pplx-...
# NEO4J_PASSWORD=password123
```

4. **Start databases**
```bash
docker-compose up -d
```


## Usage

### Quick Start (Next.js Frontend)

Run the complete system with one script:
```bash
./run_demo_nextjs.sh
```

This starts:
- Neo4j (port 7474, 7687)
- Qdrant (port 6333)
- Orchestrator API (port 8004)
- Next.js Frontend (port 3000)

Then open **http://localhost:3000** in browser.

### Example Usage

**Input in UI:**
```
We provide AI-driven analytics platforms for healthcare providers.
Find hospitals and healthcare companies that recently announced
AI partnerships, technology investments, or are hiring data scientists.
Return about 8 prospects.
```

**Output:**
```
Companies Found: 8
Signals Analyzed: 24
Web Signals: 10

Ranked Prospects:
1. mayoclinic.org        Fit Score: 0.85
   Reasons: techSignals 0.90, recentVolume 0.75, execChanges 0.60

2. kp.org                Fit Score: 0.72
   Reasons: techSignals 0.80, recentVolume 0.65, sentiment 0.70
```

## Project Structure

```
Intent-Detection-Agents/
├── services/
│   ├── orchestrator/          # Pipeline coordination (LangGraph)
│   │   ├── app.py            # FastAPI entrypoint
│   │   ├── flow.py           # Pipeline definition
│   │   ├── nodes/            # Pipeline nodes
│   │   │   ├── ingest_signals.py      # Neo4j/Qdrant ingestion
│   │   │   └── signal_classification.py
│   │   └── db/
│   │       └── neo4j_writer.py        # Database writes
│   ├── classifier/
│   │   ├── agent.py          # OpenAI classification
│   │   ├── fit_score.py      # Scoring algorithm
│   │   └── classifier_types.py
│   ├── ranker/               # Future: contextual bandit
│   │   ├── preference_service.py
│   │   └── ranker_service.py
│   ├── pplx_signal_search.py # Perplexity integration
│   ├── frontend/             # Next.js frontend
│   │   ├── app/              # Next.js App Router
│   │   │   ├── page.tsx      # Main search page
│   │   │   └── layout.tsx    # Root layout
│   │   ├── lib/              # Utilities
│   │   │   ├── api.ts        # API client
│   │   │   └── types.ts      # TypeScript interfaces
│   │   ├── package.json
│   │   └── README.md
├── shared/
│   └── graph.py              # Neo4j utilities
├── database/
│   └── neo4j/
│       └── schema/
│           └── schema.cypher # Graph schema
├── docker-compose.yml        # Database infrastructure
├── requirements.txt
├── run_demo_nextjs.sh       # One-command startup (Next.js)
└── run_demo.sh              # One-command startup (Streamlit)
```

## Pipeline Flow

```
User Input (free text)
    ↓
Perplexity Web Search (30-45s)
    ↓
Signal Extraction & Normalization
    ↓
Neo4j Storage (companies, signals, relationships)
    ↓
Qdrant Storage (embeddings)
    ↓
Signal Classification (OpenAI)
    ↓
Fit Score Computation
    ↓
Ranking by Score
    ↓
UI Display (ranked prospects)
```

**Total processing time: 45-70 seconds**

## API Reference

### Orchestrator Endpoint

**POST /run**

Request:
```json
{
  "freeText": "We provide AI analytics for healthcare. Find hospitals with AI partnerships.",
  "useWebSearch": true,
  "topK": 8,
  "webSearchOptions": {
    "recency": "month",
    "model": "sonar-pro"
  }
}
```

Response:
```json
{
  "runId": "run_20240130120000",
  "processedCompanies": 8,
  "labeledSignals": 24,
  "results": [
    {
      "companyId": "mayoclinic.org",
      "fitScore": 0.85,
      "reasons": ["techSignals 0.90", "recentVolume 0.75"]
    }
  ],
  "debug": {
    "webSignalsCount": 10,
    "ingestStats": {
      "companies": 8,
      "signals": 24,
      "embeddings": 24
    }
  }
}
```
- Perplexity AI for web search capabilities
- OpenAI for GPT-4 classification
- LangChain/LangGraph for agent orchestration
- Neo4j and Qdrant teams for database technology
