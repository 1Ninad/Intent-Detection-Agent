"""
Configuration management for TTL, rate limits, and source settings.
Supports dynamic configuration updates and monitoring.
"""

import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import yaml
import os

logger = logging.getLogger(__name__)

@dataclass
class SourceConfig:
    """Configuration for a specific source"""
    enabled: bool = True
    requests_per_minute: int = 60
    cache_ttl: int = 3600  # seconds
    user_agent: str = "EDI-Graph/1.0"
    retry_attempts: int = 3
    retry_backoff_factor: float = 2.0
    timeout: int = 30
    api_keys: Dict[str, str] = None
    custom_headers: Dict[str, str] = None
    
    def __post_init__(self):
        if self.api_keys is None:
            self.api_keys = {}
        if self.custom_headers is None:
            self.custom_headers = {}

@dataclass
class QdrantConfig:
    """Qdrant-specific configuration"""
    host: str = "localhost"
    port: int = 6333
    collection_name: str = "signals"
    embedding_dimension: int = 384
    similarity_threshold: float = 0.8
    max_results: int = 1000

@dataclass
class EmbeddingConfig:
    """Embedding generation configuration"""
    model_type: str = "sentence_transformer"  # or "openai"
    model_name: str = "all-MiniLM-L6-v2"
    openai_api_key: str = ""
    batch_size: int = 32
    max_concurrent_processing: int = 10

@dataclass
class IngestionConfig:
    """Main ingestion pipeline configuration"""
    sources: Dict[str, SourceConfig]
    qdrant: QdrantConfig
    embedding: EmbeddingConfig
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    log_level: str = "INFO"
    metrics_enabled: bool = True
    
    def __post_init__(self):
        if not isinstance(self.sources, dict):
            self.sources = {}
        if not isinstance(self.qdrant, QdrantConfig):
            self.qdrant = QdrantConfig()
        if not isinstance(self.embedding, EmbeddingConfig):
            self.embedding = EmbeddingConfig()

class ConfigManager:
    """Manage configuration loading, validation, and updates"""
    
    def __init__(self, config_path: str = "config/ingestion_config.yaml"):
        self.config_path = config_path
        self.config: Optional[IngestionConfig] = None
        self.last_modified = None
    
    def load_config(self) -> IngestionConfig:
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    if self.config_path.endswith('.yaml') or self.config_path.endswith('.yml'):
                        config_data = yaml.safe_load(f)
                    else:
                        config_data = json.load(f)
                
                # Convert nested dicts to dataclasses
                sources = {}
                for source_name, source_data in config_data.get('sources', {}).items():
                    sources[source_name] = SourceConfig(**source_data)
                
                qdrant_config = QdrantConfig(**config_data.get('qdrant', {}))
                embedding_config = EmbeddingConfig(**config_data.get('embedding', {}))
                
                self.config = IngestionConfig(
                    sources=sources,
                    qdrant=qdrant_config,
                    embedding=embedding_config,
                    **{k: v for k, v in config_data.items() 
                       if k not in ['sources', 'qdrant', 'embedding']}
                )
                
                self.last_modified = os.path.getmtime(self.config_path)
                logger.info(f"Loaded configuration from {self.config_path}")
                
            else:
                # Create default configuration
                self.config = self.create_default_config()
                self.save_config()
                logger.info("Created default configuration")
            
            return self.config
            
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return self.create_default_config()
    
    def create_default_config(self) -> IngestionConfig:
        """Create default configuration"""
        return IngestionConfig(
            sources={
                'news': SourceConfig(
                    enabled=True,
                    requests_per_minute=30,
                    cache_ttl=3600,
                    api_keys={'newsapi': ''}
                ),
                'jobs': SourceConfig(
                    enabled=True,
                    requests_per_minute=60,
                    cache_ttl=7200,
                    api_keys={'adzuna_id': '', 'adzuna_key': ''}
                ),
                'funding': SourceConfig(
                    enabled=True,
                    requests_per_minute=30,
                    cache_ttl=3600
                ),
                'tech': SourceConfig(
                    enabled=True,
                    requests_per_minute=60,
                    cache_ttl=1800
                ),
                'executives': SourceConfig(
                    enabled=True,
                    requests_per_minute=30,
                    cache_ttl=3600
                )
            },
            qdrant=QdrantConfig(),
            embedding=EmbeddingConfig()
        )
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            # Convert to serializable dict
            config_dict = asdict(self.config)
            
            with open(self.config_path, 'w') as f:
                if self.config_path.endswith('.yaml') or self.config_path.endswith('.yml'):
                    yaml.dump(config_dict, f, default_flow_style=False, indent=2)
                else:
                    json.dump(config_dict, f, indent=2)
            
            logger.info(f"Saved configuration to {self.config_path}")
            
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
    
    def has_config_changed(self) -> bool:
        """Check if configuration file has been modified"""
        if not os.path.exists(self.config_path):
            return False
        
        current_modified = os.path.getmtime(self.config_path)
        return current_modified != self.last_modified
    
    def reload_if_changed(self) -> bool:
        """Reload configuration if file has changed"""
        if self.has_config_changed():
            self.load_config()
            return True
        return False
    
    def update_source_config(self, source_name: str, updates: Dict[str, Any]):
        """Update configuration for a specific source"""
        if source_name in self.config.sources:
            source_config = self.config.sources[source_name]
            for key, value in updates.items():
                if hasattr(source_config, key):
                    setattr(source_config, key, value)
            self.save_config()
            logger.info(f"Updated {source_name} configuration")
        else:
            logger.error(f"Source {source_name} not found in configuration")

