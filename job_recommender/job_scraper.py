import os
import time
import json
import click
from datetime import datetime
from typing import List, Dict, Optional
from abc import ABC, abstractmethod
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
    def __init__(self, output_dir: str = "job_descriptions"):
        self.output_dir = output_dir
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
        """Save job descriptions to text files."""
        try:
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
                
            for job in jobs:
                filename = f"{job['site']}_{job['id']}_{datetime.now().strftime('%Y%m%d')}.txt"
                filepath = os.path.join(self.output_dir, filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"Site: {job['site']}\n")
                    f.write(f"Title: {job['title']}\n")
                    f.write(f"Company: {job['company']}\n")
                    f.write(f"URL: {job['url']}\n")
                    f.write(f"Scraped Date: {job['scraped_date']}\n")
                    f.write("\nDescription:\n")
                    f.write(job['description'])
                    
                print_success(f"Saved job description to {filename}")
        except Exception as e:
            print_error(f"Failed to save jobs: {str(e)}")
            raise ScraperError(f"Failed to save jobs: {str(e)}")
    
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
    cache_dir = ctx.params['cache_dir']
    cache_duration = ctx.params['cache_duration']
    max_workers = ctx.params['max_workers']
    clear_cache = ctx.params['clear_cache']
    clear_cache_site = ctx.params['clear_cache_site']
    
    # Initialize parallel scraper
    scraper = ParallelJobScraper(
        output_dir=output_dir,
        cache_dir=cache_dir,
        cache_duration=cache_duration,
        max_workers=max_workers
    )
    
    try:
        # Clear cache if requested
        if clear_cache:
            scraper.clear_cache()
        elif clear_cache_site:
            scraper.clear_cache(clear_cache_site)
            
        # Scrape jobs in parallel
        print_info(f"Starting parallel scraping from {len(sites)} sites...")
        all_jobs = scraper.scrape_jobs(sites, query, location, num_jobs)
        
        if all_jobs:
            # Save all jobs
            scraper = IndeedScraper(output_dir=output_dir)
            try:
                scraper.save_jobs(all_jobs)
                print_success(f"\nTotal jobs scraped: {len(all_jobs)}")
            except Exception as e:
                print_error(f"Failed to save jobs: {str(e)}")
            finally:
                scraper.close()
        else:
            print_warning("No jobs found matching the criteria.")
            
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        raise

if __name__ == "__main__":
    main() 