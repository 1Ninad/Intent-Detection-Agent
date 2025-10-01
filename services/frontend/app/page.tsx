'use client';

import { useState } from 'react';
import { runSearch, ApiError } from '@/lib/api';
import { RunResponse } from '@/lib/types';
import { formatBuyingSignals } from '@/lib/formatters';

interface Prospect {
  rank: number;
  company: string;
  domain: string;
  fitScore: number;
  reasoning: string;
}

export default function Home() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<Prospect[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [responseMetadata, setResponseMetadata] = useState<{
    processedCompanies: number;
    labeledSignals: number;
    runId: string;
  } | null>(null);

  const handleSearch = async () => {
    if (!query.trim()) return;

    setLoading(true);
    setHasSearched(true);
    setError(null);
    setResults([]);

    try {
      const response: RunResponse = await runSearch({
        freeText: query,
        useWebSearch: true,
        topK: 10,
      });

      // Transform backend response to frontend format
      const transformedResults: Prospect[] = response.results.map((result, index) => {
        // Extract company name from domain (e.g., "salesforce.com" -> "Salesforce")
        const companyName = result.companyId
          .split('.')[0]
          .split('-')
          .map(word => word.charAt(0).toUpperCase() + word.slice(1))
          .join(' ');

        return {
          rank: index + 1,
          company: companyName,
          domain: result.companyId,
          fitScore: Math.round(result.fitScore * 100), // Convert 0-1 to 0-100
          reasoning: formatBuyingSignals(result.reasons), // Convert to sales-friendly format
        };
      });

      setResults(transformedResults);
      setResponseMetadata({
        processedCompanies: response.processedCompanies,
        labeledSignals: response.labeledSignals,
        runId: response.runId,
      });
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
        console.error('API Error:', err.data);
      } else {
        setError('An unexpected error occurred. Please try again.');
        console.error('Unexpected error:', err);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSearch();
    }
  };

  const handleClear = () => {
    setQuery('');
    setResults([]);
    setHasSearched(false);
    setError(null);
    setResponseMetadata(null);
  };

  return (
    <div className="min-h-screen bg-white">
      {/* Navigation */}
      <nav className="border-b border-gray-200 bg-white/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-10">
              <h1 className="text-lg font-semibold text-gray-900">Intent Detection Agent</h1>
            </div>
            <div className="flex items-center gap-3">
              <a
                href="https://github.com/1Ninad/Intent-Detection-Agents"
                target="_blank"
                rel="noopener noreferrer"
                className="text-gray-700 hover:text-gray-900 transition-colors"
              >
                <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                  <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
                </svg>
              </a>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      {!hasSearched && (
        <section className="relative overflow-hidden">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-24">
            <div className="text-center max-w-4xl mx-auto">
              <h2 className="text-5xl sm:text-6xl lg:text-7xl font-bold text-gray-900 tracking-tight mb-6">
                Find customers ready to buy
              </h2>
              <p className="text-xl text-gray-600 mb-10 max-w-2xl mx-auto">
                AI-powered B2B intent detection that automatically discovers companies showing buying signals
              </p>

              {/* Search Input in Hero */}
              <div className="max-w-3xl mx-auto mb-8">
                <div className="bg-white border border-gray-300 rounded-lg overflow-hidden shadow-lg hover:border-emerald-500 transition-colors duration-200 focus-within:border-emerald-500 focus-within:ring-4 focus-within:ring-emerald-100">
                  <textarea
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Describe your product, ideal customer, and buying signals...&#10;&#10;Example: We provide cloud infrastructure software for fintech companies. Looking for companies that recently raised Series A or B funding, are migrating to cloud, or hiring DevOps engineers."
                    className="w-full px-6 py-5 text-gray-900 placeholder-gray-400 resize-none focus:outline-none text-base leading-relaxed bg-white"
                    rows={5}
                  />
                  <div className="border-t border-gray-200 bg-gray-50 px-6 py-4 flex justify-between items-center">
                    <span className="text-sm text-gray-500">Press Enter or click to search</span>
                    <button
                      onClick={handleSearch}
                      disabled={loading || !query.trim()}
                      className="px-8 py-3 bg-emerald-600 text-white text-base font-medium rounded-md hover:bg-emerald-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors duration-150 shadow-sm"
                    >
                      {loading ? 'Searching...' : 'Find Prospects'}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Results Section */}
      {hasSearched && (
        <section className="bg-gray-50 min-h-screen">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
            {/* Search Bar (Compact) */}
            <div className="mb-10">
              <div className="bg-white border border-gray-300 rounded-lg overflow-hidden hover:border-emerald-500 transition-colors duration-200 focus-within:border-emerald-500 focus-within:ring-4 focus-within:ring-emerald-100">
                <textarea
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Describe your product, ideal customer, and buying signals..."
                  className="w-full px-6 py-4 text-gray-900 placeholder-gray-400 resize-none focus:outline-none text-base leading-relaxed bg-white"
                  rows={3}
                />
                <div className="border-t border-gray-200 bg-gray-50 px-6 py-3 flex justify-between items-center">
                  <span className="text-sm text-gray-500">Press Enter to search</span>
                  <button
                    onClick={handleSearch}
                    disabled={loading || !query.trim()}
                    className="px-6 py-2 bg-emerald-600 text-white text-sm font-medium rounded-md hover:bg-emerald-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors duration-150"
                  >
                    {loading ? 'Searching...' : 'Find Prospects'}
                  </button>
                </div>
              </div>
            </div>

            {/* Error State */}
            {error && !loading && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-6 mb-6">
                <div className="flex items-start gap-3">
                  <svg className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <div className="flex-1">
                    <h3 className="text-base font-semibold text-red-900 mb-1">Error</h3>
                    <p className="text-sm text-red-700">{error}</p>
                    <button
                      onClick={handleClear}
                      className="mt-3 text-sm text-red-700 hover:text-red-800 underline"
                    >
                      Clear and try again
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Loading State */}
            {loading && (
              <div className="flex items-center justify-center py-32">
                <div className="text-center">
                  <div className="relative inline-block">
                    <div className="h-12 w-12 animate-spin rounded-full border-4 border-solid border-gray-200 border-t-emerald-500"></div>
                  </div>
                  <p className="text-gray-700 text-base mt-6 font-medium">Analyzing web signals...</p>
                  <p className="text-gray-500 text-sm mt-2">This may take 45-70 seconds</p>
                </div>
              </div>
            )}

            {/* Results Metadata */}
            {!loading && results.length > 0 && responseMetadata && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="bg-white border border-gray-300 rounded-lg p-4">
                  <p className="text-sm text-gray-600 mb-1">Companies Processed</p>
                  <p className="text-2xl font-bold text-gray-900">{responseMetadata.processedCompanies}</p>
                </div>
                <div className="bg-white border border-gray-300 rounded-lg p-4">
                  <p className="text-sm text-gray-600 mb-1">Signals Analyzed</p>
                  <p className="text-2xl font-bold text-gray-900">{responseMetadata.labeledSignals}</p>
                </div>
                <div className="bg-white border border-gray-300 rounded-lg p-4">
                  <p className="text-sm text-gray-600 mb-1">Top Prospects</p>
                  <p className="text-2xl font-bold text-emerald-600">{results.length}</p>
                </div>
              </div>
            )}

            {/* Results Table */}
            {!loading && results.length > 0 && (
              <div className="bg-white border border-gray-300 rounded-lg overflow-hidden animate-fade-in">
                <div className="px-6 py-4 border-b border-gray-200 bg-white">
                  <h3 className="text-base font-semibold text-gray-900">Top {results.length} Prospects</h3>
                  <p className="text-sm text-gray-600 mt-0.5">Ranked by buying intent signals</p>
                </div>
                <div className="overflow-x-auto overflow-y-visible">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-200 bg-gray-50">
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wide">
                          Rank
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wide">
                          Company
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wide">
                          Domain
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wide">
                          Fit Score
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wide">
                          Buying Signals
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {results.map((prospect, index) => (
                        <tr
                          key={prospect.rank}
                          className="hover:bg-gray-50 transition-colors duration-100 group"
                          style={{ animationDelay: `${index * 50}ms` }}
                        >
                          <td className="px-6 py-4 text-sm text-gray-900 font-medium">
                            <div className="flex items-center justify-center w-8 h-8 rounded-md bg-gray-100 group-hover:bg-emerald-100 transition-colors">
                              {prospect.rank}
                            </div>
                          </td>
                          <td className="px-6 py-4 text-[15px] font-medium text-gray-900">
                            {prospect.company}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-600">
                            <a
                              href={`https://${prospect.domain}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="hover:text-emerald-600 transition-colors inline-flex items-center gap-1.5 group/link"
                            >
                              {prospect.domain}
                              <svg className="w-3.5 h-3.5 opacity-0 group-hover/link:opacity-100 transition-opacity" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                              </svg>
                            </a>
                          </td>
                          <td className="px-6 py-4 text-sm">
                            <div className="flex items-center gap-3">
                              <span className={`text-base font-semibold ${
                                prospect.fitScore >= 85 ? 'text-emerald-700' :
                                prospect.fitScore >= 75 ? 'text-emerald-600' :
                                'text-gray-700'
                              }`}>
                                {prospect.fitScore}
                              </span>
                              <div className="w-16 bg-gray-200 rounded-full h-1.5 overflow-hidden">
                                <div
                                  className="bg-emerald-500 h-1.5 rounded-full transition-all duration-1000 ease-out"
                                  style={{
                                    width: `${prospect.fitScore}%`,
                                    transitionDelay: `${index * 100}ms`
                                  }}
                                ></div>
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-600 leading-relaxed max-w-xl">
                            {prospect.reasoning}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* No Results State */}
            {!loading && !error && hasSearched && results.length === 0 && (
              <div className="bg-white border border-gray-300 rounded-lg p-12 text-center">
                <svg className="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">No prospects found</h3>
                <p className="text-gray-600 mb-4">Try refining your search criteria or broadening your query.</p>
                <button
                  onClick={handleClear}
                  className="text-emerald-600 hover:text-emerald-700 font-medium"
                >
                  Start a new search
                </button>
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
