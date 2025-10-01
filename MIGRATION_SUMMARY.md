# Frontend Migration Summary

## Overview

Successfully migrated from Streamlit-based frontend to a modern Next.js/React frontend while maintaining full integration with the existing backend orchestrator API.

## What Was Done

### 1. Created Next.js Frontend (`services/frontend_new/`)

**New Files Created:**
- `app/page.tsx` - Main search interface with real API integration
- `app/layout.tsx` - Root layout configuration
- `lib/api.ts` - API client with error handling
- `lib/types.ts` - TypeScript interfaces matching backend API
- `.env.local` - Environment configuration
- `.env.example` - Environment template
- `README.md` - Frontend-specific documentation
- `start_frontend.sh` - Frontend startup script

**Key Features:**
- ✅ Full TypeScript support with strict type checking
- ✅ Real-time integration with orchestrator backend (port 8004)
- ✅ Modern, responsive UI with Tailwind CSS
- ✅ Comprehensive error handling and loading states
- ✅ Results metadata display (companies processed, signals analyzed)
- ✅ Animated results table with fit scores
- ✅ Mobile-responsive design

### 2. Backend Integration

**API Client (`lib/api.ts`):**
```typescript
- runSearch(): Calls POST /run endpoint
- healthCheck(): Verifies backend availability
- ApiError class: Custom error handling
- Automatic CORS and connection error detection
```

**Type Safety (`lib/types.ts`):**
```typescript
- RunRequest: Request payload interface
- RunResponse: Response data interface
- ProspectResult: Individual prospect structure
```

**Request Flow:**
```
User Input → runSearch() → POST /run → Transform Response → Display Results
```

### 3. Scripts and Configuration

**Startup Scripts:**
- `run_demo_nextjs.sh` - Complete system startup (databases + backend + Next.js)
- `services/frontend_new/start_frontend.sh` - Frontend-only startup

