import os
import time
# import json # No longer directly used for saving jobs
import click
from datetime import datetime, timezone # Added timezone
from typing import List, Dict, Optional
from abc import ABC, abstractmethod

from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from .db_schema import JobDetails
from .db_utils import create_db_engine

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import logging
from .utils import (
    retry_on_exception,
    handle_rate_limit,
    safe_click,
    ScraperError,
    RateLimitError,
    ScraperTimeoutError
)
from .parallel_scraper import ParallelJobScraper # Moved to top
from .rich_utils import (
    create_progress_bar,
    print_success,
    print_warning,
    print_error,
    print_info
)
from tqdm import tqdm

logger = logging.getLogger(__name__)

class BaseJobScraper(ABC):
    def __init__(self, output_dir: str = "job_descriptions", engine=None): # Added engine
        self.output_dir = output_dir # Kept for now, but not used by new save_jobs
        self.engine = engine or create_db_engine()
        self.Session = sessionmaker(bind=self.engine)
        self.setup_driver()
        self.setup_logging()

    def setup_logging(self):
        """Set up logging configuration."""
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
    def setup_driver(self):
        """Set up the Chrome WebDriver with appropriate options."""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            print_success("WebDriver setup completed successfully")
        except Exception as e:
            print_error(f"Failed to setup WebDriver: {str(e)}")
            raise ScraperError(f"WebDriver setup failed: {str(e)}")
    
    @abstractmethod
    @retry_on_exception(max_retries=3, delay=2.0)
    @handle_rate_limit
    def scrape_jobs(self, search_query: str, location: str, num_jobs: int) -> List[Dict]:
        """Scrape jobs from the specific job site."""
        pass
    
    def save_jobs(self, jobs: List[Dict]):
        """Save job details to the PostgreSQL database."""
        session = self.Session()
        saved_count = 0
        skipped_count = 0
        error_count = 0

        try:
            for job_dict in jobs:
                current_search_hash = job_dict.get('search_hash_for_saving')
                job_url = job_dict.get('url')

                if not job_url:
                    logger.warning(f"Job dictionary missing 'url'. Skipping: {job_dict.get('title', 'N/A')}")
                    error_count += 1
                    continue

                try:
                    existing_job = session.query(JobDetails).filter_by(url=job_url).first()
                    if existing_job:
                        logger.info(f"Job already exists in DB (URL: {job_url}). Skipping.")
                        skipped_count += 1
                        continue

                    # Parse and prepare scraped_date
                    scraped_date_str = job_dict['scraped_date']
                    dt = datetime.fromisoformat(scraped_date_str)
                    if dt.tzinfo: # Ensure naive UTC for database
                        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                    
                    job_to_save = JobDetails(
                        job_id=job_dict['id'], # This is the site-specific ID
                        site_name=job_dict['site'],
                        title=job_dict['title'],
                        company=job_dict.get('company'),
                        description=job_dict['description'],
                        url=job_url,
                        location=job_dict.get('location'), # Relies on scraper providing this
                        scraped_date=dt,
                        raw_search_hash=current_search_hash
                    )
                    session.add(job_to_save)
                    session.commit() # Commit per job
                    saved_count += 1
                    logger.info(f"Successfully saved job: {job_dict.get('title')} from {job_dict.get('site')}")

                except IntegrityError as e:
                    session.rollback()
                    # This might happen if URL is not strictly unique due to a race condition (unlikely with single saver)
                    # or if job_id (PK) is duplicated across different URLs (schema concern).
                    logger.error(f"IntegrityError saving job URL {job_url}: {e}. Job ID: {job_dict.get('id')}")
                    error_count += 1
                except Exception as e:
                    session.rollback()
                    logger.error(f"Error saving job URL {job_url}: {e}")
                    error_count += 1
            
            print_info(f"Job saving summary: {saved_count} saved, {skipped_count} skipped (already exist), {error_count} errors.")

        except Exception as e:
            # General error for the whole save_jobs operation
            logger.error(f"Critical error during save_jobs: {e}")
            session.rollback() # Rollback any pending changes not caught by inner try-except
            raise ScraperError(f"Failed to save jobs to database: {e}")
        finally:
            session.close()
            logger.info("Database session closed after saving jobs.")

    def close(self):
        """Close the WebDriver."""
        try:
            if hasattr(self, 'driver'):
                self.driver.quit()
                print_success("WebDriver closed successfully")
        except Exception as e:
            print_error(f"Error closing WebDriver: {str(e)}")

