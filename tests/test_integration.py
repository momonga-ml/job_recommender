import os
import json
import pytest
from unittest.mock import patch, MagicMock

from job_recommender.job_scraper import IndeedScraper # Using IndeedScraper as an example
from job_recommender.cache import JobCache # Corrected import
from job_recommender.job_analyzer import JobAnalyzer, analyze_jobs_and_resume
from job_recommender.job_scraper import BaseJobScraper # For save_jobs

# Sample HTML content for a job page (can be loaded from a fixture file)
SAMPLE_INDEED_HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
    <title>Indeed Job Page</title>
</head>
<body>
    <div class="jobsearch-JobInfoHeader-title">Software Engineer Integration Test</div>
    <div class="jobsearch-CompanyInfoContainer">Integration Test Inc.</div>
    <div id="jobDescriptionText">
        <p>This is a job description for an Integration Test Software Engineer.</p>
        <p>Responsibilities: Python, API, Testing</p>
    </div>
</body>
</html>
"""

# Concrete class for BaseJobScraper to use its save_jobs method
class ConcreteTestScraper(BaseJobScraper):
    def scrape_jobs(self, search_query: str, location: str, num_jobs: int):
        pass # Not used in this integration test directly for scraping
    def parse_job_details_page(self, html_content: str):
        pass # Not used

@patch('job_recommender.job_scraper.ChromeDriverManager') # Mock CDM for scraper init
def test_scraper_cache_analyzer_flow(
    mock_cdm_scraper, # From @patch for IndeedScraper
    mock_openai_client, # From conftest.py
    temp_job_descriptions_conftest, # From conftest.py (acts as output_dir for save_jobs)
    temp_resume_file_conftest,      # From conftest.py
    temp_cache_dir_conftest,        # From conftest.py
    tmp_path # Pytest fixture for general temp paths if needed by analyzer directly
):
    """
    Integration test for the scraper -> cache -> analyzer flow.
    """
    mock_cdm_scraper.return_value.install.return_value = "dummy_driver_path"

    # 1. Simulated Scraping (using parse_job_details_page)
    # We need a BaseJobScraper instance to call setup_driver if parse_job_details_page relies on it (it doesn't directly, but __init__ does)
    # or if we want to use other methods like save_jobs.
    # For this test, we'll directly use parse_job_details_page and then manually save.
    
    # We need to mock selenium.webdriver.Chrome for scraper initialization
    with patch('selenium.webdriver.Chrome') as mock_chrome_webdriver:
        mock_chrome_webdriver.return_value = MagicMock() # Basic mock for driver instance
        scraper = IndeedScraper(output_dir=temp_job_descriptions_conftest)
    
    job_data = scraper.parse_job_details_page(SAMPLE_INDEED_HTML_CONTENT)
    assert job_data is not None
    assert job_data["title"] == "Software Engineer Integration Test"

    # Manually add other required fields that parse_job_details_page doesn't add, but save_jobs expects
    job_data["id"] = "integration_test_job_001"
    job_data["url"] = "http://example.com/integration_test_job_001"
    job_data["scraped_date"] = "2023-10-26T10:00:00"
    # Site is added by parse_job_details_page

    # Create a dedicated directory for the analyzer to read from for this specific test run
    analyzer_input_dir = tmp_path / "analyzer_job_files_integration"
    analyzer_input_dir.mkdir()

    with patch('selenium.webdriver.Chrome') as mock_chrome_for_save:
        mock_chrome_for_save.return_value = MagicMock()
        # Save the single "scraped" job to this dedicated directory
        saving_scraper = ConcreteTestScraper(output_dir=str(analyzer_input_dir))
    saving_scraper.save_jobs([job_data])
    
    # Verify file was created in the dedicated directory
    job_files = os.listdir(analyzer_input_dir)
    assert len(job_files) == 1, f"Expected 1 job file in analyzer_input_dir, found {len(job_files)}"
    
    # 2. Caching
    cache = JobCache(cache_dir=temp_cache_dir_conftest, cache_duration=1) # Corrected class name
    # Use a query and location that would uniquely identify this job if it were from a real search
    search_query = "software engineer integration test"
    location = "test city"
    site_name = job_data["site"] # Get site from job_data
    
    # Add to cache (normally a list of jobs from a search)
    cache.cache_jobs(site_name, search_query, location, [job_data]) # Use correct method name
    
    # Retrieve from cache
    cached_jobs = cache.get_cached_jobs(site_name, search_query, location) # Use correct method name
    assert cached_jobs is not None
    assert len(cached_jobs) == 1
    assert cached_jobs[0]["id"] == "integration_test_job_001"
    assert cached_jobs[0]["title"] == "Software Engineer Integration Test"

    # 3. Analysis (using the main analysis function for broader coverage)
    # The analyze_jobs_and_resume function internally creates JobAnalyzer,
    # reads descriptions, reads resume, and analyzes.
    # The mock_openai_client fixture will mock the OpenAI client used by JobAnalyzer.
    
    # We need to ensure that analyze_jobs_and_resume uses the mocked OpenAI client.
    # The mock_openai_client fixture patches 'job_recommender.job_analyzer.OpenAI'.
    
    # Use click.echo patching to capture output of analyze_jobs_and_resume
    with patch('click.echo') as mock_click_echo:
        analyze_jobs_and_resume(
            job_folder=str(analyzer_input_dir), # Use the dedicated directory
            resume_path=temp_resume_file_conftest,
            max_skills=3, # Test with a specific number of skills
            model_name="gpt-integration-test" # Model name used by JobAnalyzer
        )

    # Assertions for analysis
    mock_openai_client.chat.completions.create.assert_called_once()
    
    # Verify click.echo was called (meaning analysis produced output)
    assert mock_click_echo.call_count > 0
    
    # Check some expected output patterns (flexible check)
    output_text = ""
    for call_args in mock_click_echo.call_args_list:
        output_text += str(call_args[0][0]) + "\n"
        
    assert "Top 3 Required Skills:" in output_text # Check if max_skills was respected
    assert "Matching Skills:" in output_text
    assert "Areas for Growth:" in output_text
    assert "Recommendations:" in output_text

    # Clean up the dummy driver path if created by ChromeDriverManager mock
    if os.path.exists("dummy_driver_path"):
        os.remove("dummy_driver_path")