**Environment Variables:**
- `NEXT_PUBLIC_API_BASE_URL` - Backend API endpoint (default: http://localhost:8004)

### 4. Documentation Updates

**Updated Files:**
- `README.md` - Added Next.js sections, updated usage instructions
- `.gitignore` - Added Next.js ignore patterns
- `services/frontend_new/README.md` - Comprehensive frontend documentation

## Migration Checklist

- ✅ Create Next.js project structure
- ✅ Implement TypeScript interfaces for API
- ✅ Build API client with error handling
- ✅ Migrate UI from Streamlit to React components
- ✅ Add loading states and error boundaries
- ✅ Create environment configuration
- ✅ Add startup scripts
- ✅ Update documentation
- ✅ Configure .gitignore for Node.js

## How to Use

### Quick Start

```bash
# One-command startup (recommended)
./run_demo_nextjs.sh

# Then open: http://localhost:3000
```

### Manual Start

```bash
# Terminal 1: Databases
docker-compose up -d

# Terminal 2: Backend
python -m uvicorn services.orchestrator.app:app --host 0.0.0.0 --port 8004

# Terminal 3: Frontend
cd services/frontend_new
npm install  # First time only
npm run dev
```

## API Integration Details

### Request Format

```typescript
POST http://localhost:8004/run

{
  "freeText": "Find SaaS companies...",
  "useWebSearch": true,
  "topK": 10,
  "configId": "default",
  "webSearchOptions": {
    "recency": "month",
    "maxResultsPerTask": 10
  }
}
```

### Response Format

```typescript
{
  "runId": "run_20251001220000",
  "processedCompanies": 8,
  "labeledSignals": 24,
  "results": [
    {
      "companyId": "example.com",
      "fitScore": 0.85,
      "reasons": ["techSignals 0.90", "recentVolume 0.75"]
    }
  ],
  "debug": {
    "webSignalsCount": 10,
    "ingestStats": {...},
    "runAt": "2025-10-01T22:00:00Z"
  }
}
```

### Data Transformation

Backend returns `fitScore` as 0-1 (e.g., 0.85), frontend displays as 0-100 (85).

```typescript
// In page.tsx handleSearch()
fitScore: Math.round(result.fitScore * 100)
```

## Comparison: Streamlit vs Next.js

| Aspect | Streamlit | Next.js |
|--------|-----------|---------|
| **Technology** | Python | TypeScript/React |
| **Performance** | Server-side rendering | Client-side + SSR/SSG |
| **UI/UX** | Simple, basic | Modern, polished |
| **Customization** | Limited | Highly flexible |
| **Mobile** | Basic responsive | Fully responsive |
| **Error Handling** | Basic | Comprehensive |
| **Loading States** | Spinner only | Progress indicators + metadata |
| **Deployment** | Python server | Edge/CDN optimized |
| **Development** | Quick prototyping | Production-grade |

## Architecture

```
┌─────────────────────────────────────────────────┐
│            Next.js Frontend (Port 3000)         │
│  ┌──────────────────────────────────────────┐  │
│  │  app/page.tsx (React Component)          │  │
│  │  - User input                            │  │
│  │  - Search trigger                        │  │
│  │  - Results display                       │  │
│  └────────────┬─────────────────────────────┘  │
│               │                                 │
│  ┌────────────▼─────────────────────────────┐  │
│  │  lib/api.ts (API Client)                 │  │
│  │  - runSearch()                           │  │
│  │  - Error handling                        │  │
│  │  - Type safety                           │  │
│  └────────────┬─────────────────────────────┘  │
└───────────────┼─────────────────────────────────┘
                │ HTTP POST /run
                │
┌───────────────▼─────────────────────────────────┐
│      Orchestrator API (Port 8004)               │
│  ┌──────────────────────────────────────────┐  │
│  │  FastAPI Endpoint                        │  │
│  │  - Request validation                    │  │
│  │  - Pipeline execution                    │  │
│  │  - Response formatting                   │  │
│  └────────────┬─────────────────────────────┘  │
│               │                                 │
│  ┌────────────▼─────────────────────────────┐  │
│  │  LangGraph Pipeline (flow.py)            │  │
│  │  - Web search (Perplexity)               │  │
│  │  - Signal ingestion (Neo4j/Qdrant)       │  │
│  │  - Classification (OpenAI)               │  │
│  │  - Scoring & ranking                     │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

## Testing

### Verify Integration

1. **Backend Health:**
```bash
curl http://localhost:8004/
# Expected: {"status":"ok"}
```

2. **Frontend Access:**
```bash
open http://localhost:3000
# Should load Next.js UI
```

3. **End-to-End Test:**
- Enter query: "Find SaaS companies in Europe that raised Series A"
- Click "Find Prospects"
- Wait 45-70 seconds
- Verify results table displays with fit scores

## Troubleshooting

### Common Issues

**1. "Cannot connect to backend service"**
```bash
# Check orchestrator is running
curl http://localhost:8004/

# Check .env.local
cat services/frontend_new/.env.local
# Should have: NEXT_PUBLIC_API_BASE_URL=http://localhost:8004
```

**2. Port 3000 already in use**
```bash
# Find process
lsof -i :3000

# Kill process
kill -9 <PID>

# Or use different port
npm run dev -- -p 3001
```

**3. TypeScript errors**
```bash
cd services/frontend_new
rm -rf .next
npm run build
```

## Future Enhancements

### Potential Features
- [ ] User authentication and sessions
- [ ] Save/favorite prospects
- [ ] Export results to CSV/JSON
- [ ] Real-time search progress updates (WebSockets)
- [ ] Advanced filters (industry, geo, funding stage)
- [ ] Search history
- [ ] Analytics dashboard
- [ ] A/B testing for ranking algorithms
- [ ] Integration with CRM systems

### Performance Optimizations
- [ ] Result caching (Redis)
- [ ] Pagination for large result sets
- [ ] Progressive loading of results
- [ ] Search query suggestions
- [ ] Background job queue for long searches

## Deployment

### Vercel (Recommended for Frontend)

```bash
cd services/frontend_new
vercel deploy

# Set environment variable in Vercel dashboard:
# NEXT_PUBLIC_API_BASE_URL=https://your-backend-api.com
```

### Docker (Full Stack)

```dockerfile
# services/frontend_new/Dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

```bash
docker build -t intent-frontend services/frontend_new
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_API_BASE_URL=http://backend:8004 \
  intent-frontend
```

## Conclusion

The migration to Next.js provides:
- ✅ Modern, professional user interface
- ✅ Full TypeScript type safety
- ✅ Better error handling and user feedback
- ✅ Mobile-responsive design
- ✅ Production-ready deployment options
- ✅ Maintainable, scalable codebase

The Streamlit frontend remains available at `services/frontend/` for legacy support, but the Next.js frontend is now the recommended production interface.

---

**Migration Date:** October 1, 2025
**Next.js Version:** 14.2.5
**React Version:** 18
**TypeScript Version:** 5
