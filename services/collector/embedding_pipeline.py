"""
Embedding pipeline for generating embeddings and storing in Qdrant.
Handles deduplication, semantic search, and metadata management.
"""

import asyncio
import uuid
import hashlib
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import json
from datetime import datetime

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import numpy as np

from source_adapters import RawSignal

logger = logging.getLogger(__name__)

def hash_to_uuid(hash_string: str) -> str:
    """Convert SHA-256 hash to UUID format"""
    hex_str = hash_string[:32]
    return str(uuid.UUID(hex_str))


@dataclass
class ProcessedSignal:
    """Signal after entity resolution and embedding generation"""
    id: str
    raw_signal: RawSignal
    resolved_companies: List[Dict[str, Any]]
    resolved_people: List[Dict[str, Any]]
    resolved_technologies: List[Dict[str, Any]]
    embedding: List[float]
    dedupe_key: str
    processed_at: str

class EmbeddingGenerator:
    """Generate embeddings for signals"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model_type = config.get('model_type', 'sentence_transformer')
        
        if self.model_type == 'openai':
            # Updated for OpenAI >= 1.0.0
            from openai import AsyncOpenAI
            api_key = config.get('openai_api_key')
            if not api_key:
                raise ValueError("OpenAI API key is required when using OpenAI embeddings")
            
            self.openai_client = AsyncOpenAI(api_key=api_key)
            self.model_name = config.get('openai_model', 'text-embedding-3-small')
        elif self.model_type == 'sentence_transformer':
            self.model_name = config.get('model_name', 'all-MiniLM-L6-v2')
            self.model = SentenceTransformer(self.model_name)
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        try:
            if self.model_type == 'openai':
                # Updated API call for OpenAI >= 1.0.0
                response = await self.openai_client.embeddings.create(
                    model=self.model_name,
                    input=text
                )
                return response.data[0].embedding
            
            elif self.model_type == 'sentence_transformer':
                # Run in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                embedding = await loop.run_in_executor(
                    None, 
                    lambda: self.model.encode(text).tolist()
                )
                return embedding
                
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return []
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings"""
        if self.model_type == 'openai':
            if 'text-embedding-3-small' in self.model_name:
                return 1536
            elif 'text-embedding-3-large' in self.model_name:
                return 3072
            elif 'text-embedding-ada-002' in self.model_name:
                return 1536
        elif self.model_type == 'sentence_transformer':
            return self.model.get_sentence_embedding_dimension()
        return 384  # Default fallback

class EntityResolver:
    """Resolve entity mentions to knowledge graph entities"""
    
    def __init__(self, graph_api_client):
        self.graph_api = graph_api_client
    
    async def resolve_companies(self, mentions: List[str]) -> List[Dict[str, Any]]:
        """Resolve company mentions to graph entities"""
        resolved = []
        for mention in mentions:
            if not mention.strip():
                continue
                
            # Simple fuzzy matching (in production, use more sophisticated NER/linking)
            company = await self.graph_api.find_company_by_name(mention.strip())
            if company:
                resolved.append(company)
            else:
                # Create new company entity if not found
                company = await self.graph_api.create_company({
                    'name': mention.strip(),
                    'source': 'auto_detected'
                })
                resolved.append(company)
        
        return resolved
    
    async def resolve_people(self, mentions: List[str]) -> List[Dict[str, Any]]:
        """Resolve person mentions to graph entities"""
        resolved = []
        for mention in mentions:
            if not mention.strip():
                continue
                
            person = await self.graph_api.find_person_by_name(mention.strip())
            if person:
                resolved.append(person)
            else:
                # Create new person entity
                person = await self.graph_api.create_person({
                    'name': mention.strip(),
                    'source': 'auto_detected'
                })
                resolved.append(person)
        
        return resolved
    
    async def resolve_technologies(self, mentions: List[str]) -> List[Dict[str, Any]]:
        """Resolve technology mentions to graph entities"""
        resolved = []
        for mention in mentions:
            if not mention.strip():
                continue
                
            tech = await self.graph_api.find_technology_by_name(mention.strip())
            if tech:
                resolved.append(tech)
            else:
                # Create new technology entity
                tech = await self.graph_api.create_technology({
                    'name': mention.strip(),
                    'category': 'auto_detected'
                })
                resolved.append(tech)
        
        return resolved

