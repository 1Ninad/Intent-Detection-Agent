#!/usr/bin/env python3
"""
Setup validation script to check if everything is configured correctly.
Run this after initial setup to verify all components are working.
"""

import asyncio
import sys
import os
import subprocess
import yaml
import json
import aiohttp
from typing import Dict, List, Tuple
from qdrant_client.http import models

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'step2'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'step2', 'ingestion'))

class SetupValidator:
    """Validate complete setup"""
    
    def __init__(self):
        self.results = []
        self.config = None
    
    def add_result(self, test_name: str, status: bool, message: str, details: str = ""):
        """Add validation result"""
        self.results.append({
            'test': test_name,
            'status': '✅ PASS' if status else '❌ FAIL',
            'message': message,
            'details': details
        })
    
    def print_results(self):
        """Print all validation results"""
        print("\n" + "="*60)
        print("🔍 SETUP VALIDATION RESULTS")
        print("="*60)
        
        passed = 0
        total = len(self.results)
        
        for result in self.results:
            print(f"{result['status']} {result['test']}")
            print(f"   {result['message']}")
            if result['details']:
                print(f"   Details: {result['details']}")
            print()
            
            if 'PASS' in result['status']:
                passed += 1
        
        print("="*60)
        print(f"Summary: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All validations passed! Setup is complete.")
            return True
        else:
            print("⚠️  Some validations failed. Check the details above.")
            return False
    
    async def validate_python_environment(self):
        """Validate Python environment and dependencies"""
        try:
            # Check Python version
            version = sys.version_info
            if version.major == 3 and version.minor >= 9:
                self.add_result(
                    "Python Version",
                    True,
                    f"Python {version.major}.{version.minor}.{version.micro}"
                )
            else:
                self.add_result(
                    "Python Version", 
                    False,
                    f"Python 3.9+ required, got {version.major}.{version.minor}"
                )
            
            # Check key dependencies
            required_packages = [
                'aiohttp', 'yaml', 'numpy', 'requests', 
                'sentence_transformers', 'qdrant_client'
            ]
            
            missing_packages = []
            for package in required_packages:
                try:
                    __import__(package.replace('-', '_'))
                except ImportError:
                    missing_packages.append(package)
            
            if not missing_packages:
                self.add_result(
                    "Dependencies",
                    True,
                    "All required packages installed"
                )
            else:
                self.add_result(
                    "Dependencies",
                    False,
                    f"Missing packages: {', '.join(missing_packages)}",
                    "Run: pip install -r requirements.txt"
                )
        
        except Exception as e:
            self.add_result(
                "Python Environment",
                False,
                f"Error checking environment: {e}"
            )
    
    async def validate_configuration(self):
        """Validate configuration file"""
        try:
            config_path = "config/ingestion_config.yaml"
            
            if not os.path.exists(config_path):
                self.add_result(
                    "Configuration File",
                    False,
                    f"Config file not found: {config_path}",
                    "Run the setup script to create default config"
                )
                return
            
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            
            self.add_result(
                "Configuration File",
                True,
                "Configuration file loaded successfully"
            )
            
            # Check API keys
            api_key_issues = []
            
            if self.config.get('sources', {}).get('news', {}).get('api_keys', {}).get('newsapi') == 'YOUR_NEWSAPI_KEY_HERE':
                api_key_issues.append("NewsAPI key not configured")
            
            if self.config.get('sources', {}).get('jobs', {}).get('api_keys', {}).get('adzuna_id') == 'YOUR_ADZUNA_ID_HERE':
                api_key_issues.append("Adzuna ID not configured")
            
            if api_key_issues:
                self.add_result(
                    "API Keys",
                    False,
                    f"API keys need configuration: {', '.join(api_key_issues)}",
                    "Edit config/ingestion_config.yaml with real API keys"
                )
            else:
                self.add_result(
                    "API Keys", 
                    True,
                    "API keys configured"
                )
        
        except Exception as e:
            self.add_result(
                "Configuration",
                False,
                f"Error loading config: {e}"
            )
    
    async def validate_docker_services(self):
        """Validate Docker services are running"""
        try:
            # Check if docker-compose is running
            result = subprocess.run(
                ['docker-compose', 'ps', '--services', '--filter', 'status=running'],
                capture_output=True, text=True, timeout=10
            )
            
            running_services = result.stdout.strip().split('\n') if result.stdout.strip() else []
            expected_services = ['neo4j', 'qdrant', 'redis']
            
            missing_services = [s for s in expected_services if s not in running_services]
            
            if not missing_services:
                self.add_result(
                    "Docker Services",
                    True,
                    f"All services running: {', '.join(running_services)}"
                )
            else:
                self.add_result(
                    "Docker Services",
                    False,
                    f"Services not running: {', '.join(missing_services)}",
                    "Run: make docker-up"
                )
        
        except subprocess.TimeoutExpired:
            self.add_result(
                "Docker Services",
                False,
                "Docker command timed out"
            )
        except Exception as e:
            self.add_result(
                "Docker Services",
                False,
                f"Error checking Docker services: {e}"
            )
    
    async def validate_neo4j_connectivity(self):
        """Validate Neo4j connectivity"""
        try:
            # Test HTTP connection
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:7474', timeout=5) as response:
                    if response.status == 200:
                        self.add_result(
                            "Neo4j HTTP",
                            True,
                            "Neo4j HTTP interface accessible"
                        )
                    else:
                        self.add_result(
                            "Neo4j HTTP",
                            False,
                            f"Neo4j HTTP returned status {response.status}"
                        )
        
        except Exception as e:
            self.add_result(
                "Neo4j HTTP",
                False,
                f"Neo4j HTTP connection failed: {e}",
                "Check if Neo4j container is running"
            )
        
        # Test Bolt connection (requires neo4j package)
        try:
            from neo4j import GraphDatabase
            
            driver = GraphDatabase.driver(
                "bolt://localhost:7687",
                auth=("neo4j", "password")
            )
            
            with driver.session() as session:
                result = session.run("RETURN 'Hello World' as message")
                record = result.single()
                
            driver.close()
            
            self.add_result(
                "Neo4j Bolt",
                True,
                "Neo4j Bolt connection successful"
            )
        
        except Exception as e:
            self.add_result(
                "Neo4j Bolt",
                False,
                f"Neo4j Bolt connection failed: {e}"
            )
    
    async def validate_qdrant_connectivity(self):
        """Validate Qdrant connectivity"""
        try:
            from qdrant_client import QdrantClient
            
            client = QdrantClient(host="localhost", port=6333)
            collections = client.get_collections()
            
            self.add_result(
                "Qdrant Connection",
                True,
                f"Qdrant connected, {len(collections.collections)} collections found"
            )
            
            # Test collection creation
            test_collection = "setup_test"
            try:
                client.create_collection(
                    collection_name=test_collection,
                    vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE)
                )
                client.delete_collection(test_collection)
                
                self.add_result(
                    "Qdrant Operations",
                    True,
                    "Collection create/delete operations work"
                )
            except Exception as e:
                self.add_result(
                    "Qdrant Operations",
                    False,
                    f"Collection operations failed: {e}"
                )
        
        except Exception as e:
            self.add_result(
                "Qdrant Connection",
                False,
                f"Qdrant connection failed: {e}",
                "Check if Qdrant container is running on port 6333"
            )
    
    async def validate_embedding_generation(self):
        """Validate embedding generation"""
        try:
            from embedding_pipeline import EmbeddingGenerator
            
            config = {
                'model_type': 'sentence_transformer',
                'model_name': 'all-MiniLM-L6-v2'
            }
            
            generator = EmbeddingGenerator(config)
            embedding = await generator.generate_embedding("This is a test sentence")
            
            if embedding and len(embedding) > 0:
                self.add_result(
                    "Embedding Generation",
                    True,
                    f"Generated {len(embedding)}-dimensional embeddings"
                )
            else:
                self.add_result(
                    "Embedding Generation",
                    False,
                    "Failed to generate embeddings"
                )
        
        except Exception as e:
            self.add_result(
                "Embedding Generation",
                False,
                f"Embedding generation error: {e}",
                "Check if sentence-transformers is installed correctly"
            )
    
    async def validate_api_connectivity(self):
        """Validate external API connectivity"""
        if not self.config:
            return
        
        # Test NewsAPI if configured
        news_config = self.config.get('sources', {}).get('news', {})
        if news_config.get('enabled') and news_config.get('api_keys', {}).get('newsapi'):
            api_key = news_config['api_keys']['newsapi']
            if api_key != 'YOUR_NEWSAPI_KEY_HERE':
                try:
                    async with aiohttp.ClientSession() as session:
                        url = "https://newsapi.org/v2/everything"
                        params = {
                            'apiKey': api_key,
                            'q': 'test',
                            'pageSize': 1
                        }
                        async with session.get(url, params=params, timeout=10) as response:
                            if response.status == 200:
                                self.add_result(
                                    "NewsAPI Connection",
                                    True,
                                    "NewsAPI authentication successful"
                                )
                            else:
                                self.add_result(
                                    "NewsAPI Connection",
                                    False,
                                    f"NewsAPI returned status {response.status}"
                                )
                except Exception as e:
                    self.add_result(
                        "NewsAPI Connection",
                        False,
                        f"NewsAPI connection failed: {e}"
                    )
        
        # Test Adzuna if configured
        jobs_config = self.config.get('sources', {}).get('jobs', {})
        if jobs_config.get('enabled'):
            adzuna_id = jobs_config.get('api_keys', {}).get('adzuna_id')
            adzuna_key = jobs_config.get('api_keys', {}).get('adzuna_key')
            
            if adzuna_id and adzuna_key and adzuna_id != 'YOUR_ADZUNA_ID_HERE':
                try:
                    async with aiohttp.ClientSession() as session:
                        url = "https://api.adzuna.com/v1/api/jobs/us/search/1"
                        params = {
                            'app_id': adzuna_id,
                            'app_key': adzuna_key,
                            'what': 'test',
                            'results_per_page': 1
                        }
                        async with session.get(url, params=params, timeout=10) as response:
                            if response.status == 200:
                                self.add_result(
                                    "Adzuna API Connection",
                                    True,
                                    "Adzuna API authentication successful"
                                )
                            else:
                                self.add_result(
                                    "Adzuna API Connection",
                                    False,
                                    f"Adzuna API returned status {response.status}"
                                )
                except Exception as e:
                    self.add_result(
                        "Adzuna API Connection",
                        False,
                        f"Adzuna API connection failed: {e}"
                    )
    
    async def validate_end_to_end_pipeline(self):
        """Run a minimal end-to-end test"""
        try:
            from source_adapters import RawSignal
            from embedding_pipeline import run_ingestion_pipeline
            
            # Create test signal
            test_signal = RawSignal(
                source="validation_test",
                signal_type="news",
                title="Test Signal for Validation",
                content="This is a test signal to validate the complete pipeline",
                url="https://example.com/test",
                published_date="2024-08-31T10:00:00Z",
                raw_data={},
                company_mentions=["TestCorp"],
                technology_mentions=["AI"]
            )
            
            # Mock graph API for testing
            class MockGraphAPI:
                async def find_company_by_name(self, name):
                    return {'id': f'company_{hash(name)}', 'name': name}
                async def create_company(self, data):
                    return {'id': f'company_{hash(data["name"])}', 'name': data['name']}
                async def find_person_by_name(self, name):
                    return None
                async def create_person(self, data):
                    return {'id': f'person_{hash(data["name"])}', 'name': data['name']}
                async def find_technology_by_name(self, name):
                    return {'id': f'tech_{hash(name)}', 'name': name}
                async def create_technology(self, data):
                    return {'id': f'tech_{hash(data["name"])}', 'name': data['name']}
                async def create_signal(self, data):
                    return {'id': data['id']}
                async def create_relationship(self, from_id, rel_type, to_id):
                    pass
            
            # Test pipeline
            pipeline_config = {
                'model_type': 'sentence_transformer',
                'model_name': 'all-MiniLM-L6-v2',
                'qdrant': {
                    'host': 'localhost',
                    'port': 6333,
                    'collection_name': 'validation_test',
                    'embedding_dimension': 384
                }
            }
            
            stats = await run_ingestion_pipeline(
                [test_signal], 
                pipeline_config, 
                MockGraphAPI()
            )
            
            if stats['processed_signals_count'] > 0:
                self.add_result(
                    "End-to-End Pipeline",
                    True,
                    f"Pipeline processed {stats['processed_signals_count']} signals"
                )
            else:
                self.add_result(
                    "End-to-End Pipeline",
                    False,
                    "Pipeline failed to process test signal"
                )
        
        except Exception as e:
            self.add_result(
                "End-to-End Pipeline",
                False,
                f"Pipeline test failed: {e}"
            )
    
    async def run_all_validations(self):
        """Run all validation tests"""
        print("🔍 Running setup validation tests...")
        print("This may take a few minutes...")
        print()
        
        await self.validate_python_environment()
        await self.validate_configuration()
        await self.validate_docker_services()
        await self.validate_neo4j_connectivity()
        await self.validate_qdrant_connectivity()
        await self.validate_embedding_generation()
        await self.validate_api_connectivity()
        await self.validate_end_to_end_pipeline()
        
        return self.print_results()