class IndeedScraper(BaseJobScraper):
    @retry_on_exception(max_retries=3, delay=2.0)
    @handle_rate_limit
    def scrape_jobs(self, search_query: str, location: str, num_jobs: int = 10) -> List[Dict]:
        """Scrape job listings from Indeed."""
        jobs = []
        base_url = "https://www.indeed.com"
        
        try:
            search_url = f"{base_url}/jobs?q={search_query.replace(' ', '+')}&l={location.replace(' ', '+')}"
            print_info(f"Accessing Indeed search URL: {search_url}")
            self.driver.get(search_url)
            
            # Wait for job cards to load
            wait = WebDriverWait(self.driver, 10)
            job_cards = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "job_seen_beacon")))
            
            if not job_cards:
                print_warning("No job cards found on Indeed search page")
                return jobs
            
            print_info(f"Found {len(job_cards)} job cards on Indeed")
            
            # Create progress bar for individual jobs
            with create_progress_bar("Scraping Indeed jobs", min(len(job_cards), num_jobs), "job") as progress:
                task_id = progress.add_task("[cyan]Indeed Jobs", total=min(len(job_cards), num_jobs), count="0/{}".format(min(len(job_cards), num_jobs)))
                
                for card in job_cards[:num_jobs]:
                    try:
                        # Scroll card into view and click
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", card)
                        time.sleep(1)  # Small delay to let the page settle
                        
                        if not safe_click(self.driver, card):
                            print_warning("Failed to click job card, skipping...")
                            progress.update(task_id, completed=1)
                            continue
                        
                        # Wait for job details to load
                        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "jobsearch-JobInfoHeader-title")))
                        
                        # Extract job details with error handling
                        try:
                            title = self.driver.find_element(By.CLASS_NAME, "jobsearch-JobInfoHeader-title").text
                        except NoSuchElementException:
                            print_warning("Could not find job title, skipping...")
                            progress.update(task_id, completed=1)
                            continue
                            
                        try:
                            company = self.driver.find_element(By.CLASS_NAME, "jobsearch-CompanyInfoContainer").text
                        except NoSuchElementException:
                            company = "Unknown Company"
                            print_warning("Could not find company name, using placeholder")
                            
                        try:
                            description = self.driver.find_element(By.ID, "jobDescriptionText").text
                        except NoSuchElementException:
                            print_warning("Could not find job description, skipping...")
                            progress.update(task_id, completed=1)
                            continue
                            
                        job_id = self.driver.current_url.split("?")[0].split("/")[-1]
                        
                        jobs.append({
                            "site": "indeed",
                            "id": job_id,
                            "title": title,
                            "company": company,
                            "description": description,
                            "url": self.driver.current_url,
                            "scraped_date": datetime.now().isoformat()
                        })
                        
                        print_success(f"Successfully scraped job: {title} at {company}")
                        progress.update(task_id, completed=1, count=f"{len(jobs)}/{min(len(job_cards), num_jobs)}")
                        
                    except Exception as e:
                        print_error(f"Error processing job card: {str(e)}")
                        progress.update(task_id, completed=1)
                        continue
                        
            return jobs
            
        except TimeoutException:
            print_error("Timeout while scraping Indeed jobs")
            raise ScraperTimeoutError("Indeed page load timeout")
        except Exception as e:
            print_error(f"Unexpected error while scraping Indeed: {str(e)}")
            raise ScraperError(f"Indeed scraping failed: {str(e)}")

