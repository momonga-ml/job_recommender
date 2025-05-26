import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class JobCache:
    def __init__(self, cache_dir: str = ".cache", cache_duration: int = 24,
                 max_cache_files: Optional[int] = None, 
                 max_cache_size_bytes: Optional[int] = None):
        """
        Initialize the job cache.
        
        Args:
            cache_dir: Directory to store cache files
            cache_duration: How long to keep cache entries in hours
            max_cache_files: Maximum number of files to store in the cache
            max_cache_size_bytes: Maximum total size of cache files in bytes
        """
        self.cache_dir = cache_dir
        self.cache_duration = timedelta(hours=cache_duration)
        self.max_cache_files = max_cache_files
        self.max_cache_size_bytes = max_cache_size_bytes
        self._ensure_cache_dir()

    def _scan_cache_files(self) -> List[Dict]:
        """Scans the cache directory and returns metadata for each cache file."""
        cache_files_metadata = []
        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.cache_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Get file system metadata
                    stat_info = os.stat(filepath)
                    
                    cache_files_metadata.append({
                        'filepath': filepath,
                        'site': data.get('site'),
                        'query': data.get('query'),
                        'location': data.get('location'),
                        'timestamp': data.get('timestamp'), # Creation timestamp
                        'size_bytes': stat_info.st_size,
                        'last_accessed': stat_info.st_atime # Last access time
                    })
                except Exception as e:
                    logger.error(f"Error scanning cache file {filepath}: {e}")
        
        # Sort by last accessed time (oldest first) for LRU
        cache_files_metadata.sort(key=lambda x: x['last_accessed'])
        return cache_files_metadata

    def _evict_files(self, files_to_evict: List[str]):
        """Evicts (deletes) the specified cache files."""
        for filepath in files_to_evict:
            try:
                os.remove(filepath)
                logger.info(f"Evicted cache file: {filepath}")
            except Exception as e:
                logger.error(f"Error evicting cache file {filepath}: {e}")

    def _enforce_cache_limits(self):
        """Enforces cache limits by evicting files if necessary."""
        if self.max_cache_files is None and self.max_cache_size_bytes is None:
            return # No limits set

        cache_files_metadata = self._scan_cache_files()
        
        # File count limit
        if self.max_cache_files is not None and len(cache_files_metadata) > self.max_cache_files:
            num_to_evict = len(cache_files_metadata) - self.max_cache_files
            files_to_evict = [mf['filepath'] for mf in cache_files_metadata[:num_to_evict]]
            logger.info(f"Cache file count limit ({self.max_cache_files}) exceeded. Evicting {len(files_to_evict)} files.")
            self._evict_files(files_to_evict)
            # Rescan metadata after eviction
            cache_files_metadata = self._scan_cache_files() 

        # Size limit
        if self.max_cache_size_bytes is not None:
            current_total_size = sum(mf['size_bytes'] for mf in cache_files_metadata)
            if current_total_size > self.max_cache_size_bytes:
                logger.info(f"Cache size limit ({self.max_cache_size_bytes} bytes) exceeded. Current size: {current_total_size} bytes. Evicting files.")
                files_to_evict_for_size = []
                # Sort by last_accessed (oldest first) which is already done by _scan_cache_files
                for metafile in cache_files_metadata:
                    if current_total_size <= self.max_cache_size_bytes:
                        break
                    files_to_evict_for_size.append(metafile['filepath'])
                    current_total_size -= metafile['size_bytes']
                
                if files_to_evict_for_size:
                    self._evict_files(files_to_evict_for_size)
        
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
                # Optionally remove expired file
                # os.remove(cache_file) 
                return None
            
            # Update last access time for LRU
            try:
                os.utime(cache_file, None) # Update to current time
            except Exception as e:
                logger.error(f"Error updating access time for {cache_file}: {e}")
                
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
            self._enforce_cache_limits() # Enforce cache limits after adding a new file
            
        except Exception as e:
            logger.error(f"Error writing to cache: {str(e)}")

    def clear_cache(self, site: Optional[str] = None, query: Optional[str] = None, location: Optional[str] = None):
        """
        Clear the cache based on specified criteria.

        Args:
            site: Optional site name to clear cache for.
            query: Optional query string to clear cache for.
            location: Optional location to clear cache for.
        """
        files_cleared_count = 0
        try:
            if not site and not query and not location:
                # Clear all cache files
                for filename in os.listdir(self.cache_dir):
                    if filename.endswith('.json'):
                        filepath = os.path.join(self.cache_dir, filename)
                        try:
                            os.remove(filepath)
                            files_cleared_count += 1
                        except Exception as e:
                            logger.error(f"Error deleting file {filepath}: {e}")
                if files_cleared_count > 0:
                    logger.info(f"Cleared all ({files_cleared_count}) cache files.")
                else:
                    logger.info("No cache files to clear.")
                return

            # Granular clearing
            log_message_parts = ["Cleared cache for"]
            if site: log_message_parts.append(f"site: {site}")
            if query: log_message_parts.append(f"query: {query}")
            if location: log_message_parts.append(f"location: {location}")

            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.cache_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            cache_data = json.load(f)
                        
                        match = True
                        if site and cache_data.get('site') != site:
                            match = False
                        if query and cache_data.get('query') != query:
                            match = False
                        if location and cache_data.get('location') != location:
                            match = False
                        
                        if match:
                            os.remove(filepath)
                            files_cleared_count += 1
                            logger.debug(f"Deleted cache file: {filepath}")

                    except json.JSONDecodeError:
                        logger.error(f"Error decoding JSON from {filepath}. Skipping.")
                    except Exception as e:
                        logger.error(f"Error processing file {filepath}: {e}")
            
            if files_cleared_count > 0:
                logger.info(f"{' '.join(log_message_parts)}. Removed {files_cleared_count} file(s).")
            else:
                logger.info(f"No cache files found matching criteria: {' '.join(log_message_parts[1:])}")

        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")

    def clear_expired_cache(self):
        """Clears all expired cache files based on cache_duration."""
        expired_files_count = 0
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.cache_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            cache_data = json.load(f)
                        
                        cache_time_str = cache_data.get('timestamp')
                        if not cache_time_str:
                            logger.warning(f"Cache file {filepath} has no timestamp. Skipping.")
                            continue

                        cache_time = datetime.fromisoformat(cache_time_str)
                        if datetime.now() - cache_time > self.cache_duration:
                            os.remove(filepath)
                            expired_files_count += 1
                            logger.info(f"Removed expired cache file: {filepath}")
                            
                    except json.JSONDecodeError:
                        logger.error(f"Error decoding JSON from {filepath} during expiration check. Skipping.")
                    except ValueError: # For fromisoformat errors
                        logger.error(f"Error parsing timestamp from {filepath}. Skipping.")
                    except Exception as e:
                        logger.error(f"Error processing file {filepath} for expiration check: {e}")
            
            if expired_files_count > 0:
                logger.info(f"Cleared {expired_files_count} expired cache file(s).")
            else:
                logger.info("No expired cache files found to clear.")
        
        except Exception as e:
            logger.error(f"Error during expired cache clearing process: {str(e)}")