class QuickSetupWizard:
    """Interactive setup wizard"""
    
    def __init__(self):
        self.config_path = "config/ingestion_config.yaml"
    
    def run_wizard(self):
        """Run interactive setup wizard"""
        print("🧙 EDI-Graph Setup Wizard")
        print("=" * 40)
        
        # Check if config exists
        if os.path.exists(self.config_path):
            overwrite = input(f"Configuration file exists at {self.config_path}. Overwrite? (y/N): ")
            if overwrite.lower() != 'y':
                print("Setup cancelled. Using existing configuration.")
                return
        
        print("\n📝 Let's configure your API keys...")
        
        # Load default config
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # NewsAPI setup
        print("\n1. NewsAPI (for news signals)")
        print("   Get your key at: https://newsapi.org/register")
        news_key = input("   Enter NewsAPI key (or press Enter to skip): ").strip()
        if news_key:
            config['sources']['news']['api_keys']['newsapi'] = news_key
            config['sources']['news']['enabled'] = True
        else:
            config['sources']['news']['enabled'] = False
            print("   ⚠️  News source disabled")
        
        # Adzuna setup
        print("\n2. Adzuna Jobs API (for job postings)")
        print("   Get your keys at: https://developer.adzuna.com/")
        adzuna_id = input("   Enter Adzuna App ID (or press Enter to skip): ").strip()
        adzuna_key = input("   Enter Adzuna API Key (or press Enter to skip): ").strip()
        
        if adzuna_id and adzuna_key:
            config['sources']['jobs']['api_keys']['adzuna_id'] = adzuna_id
            config['sources']['jobs']['api_keys']['adzuna_key'] = adzuna_key
            config['sources']['jobs']['enabled'] = True
        else:
            config['sources']['jobs']['enabled'] = False
            print("   ⚠️  Jobs source disabled")
        
        # OpenAI setup (optional)
        print("\n3. OpenAI API (optional, for advanced embeddings)")
        print("   Get your key at: https://platform.openai.com/api-keys")
        use_openai = input("   Use OpenAI embeddings? (y/N): ").strip().lower()
        
        if use_openai == 'y':
            openai_key = input("   Enter OpenAI API key: ").strip()
            if openai_key:
                config['embedding']['model_type'] = 'openai'
                config['embedding']['openai_api_key'] = openai_key
                print("   ✅ OpenAI embeddings enabled")
            else:
                print("   ⚠️  No key provided, using local embeddings")
        else:
            print("   ℹ️  Using local sentence-transformers (recommended for development)")
        
        # Performance settings
        print("\n4. Performance Settings")
        environment = input("   Environment (development/production): ").strip().lower()
        
        if environment == 'production':
            config['embedding']['max_concurrent_processing'] = 20
            config['embedding']['batch_size'] = 64
            for source in config['sources'].values():
                if source.get('requests_per_minute', 0) < 60:
                    source['requests_per_minute'] = min(60, source.get('requests_per_minute', 30) * 2)
            print("   ✅ Production settings applied")
        else:
            config['embedding']['max_concurrent_processing'] = 5
            config['embedding']['batch_size'] = 16
            print("   ✅ Development settings applied")
        
        # Save configuration
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        
        print(f"\n✅ Configuration saved to {self.config_path}")
        print("\nNext steps:")
        print("1. Run: make docker-up")
        print("2. Run: python setup_validator.py")
        print("3. Run: make test")
        print("4. Run: make run-single")

async def main():
    """Main validation function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="EDI-Graph Setup Validator")
    parser.add_argument('--wizard', action='store_true', 
                       help='Run interactive setup wizard')
    parser.add_argument('--quick', action='store_true',
                       help='Run quick validation (skip API tests)')
    
    args = parser.parse_args()
    
    if args.wizard:
        wizard = QuickSetupWizard()
        wizard.run_wizard()
        return
    
    # Run validation
    validator = SetupValidator()
    success = await validator.run_all_validations()
    
    if success:
        print("\n🎉 Setup validation completed successfully!")
        print("\nYou can now:")
        print("• Run single ingestion: make run-single")
        print("• Start continuous ingestion: make run-continuous") 
        print("• Run 24h validation test: make run-24h-test")
        print("• Monitor with: tail -f logs/ingestion.log")
        
        sys.exit(0)
    else:
        print("\n⚠️  Setup validation found issues.")
        print("Please fix the issues above and run validation again.")
        print("\nCommon fixes:")
        print("• Install missing dependencies: make install")
        print("• Start services: make docker-up")
        print("• Configure API keys: python setup_validator.py --wizard")
        
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nSetup validation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error during validation: {e}")
        sys.exit(1)