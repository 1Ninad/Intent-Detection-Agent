"""
Source adapters for ingesting signals from various data sources.
Includes rate limiting, caching, robots.txt compliance, and retries.
"""

import asyncio
import aiohttp
import time
import hashlib
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin, urlparse
import backoff

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RawSignal:
    """Normalized signal object before entity resolution"""
    source: str
    signal_type: str  # news, job_posting, funding, tech_mention, exec_change
    title: str
    content: str
    url: str
    published_date: str
    raw_data: Dict[str, Any]
    company_mentions: List[str] = None
    person_mentions: List[str] = None
    technology_mentions: List[str] = None
    
    def __post_init__(self):
        if self.company_mentions is None:
            self.company_mentions = []
        if self.person_mentions is None:
            self.person_mentions = []
        if self.technology_mentions is None:
            self.technology_mentions = []

class RateLimiter:
    """Token bucket rate limiter"""
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.tokens = requests_per_minute
        self.last_update = time.time()
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        async with self.lock:
            now = time.time()
            time_passed = now - self.last_update
            self.tokens = min(
                self.requests_per_minute,
                self.tokens + time_passed * (self.requests_per_minute / 60.0)
            )
            self.last_update = now
            
            if self.tokens < 1:
                sleep_time = (1 - self.tokens) / (self.requests_per_minute / 60.0)
                await asyncio.sleep(sleep_time)
                self.tokens = 0
            else:
                self.tokens -= 1

class CacheManager:
    """Simple in-memory cache with TTL"""
    def __init__(self, default_ttl: int = 3600):
        self.cache = {}
        self.default_ttl = default_ttl
    
    def _generate_key(self, url: str, params: Dict = None) -> str:
        key_data = f"{url}_{params or ''}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, url: str, params: Dict = None) -> Optional[Any]:
        key = self._generate_key(url, params)
        if key in self.cache:
            data, timestamp, ttl = self.cache[key]
            if time.time() - timestamp < ttl:
                return data
            else:
                del self.cache[key]
        return None
    
    def set(self, url: str, data: Any, params: Dict = None, ttl: int = None):
        key = self._generate_key(url, params)
        ttl = ttl or self.default_ttl
        self.cache[key] = (data, time.time(), ttl)

class RobotsChecker:
    """Check robots.txt compliance"""
    def __init__(self):
        self.robots_cache = {}
    
    async def can_fetch(self, url: str, user_agent: str = "*") -> bool:
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        if base_url not in self.robots_cache:
            robots_url = urljoin(base_url, "/robots.txt")
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(robots_url, timeout=10) as response:
                        if response.status == 200:
                            robots_content = await response.text()
                            rp = RobotFileParser()
                            rp.set_url(robots_url)
                            rp.read_file(robots_content.splitlines())
                            self.robots_cache[base_url] = rp
                        else:
                            # If no robots.txt, assume allowed
                            self.robots_cache[base_url] = None
            except Exception as e:
                logger.warning(f"Failed to fetch robots.txt for {base_url}: {e}")
                self.robots_cache[base_url] = None
        
        robots_parser = self.robots_cache[base_url]
        if robots_parser is None:
            return True
        
        return robots_parser.can_fetch(user_agent, url)

