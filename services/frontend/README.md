# Next.js Frontend for Intent Detection Agent

Modern, responsive frontend built with Next.js 14, React 18, and Tailwind CSS.

## Features

- **Modern UI/UX**: Clean, professional design with smooth animations
- **Real-time Integration**: Direct connection to orchestrator backend API
- **Responsive Design**: Works seamlessly on desktop, tablet, and mobile
- **Error Handling**: Comprehensive error states and user feedback
- **TypeScript**: Full type safety with backend API contracts
- **Performance**: Optimized with Next.js App Router and React Server Components

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **UI Library**: React 18
- **Styling**: Tailwind CSS 3.4
- **Language**: TypeScript 5
- **API Client**: Native Fetch API with error handling

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn
- Backend orchestrator running on port 8004

### Installation

```bash
cd services/frontend_new
npm install
```

### Configuration

Create a `.env.local` file (or copy from `.env.example`):

```bash
cp .env.example .env.local
```

Edit `.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8004
```

### Development

Start the development server:

```bash
npm run dev
```

Or use the startup script:

```bash
./start_frontend.sh
```

The frontend will be available at [http://localhost:3000](http://localhost:3000)

### Production Build

Build for production:

```bash
npm run build
npm start
```

## Project Structure

```
services/frontend_new/
├── app/
│   ├── layout.tsx       # Root layout component
│   ├── page.tsx         # Main search page
│   └── globals.css      # Global styles
├── lib/
│   ├── api.ts           # API client functions
│   └── types.ts         # TypeScript interfaces
├── .env.local           # Environment variables (local)
├── .env.example         # Environment template
├── package.json         # Dependencies
├── tailwind.config.ts   # Tailwind configuration
└── tsconfig.json        # TypeScript configuration
```

## API Integration

The frontend communicates with the orchestrator backend through a clean API client:

```typescript
// Example usage
import { runSearch } from '@/lib/api';

const response = await runSearch({
  freeText: 'Find SaaS companies in Europe...',
  useWebSearch: true,
  topK: 10,
});
```

### Response Format

The backend returns:

```typescript
interface RunResponse {
  runId: string;
  processedCompanies: number;
  labeledSignals: number;
  results: ProspectResult[];
  debug?: {
    webSignalsCount: number;
    ingestStats: {...};
    runAt: string;
  };
}
```

## Features

### Search Interface

- **Natural Language Input**: Users describe their ICP in plain English
- **Real-time Search**: Integrated with backend web search and signal analysis
- **Loading States**: Clear feedback during 45-70 second processing time

### Results Display

- **Ranked Prospects**: Top companies sorted by fit score
- **Metadata Cards**: Shows companies processed, signals analyzed, and top prospects
- **Interactive Table**: Clickable domains, color-coded scores, detailed reasoning
- **Animations**: Smooth transitions and staggered result rendering

### Error Handling

- **Connection Errors**: Clear messaging when backend is unavailable
- **API Errors**: Displays specific error messages from backend
- **Validation**: Client-side validation before API calls
- **Recovery**: Easy reset and retry mechanisms

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_BASE_URL` | Orchestrator API base URL | `http://localhost:8004` |

## Deployment

### Vercel (Recommended)

1. Push your code to GitHub
2. Import project in Vercel
3. Set environment variables:
   - `NEXT_PUBLIC_API_BASE_URL`: Your production backend URL
4. Deploy

### Docker

Build Docker image:

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

Run:

```bash
docker build -t intent-frontend .
docker run -p 3000:3000 -e NEXT_PUBLIC_API_BASE_URL=http://your-backend:8004 intent-frontend
```

## Troubleshooting

**Error: "Cannot connect to backend service"**
- Ensure orchestrator is running: `curl http://localhost:8004/`
- Check `.env.local` has correct `NEXT_PUBLIC_API_BASE_URL`
- Verify no CORS issues (backend should allow frontend origin)

**Build errors**
- Clear Next.js cache: `rm -rf .next`
- Reinstall dependencies: `rm -rf node_modules && npm install`

**Slow initial load**
- First search takes 45-70 seconds (backend web search)
- Subsequent searches may be faster if data is cached

## Comparison with Streamlit Frontend

| Feature | Streamlit | Next.js |
|---------|-----------|---------|
| Tech | Python | TypeScript/React |
| Performance | Server-rendered | Client-side + SSR |
| UI/UX | Simple | Modern, polished |
| Customization | Limited | Highly flexible |
| Mobile | Basic | Fully responsive |
| Deployment | Python server | Edge/CDN optimized |

## Contributing

1. Follow TypeScript strict mode
2. Use Tailwind utility classes (avoid custom CSS)
3. Maintain responsive design (mobile-first)
4. Add proper error handling
5. Update types when API changes

## License

Same as main project
