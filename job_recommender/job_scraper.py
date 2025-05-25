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
    ScraperTimeoutError,
    USER_AGENTS # Import USER_AGENTS
)
from .rich_utils import (
    create_progress_bar,
    print_success,
    print_warning,
    print_error,
    print_info
)
from tqdm import tqdm
import random # Moved import random to the top

logger = logging.getLogger(__name__)

class BaseJobScraper(ABC):
    def __init__(self, output_dir: str = "job_descriptions", selectors_path: str = "job_recommender/selectors.json"):
        self.output_dir = output_dir
        self.wait_time = 10 # Default wait time for WebDriverWait
        self.name = self.__class__.__name__.lower().replace("scraper", "")
        self.selectors = self._load_selectors(selectors_path)
        self.setup_driver()
        self.setup_logging()

    def _load_selectors(self, selectors_path: str) -> Dict:
        """Load selectors from the JSON file for the current scraper."""
        try:
            with open(selectors_path, 'r') as f:
                all_selectors = json.load(f)
            
            if self.name in all_selectors:
                return all_selectors[self.name]
            else:
                # Fallback to an empty dict if scraper name not in selectors_path
                # or if the specific scraper (e.g. ParallelJobScraper) does not have selectors
                logger.warning(f"Selectors for '{self.name}' not found in {selectors_path}. Using empty selectors.")
                return {}
        except FileNotFoundError:
            logger.error(f"Selectors file not found at {selectors_path}. Using empty selectors.")
            return {}
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from {selectors_path}. Using empty selectors.")
            return {}

    def _safe_get_text(self, selector_key: str, default: str = "Not specified") -> str:
        """Safely get text from an element by its selector key, with a default if not found."""
        selector = self.selectors.get(selector_key)
        if not selector:
            logger.debug(f"Selector key '{selector_key}' not found in self.selectors.")
            return default
        try:
            # Attempt to find a single element
            element = self.driver.find_element(By.CSS_SELECTOR, selector.split(',')[0].strip()) # Use first selector if multiple
            return element.text.strip() if element.text else default
        except NoSuchElementException:
            logger.debug(f"Element not found with primary selector for '{selector_key}': {selector.split(',')[0].strip()}")
            # Try alternative selectors if provided as a comma-separated list
            alternative_selectors = selector.split(',')[1:]
            for alt_selector in alternative_selectors:
                alt_selector = alt_selector.strip()
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, alt_selector)
                    return element.text.strip() if element.text else default
                except NoSuchElementException:
                    logger.debug(f"Element not found with alternative selector for '{selector_key}': {alt_selector}")
            return default
        except Exception as e:
            logger.warning(f"Error getting text for selector key '{selector_key}': {e}")
            return default

    def _safe_get_multiple_texts(self, selector_key: str, default: str = "Not specified") -> str:
        """Safely get texts from multiple elements (e.g., skills) and join them, with a default."""
        selector = self.selectors.get(selector_key)
        if not selector:
            logger.debug(f"Selector key '{selector_key}' not found in self.selectors.")
            return default
        
        all_texts = []
        # Iterate over each selector in the comma-separated list
        for s_option in selector.split(','):
            s_option = s_option.strip()
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, s_option)
                for element in elements:
                    if element.text.strip():
                        all_texts.append(element.text.strip())
                if all_texts: # If primary selector yields results, use them
                    return ", ".join(list(dict.fromkeys(all_texts))) # Remove duplicates, preserve order
            except NoSuchElementException: # Should not happen with find_elements
                logger.debug(f"No elements found with selector for '{selector_key}': {s_option}")
            except Exception as e:
                logger.warning(f"Error getting multiple texts for selector key '{selector_key}' with selector {s_option}: {e}")
        
        if all_texts:
            return ", ".join(list(dict.fromkeys(all_texts)))
        return default

    def _find_and_click_next_page(self, wait: WebDriverWait) -> bool:
        """
        Find and click the next page button using a list of potential selectors.
        Returns True if successfully clicked, False otherwise.
        """
        next_page_selectors = self.selectors.get('next_page_button', [])
        if isinstance(next_page_selectors, str): # Handle if it's a single string
            next_page_selectors = [next_page_selectors]

        for selector in next_page_selectors:
            try:
                # Scroll to the bottom to make sure the button is in view
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(random.uniform(0.5, 1.5)) # Brief pause for scroll

                # Add delay before clicking next page button
                time.sleep(random.uniform(1.0, 2.5))
                next_page_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                if next_page_button:
                    print_info(f"Found next page button with selector: {selector}")
                    self.driver.execute_script("arguments[0].click();", next_page_button)
                    print_success(f"Clicked next page button using selector: {selector}")
                    # Increased delay after clicking next page, simulating page load and reading time
                    time.sleep(random.uniform(2.5, 4.5)) 
                    return True
            except (TimeoutException, NoSuchElementException):
                logger.debug(f"Next page button not found or not clickable with selector: {selector}")
            except Exception as e:
                print_warning(f"Error clicking next page button with selector {selector}: {e}")
        
        print_warning("Could not find or click any next page button.")
        return False

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
            
            # Choose a random user agent
            chosen_user_agent = random.choice(USER_AGENTS)
            print_info(f"Using User-Agent: {chosen_user_agent}")
            chrome_options.add_argument(f"user-agent={chosen_user_agent}") # Standard way to set UA

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Fallback or additional measure for UA override if needed, though options usually suffice
            # self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            #     "userAgent": chosen_user_agent
            # })
            print_success("WebDriver setup completed successfully with rotated User-Agent")
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
                    f.write(f"Site: {job.get('site', 'N/A')}\n")
                    f.write(f"Title: {job.get('title', 'N/A')}\n")
                    f.write(f"Company: {job.get('company', 'N/A')}\n")
                    f.write(f"URL: {job.get('url', 'N/A')}\n")
                    f.write(f"Scraped Date: {job.get('scraped_date', 'N/A')}\n")
                    f.write(f"Date Posted: {job.get('date_posted', 'Not specified')}\n")
                    f.write(f"Salary Range: {job.get('salary_range', 'Not specified')}\n")
                    f.write(f"Job Type: {job.get('job_type', 'Not specified')}\n")
                    f.write(f"Location (Granular): {job.get('location_granular', 'Not specified')}\n")
                    f.write(f"Skills: {job.get('skills', 'Not specified')}\n")
                    f.write("\nDescription:\n")
                    f.write(job.get('description', 'N/A'))
                    
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
            wait = WebDriverWait(self.driver, self.wait_time)

            with create_progress_bar(f"Scraping {self.name.capitalize()} jobs", num_jobs, "job") as progress:
                task_id = progress.add_task(f"[{self.selectors.get('color', 'cyan')}]{self.name.capitalize()} Jobs", total=num_jobs, count=f"0/{num_jobs}")
                
                page_count = 1
                while len(jobs) < num_jobs:
                    print_info(f"Scraping page {page_count} for {self.name}...")
                    try:
                        # Wait for job cards to load on the current page
                        current_job_cards = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, self.selectors['job_card'])))
                        if not current_job_cards:
                            print_warning(f"No job cards found on page {page_count} for {self.name}.")
                            break 
                        print_info(f"Found {len(current_job_cards)} job cards on page {page_count}.")
                    except TimeoutException:
                        print_warning(f"Timeout waiting for job cards on page {page_count} for {self.name}.")
                        break # Stop if job cards don't load

                    for card_index, card in enumerate(current_job_cards):
                        if len(jobs) >= num_jobs:
                            break
                        
                        try:
                            # Scroll card into view
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", card)
                            time.sleep(random.uniform(0.5, 1.5)) # Delay after scroll

                            # Add delay before clicking job card
                            time.sleep(random.uniform(1.0, 2.5))
                            
                            if not safe_click(self.driver, card): 
                                print_warning(f"Failed to click job card {card_index + 1} on page {page_count}, skipping...")
                                continue
                            
                            # Add delay after clicking job card, before extracting details
                            time.sleep(random.uniform(1.5, 3.0))
                            
                            # Wait for job details to load
                            wait.until(EC.presence_of_element_located((By.CLASS_NAME, self.selectors['title'])))
                            
                            title = self.driver.find_element(By.CLASS_NAME, self.selectors['title']).text
                            company = self.driver.find_element(By.CLASS_NAME, self.selectors['company']).text
                            description = self.driver.find_element(By.ID, self.selectors['description']).text # Note: Indeed description selector is an ID
                            job_id = f"{self.name}_{title}_{company}_{datetime.now().timestamp()}".replace(" ", "_")

                            # Extract new fields
                            date_posted = self._safe_get_text('date_posted')
                            salary_range = self._safe_get_text('salary_range')
                            job_type = self._safe_get_text('job_type')
                            # For location_granular, prefer it over the general 'location' if available
                            location_granular = self._safe_get_text('location_granular', default=self._safe_get_text('location'))
                            skills = self._safe_get_multiple_texts('skills')
                            
                            jobs.append({
                                "site": self.name,
                                "id": job_id,
                                "title": title,
                                "company": company,
                                "description": description,
                                "url": self.driver.current_url,
                                "scraped_date": datetime.now().isoformat(),
                                "date_posted": date_posted,
                                "salary_range": salary_range,
                                "job_type": job_type,
                                "location_granular": location_granular,
                                "skills": skills
                            })
                            
                            print_success(f"Scraped: {title} at {company} ({len(jobs)}/{num_jobs})")
                            progress.update(task_id, advance=1, count=f"{len(jobs)}/{num_jobs}")
                            
                        except NoSuchElementException as e:
                            print_warning(f"Missing element for job card {card_index + 1} on page {page_count}: {e}. Skipping job.")
                        except TimeoutException:
                            print_warning(f"Timeout processing job card {card_index + 1} on page {page_count}. Skipping job.")
                        except Exception as e:
                            print_error(f"Error processing job card {card_index + 1} on page {page_count}: {e}. Skipping job.")
                            
                        if len(jobs) >= num_jobs:
                            break 
                    
                    if len(jobs) >= num_jobs:
                        print_info(f"Collected {num_jobs} jobs for {self.name}. Ending pagination.")
                        break

                    print_info("Attempting to go to the next page...")
                    if not self._find_and_click_next_page(wait):
                        print_info(f"No more pages found or failed to click next for {self.name}.")
                        break 
                    
                    page_count += 1
                    # Optional: Add a check to ensure new content has loaded
                    print_info(f"Successfully navigated to page {page_count} for {self.name}.")
                    # Delay after new page loads (already handled by _find_and_click_next_page's post-click delay)
                    # but can add a bit more if needed for content to fully render.
                    time.sleep(random.uniform(1.0, 2.0)) 

            return jobs[:num_jobs]

        except TimeoutException:
            print_error(f"Timeout during overall scraping process for {self.name}")
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
            wait = WebDriverWait(self.driver, self.wait_time)

            with create_progress_bar(f"Scraping {self.name.capitalize()} jobs", num_jobs, "job") as progress:
                task_id = progress.add_task(f"[{self.selectors.get('color', 'blue')}]{self.name.capitalize()} Jobs", total=num_jobs, count=f"0/{num_jobs}")

                page_count = 1
                last_job_count = 0 # For detecting if "See more jobs" loaded new content

                while len(jobs) < num_jobs:
                    print_info(f"Scraping page {page_count} for {self.name}...")
                    
                    # LinkedIn might load jobs dynamically on scroll or with a "See more jobs" button
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(random.uniform(1.5, 3.0)) # Increased delay for scroll to load jobs

                    try:
                        current_job_cards = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, self.selectors['job_card'])))
                        if not current_job_cards or len(current_job_cards) == last_job_count and page_count > 1:
                             # If no new cards after scroll/button click on subsequent pages, assume end of results
                            print_warning(f"No new job cards found on page {page_count} for {self.name} after scroll/click.")
                            break
                        print_info(f"Found {len(current_job_cards)} job cards on page {page_count}.")
                        last_job_count = len(current_job_cards) # Update for next iteration check
                    except TimeoutException:
                        print_warning(f"Timeout waiting for job cards on page {page_count} for {self.name}.")
                        break
                    
                    # Process only newly loaded cards if possible, this is tricky.
                    # For now, iterate through all visible cards, and skip if already processed (not implemented yet, relies on unique job_id)
                    # This simplified version re-iterates, but job list `jobs` prevents duplicates if IDs are same.
                    
                    # We need to process cards from where we left off, or handle already processed ones.
                    # A simpler approach for now: process all cards, and rely on job_id uniqueness.
                    # This might be inefficient if many cards are re-processed visually.
                    # A better way: keep track of processed card elements or their unique attributes.

                    start_index = 0 # This should ideally be where the last page left off
                                    # For simplicity, we are processing all current_job_cards and relying on `len(jobs)`
                                    # and unique job IDs to manage `num_jobs`.

                    for card_index, card in enumerate(current_job_cards[start_index:]): # card_index is relative to current_job_cards
                        if len(jobs) >= num_jobs:
                            break
                        
                        actual_card_index_for_logging = start_index + card_index + 1

                        try:
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", card)
                            time.sleep(random.uniform(0.5, 1.5)) # Delay after scroll

                            # Add delay before clicking job card
                            time.sleep(random.uniform(1.0, 2.5))
                            if not safe_click(self.driver, card):
                                print_warning(f"Failed to click job card {actual_card_index_for_logging} on page {page_count}, skipping...")
                                continue
                            
                            # Add delay after clicking job card, before extracting details
                            time.sleep(random.uniform(1.5, 3.0))
                            wait.until(EC.presence_of_element_located((By.CLASS_NAME, self.selectors['title'])))
                            
                            title = self.driver.find_element(By.CLASS_NAME, self.selectors['title']).text
                            company = self.driver.find_element(By.CLASS_NAME, self.selectors['company']).text
                            # Ensure description area is present before getting text
                            description_element = wait.until(EC.presence_of_element_located((By.CLASS_NAME, self.selectors['description'])))
                            description = description_element.text
                            job_id = f"{self.name}_{title}_{company}_{datetime.now().timestamp()}".replace(" ", "_")

                            # Extract new fields
                            date_posted = self._safe_get_text('date_posted')
                            salary_range = self._safe_get_text('salary_range')
                            job_type = self._safe_get_text('job_type')
                            location_granular = self._safe_get_text('location_granular', default=self._safe_get_text('location'))
                            skills = self._safe_get_multiple_texts('skills')
                            
                            jobs.append({
                                "site": self.name,
                                "id": job_id,
                                "title": title,
                                "company": company,
                                "description": description,
                                "url": self.driver.current_url,
                                "scraped_date": datetime.now().isoformat(),
                                "date_posted": date_posted,
                                "salary_range": salary_range,
                                "job_type": job_type,
                                "location_granular": location_granular,
                                "skills": skills
                            })
                            
                            print_success(f"Scraped: {title} at {company} ({len(jobs)}/{num_jobs})")
                            progress.update(task_id, advance=1, count=f"{len(jobs)}/{num_jobs}")
                            
                        except NoSuchElementException as e:
                            print_warning(f"Missing element for job card {actual_card_index_for_logging} on page {page_count}: {e}. Skipping job.")
                        except TimeoutException:
                            print_warning(f"Timeout processing job card {actual_card_index_for_logging} on page {page_count}. Skipping job.")
                        except Exception as e:
                            print_error(f"Error processing job card {actual_card_index_for_logging} on page {page_count}: {e}. Skipping job.")
                        
                        if len(jobs) >= num_jobs:
                            break
                    
                    if len(jobs) >= num_jobs:
                        print_info(f"Collected {num_jobs} jobs for {self.name}. Ending pagination.")
                        break

                    print_info(f"Attempting to find and click 'next' or 'see more jobs' for {self.name}...")
                    if not self._find_and_click_next_page(wait): # This handles "see more jobs" type buttons too
                        print_info(f"No 'next' or 'see more jobs' button found or clickable for {self.name}.")
                        # LinkedIn might not have a traditional next button if it's infinite scroll that eventually stops
                        # Or if the "see more jobs" button disappears
                        if len(current_job_cards) == last_job_count and page_count > 1 : # extra check
                             print_info(f"Job count ({len(current_job_cards)}) did not change after trying to load more. Assuming end of results for {self.name}.")
                             break
                    else:
                         print_info(f"Successfully clicked 'next' or 'see more jobs' for {self.name}.")
                         # Delay after clicking "see more" (already handled by _find_and_click_next_page)
                         # Can add more specific delay for LinkedIn if its loading behavior is distinct
                         time.sleep(random.uniform(1.0, 2.5)) 

                    page_count += 1
            
            return jobs[:num_jobs]

        except TimeoutException:
            print_error(f"Timeout during overall scraping process for {self.name}")
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
            search_url = f"{base_url}?sc.keyword={search_query.replace(' ', '%20')}&locT=C&locId=1146821&suggestCount=0&suggestChosen=false&clickSource=searchBtn&typedKeyword={search_query.replace(' ', '%20')}&sc.location={location.replace(' ', '%20')}" # Example, may need adjustment
            print_info(f"Accessing Glassdoor search URL: {search_url}")
            self.driver.get(search_url)
            wait = WebDriverWait(self.driver, self.wait_time)

            with create_progress_bar(f"Scraping {self.name.capitalize()} jobs", num_jobs, "job") as progress:
                task_id = progress.add_task(f"[{self.selectors.get('color', 'green')}]{self.name.capitalize()} Jobs", total=num_jobs, count=f"0/{num_jobs}")

                page_count = 1
                while len(jobs) < num_jobs:
                    print_info(f"Scraping page {page_count} for {self.name}...")
                    
                    # Handle potential pop-ups or overlays if Glassdoor is prone to them
                    # Example: self.handle_popup(wait) # You'd need to implement this

                    try:
                        current_job_cards = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, self.selectors['job_card'])))
                        if not current_job_cards:
                            print_warning(f"No job cards found on page {page_count} for {self.name}.")
                            break
                        print_info(f"Found {len(current_job_cards)} job cards on page {page_count}.")
                    except TimeoutException:
                        print_warning(f"Timeout waiting for job cards on page {page_count} for {self.name}.")
                        break
                    
                    # Glassdoor might have a specific way of loading job details, e.g., in an iframe or modal
                    # The current logic assumes clicking a card loads details in the main panel.

                    for card_index, card in enumerate(current_job_cards):
                        if len(jobs) >= num_jobs:
                            break
                        
                        try:
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", card)
                            time.sleep(random.uniform(0.5, 1.5)) # Delay after scroll

                            # Add delay before clicking job card
                            time.sleep(random.uniform(1.0, 2.5))
                            if not safe_click(self.driver, card):
                                print_warning(f"Failed to click job card {card_index + 1} on page {page_count}, skipping...")
                                continue
                            
                            # Add delay after clicking job card, before extracting details
                            # This replaces the previous time.sleep(random.uniform(1,2))
                            time.sleep(random.uniform(1.5, 3.0)) 
                            wait.until(EC.presence_of_element_located((By.CLASS_NAME, self.selectors['title']))) 
                            
                            title = self.driver.find_element(By.CLASS_NAME, self.selectors['title']).text
                            company_element = self.driver.find_element(By.CLASS_NAME, self.selectors['company'])
                            company = company_element.text.splitlines()[0] if company_element.text else "Unknown Company"
                            
                            description_element = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, self.selectors['description'])))
                            description = description_element.text
                            job_id = f"{self.name}_{title}_{company}_{datetime.now().timestamp()}".replace(" ", "_")

                            # Extract new fields
                            date_posted = self._safe_get_text('date_posted')
                            salary_range = self._safe_get_text('salary_range')
                            job_type = self._safe_get_text('job_type')
                            location_granular = self._safe_get_text('location_granular', default=self._safe_get_text('location'))
                            skills = self._safe_get_multiple_texts('skills')

                            jobs.append({
                                "site": self.name,
                                "id": job_id,
                                "title": title,
                                "company": company,
                                "description": description,
                                "url": self.driver.current_url, 
                                "scraped_date": datetime.now().isoformat(),
                                "date_posted": date_posted,
                                "salary_range": salary_range,
                                "job_type": job_type,
                                "location_granular": location_granular,
                                "skills": skills
                            })
                            
                            print_success(f"Scraped: {title} at {company} ({len(jobs)}/{num_jobs})")
                            progress.update(task_id, advance=1, count=f"{len(jobs)}/{num_jobs}")
                            
                        except NoSuchElementException as e:
                            print_warning(f"Missing element for job card {card_index + 1} on page {page_count}: {e}. Skipping job.")
                        except TimeoutException:
                            print_warning(f"Timeout processing job card {card_index + 1} on page {page_count}. Skipping job.")
                        except Exception as e:
                            print_error(f"Error processing job card {card_index + 1} on page {page_count}: {e}. Skipping job.")
                        
                        if len(jobs) >= num_jobs:
                            break
                    
                    if len(jobs) >= num_jobs:
                        print_info(f"Collected {num_jobs} jobs for {self.name}. Ending pagination.")
                        break

                    print_info(f"Attempting to go to the next page for {self.name}...")
                    if not self._find_and_click_next_page(wait):
                        print_info(f"No more pages found or failed to click next for {self.name}.")
                        break
                    
                    page_count += 1
                    print_info(f"Successfully navigated to page {page_count} for {self.name}.")
                    # Add a specific wait for new job cards to appear after pagination for Glassdoor
                    try:
                        wait.until(EC.staleness_of(current_job_cards[0])) # Wait for old cards to go stale
                        wait.until(EC.presence_of_element_located((By.CLASS_NAME, self.selectors['job_card']))) # Wait for new cards
                        print_info("New job cards detected on the next page.")
                    except TimeoutException:
                        print_warning(f"Timeout waiting for new job cards to load on page {page_count} for {self.name}. May be end of results.")
                        break
                    # Delay after new page loads (already handled by _find_and_click_next_page's post-click delay)
                    # Can add a bit more if needed for content to fully render.
                    time.sleep(random.uniform(1.0, 2.0))


            return jobs[:num_jobs]

        except TimeoutException:
            print_error(f"Timeout during overall scraping process for {self.name}")
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
    scraper_class = scrapers.get(site.lower())
    if scraper_class:
        return scraper_class() # Instantiated here
    return None