class QdrantManager:
    """Manage Qdrant collections and operations"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client = QdrantClient(
            host=config.get('host', 'localhost'),
            port=config.get('port', 6333)
        )
        self.collection_name = config.get('collection_name', 'signals')
        self.embedding_dim = config.get('embedding_dimension', 384)
    
    async def setup_collection(self):
        """Initialize Qdrant collection"""
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_exists = any(
                col.name == self.collection_name 
                for col in collections.collections
            )
            
            if not collection_exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dim,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
            else:
                logger.info(f"Collection {self.collection_name} already exists")
                
        except Exception as e:
            logger.error(f"Error setting up Qdrant collection: {e}")
            raise
    
    async def store_signal(self, processed_signal: ProcessedSignal) -> bool:
        """Store processed signal in Qdrant"""
        try:
            # Check for duplicates using dedupe_key
            search_result = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="dedupe_key",
                            match=models.MatchValue(value=processed_signal.dedupe_key)
                        )
                    ]
                ),
                limit=1
            )
            
            if search_result[0]:  # If duplicate found
                logger.info(f"Duplicate signal found for dedupe_key: {processed_signal.dedupe_key}")
                return False
            
            # Create point with metadata
            point = PointStruct(
                id=processed_signal.id,
                vector=processed_signal.embedding,
                payload={
                    'dedupe_key': processed_signal.dedupe_key,
                    'source': processed_signal.raw_signal.source,
                    'signal_type': processed_signal.raw_signal.signal_type,
                    'title': processed_signal.raw_signal.title,
                    'content': processed_signal.raw_signal.content[:1000],  # Truncate for storage
                    'url': processed_signal.raw_signal.url,
                    'published_date': processed_signal.raw_signal.published_date,
                    'processed_at': processed_signal.processed_at,
                    'company_ids': [c.get('id') for c in processed_signal.resolved_companies],
                    'person_ids': [p.get('id') for p in processed_signal.resolved_people],
                    'technology_ids': [t.get('id') for t in processed_signal.resolved_technologies],
                    'company_names': [c.get('name') for c in processed_signal.resolved_companies],
                    'person_names': [p.get('name') for p in processed_signal.resolved_people],
                    'technology_names': [t.get('name') for t in processed_signal.resolved_technologies]
                }
            )
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            logger.info(f"Stored signal: {processed_signal.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing signal in Qdrant: {e}")
            return False
    
    async def similarity_search(self, query_embedding: List[float], 
                              limit: int = 10, 
                              filter_conditions: Dict = None) -> List[Dict[str, Any]]:
        """Perform similarity search"""
        try:
            search_filter = None
            if filter_conditions:
                conditions = []
                for key, value in filter_conditions.items():
                    conditions.append(
                        models.FieldCondition(
                            key=key,
                            match=models.MatchValue(value=value)
                        )
                    )
                search_filter = models.Filter(must=conditions)
            
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=limit,
                with_payload=True
            )
            
            return [
                {
                    'id': result.id,
                    'score': result.score,
                    'payload': result.payload
                }
                for result in results
            ]
            
        except Exception as e:
            logger.error(f"Error in similarity search: {e}")
            return []

class DedupeManager:
    """Handle signal deduplication"""
    
    @staticmethod
    def generate_dedupe_key(signal: RawSignal) -> str:
        """Generate deduplication key for signal"""
        # Combine title, content snippet, and source for dedup
        content_snippet = signal.content[:200] if signal.content else ""
        dedupe_content = f"{signal.source}_{signal.title}_{content_snippet}"
        
        # Normalize whitespace and case
        normalized = " ".join(dedupe_content.lower().split())
        
        # Generate hash
        return hashlib.sha256(normalized.encode()).hexdigest()

class IngestionPipeline:
    """Main ingestion pipeline orchestrator"""
    
    def __init__(self, config: Dict[str, Any], graph_api_client, embedding_generator: EmbeddingGenerator):
        self.config = config
        self.graph_api = graph_api_client
        self.embedding_generator = embedding_generator
        self.entity_resolver = EntityResolver(graph_api_client)
        self.qdrant_manager = QdrantManager(config.get('qdrant', {}))
        self.dedupe_manager = DedupeManager()
    
    async def setup(self):
        """Initialize pipeline components"""
        await self.qdrant_manager.setup_collection()
    
    def create_embedding_text(self, signal: RawSignal) -> str:
        """Create text for embedding generation"""
        parts = [signal.title]
        if signal.content:
            parts.append(signal.content)
        
        # Add entity mentions for richer context
        if signal.company_mentions:
            parts.append(f"Companies: {', '.join(signal.company_mentions)}")
        if signal.technology_mentions:
            parts.append(f"Technologies: {', '.join(signal.technology_mentions)}")
        if signal.person_mentions:
            parts.append(f"People: {', '.join(signal.person_mentions)}")
        
        return " | ".join(parts)
    
    async def process_signal(self, raw_signal: RawSignal) -> Optional[ProcessedSignal]:
        """Process a single raw signal through the full pipeline"""
        try:
            # Generate dedupe key
            dedupe_key = self.dedupe_manager.generate_dedupe_key(raw_signal)
            
            # Entity resolution
            resolved_companies = await self.entity_resolver.resolve_companies(
                raw_signal.company_mentions
            )
            resolved_people = await self.entity_resolver.resolve_people(
                raw_signal.person_mentions
            )
            resolved_technologies = await self.entity_resolver.resolve_technologies(
                raw_signal.technology_mentions
            )
            
            # Generate embedding
            embedding_text = self.create_embedding_text(raw_signal)
            embedding = await self.embedding_generator.generate_embedding(embedding_text)
            
            if not embedding:
                logger.error(f"Failed to generate embedding for signal: {raw_signal.title}")
                return None
            
            base_hash = hashlib.sha256(f"{dedupe_key}_{raw_signal.source}".encode()).hexdigest()
            signal_id = hash_to_uuid(base_hash)

            # Create processed signal
            processed_signal = ProcessedSignal(
                id=signal_id,
                raw_signal=raw_signal,
                resolved_companies=resolved_companies,
                resolved_people=resolved_people,
                resolved_technologies=resolved_technologies,
                embedding=embedding,
                dedupe_key=dedupe_key,
                processed_at=datetime.utcnow().isoformat()
            )
            
            return processed_signal
            
        except Exception as e:
            logger.error(f"Error processing signal: {e}")
            return None
    
    async def process_batch(self, raw_signals: List[RawSignal]) -> Tuple[List[ProcessedSignal], List[str]]:
        """Process a batch of raw signals"""
        processed_signals = []
        error_logs = []
        
        # Process in parallel with concurrency limit
        semaphore = asyncio.Semaphore(self.config.get('max_concurrent_processing', 10))
        
        async def process_with_semaphore(signal):
            async with semaphore:
                return await self.process_signal(signal)
        
        tasks = [process_with_semaphore(signal) for signal in raw_signals]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_msg = f"Error processing signal {i}: {result}"
                error_logs.append(error_msg)
                logger.error(error_msg)
            elif result is not None:
                processed_signals.append(result)
        
        return processed_signals, error_logs
    
    async def store_signals(self, processed_signals: List[ProcessedSignal]) -> Tuple[int, int]:
        """Store processed signals in Qdrant and Neo4j"""
        stored_count = 0
        duplicate_count = 0
        
        for signal in processed_signals:
            # Store in Qdrant
            stored = await self.qdrant_manager.store_signal(signal)
            if stored:
                stored_count += 1
                
                # Store in Neo4j graph
                await self.store_in_graph(signal)
            else:
                duplicate_count += 1
        
        return stored_count, duplicate_count
    
    async def store_in_graph(self, processed_signal: ProcessedSignal):
        """Store signal and relationships in Neo4j"""
        try:
            # Create Signal node
            signal_data = {
                'id': processed_signal.id,
                'dedupe_key': processed_signal.dedupe_key,
                'source': processed_signal.raw_signal.source,
                'signal_type': processed_signal.raw_signal.signal_type,
                'title': processed_signal.raw_signal.title,
                'content': processed_signal.raw_signal.content,
                'url': processed_signal.raw_signal.url,
                'published_date': processed_signal.raw_signal.published_date,
                'processed_at': processed_signal.processed_at
            }
            
            signal_node = await self.graph_api.create_signal(signal_data)
            
            # Create relationships
            for company in processed_signal.resolved_companies:
                await self.graph_api.create_relationship(
                    company['id'], 'HAS_SIGNAL', signal_node['id']
                )
            
            for person in processed_signal.resolved_people:
                await self.graph_api.create_relationship(
                    person['id'], 'MENTIONED_IN', signal_node['id']
                )
            
            for technology in processed_signal.resolved_technologies:
                await self.graph_api.create_relationship(
                    technology['id'], 'MENTIONED_IN', signal_node['id']
                )
            
            logger.info(f"Stored signal in graph: {processed_signal.id}")
            
        except Exception as e:
            logger.error(f"Error storing signal in graph: {e}")

class SimilaritySearcher:
    """Handle similarity searches and related queries"""
    
    def __init__(self, qdrant_manager: QdrantManager, embedding_generator: EmbeddingGenerator):
        self.qdrant_manager = qdrant_manager
        self.embedding_generator = embedding_generator
    
    async def search_similar_signals(self, 
                                   query_text: str, 
                                   limit: int = 10,
                                   filter_by: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Search for similar signals using semantic similarity"""
        try:
            # Generate embedding for query
            query_embedding = await self.embedding_generator.generate_embedding(query_text)
            if not query_embedding:
                return []
            
            # Perform similarity search
            results = await self.qdrant_manager.similarity_search(
                query_embedding=query_embedding,
                limit=limit,
                filter_conditions=filter_by
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error in similarity search: {e}")
            return []
    
    async def find_signals_for_company(self, company_name: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Find all signals related to a specific company"""
        return await self.search_similar_signals(
            query_text=f"company {company_name}",
            limit=limit,
            filter_by={'company_names': company_name}
        )
    
    async def find_technology_trends(self, technology: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Find signals related to technology trends"""
        return await self.search_similar_signals(
            query_text=f"technology {technology} trend adoption",
            limit=limit,
            filter_by={'signal_type': 'tech_mention'}
        )

# Configuration example
EMBEDDING_CONFIG = {
    'model_type': 'sentence_transformer',  # or 'openai'
    'model_name': 'all-MiniLM-L6-v2',
    'max_concurrent_processing': 10,
    'qdrant': {
        'host': 'localhost',
        'port': 6333,
        'collection_name': 'signals',
        'embedding_dimension': 384  # Should match your embedding model
    }
}

# Example pipeline usage
async def run_ingestion_pipeline(raw_signals: List[RawSignal], 
                               config: Dict[str, Any], 
                               graph_api_client) -> Dict[str, Any]:
    """Run the complete ingestion pipeline"""
    
    # Initialize components
    embedding_generator = EmbeddingGenerator(config)
    pipeline = IngestionPipeline(config, graph_api_client, embedding_generator)
    
    # Setup
    await pipeline.setup()
    
    # Process signals
    logger.info(f"Processing {len(raw_signals)} raw signals...")
    processed_signals, errors = await pipeline.process_batch(raw_signals)
    
    # Store signals
    logger.info(f"Storing {len(processed_signals)} processed signals...")
    stored_count, duplicate_count = await pipeline.store_signals(processed_signals)
    
    # Return statistics
    stats = {
        'raw_signals_count': len(raw_signals),
        'processed_signals_count': len(processed_signals),
        'stored_count': stored_count,
        'duplicate_count': duplicate_count,
        'error_count': len(errors),
        'errors': errors
    }
    
    logger.info(f"Pipeline completed: {stats}")
    return stats

# Example similarity search usage
async def demo_similarity_search(config: Dict[str, Any]):
    """Demonstrate similarity search capabilities"""
    
    embedding_generator = EmbeddingGenerator(config)
    qdrant_manager = QdrantManager(config.get('qdrant', {}))
    searcher = SimilaritySearcher(qdrant_manager, embedding_generator)
    
    # Search for AI-related signals
    ai_signals = await searcher.search_similar_signals(
        "artificial intelligence machine learning startup funding",
        limit=5
    )
    
    print("AI-related signals:")
    for signal in ai_signals:
        print(f"- {signal['payload']['title']} (score: {signal['score']:.3f})")
    
    # Search for specific company
    company_signals = await searcher.find_signals_for_company("TechCorp", limit=5)
    print(f"\nTechCorp signals: {len(company_signals)} found")
    
    # Search for technology trends
    react_trends = await searcher.find_technology_trends("React", limit=5)
    print(f"\nReact trend signals: {len(react_trends)} found")

if __name__ == "__main__":
    # Example usage
    async def main():
        config = EMBEDDING_CONFIG
        
        # Mock graph API client (replace with actual implementation)
        class MockGraphAPI:
            async def find_company_by_name(self, name): return None
            async def create_company(self, data): return {'id': f'company_{hash(data["name"])}', 'name': data['name']}
            async def find_person_by_name(self, name): return None
            async def create_person(self, data): return {'id': f'person_{hash(data["name"])}', 'name': data['name']}
            async def find_technology_by_name(self, name): return None
            async def create_technology(self, data): return {'id': f'tech_{hash(data["name"])}', 'name': data['name']}
            async def create_signal(self, data): return {'id': data['id']}
            async def create_relationship(self, from_id, rel_type, to_id): pass
        
        graph_api = MockGraphAPI()
        
        # Create sample signals
        sample_signals = [
            RawSignal(
                source="test",
                signal_type="news",
                title="TechCorp raises Series A funding",
                content="TechCorp announced $5M Series A funding for AI development",
                url="https://example.com/news/1",
                published_date="2024-08-30",
                raw_data={},
                company_mentions=["TechCorp"],
                technology_mentions=["AI"]
            )
        ]
        
        # Run pipeline
        stats = await run_ingestion_pipeline(sample_signals, config, graph_api)
        print(f"Pipeline stats: {stats}")
    
    asyncio.run(main())