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
        self.output_dir = output_dir # Kept for BaseJobScraper instances, not directly used by ParallelJobScraper for saving
        # JobCache now takes cache_duration and optional engine. cache_dir is removed for DB ops.
        self.cache = JobCache(cache_duration=cache_duration) 
        self.engine = self.cache.engine # Expose engine from JobCache
        self.max_workers = max_workers
        
    def _scrape_site(
        self,
        site: str,
        query: str,
        location: str, # This is the search location
        num_jobs: int,
        progress_bar: Optional['Progress'] = None # Use quotes if Progress not imported/defined here
    ) -> List[Dict]:
        """
        Scrape jobs from a single site, adding search_hash and ensuring location for saving.
        
        Args:
            site: Job site name
            query: Search query
            location: Location searched in (used as default for job_dict if not otherwise specified)
            num_jobs: Number of jobs to scrape
            progress_bar: Optional progress bar to update
            
        Returns:
            List of scraped/cached jobs, each with 'search_hash_for_saving' and 'location' keys.
        """
        search_hash = self.cache._get_cache_key(site, query, location)
        retrieved_jobs: List[Dict] = [] # Ensure it's always a list

        # Check cache first
        cached_jobs_data = self.cache.get_cached_jobs(site, query, location)
        if cached_jobs_data:
            if progress_bar and hasattr(progress_bar, 'task_ids') and progress_bar.task_ids:
                progress_bar.update(progress_bar.task_ids[0], completed=1)
                progress_bar.update(progress_bar.task_ids[0], description=f"[green]Using cached results from {site}")
            print_success(f"Using cached results from {site} for query: '{query}', location: '{location}'")
            # Add search_hash and ensure location for each job from cache
            for job_data in cached_jobs_data[:num_jobs]:
                job_data['search_hash_for_saving'] = search_hash
                # Use job's own location if present, else default to search location
                job_data['location'] = job_data.get('location', location) 
            retrieved_jobs = cached_jobs_data[:num_jobs]
            return retrieved_jobs
            
        # If not in cache, scrape the site
        scraper_class = get_scraper(site) # Returns the specific scraper class
        if not scraper_class:
            print_warning(f"Unsupported job site: {site}")
            if progress_bar and hasattr(progress_bar, 'task_ids') and progress_bar.task_ids:
                progress_bar.update(progress_bar.task_ids[0], completed=1)
            return [] # Return empty list
            
        # Instantiate the specific scraper, passing the shared engine
        scraper_instance = scraper_class(output_dir=self.output_dir, engine=self.engine)
        try:
            if progress_bar and hasattr(progress_bar, 'task_ids') and progress_bar.task_ids:
                progress_bar.update(progress_bar.task_ids[0], description=f"[yellow]Scraping {site} for '{query}'")
            print_info(f"Starting to scrape {site} for query: '{query}', location: '{location}'")
            
            # Get jobs from the specific scraper
            scraped_job_list = scraper_instance.scrape_jobs(query, location, num_jobs)
            
            # Add search_hash and ensure location for each scraped job
            for job_data in scraped_job_list:
                job_data['search_hash_for_saving'] = search_hash
                # Use job's own location if present, else default to search location
                job_data['location'] = job_data.get('location', location) 
            
            # Cache the processed results (now including search_hash_for_saving and location)
            # Note: cache_jobs in JobCache expects List[Dict] where Dict is the job data.
            self.cache.cache_jobs(site, query, location, scraped_job_list)

            if progress_bar and hasattr(progress_bar, 'task_ids') and progress_bar.task_ids:
                progress_bar.update(progress_bar.task_ids[0], completed=1)
                progress_bar.update(progress_bar.task_ids[0], description=f"[green]Completed {site}")
            print_success(f"Completed scraping {len(scraped_job_list)} jobs from {site} for query: '{query}', loc: '{location}'")
            retrieved_jobs = scraped_job_list
            return retrieved_jobs
        except Exception as e:
            print_error(f"Error scraping {site} for query: '{query}', loc: '{location}': {str(e)}")
            if progress_bar and hasattr(progress_bar, 'task_ids') and progress_bar.task_ids:
                progress_bar.update(progress_bar.task_ids[0], completed=1)
                progress_bar.update(progress_bar.task_ids[0], description=f"[red]Failed {site}")
            return [] # Return empty list on error
        finally:
            scraper_instance.close() # Close WebDriver of the individual scraper
            
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