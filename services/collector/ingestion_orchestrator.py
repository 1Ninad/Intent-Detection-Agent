"""
Main ingestion orchestrator that coordinates source adapters, 
embedding pipeline, and handles scheduling for continuous ingestion.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from dataclasses import asdict
from typing import Dict, Any, List
import signal
import sys

from source_adapters import SourceManager, RawSignal
from embedding_pipeline import IngestionPipeline, EmbeddingGenerator, run_ingestion_pipeline
from config_management import ConfigManager, MetricsCollector

logger = logging.getLogger(__name__)

class IngestionOrchestrator:
    """Main orchestrator for the ingestion pipeline"""
    
    def __init__(self, config_path: str = "config/ingestion_config.yaml"):
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.load_config()
        self.metrics_collector = MetricsCollector()
        self.running = False
        self.graph_api_client = None  # Will be injected
        
        # Setup logging
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/ingestion.log'),
                logging.StreamHandler()
            ]
        )
    
    def set_graph_api_client(self, client):
        """Inject graph API client dependency"""
        self.graph_api_client = client
    
    async def run_single_ingestion_cycle(self, icp_query: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run a single ingestion cycle"""
        start_time = time.time()
        
        try:
            logger.info("Starting ingestion cycle...")
            
            # Reload config if changed
            self.config_manager.reload_if_changed()
            
            # Initialize source manager
            source_manager = SourceManager({
                name: asdict(config) for name, config in self.config.sources.items()
            })
            
            # Fetch raw signals from all sources
            logger.info("Fetching signals from all sources...")
            raw_signals = await source_manager.fetch_all_signals(icp_query)
            
            if not raw_signals:
                logger.warning("No signals fetched from any source")
                return {'raw_signals_count': 0, 'stored_count': 0}
            
            logger.info(f"Fetched {len(raw_signals)} raw signals")
            
            # Process through embedding pipeline
            embedding_config = asdict(self.config.embedding)
            embedding_config['qdrant'] = asdict(self.config.qdrant)
            
            stats = await run_ingestion_pipeline(
                raw_signals, 
                embedding_config, 
                self.graph_api_client
            )
            
            # Record metrics
            processing_time = time.time() - start_time
            self.metrics_collector.record_batch_completion(stats)
            self.metrics_collector.record_processing_time(processing_time)
            
            # Save metrics
            if self.config.metrics_enabled:
                self.metrics_collector.save_metrics()
            
            logger.info(f"Ingestion cycle completed in {processing_time:.2f}s")
            logger.info(f"Stats: {stats}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error in ingestion cycle: {e}")
            processing_time = time.time() - start_time
            self.metrics_collector.record_processing_time(processing_time)
            
            error_stats = {
                'raw_signals_count': 0,
                'stored_count': 0,
                'error_count': 1,
                'errors': [str(e)]
            }
            self.metrics_collector.record_batch_completion(error_stats)
            return error_stats
    
    async def run_continuous_ingestion(self, 
                                     interval_minutes: int = 60,
                                     icp_query: Dict[str, Any] = None):
        """Run continuous ingestion with specified interval"""
        self.running = True
        logger.info(f"Starting continuous ingestion (interval: {interval_minutes} minutes)")
        
        while self.running:
            try:
                # Run ingestion cycle
                await self.run_single_ingestion_cycle(icp_query)
                
                # Wait for next cycle
                if self.running:
                    logger.info(f"Waiting {interval_minutes} minutes until next cycle...")
                    await asyncio.sleep(interval_minutes * 60)
                    
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, stopping ingestion...")
                self.running = False
                break
            except Exception as e:
                logger.error(f"Unexpected error in continuous ingestion: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying
    
    def stop(self):
        """Stop continuous ingestion"""
        self.running = False
        logger.info("Ingestion orchestrator stopped")
    
    async def run_icp_targeted_ingestion(self, icp_config: Dict[str, Any]) -> Dict[str, Any]:
        """Run ingestion targeted at specific ICP"""
        logger.info(f"Running ICP-targeted ingestion for: {icp_config.get('name', 'Unknown')}")
        
        # Build query parameters based on ICP
        query_params = {
            'query': self._build_icp_query(icp_config),
            'companies': icp_config.get('target_companies', []),
            'technologies': icp_config.get('technologies', []),
            'industries': icp_config.get('industries', [])
        }
        
        return await self.run_single_ingestion_cycle(query_params)
    
    def _build_icp_query(self, icp_config: Dict[str, Any]) -> str:
        """Build search query from ICP configuration"""
        query_parts = []
        
        if icp_config.get('industries'):
            query_parts.extend(icp_config['industries'])
        
        if icp_config.get('technologies'):
            query_parts.extend(icp_config['technologies'])
        
        if icp_config.get('company_size'):
            query_parts.append(icp_config['company_size'])
        
        if icp_config.get('funding_stage'):
            query_parts.append(icp_config['funding_stage'])
        
        return " ".join(query_parts)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status and metrics"""
        metrics_summary = self.metrics_collector.get_metrics_summary()
        
        return {
            'running': self.running,
            'config_last_modified': self.config_manager.last_modified,
            'metrics': metrics_summary,
            'sources_enabled': [
                name for name, config in self.config.sources.items() 
                if config.enabled
            ]
        }

class ScheduledIngestionRunner:
    """Handle scheduled ingestion runs with different ICPs"""
    
    def __init__(self, orchestrator: IngestionOrchestrator):
        self.orchestrator = orchestrator
        self.schedules = []
        self.running = False
    
    def add_schedule(self, 
                    icp_config: Dict[str, Any], 
                    interval_minutes: int = 60,
                    enabled: bool = True):
        """Add a scheduled ingestion for specific ICP"""
        schedule = {
            'id': f"icp_{len(self.schedules)}",
            'icp_config': icp_config,
            'interval_minutes': interval_minutes,
            'enabled': enabled,
            'last_run': None,
            'next_run': datetime.utcnow(),
            'stats': {'total_runs': 0, 'total_signals': 0, 'total_errors': 0}
        }
        
        self.schedules.append(schedule)
        logger.info(f"Added schedule for ICP: {icp_config.get('name', 'Unknown')}")
    
    async def run_scheduler(self):
        """Run the scheduler loop"""
        self.running = True
        logger.info("Starting ingestion scheduler...")
        
        while self.running:
            try:
                current_time = datetime.utcnow()
                
                # Check each schedule
                for schedule in self.schedules:
                    if (schedule['enabled'] and 
                        current_time >= schedule['next_run']):
                        
                        logger.info(f"Running scheduled ingestion for: {schedule['icp_config'].get('name')}")
                        
                        # Run ingestion
                        stats = await self.orchestrator.run_icp_targeted_ingestion(
                            schedule['icp_config']
                        )
                        
                        # Update schedule
                        schedule['last_run'] = current_time.isoformat()
                        schedule['next_run'] = current_time + timedelta(
                            minutes=schedule['interval_minutes']
                        )
                        schedule['stats']['total_runs'] += 1
                        schedule['stats']['total_signals'] += stats.get('stored_count', 0)
                        schedule['stats']['total_errors'] += stats.get('error_count', 0)
                
                # Sleep for 1 minute before next check
                await asyncio.sleep(60)
                
            except KeyboardInterrupt:
                logger.info("Scheduler stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in scheduler: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
        
        self.running = False
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
    
    def get_schedule_status(self) -> List[Dict[str, Any]]:
        """Get status of all schedules"""
        return [
            {
                'id': schedule['id'],
                'icp_name': schedule['icp_config'].get('name', 'Unknown'),
                'enabled': schedule['enabled'],
                'interval_minutes': schedule['interval_minutes'],
                'last_run': schedule['last_run'],
                'next_run': schedule['next_run'].isoformat() if schedule['next_run'] else None,
                'stats': schedule['stats']
            }
            for schedule in self.schedules
        ]

# Main execution functions
async def run_24h_test_ingestion(orchestrator: IngestionOrchestrator, 
                               target_signals: int = 500) -> Dict[str, Any]:
    """Run ingestion for 24 hours targeting minimum signal count"""
    
    # Sample ICP for testing
    test_icp = {
        'name': 'B2B SaaS Test ICP',
        'industries': ['SaaS', 'B2B', 'enterprise software'],
        'technologies': ['cloud computing', 'AI', 'machine learning', 'API'],
        'company_size': 'startup',
        'funding_stage': 'Series A Series B',
        'target_companies': ['Salesforce', 'HubSpot', 'Slack', 'Zoom', 'Notion']
    }
    
    start_time = datetime.utcnow()
    end_time = start_time + timedelta(hours=24)
    total_signals_stored = 0
    cycles_completed = 0
    
    logger.info(f"Starting 24h test ingestion targeting {target_signals} signals")
    
    while datetime.utcnow() < end_time and total_signals_stored < target_signals:
        cycle_stats = await orchestrator.run_icp_targeted_ingestion(test_icp)
        
        total_signals_stored += cycle_stats.get('stored_count', 0)
        cycles_completed += 1
        
        logger.info(f"Cycle {cycles_completed}: {total_signals_stored}/{target_signals} signals stored")
        
        if total_signals_stored < target_signals:
            # Wait before next cycle (adjust based on API limits)
            await asyncio.sleep(1800)  # 30 minutes between cycles
    
    duration = datetime.utcnow() - start_time
    
    return {
        'test_duration_hours': duration.total_seconds() / 3600,
        'cycles_completed': cycles_completed,
        'total_signals_stored': total_signals_stored,
        'target_achieved': total_signals_stored >= target_signals,
        'signals_per_hour': total_signals_stored / (duration.total_seconds() / 3600),
        'final_metrics': orchestrator.get_status()
    }

def setup_signal_handlers(orchestrator: IngestionOrchestrator):
    """Setup graceful shutdown handlers"""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        orchestrator.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

# CLI interface
async def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="EDI-Graph Ingestion Pipeline")
    parser.add_argument('--config', default='config/ingestion_config.yaml',
                       help='Configuration file path')
    parser.add_argument('--mode', choices=['single', 'continuous', 'scheduled', 'test-24h'],
                       default='single', help='Ingestion mode')
    parser.add_argument('--interval', type=int, default=60,
                       help='Interval in minutes for continuous mode')
    parser.add_argument('--target-signals', type=int, default=500,
                       help='Target signal count for 24h test')
    
    args = parser.parse_args()
    
    # Initialize orchestrator
    orchestrator = IngestionOrchestrator(args.config)
    
    # Mock graph API client (replace with actual implementation)
    class MockGraphAPI:
        async def find_company_by_name(self, name): 
            return {'id': f'company_{hash(name)}', 'name': name} if name else None
        async def create_company(self, data): 
            return {'id': f'company_{hash(data["name"])}', 'name': data['name']}
        async def find_person_by_name(self, name): 
            return {'id': f'person_{hash(name)}', 'name': name} if name else None
        async def create_person(self, data): 
            return {'id': f'person_{hash(data["name"])}', 'name': data['name']}
        async def find_technology_by_name(self, name): 
            return {'id': f'tech_{hash(name)}', 'name': name} if name else None
        async def create_technology(self, data): 
            return {'id': f'tech_{hash(data["name"])}', 'name': data['name']}
        async def create_signal(self, data): 
            return {'id': data['id']}
        async def create_relationship(self, from_id, rel_type, to_id): 
            pass
    
    orchestrator.set_graph_api_client(MockGraphAPI())
    
    # Setup signal handlers for graceful shutdown
    setup_signal_handlers(orchestrator)
    
    try:
        if args.mode == 'single':
            # Run single ingestion cycle
            stats = await orchestrator.run_single_ingestion_cycle()
            print(f"Single ingestion completed: {stats}")
        
        elif args.mode == 'continuous':
            # Run continuous ingestion
            await orchestrator.run_continuous_ingestion(args.interval)
        
        elif args.mode == 'scheduled':
            # Run with multiple ICP schedules
            scheduler = ScheduledIngestionRunner(orchestrator)
            
            # Add sample schedules
            sample_icps = [
                {
                    'name': 'Enterprise SaaS',
                    'industries': ['SaaS', 'enterprise software'],
                    'technologies': ['cloud', 'API', 'microservices'],
                    'company_size': 'enterprise',
                    'funding_stage': 'Series C+'
                },
                {
                    'name': 'AI Startups',
                    'industries': ['artificial intelligence', 'machine learning'],
                    'technologies': ['AI', 'ML', 'deep learning', 'neural networks'],
                    'company_size': 'startup',
                    'funding_stage': 'Series A Series B'
                }
            ]
            
            for icp in sample_icps:
                scheduler.add_schedule(icp, interval_minutes=90)
            
            await scheduler.run_scheduler()
        
        elif args.mode == 'test-24h':
            # Run 24-hour test
            test_results = await run_24h_test_ingestion(orchestrator, args.target_signals)
            print(f"24h test results: {test_results}")
    
    except KeyboardInterrupt:
        logger.info("Ingestion stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

# Monitoring and health check utilities
class IngestionMonitor:
    """Monitor ingestion pipeline health and performance"""
    
    def __init__(self, orchestrator: IngestionOrchestrator):
        self.orchestrator = orchestrator
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all components"""
        health_status = {
            'overall_status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'components': {}
        }
        
        # Check Qdrant connectivity
        try:
            qdrant_config = self.orchestrator.config.qdrant
            from qdrant_client import QdrantClient
            client = QdrantClient(host=qdrant_config.host, port=qdrant_config.port)
            collections = client.get_collections()
            health_status['components']['qdrant'] = {
                'status': 'healthy',
                'collections_count': len(collections.collections)
            }
        except Exception as e:
            health_status['components']['qdrant'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['overall_status'] = 'unhealthy'
        
        # Check Neo4j connectivity (mock check)
        try:
            # In real implementation, ping Neo4j
            health_status['components']['neo4j'] = {
                'status': 'healthy',
                'uri': self.orchestrator.config.neo4j_uri
            }
        except Exception as e:
            health_status['components']['neo4j'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['overall_status'] = 'unhealthy'
        
        # Check source configurations
        enabled_sources = [
            name for name, config in self.orchestrator.config.sources.items()
            if config.enabled
        ]
        health_status['components']['sources'] = {
            'status': 'healthy' if enabled_sources else 'warning',
            'enabled_sources': enabled_sources,
            'total_sources': len(self.orchestrator.config.sources)
        }
        
        return health_status
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics"""
        metrics = self.orchestrator.metrics_collector.get_metrics_summary()
        
        # Add additional performance analysis
        if metrics.get('source_breakdown'):
            for source, stats in metrics['source_breakdown'].items():
                if stats['processed'] > 0:
                    stats['success_rate'] = (stats['stored'] / stats['processed']) * 100
                    stats['duplicate_rate'] = (stats['duplicates'] / stats['processed']) * 100
        
        return metrics

# Docker healthcheck endpoint (for containerized deployment)
async def healthcheck_endpoint():
    """Simple healthcheck for Docker/K8s"""
    try:
        orchestrator = IngestionOrchestrator()
        monitor = IngestionMonitor(orchestrator)
        health = await monitor.health_check()
        
        if health['overall_status'] == 'healthy':
            print("HEALTHY")
            sys.exit(0)
        else:
            print("UNHEALTHY")
            sys.exit(1)
    except Exception as e:
        print(f"UNHEALTHY: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Check if running as healthcheck
    if len(sys.argv) > 1 and sys.argv[1] == 'healthcheck':
        asyncio.run(healthcheck_endpoint())
    else:
        asyncio.run(main())
