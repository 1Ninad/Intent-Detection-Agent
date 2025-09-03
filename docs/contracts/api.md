# API Contracts

This document defines the exact request/response formats for all service endpoints.

## Collector Service (`/signals/ingest`)

### POST /signals/ingest
Ingest raw signals from various sources.

**Request:**
```json
{
  "signals": [
    {
      "source": "linkedin",
      "company_name": "Acme Corp",
      "signal_type": "job_posting",
      "content": "Senior Software Engineer - Cloud Infrastructure",
      "url": "https://linkedin.com/jobs/123",
      "timestamp": "2024-01-15T10:30:00Z",
      "metadata": {
        "location": "San Francisco, CA",
        "department": "Engineering",
        "experience_level": "Senior"
      }
    }
  ]
}
```

**Response:**
```json
{
  "status": "success",
  "processed": 1,
  "errors": [],
  "signal_ids": ["signal_123", "signal_124"]
}
```

## Classifier Service (`/classify`)

### POST /classify
Classify signals and assign fitScores.

**Request:**
```json
{
  "signals": [
    {
      "signal_id": "signal_123",
      "content": "Senior Software Engineer - Cloud Infrastructure",
      "signal_type": "job_posting",
      "company_name": "Acme Corp",
      "metadata": {
        "location": "San Francisco, CA",
        "department": "Engineering"
      }
    }
  ]
}
```

**Response:**
```json
{
  "classifications": [
    {
      "signal_id": "signal_123",
      "label": "buying_intent",
      "fit_score": 0.85,
      "confidence": 0.92,
      "reasoning": "High relevance keywords: cloud, infrastructure, senior level"
    }
  ]
}
```

## Ranker Service

### POST /preference/recompute
Recompute preference indicators for all companies.

**Request:**
```json
{
  "force_refresh": false
}
```

**Response:**
```json
{
  "status": "success",
  "companies_processed": 150,
  "preference_indicators_updated": 45
}
```

### POST /rank
Rank companies based on signals and preferences.

**Request:**
```json
{
  "query": "cloud infrastructure",
  "filters": {
    "min_fit_score": 0.5,
    "signal_types": ["job_posting", "news"],
    "date_range": {
      "start": "2024-01-01",
      "end": "2024-01-31"
    }
  },
  "limit": 20
}
```

**Response:**
```json
{
  "ranked_companies": [
    {
      "company_id": "company_123",
      "company_name": "Acme Corp",
      "rank_score": 0.92,
      "preference_indicator": 0.78,
      "signal_count": 5,
      "avg_fit_score": 0.85,
      "recent_signals": [
        {
          "signal_id": "signal_123",
          "signal_type": "job_posting",
          "fit_score": 0.85,
          "timestamp": "2024-01-15T10:30:00Z"
        }
      ]
    }
  ],
  "total_companies": 150,
  "query_time_ms": 245
}
```

## Orchestrator Service

### POST /run
Start a new intent detection job.

**Request:**
```json
{
  "query": "cloud infrastructure",
  "filters": {
    "min_fit_score": 0.5,
    "signal_types": ["job_posting", "news", "rfp"],
    "industries": ["technology", "finance"]
  },
  "limit": 20,
  "timeout_seconds": 300
}
```

**Response:**
```json
{
  "job_id": "job_abc123",
  "status": "started",
  "estimated_completion": "2024-01-15T10:35:00Z",
  "poll_url": "/run/job_abc123"
}
```

### GET /run/{job_id}
Get job status and results.

**Response:**
```json
{
  "job_id": "job_abc123",
  "status": "completed",
  "progress": 100,
  "results": {
    "ranked_companies": [
      {
        "company_id": "company_123",
        "company_name": "Acme Corp",
        "rank_score": 0.92,
        "evidence": [
          {
            "signal_id": "signal_123",
            "signal_type": "job_posting",
            "content": "Senior Software Engineer - Cloud Infrastructure",
            "fit_score": 0.85,
            "timestamp": "2024-01-15T10:30:00Z"
          }
        ]
      }
    ],
    "total_companies": 150,
    "processing_time_ms": 45000
  },
  "created_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:30:45Z"
}
```

## Error Responses

All endpoints return consistent error formats:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid signal format",
    "details": {
      "field": "content",
      "issue": "Content cannot be empty"
    }
  }
}
```

Common error codes:
- `VALIDATION_ERROR`: Invalid request format
- `SERVICE_UNAVAILABLE`: Service temporarily unavailable
- `TIMEOUT_ERROR`: Request timed out
- `DATABASE_ERROR`: Database connection issues
- `RATE_LIMIT_EXCEEDED`: Too many requests
