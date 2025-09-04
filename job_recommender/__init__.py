"""
Job Recommender package for scraping and analyzing job descriptions.
""" 
__version__ = "0.1.0"

# Make key classes and functions available at package level
from .job_scraper import BaseJobScraper, IndeedScraper, LinkedInScraper, GlassdoorScraper
from .job_analyzer import JobAnalyzer, analyze_jobs_and_resume
from .parallel_scraper import ParallelJobScraper
from .cache import JobCache
from .scraper_factory import get_scraper
from .utils import ScraperError, RateLimitError, ScraperTimeoutError
from .logging_config import setup_logging, get_logger

__all__ = [
    'BaseJobScraper',
    'IndeedScraper', 
    'LinkedInScraper',
    'GlassdoorScraper',
    'JobAnalyzer',
    'analyze_jobs_and_resume',
    'ParallelJobScraper',
    'JobCache',
    'get_scraper',
    'ScraperError',
    'RateLimitError', 
    'ScraperTimeoutError',
    'setup_logging',
    'get_logger'
]