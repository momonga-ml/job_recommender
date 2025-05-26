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
        # progress_bar is problematic here as it's shared state modified by multiple threads
        # Individual site progress should be handled by the main loop observing futures.
        # For now, removing direct progress_bar update from here for overall task.
        # Site-specific status (like "Scraping X", "Failed X") will be printed.
    ) -> tuple[bool, List[Dict]]:
        """
        Scrape jobs from a single site.
        
        Args:
            site: Job site name
            query: Search query
            location: Location to search in
            num_jobs: Number of jobs to scrape
            
        Returns:
            A tuple (success_status: bool, jobs_list: List[Dict])
        """
        # Check cache first
        cached_jobs = self.cache.get_cached_jobs(site, query, location)
        if cached_jobs:
            print_success(f"Using cached results for {site} ({len(cached_jobs)} jobs found).")
            return True, cached_jobs[:num_jobs]
            
        # If not in cache, scrape the site
        scraper_instance_result = get_scraper(site) # get_scraper now returns instance or None
        if not scraper_instance_result: # This means scraper_class was None in get_scraper
            print_warning(f"Unsupported job site: {site}. Scraper could not be initialized.")
            return False, [] # Explicitly return False for status
            
        # If get_scraper was successful, it returns an instance of the scraper.
        scraper = scraper_instance_result 
        # scraper = scraper_class(output_dir=self.output_dir) # Old way

        try:
            print_info(f"Starting to scrape {site}...")
            jobs = scraper.scrape_jobs(query, location, num_jobs)
            self.cache.cache_jobs(site, query, location, jobs) # Cache even if no jobs found (empty list)
            print_success(f"Completed scraping {site}. Found {len(jobs)} jobs.")
            return True, jobs
        except Exception as e:
            print_error(f"Error scraping {site}: {str(e)}")
            # logger.exception(f"Detailed error scraping {site}:") # For more detailed logs if needed
            return False, []
        finally:
            # Ensure scraper.close() is called if scraper was initialized
            if scraper_instance_result: # Check if scraper object exists
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
        # The progress bar instance from create_progress_bar should not be passed to _scrape_site directly
        # as its updates are not thread-safe in the way it was used.
        # Instead, the main loop here will update the overall progress.
        with create_progress_bar("Scraping sites", len(sites), "site") as progress:
            overall_task_id = progress.add_task("[cyan]Overall Progress", total=len(sites), count="0/{}".format(len(sites)))
            
            successful_site_runs = 0
            failed_site_runs = 0

            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_site = {
                    executor.submit(self._scrape_site, site, query, location, num_jobs): site
                    for site in sites
                }
                
                sites_processed_count = 0
                for future in concurrent.futures.as_completed(future_to_site):
                    site = future_to_site[future]
                    try:
                        status, jobs_data = future.result()
                        if status:
                            all_jobs.extend(jobs_data)
                            successful_site_runs +=1
                            # Update progress description for the specific site if possible, or just overall.
                            # For now, rich_utils.create_progress_bar might not support per-site dynamic descriptions easily here.
                            # We can log success.
                            # print_success(f"Successfully processed results from {site}.") # This might be too verbose
                        else:
                            failed_site_runs += 1
                            # Error already printed in _scrape_site
                            # print_warning(f"Site {site} failed or returned no data due to errors.")
                    except Exception as e:
                        # This catches errors from future.result() itself, e.g., if _scrape_site had an unhandled error
                        # before returning the tuple, or if the task was cancelled, etc.
                        print_error(f"Critical error processing future for site {site}: {str(e)}")
                        failed_site_runs += 1
                    
                    sites_processed_count += 1
                    progress.update(overall_task_id, advance=1, count=f"{sites_processed_count}/{len(sites)}")

        # Print job summary
        print_job_summary(all_jobs) # Shows total jobs collected
        
        # Print completion summary
        duration = time.time() - start_time
        # Pass new counts to print_scraping_complete or a new summary function
        print_scraping_complete(
            total_jobs_scraped=len(all_jobs),
            duration=duration,
            sites_attempted=len(sites),
            successful_sites=successful_site_runs,
            failed_sites=failed_site_runs
        )
        
        return all_jobs
        
    def clear_cache(self, site: Optional[str] = None):
        """
        Clear the job cache.
        
        Args:
            site: Optional site name to clear cache for
        """
        self.cache.clear_cache(site)
        if site:
            print_info(f"Cleared cache for site: {site}") # Changed to print_info for consistency
        else:
            print_info("Cleared all cache files") # Changed to print_info