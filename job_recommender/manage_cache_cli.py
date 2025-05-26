#!/usr/bin/env python3
import argparse
import logging
import sys

# Explicitly import JobCache from the job_recommender.cache module
from job_recommender.cache import JobCache


# Configure basic logging to stdout
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

def handle_clear(args, job_cache: JobCache):
    """Handles the 'clear' command."""
    logger.info(
        f"Attempting to clear cache with criteria: Site='{args.site}', Query='{args.query}', Location='{args.location}'"
    )
    job_cache.clear_cache(site=args.site, query=args.query, location=args.location)
    # The JobCache.clear_cache method already logs the outcome.
    # We can add a summary here if needed, e.g. "Clear command processed."

def handle_clear_expired(args, job_cache: JobCache):
    """Handles the 'clear-expired' command."""
    logger.info("Attempting to clear expired cache entries.")
    job_cache.clear_expired_cache()
    # The JobCache.clear_expired_cache method already logs the outcome.
    # We can add a summary here, e.g. "Clear-expired command processed."

def main():
    parser = argparse.ArgumentParser(description="Manage the job recommender cache.")
    parser.add_argument('--cache-dir', type=str, default='.cache',
                        help='The directory to use for caching. Defaults to ./.cache')
    
    subparsers = parser.add_subparsers(dest='command', required=True, 
                                       help="Available commands")

    # 'clear' command
    clear_parser = subparsers.add_parser('clear', help="Clear cache entries. "
                                       "Without arguments, clears all cache.")
    clear_parser.add_argument('--site', type=str, default=None,
                              help="The site name to clear cache for (e.g., 'LinkedIn').")
    clear_parser.add_argument('--query', type=str, default=None,
                              help="The search query to clear cache for (e.g., 'Software Engineer').")
    clear_parser.add_argument('--location', type=str, default=None,
                              help="The location to clear cache for (e.g., 'Remote').")
    clear_parser.set_defaults(func=handle_clear)

    # 'clear-expired' command
    clear_expired_parser = subparsers.add_parser('clear-expired', 
                                                 help="Clear all expired cache entries based on duration.")
    clear_expired_parser.set_defaults(func=handle_clear_expired)
    
    # Initialize JobCache - using default settings for now
    # TODO: Consider allowing configuration of cache_dir and cache_duration via CLI args or env vars if needed.
    # For now, cache_duration uses JobCache's default.
    
    args = parser.parse_args() # Parse arguments first to get cache_dir

    # Initialize JobCache with the specified or default cache_dir
    # Assuming JobCache's __init__ is like: JobCache(cache_dir="...", cache_duration=..., etc.)
    # We are only overriding cache_dir here. Other params will use JobCache defaults.
    job_cache_instance = JobCache(cache_dir=args.cache_dir)

    args.func(args, job_cache_instance)

if __name__ == '__main__':
    main()