class LinkedInScraper(BaseJobScraper):
    @retry_on_exception(max_retries=3, delay=2.0)
    @handle_rate_limit
    def scrape_jobs(self, search_query: str, location: str, num_jobs: int = 10) -> List[Dict]:
        """Scrape job listings from LinkedIn."""
        jobs = []
        base_url = "https://www.linkedin.com/jobs/search"
        
        try:
            search_url = f"{base_url}/?keywords={search_query.replace(' ', '%20')}&location={location.replace(' ', '%20')}"
            print_info(f"Accessing LinkedIn search URL: {search_url}")
            self.driver.get(search_url)
            
            # Wait for job cards to load
            wait = WebDriverWait(self.driver, 10)
            job_cards = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "job-card-container")))
            
            if not job_cards:
                print_warning("No job cards found on LinkedIn search page")
                return jobs
            
            print_info(f"Found {len(job_cards)} job cards on LinkedIn")
            
            # Create progress bar for individual jobs
            with create_progress_bar("Scraping LinkedIn jobs", min(len(job_cards), num_jobs), "job") as progress:
                task_id = progress.add_task("[cyan]LinkedIn Jobs", total=min(len(job_cards), num_jobs), count="0/{}".format(min(len(job_cards), num_jobs)))
                
                for card in job_cards[:num_jobs]:
                    try:
                        # Scroll card into view and click
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", card)
                        time.sleep(1)  # Small delay to let the page settle
                        
                        if not safe_click(self.driver, card):
                            print_warning("Failed to click job card, skipping...")
                            progress.update(task_id, completed=1)
                            continue
                        
                        # Wait for job details to load
                        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "jobs-unified-top-card__job-title")))
                        
                        # Extract job details with error handling
                        try:
                            title = self.driver.find_element(By.CLASS_NAME, "jobs-unified-top-card__job-title").text
                        except NoSuchElementException:
                            print_warning("Could not find job title, skipping...")
                            progress.update(task_id, completed=1)
                            continue
                            
                        try:
                            company = self.driver.find_element(By.CLASS_NAME, "jobs-unified-top-card__company-name").text
                        except NoSuchElementException:
                            company = "Unknown Company"
                            print_warning("Could not find company name, using placeholder")
                            
                        try:
                            description = self.driver.find_element(By.CLASS_NAME, "jobs-description__content").text
                        except NoSuchElementException:
                            print_warning("Could not find job description, skipping...")
                            progress.update(task_id, completed=1)
                            continue
                            
                        job_id = self.driver.current_url.split("?")[0].split("/")[-1]
                        
                        jobs.append({
                            "site": "linkedin",
                            "id": job_id,
                            "title": title,
                            "company": company,
                            "description": description,
                            "url": self.driver.current_url,
                            "scraped_date": datetime.now().isoformat()
                        })
                        
                        print_success(f"Successfully scraped job: {title} at {company}")
                        progress.update(task_id, completed=1, count=f"{len(jobs)}/{min(len(job_cards), num_jobs)}")
                        
                    except Exception as e:
                        print_error(f"Error processing job card: {str(e)}")
                        progress.update(task_id, completed=1)
                        continue
                        
            return jobs
            
        except TimeoutException:
            print_error("Timeout while scraping LinkedIn jobs")
            raise ScraperTimeoutError("LinkedIn page load timeout")
        except Exception as e:
            print_error(f"Unexpected error while scraping LinkedIn: {str(e)}")
            raise ScraperError(f"LinkedIn scraping failed: {str(e)}")