@click.command(context_settings=dict(
    default_map={
        'main': {
            'query': None,
            'location': None,
            'num_jobs': 10,
            'output_dir': 'job_descriptions',
            'sites': ['indeed'],
            'log_level': 'INFO',
            'cache_dir': '.cache',
            'cache_duration': 24,
            'max_workers': 3,
            'clear_cache': False,
            'clear_cache_site': None
        }
    }
))
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
def main(query: str, location: str, num_jobs: int, output_dir: str, sites: List[str], 
         log_level: str, cache_dir: str, cache_duration: int, max_workers: int, 
         clear_cache: bool, clear_cache_site: Optional[str]):
    """Scrape job descriptions from multiple job sites and save them to text files."""
    # Set up logging level
    logging.getLogger().setLevel(getattr(logging, log_level.upper()))
    
    # Initialize parallel scraper
    # Note: ParallelJobScraper itself does not use selectors directly from the file in its own methods,
    # but it instantiates other scrapers which do.
    parallel_scraper = ParallelJobScraper(
        output_dir=output_dir,
        cache_dir=cache_dir,
        cache_duration=cache_duration,
        max_workers=max_workers
    )
    
    try:
        # Clear cache if requested
        if clear_cache:
            parallel_scraper.clear_cache()
        elif clear_cache_site:
            parallel_scraper.clear_cache(clear_cache_site)
            
        # Scrape jobs in parallel
        print_info(f"Starting parallel scraping from {len(sites)} sites...")
        all_jobs = parallel_scraper.scrape_jobs(sites, query, location, num_jobs)
        
        if all_jobs:
            # Save all jobs using a base scraper instance for the save_jobs method
            # (save_jobs is generic and doesn't depend on specific site selectors)
            # Any scraper instance would do here, choosing IndeedScraper for consistency.
            # We need an instance to call save_jobs and then close its driver.
            # This part might need a rethink if save_jobs becomes part of ParallelJobScraper
            # or if we want to avoid instantiating a driver just for saving.
            # For now, keeping it simple.
            saver_scraper = IndeedScraper(output_dir=output_dir)
            try:
                saver_scraper.save_jobs(all_jobs)
                print_success(f"\nTotal jobs scraped: {len(all_jobs)}")
            except Exception as e:
                print_error(f"Failed to save jobs: {str(e)}")
            finally:
                saver_scraper.close() # Ensure driver for saving is closed
        else:
            print_warning("No jobs found matching the criteria.")
            
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        # Ensure the parallel_scraper's drivers are closed if an error occurs mid-process
        # The ParallelJobScraper should ideally handle this in its own error handling or a __del__ method
        if hasattr(parallel_scraper, 'close_all'):
             parallel_scraper.close_all()
        raise

if __name__ == "__main__":
    # Create a context for the Click command
    # This is a bit of a workaround to call the main function directly
    # while respecting Click's parameter handling.
    # For direct calls, you might not need this if you simplify main's signature
    # or call it with keyword arguments directly.
    main.main(standalone_mode=False)