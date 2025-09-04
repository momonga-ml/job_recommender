"""Factory module for job scrapers to avoid circular imports."""
from typing import Optional, Type
from .job_scraper import IndeedScraper, LinkedInScraper, GlassdoorScraper, BaseJobScraper

def get_scraper(site: str) -> Optional[Type[BaseJobScraper]]:
    """Factory function to get the appropriate scraper based on the site."""
    scrapers = {
        "indeed": IndeedScraper,
        "linkedin": LinkedInScraper,
        "glassdoor": GlassdoorScraper
    }
    return scrapers.get(site.lower())