class BaseSourceAdapter(ABC):
    """Base class for all source adapters"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.rate_limiter = RateLimiter(config.get('requests_per_minute', 60))
        self.cache = CacheManager(config.get('cache_ttl', 3600))
        self.robots_checker = RobotsChecker()
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={'User-Agent': self.config.get('user_agent', 'EDI-Graph/1.0')},
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3,
        max_time=300
    )
    async def fetch_url(self, url: str, params: Dict = None) -> Optional[Dict]:
        """Fetch URL with rate limiting, caching, and retries"""
        
        # Check cache first
        cached_data = self.cache.get(url, params)
        if cached_data:
            logger.info(f"Cache hit for {url}")
            return cached_data
        
        # Check robots.txt
        if not await self.robots_checker.can_fetch(url):
            logger.warning(f"Robots.txt disallows fetching {url}")
            return None
        
        # Rate limit
        await self.rate_limiter.acquire()
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json() if 'json' in response.content_type else await response.text()
                    self.cache.set(url, data, params)
                    logger.info(f"Successfully fetched {url}")
                    return data
                else:
                    logger.warning(f"HTTP {response.status} for {url}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            raise
    
    @abstractmethod
    async def fetch_signals(self, query_params: Dict = None) -> List[RawSignal]:
        """Fetch and normalize signals from this source"""
        pass
    
    @abstractmethod
    def normalize_signal(self, raw_data: Dict) -> RawSignal:
        """Convert source-specific data to RawSignal format"""
        pass

class NewsAdapter(BaseSourceAdapter):
    """Adapter for news/press sources"""
    
    async def fetch_signals(self, query_params: Dict = None) -> List[RawSignal]:
        """Fetch news signals"""
        signals = []
        
        # Example: NewsAPI integration
        if 'newsapi_key' in self.config:
            url = "https://newsapi.org/v2/everything"
            params = {
                'apiKey': self.config['newsapi_key'],
                'q': query_params.get('query', 'technology startup funding'),
                'sortBy': 'publishedAt',
                'pageSize': 100,
                'language': 'en'
            }
            
            data = await self.fetch_url(url, params)
            if data and 'articles' in data:
                for article in data['articles']:
                    signal = self.normalize_signal(article)
                    if signal:
                        signals.append(signal)
        
        return signals
    
    def normalize_signal(self, raw_data: Dict) -> RawSignal:
        """Normalize news article to RawSignal"""
        return RawSignal(
            source="newsapi",
            signal_type="news",
            title=raw_data.get('title', ''),
            content=raw_data.get('description', '') + ' ' + raw_data.get('content', ''),
            url=raw_data.get('url', ''),
            published_date=raw_data.get('publishedAt', ''),
            raw_data=raw_data
        )

class JobsAdapter(BaseSourceAdapter):
    """Adapter for job posting sources"""
    
    async def fetch_signals(self, query_params: Dict = None) -> List[RawSignal]:
        """Fetch job posting signals"""
        signals = []
        
        # Example: Adzuna Jobs API
        if 'adzuna_id' in self.config and 'adzuna_key' in self.config:
            url = f"https://api.adzuna.com/v1/api/jobs/us/search/1"
            params = {
                'app_id': self.config['adzuna_id'],
                'app_key': self.config['adzuna_key'],
                'what': query_params.get('query', 'software engineer'),
                'results_per_page': 50,
                'sort_by': 'date'
            }
            
            data = await self.fetch_url(url, params)
            if data and 'results' in data:
                for job in data['results']:
                    signal = self.normalize_signal(job)
                    if signal:
                        signals.append(signal)
        
        return signals
    
    def normalize_signal(self, raw_data: Dict) -> RawSignal:
        """Normalize job posting to RawSignal"""
        company_name = raw_data.get('company', {}).get('display_name', '')
        
        return RawSignal(
            source="adzuna",
            signal_type="job_posting",
            title=raw_data.get('title', ''),
            content=raw_data.get('description', ''),
            url=raw_data.get('redirect_url', ''),
            published_date=raw_data.get('created', ''),
            raw_data=raw_data,
            company_mentions=[company_name] if company_name else []
        )

class FundingAdapter(BaseSourceAdapter):
    """Adapter for funding/investment sources"""
    
    async def fetch_signals(self, query_params: Dict = None) -> List[RawSignal]:
        """Fetch funding signals"""
        signals = []
        
        # Example: Crunchbase-like API (mock implementation)
        # In real implementation, you'd use actual funding APIs
        mock_funding_data = [
            {
                'company': 'TechCorp',
                'round_type': 'Series A',
                'amount': 5000000,
                'date': '2024-08-15',
                'investors': ['VC Fund 1', 'Angel Investor'],
                'description': 'TechCorp raises $5M Series A for AI platform development'
            }
        ]
        
        for funding in mock_funding_data:
            signal = self.normalize_signal(funding)
            signals.append(signal)
        
        return signals
    
    def normalize_signal(self, raw_data: Dict) -> RawSignal:
        """Normalize funding data to RawSignal"""
        return RawSignal(
            source="funding_tracker",
            signal_type="funding",
            title=f"{raw_data.get('company', '')} raises {raw_data.get('round_type', '')}",
            content=raw_data.get('description', ''),
            url="",  # Would be populated with actual source URL
            published_date=raw_data.get('date', ''),
            raw_data=raw_data,
            company_mentions=[raw_data.get('company', '')]
        )

class TechTrackerAdapter(BaseSourceAdapter):
    """Adapter for technology tracking sources"""
    
    async def fetch_signals(self, query_params: Dict = None) -> List[RawSignal]:
        """Fetch technology signals"""
        signals = []
        
        # Example: GitHub trending, Stack Overflow trends, etc.
        # Mock implementation
        mock_tech_data = [
            {
                'technology': 'React 18',
                'trend_score': 95,
                'description': 'React 18 adoption increasing in enterprise applications',
                'date': '2024-08-30',
                'source_url': 'https://github.com/trending'
            }
        ]
        
        for tech in mock_tech_data:
            signal = self.normalize_signal(tech)
            signals.append(signal)
        
        return signals
    
    def normalize_signal(self, raw_data: Dict) -> RawSignal:
        """Normalize tech data to RawSignal"""
        return RawSignal(
            source="tech_tracker",
            signal_type="tech_mention",
            title=f"Technology trend: {raw_data.get('technology', '')}",
            content=raw_data.get('description', ''),
            url=raw_data.get('source_url', ''),
            published_date=raw_data.get('date', ''),
            raw_data=raw_data,
            technology_mentions=[raw_data.get('technology', '')]
        )

class ExecChangesAdapter(BaseSourceAdapter):
    """Adapter for executive changes sources"""
    
    async def fetch_signals(self, query_params: Dict = None) -> List[RawSignal]:
        """Fetch executive change signals"""
        signals = []
        
        # Example: LinkedIn job changes, press releases
        # Mock implementation
        mock_exec_data = [
            {
                'person': 'John Smith',
                'company': 'TechCorp',
                'position': 'CTO',
                'change_type': 'new_hire',
                'date': '2024-08-25',
                'description': 'John Smith joins TechCorp as new CTO'
            }
        ]
        
        for exec_change in mock_exec_data:
            signal = self.normalize_signal(exec_change)
            signals.append(signal)
        
        return signals
    
    def normalize_signal(self, raw_data: Dict) -> RawSignal:
        """Normalize executive change to RawSignal"""
        return RawSignal(
            source="exec_tracker",
            signal_type="exec_change",
            title=f"Executive change: {raw_data.get('change_type', '')}",
            content=raw_data.get('description', ''),
            url="",  # Would be populated with actual source URL
            published_date=raw_data.get('date', ''),
            raw_data=raw_data,
            company_mentions=[raw_data.get('company', '')],
            person_mentions=[raw_data.get('person', '')]
        )

class SourceManager:
    """Manages multiple source adapters"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.adapters = {
            'news': NewsAdapter(config.get('news', {})),
            'jobs': JobsAdapter(config.get('jobs', {})),
            'funding': FundingAdapter(config.get('funding', {})),
            'tech': TechTrackerAdapter(config.get('tech', {})),
            'executives': ExecChangesAdapter(config.get('executives', {}))
        }
    
    async def fetch_all_signals(self, query_params: Dict = None) -> List[RawSignal]:
        """Fetch signals from all configured sources"""
        all_signals = []
        
        tasks = []
        for source_name, adapter in self.adapters.items():
            if self.config.get(source_name, {}).get('enabled', True):
                async with adapter:
                    task = adapter.fetch_signals(query_params)
                    tasks.append((source_name, task))
        
        for source_name, task in tasks:
            try:
                signals = await task
                all_signals.extend(signals)
                logger.info(f"Fetched {len(signals)} signals from {source_name}")
            except Exception as e:
                logger.error(f"Error fetching from {source_name}: {e}")
        
        return all_signals