class MetricsCollector:
    """Collect and track ingestion metrics"""
    
    def __init__(self):
        self.metrics = {
            'signals_processed': 0,
            'signals_stored': 0,
            'duplicates_found': 0,
            'errors_count': 0,
            'last_run': None,
            'source_stats': {},
            'processing_times': []
        }
    
    def record_batch_completion(self, stats: Dict[str, Any], source: str = "mixed"):
        """Record completion of a batch processing"""
        self.metrics['signals_processed'] += stats.get('raw_signals_count', 0)
        self.metrics['signals_stored'] += stats.get('stored_count', 0)
        self.metrics['duplicates_found'] += stats.get('duplicate_count', 0)
        self.metrics['errors_count'] += stats.get('error_count', 0)
        self.metrics['last_run'] = datetime.utcnow().isoformat()
        
        # Track per-source stats
        if source not in self.metrics['source_stats']:
            self.metrics['source_stats'][source] = {
                'processed': 0, 'stored': 0, 'duplicates': 0, 'errors': 0
            }
        
        source_stats = self.metrics['source_stats'][source]
        source_stats['processed'] += stats.get('raw_signals_count', 0)
        source_stats['stored'] += stats.get('stored_count', 0)
        source_stats['duplicates'] += stats.get('duplicate_count', 0)
        source_stats['errors'] += stats.get('error_count', 0)
    
    def record_processing_time(self, duration_seconds: float):
        """Record processing time for performance monitoring"""
        self.metrics['processing_times'].append({
            'duration': duration_seconds,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Keep only last 100 processing times
        if len(self.metrics['processing_times']) > 100:
            self.metrics['processing_times'] = self.metrics['processing_times'][-100:]
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of current metrics"""
        avg_processing_time = 0
        if self.metrics['processing_times']:
            avg_processing_time = sum(
                pt['duration'] for pt in self.metrics['processing_times']
            ) / len(self.metrics['processing_times'])
        
        return {
            'total_processed': self.metrics['signals_processed'],
            'total_stored': self.metrics['signals_stored'],
            'total_duplicates': self.metrics['duplicates_found'],
            'total_errors': self.metrics['errors_count'],
            'success_rate': (
                self.metrics['signals_stored'] / max(1, self.metrics['signals_processed'])
            ) * 100,
            'avg_processing_time_seconds': avg_processing_time,
            'last_run': self.metrics['last_run'],
            'source_breakdown': self.metrics['source_stats']
        }
    
    def save_metrics(self, filepath: str = "logs/ingestion_metrics.json"):
        """Save metrics to file"""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(self.metrics, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving metrics: {e}")

# Example YAML configuration file content
SAMPLE_CONFIG_YAML = """
# EDI-Graph Ingestion Configuration
sources:
  news:
    enabled: true
    requests_per_minute: 30
    cache_ttl: 3600
    timeout: 30
    retry_attempts: 3
    api_keys:
      newsapi: "your_newsapi_key_here"
    custom_headers:
      Accept: "application/json"

  jobs:
    enabled: true
    requests_per_minute: 60
    cache_ttl: 7200
    timeout: 45
    api_keys:
      adzuna_id: "your_adzuna_id"
      adzuna_key: "your_adzuna_key"

  funding:
    enabled: true
    requests_per_minute: 30
    cache_ttl: 3600
    timeout: 30

  tech:
    enabled: true
    requests_per_minute: 60
    cache_ttl: 1800
    timeout: 30

  executives:
    enabled: true
    requests_per_minute: 30
    cache_ttl: 3600
    timeout: 30

qdrant:
  host: "localhost"
  port: 6333
  collection_name: "signals"
  embedding_dimension: 384
  similarity_threshold: 0.8

embedding:
  model_type: "sentence_transformer"
  model_name: "all-MiniLM-L6-v2"
  batch_size: 32
  max_concurrent_processing: 10

neo4j_uri: "bolt://localhost:7687"
neo4j_user: "neo4j"
neo4j_password: "password"
log_level: "INFO"
metrics_enabled: true
"""

def create_config_files():
    """Create sample configuration files"""
    
    # Create config directory
    os.makedirs("config", exist_ok=True)
    
    # Save YAML config
    with open("config/ingestion_config.yaml", "w") as f:
        f.write(SAMPLE_CONFIG_YAML)
    
    # Create environment-specific configs
    environments = ['development', 'staging', 'production']
    
    for env in environments:
        env_config = SAMPLE_CONFIG_YAML.replace(
            'requests_per_minute: 30',
            f'requests_per_minute: {30 if env == "development" else 60}'
        ).replace(
            'cache_ttl: 3600',
            f'cache_ttl: {1800 if env == "development" else 3600}'
        )
        
        with open(f"config/ingestion_config_{env}.yaml", "w") as f:
            f.write(env_config)
    
    logger.info("Created configuration files")

if __name__ == "__main__":
    # Create sample configuration files
    create_config_files()
    
    # Example usage
    config_manager = ConfigManager("config/ingestion_config.yaml")
    config = config_manager.load_config()
    
    print("Loaded configuration:")
    print(f"- Sources enabled: {[name for name, src in config.sources.items() if src.enabled]}")
    print(f"- Qdrant collection: {config.qdrant.collection_name}")
    print(f"- Embedding model: {config.embedding.model_name}")
    
    # Example of updating source configuration
    config_manager.update_source_config('news', {
        'requests_per_minute': 45,
        'cache_ttl': 7200
    })
    
    print("Updated news source configuration")