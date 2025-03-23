import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from click.testing import CliRunner
from job_recommender.job_scraper import (
    BaseJobScraper,
    IndeedScraper,
    LinkedInScraper,
    GlassdoorScraper,
    get_scraper,
    main
)
from typing import List, Dict

# Sample job data for testing
SAMPLE_JOB_DATA = {
    "site": "test_site",
    "id": "test_id",
    "title": "Test Job Title",
    "company": "Test Company",
    "description": "Test job description",
    "url": "https://test.com/job/test_id",
    "scraped_date": datetime.now().isoformat()
}

@pytest.fixture
def mock_driver():
    """Create a mock Selenium WebDriver."""
    with patch('selenium.webdriver.Chrome') as mock_chrome:
        driver = MagicMock()
        mock_chrome.return_value = driver
        yield driver

@pytest.fixture
def mock_webdriver_wait():
    """Mock WebDriverWait for testing."""
    with patch('selenium.webdriver.support.ui.WebDriverWait') as mock_wait:
        wait = MagicMock()
        mock_wait.return_value = wait
        yield wait

@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary directory for test output."""
    output_dir = tmp_path / "test_job_descriptions"
    output_dir.mkdir()
    return str(output_dir)

class TestBaseJobScraper:
    class ConcreteJobScraper(BaseJobScraper):
        def scrape_jobs(self, search_query: str, location: str, num_jobs: int) -> List[Dict]:
            return [SAMPLE_JOB_DATA]

    def test_init(self, mock_driver, temp_output_dir):
        """Test BaseJobScraper initialization."""
        scraper = self.ConcreteJobScraper(output_dir=temp_output_dir)
        assert scraper.output_dir == temp_output_dir
        assert scraper.driver is not None

    def test_save_jobs(self, mock_driver, temp_output_dir):
        """Test saving jobs to files."""
        scraper = self.ConcreteJobScraper(output_dir=temp_output_dir)
        jobs = [SAMPLE_JOB_DATA]
        
        scraper.save_jobs(jobs)
        
        # Check if file was created
        files = os.listdir(temp_output_dir)
        assert len(files) == 1
        
        # Check file contents
        with open(os.path.join(temp_output_dir, files[0]), 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Test Job Title" in content
            assert "Test Company" in content
            assert "Test job description" in content

    def test_close(self, mock_driver):
        """Test closing the WebDriver."""
        scraper = self.ConcreteJobScraper()
        scraper.close()
        mock_driver.quit.assert_called_once()

class TestIndeedScraper:
    def test_scrape_jobs_success(self, mock_driver, mock_webdriver_wait, temp_output_dir):
        """Test successful job scraping from Indeed."""
        # Setup mock elements
        mock_card = MagicMock()
        mock_title = MagicMock()
        mock_company = MagicMock()
        mock_description = MagicMock()
        
        mock_title.text = "Software Engineer"
        mock_company.text = "Test Company"
        mock_description.text = "Test job description"
        
        # Setup find_element calls with correct class names
        mock_driver.find_element.side_effect = [
            mock_title,  # jobsearch-JobInfoHeader-title
            mock_company,  # jobsearch-CompanyInfoContainer
            mock_description  # jobDescriptionText
        ]
        mock_driver.current_url = "https://indeed.com/viewjob?jk=test123"
        
        # Setup WebDriverWait mock
        mock_webdriver_wait.until.return_value = [mock_card]
        
        # Mock the click method
        mock_card.click = MagicMock()
        
        # Mock the get method
        mock_driver.get = MagicMock()
        
        # Mock the find_element method with correct class names
        mock_driver.find_element.side_effect = [
            mock_title,  # jobsearch-JobInfoHeader-title
            mock_company,  # jobsearch-CompanyInfoContainer
            mock_description  # jobDescriptionText
        ]
        
        # Mock the find_element_by_class_name method
        mock_driver.find_element_by_class_name = MagicMock(side_effect=[
            mock_title,  # jobsearch-JobInfoHeader-title
            mock_company,  # jobsearch-CompanyInfoContainer
            mock_description  # jobDescriptionText
        ])
        
        scraper = IndeedScraper(output_dir=temp_output_dir)
        jobs = scraper.scrape_jobs("software engineer", "New York", 1)
        
        assert len(jobs) == 1
        assert jobs[0]["site"] == "indeed"
        assert jobs[0]["title"] == "Software Engineer"
        assert jobs[0]["company"] == "Test Company"
        assert jobs[0]["description"] == "Test job description"
        assert "test123" in jobs[0]["id"]

    def test_scrape_jobs_timeout(self, mock_driver, mock_webdriver_wait):
        """Test handling of timeout during job scraping."""
        mock_webdriver_wait.until.side_effect = TimeoutException()
        
        scraper = IndeedScraper()
        jobs = scraper.scrape_jobs("software engineer", "New York", 1)
        
        assert len(jobs) == 0

class TestLinkedInScraper:
    def test_scrape_jobs_success(self, mock_driver, mock_webdriver_wait, temp_output_dir):
        """Test successful job scraping from LinkedIn."""
        # Setup mock elements
        mock_card = MagicMock()
        mock_title = MagicMock()
        mock_company = MagicMock()
        mock_description = MagicMock()
        
        mock_title.text = "Senior Developer"
        mock_company.text = "Tech Corp"
        mock_description.text = "Test job description"
        
        # Setup find_element calls with correct class names
        mock_driver.find_element.side_effect = [
            mock_title,  # jobs-unified-top-card__job-title
            mock_company,  # jobs-unified-top-card__company-name
            mock_description  # jobs-description__content
        ]
        mock_driver.current_url = "https://linkedin.com/jobs/view/123456"
        
        # Setup WebDriverWait mock
        mock_webdriver_wait.until.return_value = [mock_card]
        
        # Mock the click method
        mock_card.click = MagicMock()
        
        # Mock the get method
        mock_driver.get = MagicMock()
        
        # Mock the find_element_by_class_name method
        mock_driver.find_element_by_class_name = MagicMock(side_effect=[
            mock_title,  # jobs-unified-top-card__job-title
            mock_company,  # jobs-unified-top-card__company-name
            mock_description  # jobs-description__content
        ])
        
        scraper = LinkedInScraper(output_dir=temp_output_dir)
        jobs = scraper.scrape_jobs("senior developer", "San Francisco", 1)
        
        assert len(jobs) == 1
        assert jobs[0]["site"] == "linkedin"
        assert jobs[0]["title"] == "Senior Developer"
        assert jobs[0]["company"] == "Tech Corp"
        assert jobs[0]["description"] == "Test job description"
        assert "123456" in jobs[0]["id"]

class TestGlassdoorScraper:
    def test_scrape_jobs_success(self, mock_driver, mock_webdriver_wait, temp_output_dir):
        """Test successful job scraping from Glassdoor."""
        # Setup mock elements
        mock_card = MagicMock()
        mock_title = MagicMock()
        mock_company = MagicMock()
        mock_description = MagicMock()
        
        mock_title.text = "Product Manager"
        mock_company.text = "Startup Inc"
        mock_description.text = "Test job description"
        
        # Setup find_element calls with correct class names
        mock_driver.find_element.side_effect = [
            mock_title,  # job-title
            mock_company,  # employer-name
            mock_description  # jobDescriptionContent
        ]
        mock_driver.current_url = "https://glassdoor.com/job-listing/product-manager-startup-inc-JV_123456"
        
        # Setup WebDriverWait mock
        mock_webdriver_wait.until.return_value = [mock_card]
        
        # Mock the click method
        mock_card.click = MagicMock()
        
        # Mock the get method
        mock_driver.get = MagicMock()
        
        # Mock the find_element_by_class_name method
        mock_driver.find_element_by_class_name = MagicMock(side_effect=[
            mock_title,  # job-title
            mock_company,  # employer-name
            mock_description  # jobDescriptionContent
        ])
        
        scraper = GlassdoorScraper(output_dir=temp_output_dir)
        jobs = scraper.scrape_jobs("product manager", "Boston", 1)
        
        assert len(jobs) == 1
        assert jobs[0]["site"] == "glassdoor"
        assert jobs[0]["title"] == "Product Manager"
        assert jobs[0]["company"] == "Startup Inc"
        assert jobs[0]["description"] == "Test job description"
        assert "JV_123456" in jobs[0]["id"]

def test_get_scraper():
    """Test the scraper factory function."""
    # Test supported sites
    assert get_scraper("indeed") == IndeedScraper
    assert get_scraper("linkedin") == LinkedInScraper
    assert get_scraper("glassdoor") == GlassdoorScraper
    
    # Test unsupported site
    assert get_scraper("unsupported") is None
    
    # Test case insensitivity
    assert get_scraper("INDEED") == IndeedScraper

@pytest.mark.integration
def test_full_scraping_process(temp_output_dir):
    """Integration test for the full scraping process."""
    with patch('job_recommender.job_scraper.IndeedScraper') as mock_indeed_scraper, \
         patch('job_recommender.job_scraper.LinkedInScraper') as mock_linkedin_scraper, \
         patch('click.echo') as mock_echo:
        
        # Setup mock scrapers
        mock_indeed_scraper.return_value.scrape_jobs.return_value = [SAMPLE_JOB_DATA]
        mock_linkedin_scraper.return_value.scrape_jobs.return_value = [SAMPLE_JOB_DATA]
        
        # Create a Click test runner
        runner = CliRunner()
        
        # Run the command with test arguments
        result = runner.invoke(main, [
            '--query', 'software engineer',
            '--location', 'New York',
            '--num-jobs', '1',
            '--output-dir', temp_output_dir,
            '--sites', 'indeed', 'linkedin'
        ])
        
        # Check if command executed successfully
        assert result.exit_code == 0
        
        # Check if files were created
        files = os.listdir(temp_output_dir)
        assert len(files) == 2
        
        # Verify file contents
        for file in files:
            with open(os.path.join(temp_output_dir, file), 'r', encoding='utf-8') as f:
                content = f.read()
                assert "Test Job Title" in content
                assert "Test Company" in content
                assert "Test job description" in content 