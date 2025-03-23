import concurrent.futures
from typing import List, Dict, Optional
import logging
import time
from .job_scraper import get_scraper, BaseJobScraper
from .cache import JobCache
from .rich_utils import (
    create_progress_bar,
    print_success,
    print_warning,
    print_error,
    print_info,
    print_job_summary,
    print_scraping_start,
    print_scraping_complete
)

logger = logging.getLogger(__name__)

class ParallelJobScraper:
    def __init__(
        self,
        output_dir: str = "job_descriptions",
        cache_dir: str = ".cache",
        cache_duration: int = 24,
        max_workers: int = 3
    ):
        """
        Initialize the parallel job scraper.
        
        Args:
            output_dir: Directory to save job descriptions
            cache_dir: Directory for cache files
            cache_duration: How long to keep cache entries in hours
            max_workers: Maximum number of parallel scraping workers
        """
        self.output_dir = output_dir
        self.cache = JobCache(cache_dir, cache_duration)
        self.max_workers = max_workers
        
    def _scrape_site(
        self,
        site: str,
        query: str,
        location: str,
        num_jobs: int,
        progress_bar: Optional[Progress] = None
    ) -> List[Dict]:
        """
        Scrape jobs from a single site.
        
        Args:
            site: Job site name
            query: Search query
            location: Location to search in
            num_jobs: Number of jobs to scrape
            progress_bar: Optional progress bar to update
            
        Returns:
            List of scraped jobs
        """
        # Check cache first
        cached_jobs = self.cache.get_cached_jobs(site, query, location)
        if cached_jobs:
            if progress_bar:
                progress_bar.update(progress_bar.task_ids[0], completed=1)
                progress_bar.update(progress_bar.task_ids[0], description=f"[green]Using cached results from {site}")
            print_success(f"Using cached results from {site}")
            return cached_jobs[:num_jobs]
            
        # If not in cache, scrape the site
        scraper_class = get_scraper(site)
        if not scraper_class:
            print_warning(f"Unsupported job site: {site}")
            if progress_bar:
                progress_bar.update(progress_bar.task_ids[0], completed=1)
            return []
            
        scraper = scraper_class(output_dir=self.output_dir)
        try:
            if progress_bar:
                progress_bar.update(progress_bar.task_ids[0], description=f"[yellow]Scraping {site}")
            print_info(f"Starting to scrape {site}")
            jobs = scraper.scrape_jobs(query, location, num_jobs)
            # Cache the results
            self.cache.cache_jobs(site, query, location, jobs)
            if progress_bar:
                progress_bar.update(progress_bar.task_ids[0], completed=1)
                progress_bar.update(progress_bar.task_ids[0], description=f"[green]Completed {site}")
            print_success(f"Completed scraping {len(jobs)} jobs from {site}")
            return jobs
        except Exception as e:
            print_error(f"Error scraping {site}: {str(e)}")
            if progress_bar:
                progress_bar.update(progress_bar.task_ids[0], completed=1)
                progress_bar.update(progress_bar.task_ids[0], description=f"[red]Failed {site}")
            return []
        finally:
            scraper.close()
            
    def scrape_jobs(
        self,
        sites: List[str],
        query: str,
        location: str,
        num_jobs: int = 10
    ) -> List[Dict]:
        """
        Scrape jobs from multiple sites in parallel.
        
        Args:
            sites: List of job sites to scrape
            query: Search query
            location: Location to search in
            num_jobs: Number of jobs to scrape per site
            
        Returns:
            List of all scraped jobs
        """
        start_time = time.time()
        all_jobs = []
        
        # Print scraping start header
        print_scraping_start(sites, query, location)
        
        # Create progress bar for sites
        with create_progress_bar("Scraping sites", len(sites), "site") as progress:
            task_id = progress.add_task("[cyan]Overall Progress", total=len(sites), count="0/{}".format(len(sites)))
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit scraping tasks for each site
                future_to_site = {
                    executor.submit(
                        self._scrape_site,
                        site,
                        query,
                        location,
                        num_jobs,
                        progress
                    ): site for site in sites
                }
                
                # Process completed tasks
                completed = 0
                for future in concurrent.futures.as_completed(future_to_site):
                    site = future_to_site[future]
                    try:
                        jobs = future.result()
                        all_jobs.extend(jobs)
                        completed += 1
                        progress.update(task_id, count=f"{completed}/{len(sites)}")
                    except Exception as e:
                        print_error(f"Error processing results from {site}: {str(e)}")
        
        # Print job summary
        print_job_summary(all_jobs)
        
        # Print completion summary
        duration = time.time() - start_time
        print_scraping_complete(len(all_jobs), duration)
        
        return all_jobs
        
    def clear_cache(self, site: Optional[str] = None):
        """
        Clear the job cache.
        
        Args:
            site: Optional site name to clear cache for
        """
        self.cache.clear_cache(site)
        if site:
            print_success(f"Cleared cache for site: {site}")
        else:
            print_success("Cleared all cache files") 