class GlassdoorScraper(BaseJobScraper):
    @retry_on_exception(max_retries=3, delay=2.0)
    @handle_rate_limit
    def scrape_jobs(self, search_query: str, location: str, num_jobs: int = 10) -> List[Dict]:
        """Scrape job listings from Glassdoor."""
        jobs = []
        base_url = "https://www.glassdoor.com/Job/jobs.htm"
        
        try:
            search_url = f"{base_url}?sc.keyword={search_query.replace(' ', '%20')}&locT=C&locId=1146821&suggestCount=0&suggestChosen=false&clickSource=searchBtn&typedKeyword={search_query.replace(' ', '%20')}&sc.location={location.replace(' ', '%20')}"
            print_info(f"Accessing Glassdoor search URL: {search_url}")
            self.driver.get(search_url)
            
            # Wait for job cards to load
            wait = WebDriverWait(self.driver, 10)
            job_cards = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "jobCard")))
            
            if not job_cards:
                print_warning("No job cards found on Glassdoor search page")
                return jobs
            
            print_info(f"Found {len(job_cards)} job cards on Glassdoor")
            
            # Create progress bar for individual jobs
            with create_progress_bar("Scraping Glassdoor jobs", min(len(job_cards), num_jobs), "job") as progress:
                task_id = progress.add_task("[cyan]Glassdoor Jobs", total=min(len(job_cards), num_jobs), count="0/{}".format(min(len(job_cards), num_jobs)))
                
                for card in job_cards[:num_jobs]:
                    try:
                        # Scroll card into view and click
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", card)
                        time.sleep(1)  # Small delay to let the page settle
                        
                        if not safe_click(self.driver, card):
                            print_warning("Failed to click job card, skipping...")
                            progress.update(task_id, completed=1)
                            continue
                        
                        # Wait for job details to load
                        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "job-title")))
                        
                        # Extract job details with error handling
                        try:
                            title = self.driver.find_element(By.CLASS_NAME, "job-title").text
                        except NoSuchElementException:
                            print_warning("Could not find job title, skipping...")
                            progress.update(task_id, completed=1)
                            continue
                            
                        try:
                            company = self.driver.find_element(By.CLASS_NAME, "employer-name").text
                        except NoSuchElementException:
                            company = "Unknown Company"
                            print_warning("Could not find company name, using placeholder")
                            
                        try:
                            description = self.driver.find_element(By.CLASS_NAME, "jobDescriptionContent").text
                        except NoSuchElementException:
                            print_warning("Could not find job description, skipping...")
                            progress.update(task_id, completed=1)
                            continue
                            
                        job_id = self.driver.current_url.split("?")[0].split("/")[-1]
                        
                        jobs.append({
                            "site": "glassdoor",
                            "id": job_id,
                            "title": title,
                            "company": company,
                            "description": description,
                            "url": self.driver.current_url,
                            "scraped_date": datetime.now().isoformat()
                        })
                        
                        print_success(f"Successfully scraped job: {title} at {company}")
                        progress.update(task_id, completed=1, count=f"{len(jobs)}/{min(len(job_cards), num_jobs)}")
                        
                    except Exception as e:
                        print_error(f"Error processing job card: {str(e)}")
                        progress.update(task_id, completed=1)
                        continue
                        
            return jobs
            
        except TimeoutException:
            print_error("Timeout while scraping Glassdoor jobs")
            raise ScraperTimeoutError("Glassdoor page load timeout")
        except Exception as e:
            print_error(f"Unexpected error while scraping Glassdoor: {str(e)}")
            raise ScraperError(f"Glassdoor scraping failed: {str(e)}")

def get_scraper(site: str) -> Optional[BaseJobScraper]:
    """Factory function to get the appropriate scraper based on the site."""
    scrapers = {
        "indeed": IndeedScraper,
        "linkedin": LinkedInScraper,
        "glassdoor": GlassdoorScraper
    }
    return scrapers.get(site.lower())

