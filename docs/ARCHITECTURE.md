# Intent Detection Agents - Architecture Overview

## System Overview

The Intent Detection Agents system is a multi-agent architecture designed to detect B2B buying intent in real-time by analyzing various signals and ranking companies based on relevance and preference indicators.

## Core Components

### 1. Data Storage Layer

**Neo4j (Knowledge Graph)**
- Stores companies and signals as nodes
- Relationships: `Company -[:HAS_SIGNAL]-> Signal`
- Supports complex graph queries for discovery and analysis
- Stores metadata, labels, and fitScores

**Qdrant (Vector Database)**
- Stores semantic embeddings of signals
- Enables fast similarity search and discovery
- Supports real-time vector operations

### 2. Service Layer

**Collector Service**
- **Purpose**: Data ingestion and preprocessing
- **Input**: Raw signals from various sources (APIs, web scraping)
- **Output**: Cleaned signals stored in Neo4j + Qdrant
- **Key Functions**:
  - Source integration (LinkedIn, news APIs, job boards)
  - Data cleaning and deduplication
  - Embedding generation
  - Batch storage operations

**Classifier Service**
- **Purpose**: Signal labeling and scoring
- **Input**: Raw signals from Collector
- **Output**: Labeled signals with fitScores
- **Key Functions**:
  - Rule-based classification (keywords, regex)
  - LLM fallback for uncertain cases
  - fitScore calculation (0-1 scale)
  - Confidence scoring

**Ranker Service**
- **Purpose**: Company ranking and preference modeling
- **Input**: Company signals and metadata
- **Output**: Ranked companies with preference indicators
- **Key Functions**:
  - Feature engineering (fitScore stats, recency, diversity)
  - DBSCAN clustering for preference modeling
  - Contextual bandit ranking
  - Real-time score updates

**Orchestrator Service**
- **Purpose**: Pipeline coordination and job management
- **Input**: User queries and search parameters
- **Output**: Ranked results with evidence
- **Key Functions**:
  - Job lifecycle management
  - Service coordination
  - Result aggregation and caching
  - Timeout handling

### 3. Frontend Layer

**Streamlit App**
- **Purpose**: User interface for search and results viewing
- **Features**:
  - Search interface
  - Results display with evidence
  - Real-time updates
  - Filtering and sorting

## Data Flow

### 1. Data Ingestion Flow
```
External Sources → Collector → Clean → Store (Neo4j + Qdrant)
```

### 2. Classification Flow
```
Raw Signals → Classifier → Rules/LLM → Label + fitScore → Neo4j
```

### 3. Ranking Flow
```
Company Signals → Feature Engineering → DBSCAN → Contextual Bandit → Ranked Results
```

### 4. Search Flow
```
User Query → Orchestrator → Discovery → Classification → Ranking → Results
```

## Key Algorithms

### 1. Signal Classification
- **Rule-based**: Keyword matching, regex patterns, metadata analysis
- **LLM Fallback**: OpenAI GPT for uncertain cases with caching
- **fitScore**: Normalized score based on signal strength and relevance

### 2. Preference Modeling (DBSCAN)
- **Purpose**: Identify similar companies for preference learning
- **Features**: fitScore distribution, signal types, temporal patterns
- **Output**: preferenceIndicator ∈ [0,1]

### 3. Contextual Bandit Ranking
- **Purpose**: Optimize ranking based on user feedback
- **Features**: Company features + preference indicators
- **Policy**: RLlib contextual bandit with exploration

## Performance Characteristics

- **Discovery**: < 10 seconds for initial results
- **Classification**: < 30 seconds per batch
- **Ranking**: < 15 seconds for top-K results
- **Total Pipeline**: < 1 minute for first results, continuous improvement

## Scalability Considerations

- **Horizontal Scaling**: Each service can be scaled independently
- **Caching**: Redis for intermediate results and LLM responses
- **Batch Processing**: Collector handles large data volumes
- **Async Processing**: Non-blocking operations for better UX

## Security & Privacy

- **API Key Management**: Environment-based configuration
- **Data Encryption**: At-rest and in-transit encryption
- **Access Control**: Service-to-service authentication
- **Audit Logging**: Comprehensive operation logging
