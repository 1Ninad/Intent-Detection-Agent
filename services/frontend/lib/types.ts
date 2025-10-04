// TypeScript interfaces matching the backend API

export interface ProspectResult {
  companyId: string;
  fitScore: number;
  reasons: string[];
}

export interface RunResponse {
  runId: string;
  processedCompanies: number;
  labeledSignals: number;
  results: ProspectResult[];
  echo?: {
    configId: string;
    topK: number;
    useWebSearch: boolean;
    hasFreeText: boolean;
  };
  debug?: {
    webSignalsCount: number;
    ingestStats: {
      companies: number;
      signals: number;
      embeddings: number;
    };
    runAt: string;
  };
}

export interface RunRequest {
  freeText: string;
  useWebSearch?: boolean;
  topK?: number;
  configId?: string;
  webSearchOptions?: {
    recency?: 'week' | 'month';
    maxResultsPerTask?: number;
  };
}