# Example configuration
CONFIG_EXAMPLE = {
    'news': {
        'enabled': True,
        'newsapi_key': 'your_newsapi_key_here',
        'requests_per_minute': 30,
        'cache_ttl': 3600,
        'user_agent': 'EDI-Graph/1.0'
    },
    'jobs': {
        'enabled': True,
        'adzuna_id': 'your_adzuna_id',
        'adzuna_key': 'your_adzuna_key',
        'requests_per_minute': 60,
        'cache_ttl': 7200
    },
    'funding': {
        'enabled': True,
        'requests_per_minute': 30,
        'cache_ttl': 3600
    },
    'tech': {
        'enabled': True,
        'requests_per_minute': 60,
        'cache_ttl': 1800
    },
    'executives': {
        'enabled': True,
        'requests_per_minute': 30,
        'cache_ttl': 3600
    }
}

# Example usage
async def main():
    """Example usage of source adapters"""
    config = CONFIG_EXAMPLE
    manager = SourceManager(config)
    
    # Fetch signals for a specific ICP query
    query_params = {
        'query': 'B2B SaaS startup funding AI machine learning',
        'companies': ['Salesforce', 'HubSpot', 'Slack'],
        'technologies': ['AI', 'machine learning', 'cloud computing']
    }
    
    signals = await manager.fetch_all_signals(query_params)
    
    logger.info(f"Total signals fetched: {len(signals)}")
    for signal in signals[:5]:  # Show first 5
        print(f"Signal: {signal.title[:50]}... from {signal.source}")

if __name__ == "__main__":
    asyncio.run(main())