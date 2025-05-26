import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

from sqlalchemy.orm import sessionmaker, Session as SqlaSession
from sqlalchemy.exc import SQLAlchemyError

from job_recommender.db_schema import CachedSearches
from job_recommender.db_utils import create_db_engine

logger = logging.getLogger(__name__)

class JobCache:
    def __init__(self, cache_duration: int = 24, engine=None):
        """
        Initialize the job cache using a PostgreSQL database.

        Args:
            cache_duration: How long to keep cache entries in hours.
            engine: Optional SQLAlchemy engine. If None, a new engine
                    will be created using create_db_engine().
        """
        self.cache_duration = timedelta(hours=cache_duration)
        self.engine = engine or create_db_engine()
        self.Session = sessionmaker(bind=self.engine)

    def _get_cache_key(self, site: str, query: str, location: str) -> str:
        """Generate a unique cache key (search_hash) for the search parameters."""
        key_string = f"{site}:{query}:{location}".lower()
        return hashlib.md5(key_string.encode()).hexdigest()

    def get_cached_jobs(self, site: str, query: str, location: str) -> Optional[List[Dict]]:
        """
        Retrieve cached jobs from the database if they exist and are not expired.

        Args:
            site: Job site name.
            query: Search query.
            location: Location to search in.

        Returns:
            List of cached job dictionaries if a valid cache entry is found, None otherwise.
        """
        cache_key = self._get_cache_key(site, query, location)
        session: SqlaSession = self.Session()
        try:
            cached_entry = session.query(CachedSearches).filter_by(search_hash=cache_key).first()

            if cached_entry:
                if datetime.utcnow() - cached_entry.timestamp > self.cache_duration:
                    logger.info(
                        f"Cache expired for {site} search: {query} in {location} (hash: {cache_key})"
                    )
                    # Delete expired entry
                    session.delete(cached_entry)
                    session.commit()
                    return None
                
                logger.info(
                    f"Using cached results for {site} search: {query} in {location} (hash: {cache_key})"
                )
                return cached_entry.job_data
            else:
                logger.debug(f"No cache found for {site} search: {query} in {location} (hash: {cache_key})")
                return None
        except SQLAlchemyError as e:
            logger.error(f"Database error while getting cached jobs (hash: {cache_key}): {e}")
            session.rollback()
            return None
        finally:
            session.close()

    def cache_jobs(self, site: str, query: str, location: str, jobs: List[Dict]):
        """
        Cache job results in the database. Creates a new entry or updates an existing one.

        Args:
            site: Job site name.
            query: Search query.
            location: Location to search in.
            jobs: List of job dictionaries to cache.
        """
        cache_key = self._get_cache_key(site, query, location)
        session: SqlaSession = self.Session()
        try:
            existing_entry = session.query(CachedSearches).filter_by(search_hash=cache_key).first()

            if existing_entry:
                existing_entry.timestamp = datetime.utcnow()
                existing_entry.job_data = jobs
                logger.info(
                    f"Updating existing cache for {site} search: {query} in {location} (hash: {cache_key})"
                )
            else:
                new_entry = CachedSearches(
                    search_hash=cache_key,
                    site_name=site,
                    query_string=query,
                    location_string=location,
                    timestamp=datetime.utcnow(),
                    job_data=jobs,
                )
                session.add(new_entry)
                logger.info(
                    f"Caching {len(jobs)} jobs for {site} search: {query} in {location} (hash: {cache_key})"
                )
            
            session.commit()

        except SQLAlchemyError as e:
            logger.error(f"Database error while caching jobs (hash: {cache_key}): {e}")
            session.rollback()
        finally:
            session.close()

    def clear_cache(self, site: Optional[str] = None):
        """
        Clear the cache from the database, optionally for a specific site.

        Args:
            site: Optional site name to clear cache for. If None, clears all cached searches.
        """
        session: SqlaSession = self.Session()
        try:
            if site:
                deleted_count = (
                    session.query(CachedSearches)
                    .filter(CachedSearches.site_name == site)
                    .delete(synchronize_session=False)
                )
                logger.info(f"Cleared {deleted_count} cache entries for site: {site}")
            else:
                deleted_count = session.query(CachedSearches).delete(synchronize_session=False)
                logger.info(f"Cleared all {deleted_count} cache entries from the database.")
            
            session.commit()

        except SQLAlchemyError as e:
            logger.error(f"Database error while clearing cache: {e}")
            session.rollback()
        finally:
            session.close()