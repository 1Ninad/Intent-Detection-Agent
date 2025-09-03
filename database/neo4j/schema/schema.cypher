-- Neo4j Schema for Intent Detection Agents
-- This file contains all node labels, relationships, constraints, and indexes

-- Node Labels
-- Company: Represents companies in the system
-- Signal: Represents buying intent signals (jobs, RFPs, news, etc.)

-- Relationships
-- Company -[:HAS_SIGNAL]-> Signal
-- Company -[:SIMILAR_TO]-> Company (for preference modeling)

-- Constraints
CREATE CONSTRAINT company_id_unique IF NOT EXISTS FOR (c:Company) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT signal_id_unique IF NOT EXISTS FOR (s:Signal) REQUIRE s.id IS UNIQUE;

-- Indexes for performance
CREATE INDEX company_name_index IF NOT EXISTS FOR (c:Company) ON (c.name);
CREATE INDEX signal_timestamp_index IF NOT EXISTS FOR (s:Signal) ON (s.timestamp);
CREATE INDEX signal_type_index IF NOT EXISTS FOR (s:Signal) ON (s.signal_type);
CREATE INDEX signal_label_index IF NOT EXISTS FOR (s:Signal) ON (s.label);
CREATE INDEX signal_source_index IF NOT EXISTS FOR (s:Signal) ON (s.source);

-- Composite indexes for common queries
CREATE INDEX signal_company_timestamp_index IF NOT EXISTS FOR (s:Signal) ON (s.company_id, s.timestamp);
CREATE INDEX signal_type_label_index IF NOT EXISTS FOR (s:Signal) ON (s.signal_type, s.label);

-- Text search indexes
CREATE TEXT INDEX company_name_text_index IF NOT EXISTS FOR (c:Company) ON (c.name);
CREATE TEXT INDEX signal_content_text_index IF NOT EXISTS FOR (s:Signal) ON (s.content);

-- Example data insertion
-- Companies
CREATE (c1:Company {
    id: "company_123",
    name: "Acme Corporation",
    industry: "technology",
    size: "large",
    location: "San Francisco, CA",
    website: "https://acme.com",
    created_at: datetime(),
    updated_at: datetime()
});

CREATE (c2:Company {
    id: "company_456",
    name: "TechStart Inc",
    industry: "technology",
    size: "startup",
    location: "Austin, TX",
    website: "https://techstart.com",
    created_at: datetime(),
    updated_at: datetime()
});

-- Signals
CREATE (s1:Signal {
    id: "signal_123",
    source: "linkedin",
    signal_type: "job_posting",
    content: "Senior Software Engineer - Cloud Infrastructure",
    url: "https://linkedin.com/jobs/123",
    timestamp: datetime("2024-01-15T10:30:00Z"),
    label: "buying_intent",
    fit_score: 0.85,
    confidence: 0.92,
    reasoning: "High relevance: cloud infrastructure, senior level",
    created_at: datetime(),
    updated_at: datetime()
});

CREATE (s2:Signal {
    id: "signal_124",
    source: "news_api",
    signal_type: "news_article",
    content: "Acme Corp announces new cloud migration initiative",
    url: "https://news.com/article/456",
    timestamp: datetime("2024-01-14T15:20:00Z"),
    label: "buying_intent",
    fit_score: 0.78,
    confidence: 0.88,
    reasoning: "Cloud migration indicates infrastructure investment",
    created_at: datetime(),
    updated_at: datetime()
});

-- Relationships
CREATE (c1)-[:HAS_SIGNAL]->(s1);
CREATE (c1)-[:HAS_SIGNAL]->(s2);

-- Similarity relationship for preference modeling
CREATE (c1)-[:SIMILAR_TO {similarity_score: 0.75}]->(c2);
CREATE (c2)-[:SIMILAR_TO {similarity_score: 0.75}]->(c1);
