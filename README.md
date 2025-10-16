# Intent Detection Agents

B2B sales prospecting system that finds companies with buying signals using AI agents.

## What It Does

Finds relevant companies based on free-text queries by:
1. Searching web for company signals (Perplexity API)
2. Storing data in PostgreSQL database
3. Classifying signals with OpenAI (hiring, funding, tech adoption, etc.)
4. Ranking companies by fit score

## Tech Stack

- **Backend**: FastAPI, LangGraph
- **Database**: PostgreSQL
- **AI**: OpenAI GPT-4o-mini (classification), Perplexity Sonar Pro (search)
- **Deployment**: Google Cloud Run

## Quick Start

### First Time Setup

```bash
# 1. Install PostgreSQL
brew install postgresql@15
brew services start postgresql@15
createdb sales_prospects

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp " env.example" .env
# Edit .env with your OPENAI_API_KEY and PPLX_API_KEY
```

### Run Everything

```bash
# Simple one-command startup
./run.sh
```

This starts the backend API at http://localhost:8000

### Alternative: Manual Commands

```bash
# Test the pipeline
python test_pipeline.py

# Or start the API server manually
uvicorn services.orchestrator.app:app --reload --port 8000
```

### API Usage

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "freeText": "Fintech companies in US hiring data engineers",
    "topK": 5,
    "useWebSearch": true
  }'
```

## Project Structure

```
.
├── services/
│   ├── orchestrator/          # LangGraph pipeline
│   │   ├── app.py            # FastAPI endpoints
│   │   ├── flow.py           # Pipeline orchestration
│   │   ├── db/               # PostgreSQL client
│   │   └── nodes/            # Pipeline nodes
│   ├── classifier/           # Signal classification
│   └── pplx_signal_search.py # Web search
├── evaluation/               # Test queries and results
├── .deployment/              # Docker and deployment configs
└── test_pipeline.py          # End-to-end test script
```

## Database Schema

**companies**: id, name, domain, industry, geo, fit_score, fit_reasons

**signals**: id, company_id, type, title, text, sentiment, confidence, source, url

## Configuration

Required environment variables:
- `DATABASE_URL`: PostgreSQL connection string
- `OPENAI_API_KEY`: OpenAI API key for classification
- `PPLX_API_KEY`: Perplexity API key for web search
- `LLM_MODEL`: Model name (default: gpt-4o-mini)

## Performance

Typical query: 50-60 seconds end-to-end
- Web search: ~18s (35%)
- Classification: ~26s (50%)
- Database ops: ~5s (10%)
- Fit scoring: ~3s (5%)

## Deployment

See `DEPLOYMENT.md` for complete deployment guide (Vercel + Google Cloud Run).

## API Endpoints

**GET /** - Health check

**POST /run** - Main endpoint
- Input: `{freeText, topK, useWebSearch}`
- Output: `{processedCompanies, labeledSignals, results}`