@click.command()
@click.option('--query', required=True, help='Job search query')
@click.option('--location', required=True, help='Location for job search')
@click.option('--num-jobs', default=10, help='Number of jobs to scrape')
@click.option('--output-dir', default='job_descriptions', help='Directory to save job descriptions')
@click.option('--sites', multiple=True, default=['indeed'], help='Job sites to scrape (indeed, linkedin, glassdoor)')
@click.option('--log-level', default='INFO', help='Logging level (DEBUG, INFO, WARNING, ERROR)')
@click.option('--cache-dir', default='.cache', help='Directory for cache files')
@click.option('--cache-duration', default=24, help='How long to keep cache entries in hours')
@click.option('--max-workers', default=3, help='Maximum number of parallel scraping workers')
@click.option('--clear-cache', is_flag=True, help='Clear the cache before scraping')
@click.option('--clear-cache-site', help='Clear cache for a specific site')
def main(ctx):
    """Scrape job descriptions from multiple job sites and save them to text files."""
    # Set up logging level
    logging.getLogger().setLevel(getattr(logging, ctx.params['log_level'].upper()))
    
    # Get parameters from context
    query = ctx.params['query']
    location = ctx.params['location']
    num_jobs = ctx.params['num_jobs']
    output_dir = ctx.params['output_dir']
    sites = ctx.params['sites']
    # cache_dir = ctx.params['cache_dir'] # No longer directly needed by ParallelJobScraper init for DB cache
    cache_duration = ctx.params['cache_duration']
    max_workers = ctx.params['max_workers']
    clear_cache_flag = ctx.params['clear_cache'] # Renamed to avoid conflict
    clear_cache_site_name = ctx.params['clear_cache_site'] # Renamed for clarity
    
    # Initialize parallel scraper
    # Note: ParallelJobScraper will now use JobCache which uses DB.
    # JobCache's __init__ might need adjustment if it still expects cache_dir for other reasons,
    # but for DB-based caching, it's not essential.
    parallel_scraper = ParallelJobScraper(
        # output_dir=output_dir, # Not used by ParallelJobScraper directly for saving
        cache_duration=cache_duration, # Pass to JobCache via ParallelJobScraper
        max_workers=max_workers
        # engine can be implicitly created by JobCache within ParallelJobScraper
    )
    
    db_engine = parallel_scraper.engine # Get engine from ParallelJobScraper (assuming it's exposed)

    try:
        # Clear cache if requested (JobCache.clear_cache uses the DB)
        if clear_cache_flag:
            parallel_scraper.clear_cache() # Assumes ParallelJobScraper exposes this from its JobCache
        elif clear_cache_site_name:
            parallel_scraper.clear_cache(clear_cache_site_name)
            
        # Scrape jobs in parallel
        print_info(f"Starting parallel scraping from {len(sites)} sites...")
        # scrape_jobs in ParallelJobScraper should now ensure 'search_hash_for_saving' is in job dicts
        all_jobs = parallel_scraper.scrape_jobs(sites, query, location, num_jobs)
        
        if all_jobs:
            # Save all jobs to DB
            # Pass the engine obtained from parallel_scraper to the saving_scraper instance
            # output_dir is still passed but won't be used by the new save_jobs
            saving_scraper = IndeedScraper(output_dir=output_dir, engine=db_engine) 
            try:
                print_info(f"Attempting to save {len(all_jobs)} jobs to the database...")
                saving_scraper.save_jobs(all_jobs) # This now saves to DB
                # Success/error messages are now handled within save_jobs
            except Exception as e:
                # This will catch errors from save_jobs if they are re-raised (like ScraperError)
                print_error(f"Failed to save jobs to database: {str(e)}")
            finally:
                saving_scraper.close() # Closes WebDriver for the saving_scraper instance
        else:
            print_warning("No jobs found matching the criteria.")
            
    except Exception as e:
        print_error(f"Unexpected error in main: {str(e)}")
        # Consider if parallel_scraper's WebDriver needs closing if an error occurs before saving_scraper is used
        # For now, assume WebDriver cleanup is handled by individual scraper instances or context managers if used
        raise

if __name__ == "__main__":
    # from .parallel_scraper import ParallelJobScraper # Already moved to top
    main()