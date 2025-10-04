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


### Example Usage

### Open **https://intent-detection-agent.vercel.app/** in browser

**Input in UI:**
```
We provide AI-driven analytics platforms for healthcare providers.
Find hospitals and healthcare companies that recently announced
AI partnerships, technology investments, or are hiring data scientists.
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