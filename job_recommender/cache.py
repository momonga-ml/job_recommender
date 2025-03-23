import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class JobCache:
    def __init__(self, cache_dir: str = ".cache", cache_duration: int = 24):
        """
        Initialize the job cache.
        
        Args:
            cache_dir: Directory to store cache files
            cache_duration: How long to keep cache entries in hours
        """
        self.cache_dir = cache_dir
        self.cache_duration = timedelta(hours=cache_duration)
        self._ensure_cache_dir()
        
    def _ensure_cache_dir(self):
        """Ensure the cache directory exists."""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            
    def _get_cache_key(self, site: str, query: str, location: str) -> str:
        """Generate a unique cache key for the search parameters."""
        key_string = f"{site}:{query}:{location}".lower()
        return hashlib.md5(key_string.encode()).hexdigest()
        
    def _get_cache_file(self, cache_key: str) -> str:
        """Get the path to the cache file for a given key."""
        return os.path.join(self.cache_dir, f"{cache_key}.json")
        
    def get_cached_jobs(self, site: str, query: str, location: str) -> Optional[List[Dict]]:
        """
        Retrieve cached jobs if they exist and are not expired.
        
        Args:
            site: Job site name
            query: Search query
            location: Location to search in
            
        Returns:
            List of cached jobs if valid, None otherwise
        """
        cache_key = self._get_cache_key(site, query, location)
        cache_file = self._get_cache_file(cache_key)
        
        if not os.path.exists(cache_file):
            return None
            
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                
            # Check if cache is expired
            cache_time = datetime.fromisoformat(cache_data['timestamp'])
            if datetime.now() - cache_time > self.cache_duration:
                logger.info(f"Cache expired for {site} search: {query} in {location}")
                return None
                
            logger.info(f"Using cached results for {site} search: {query} in {location}")
            return cache_data['jobs']
            
        except Exception as e:
            logger.error(f"Error reading cache: {str(e)}")
            return None
            
    def cache_jobs(self, site: str, query: str, location: str, jobs: List[Dict]):
        """
        Cache job results.
        
        Args:
            site: Job site name
            query: Search query
            location: Location to search in
            jobs: List of job dictionaries to cache
        """
        cache_key = self._get_cache_key(site, query, location)
        cache_file = self._get_cache_file(cache_key)
        
        try:
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'site': site,
                'query': query,
                'location': location,
                'jobs': jobs
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Cached {len(jobs)} jobs for {site} search: {query} in {location}")
            
        except Exception as e:
            logger.error(f"Error writing to cache: {str(e)}")
            
    def clear_cache(self, site: Optional[str] = None):
        """
        Clear the cache, optionally for a specific site.
        
        Args:
            site: Optional site name to clear cache for
        """
        try:
            if site:
                # Clear cache files for specific site
                for filename in os.listdir(self.cache_dir):
                    if filename.endswith('.json'):
                        cache_file = os.path.join(self.cache_dir, filename)
                        with open(cache_file, 'r', encoding='utf-8') as f:
                            cache_data = json.load(f)
                            if cache_data['site'] == site:
                                os.remove(cache_file)
                logger.info(f"Cleared cache for site: {site}")
            else:
                # Clear all cache files
                for filename in os.listdir(self.cache_dir):
                    if filename.endswith('.json'):
                        os.remove(os.path.join(self.cache_dir, filename))
                logger.info("Cleared all cache files")
                
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}") 