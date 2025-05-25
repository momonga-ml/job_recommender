import pytest
from unittest.mock import patch, MagicMock

from job_recommender.rich_utils import (
    create_progress_bar,
    print_success,
    print_warning,
    print_error,
    print_info,
    print_job_summary,
    print_job_details,
    print_scraping_start,
    print_scraping_complete
)
from rich.progress import Progress
from rich.panel import Panel
from rich.table import Table
from rich.text import Text # Import Text for isinstance check if needed

@patch('rich.progress.Progress')
def test_create_progress_bar(MockProgressClass):
    """Test that create_progress_bar returns a Progress instance."""
    # create_progress_bar instantiates Progress and returns that instance.
    # When Progress is patched, calling Progress() returns MockProgressClass.return_value.
    progress_bar_instance_mock = MockProgressClass.return_value
    
    progress_bar = create_progress_bar("Testing", 100, "tests")
    assert progress_bar is progress_bar_instance_mock # Check it's the instance returned by the mock class

@patch('job_recommender.rich_utils.console.print')
def test_print_success(mock_rprint):
    """Test print_success calls console.print with correct formatting."""
    print_success("Operation successful.")
    mock_rprint.assert_called_once_with("[green]✓[/green] Operation successful.")

@patch('job_recommender.rich_utils.console.print')
def test_print_warning(mock_rprint):
    """Test print_warning calls console.print with correct formatting."""
    print_warning("This is a warning.")
    mock_rprint.assert_called_once_with("[yellow]⚠[/yellow] This is a warning.")

@patch('job_recommender.rich_utils.console.print')
def test_print_error(mock_rprint):
    """Test print_error calls console.print with correct formatting."""
    print_error("An error occurred.")
    mock_rprint.assert_called_once_with("[red]✗[/red] An error occurred.")

@patch('job_recommender.rich_utils.console.print')
def test_print_info(mock_rprint):
    """Test print_info calls console.print with correct formatting."""
    print_info("Some information.")
    mock_rprint.assert_called_once_with("[blue]ℹ[/blue] Some information.")

@patch('job_recommender.rich_utils.console.print')
def test_print_job_summary(mock_rprint):
    """Test print_job_summary creates and prints a Table."""
    jobs = [
        {"site": "indeed", "title": "Job1", "company": "CompA", "url": "url1", "scraped_date": "date1", "description": "desc1"},
        {"site": "linkedin", "title": "Job2", "company": "CompB", "url": "url2", "scraped_date": "date2", "description": "desc2"},
        {"site": "indeed", "title": "Job3", "company": "CompC", "url": "url3", "scraped_date": "date3", "description": "desc3"},
    ]
    print_job_summary(jobs)
    args, _ = mock_rprint.call_args
    assert isinstance(args[0], Table)
    table_arg = args[0]
    assert table_arg.title == "Job Scraping Summary"
    assert len(table_arg.rows) == 2 
    assert table_arg.columns[0].header == "Site"
    assert table_arg.columns[1].header == "Jobs Scraped"

@patch('job_recommender.rich_utils.console.print')
def test_print_job_details(mock_rprint):
    """Test print_job_details creates and prints a Panel."""
    job = {"title": "Test Job", "company": "Test Co", "site": "tests", "url": "http://test.com", "scraped_date": "today", "description": "A long description."}
    print_job_details(job)
    args, _ = mock_rprint.call_args
    assert isinstance(args[0], Panel)
    panel_arg = args[0]
    # panel_arg.title is a Text object. Convert to plain string for simple check.
    assert "Test Job at Test Co" in panel_arg.title.plain
    
    content_str = str(panel_arg.renderable) # renderable is the string passed to Panel
    assert "[bold blue]Site:[/bold blue] tests" in content_str
    assert "[bold blue]URL:[/bold blue] http://test.com" in content_str
    assert "A long description..." in content_str


@patch('job_recommender.rich_utils.console.print')
def test_print_scraping_start(mock_rprint):
    """Test print_scraping_start creates and prints a Panel."""
    print_scraping_start(["indeed", "linkedin"], "Python Developer", "New York")
    args, _ = mock_rprint.call_args
    assert isinstance(args[0], Panel)
    panel_arg = args[0]
    panel_content_str = str(panel_arg.renderable) # renderable is the string passed to Panel
    assert "[bold cyan]Starting Job Scraping[/bold cyan]" in panel_content_str
    assert "[bold green]Query:[/bold green] Python Developer" in panel_content_str
    assert "[bold green]Location:[/bold green] New York" in panel_content_str
    assert "[bold green]Sites:[/bold green] indeed, linkedin" in panel_content_str

@patch('job_recommender.rich_utils.console.print')
def test_print_scraping_complete(mock_rprint):
    """Test print_scraping_complete creates and prints a Panel."""
    print_scraping_complete(15, 123.45)
    args, _ = mock_rprint.call_args
    assert isinstance(args[0], Panel)
    panel_arg = args[0]
    panel_content_str = str(panel_arg.renderable) # renderable is the string passed to Panel
    assert "[bold green]Scraping Complete![/bold green]" in panel_content_str
    assert "[bold blue]Total Jobs:[/bold blue] 15" in panel_content_str
    assert "[bold blue]Duration:[/bold blue] 123.5 seconds" in panel_content_str
