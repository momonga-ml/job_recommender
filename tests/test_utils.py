import pytest
import time
from unittest.mock import MagicMock, call, patch
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
    ElementClickInterceptedException
)

from job_recommender.utils import (
    ScraperError,
    RateLimitError,
    ScraperTimeoutError,
    retry_on_exception,
    handle_rate_limit,
    safe_click,
    logger as utils_logger # Import the logger used in utils.py
)

# Test Custom Exceptions
def test_custom_exceptions():
    """Test that custom exceptions can be raised."""
    with pytest.raises(ScraperError):
        raise ScraperError("Test scraper error")
    with pytest.raises(RateLimitError):
        raise RateLimitError("Test rate limit error")
    with pytest.raises(ScraperTimeoutError):
        raise ScraperTimeoutError("Test timeout error")

# Tests for retry_on_exception decorator
@patch('time.sleep', return_value=None) # Mock time.sleep to speed up tests
def test_retry_on_exception_success_first_try(mock_sleep):
    """Test that the function is called once if no exception occurs."""
    mock_func = MagicMock(return_value="success")
    
    @retry_on_exception(max_retries=3, delay=0.1)
    def decorated_func():
        return mock_func()
        
    result = decorated_func()
    assert result == "success"
    mock_func.assert_called_once()
    mock_sleep.assert_not_called()

@patch('time.sleep', return_value=None)
@patch.object(utils_logger, 'warning') # Patch the logger used in the decorator
def test_retry_on_exception_retries_and_succeeds(mock_logger_warning, mock_sleep):
    """Test that the function retries on specified exceptions and then succeeds."""
    mock_func = MagicMock()
    mock_func.side_effect = [TimeoutException("Fail1"), TimeoutException("Fail2"), "success"]
    
    @retry_on_exception(max_retries=3, delay=0.1, exceptions=(TimeoutException,))
    def decorated_func():
        return mock_func()
        
    result = decorated_func()
    assert result == "success"
    assert mock_func.call_count == 3
    assert mock_sleep.call_count == 2
    # Adjust for actual str(e) format which includes "Message: ...\n"
    mock_logger_warning.assert_any_call("Attempt 1/3 failed: Message: Fail1\n. Retrying in 0.1 seconds...")
    mock_logger_warning.assert_any_call("Attempt 2/3 failed: Message: Fail2\n. Retrying in 0.2 seconds...")


@patch('time.sleep', return_value=None)
@patch.object(utils_logger, 'error') # Patch the logger for error messages
def test_retry_on_exception_fails_after_max_retries(mock_logger_error, mock_sleep):
    """Test that the function fails after max_retries if exceptions persist."""
    mock_func = MagicMock(side_effect=TimeoutException("Persistent failure"))
    
    @retry_on_exception(max_retries=3, delay=0.1, exceptions=(TimeoutException,))
    def decorated_func():
        return mock_func()
        
    with pytest.raises(ScraperError, match=r"Failed after 3 attempts: Message: Persistent failure\n"):
        decorated_func()
    assert mock_func.call_count == 3
    assert mock_sleep.call_count == 2
    mock_logger_error.assert_called_once_with("All 3 attempts failed. Last error: Message: Persistent failure\n")

# Tests for handle_rate_limit decorator
@patch('time.sleep', return_value=None)
@patch.object(utils_logger, 'warning')
def test_handle_rate_limit_success(mock_logger_warning, mock_sleep):
    """Test that the function runs normally without rate limit error."""
    mock_func = MagicMock(return_value="success")
    
    @handle_rate_limit
    def decorated_func():
        return mock_func()
        
    result = decorated_func()
    assert result == "success"
    mock_func.assert_called_once()
    mock_sleep.assert_not_called()
    mock_logger_warning.assert_not_called()

@patch('time.sleep', return_value=None)
@patch.object(utils_logger, 'warning')
def test_handle_rate_limit_triggered_and_retries(mock_logger_warning, mock_sleep):
    """Test that rate limit error is handled with sleep and retry."""
    mock_func = MagicMock()
    # Simulate rate limit error on first call, success on second
    mock_func.side_effect = [Exception("Rate limit exceeded"), "success_after_retry"]
    
    @handle_rate_limit
    def decorated_func():
        return mock_func()
        
    result = decorated_func()
    assert result == "success_after_retry"
    assert mock_func.call_count == 2
    mock_sleep.assert_called_once_with(60)
    mock_logger_warning.assert_called_once_with("Rate limit detected. Waiting for 60 seconds...")

@patch('time.sleep', return_value=None)
def test_handle_rate_limit_other_exception(mock_sleep):
    """Test that other exceptions are re-raised."""
    mock_func = MagicMock(side_effect=ValueError("Other error"))
    
    @handle_rate_limit
    def decorated_func():
        return mock_func()
        
    with pytest.raises(ValueError, match="Other error"):
        decorated_func()
    mock_func.assert_called_once()
    mock_sleep.assert_not_called()

# Tests for safe_click function
def test_safe_click_success_first_try():
    """Test safe_click succeeds on the first attempt."""
    mock_driver = MagicMock()
    mock_element = MagicMock()
    mock_element.click = MagicMock()
    
    result = safe_click(mock_driver, mock_element)
    assert result is True
    mock_element.click.assert_called_once()
    mock_driver.execute_script.assert_not_called()

@patch('time.sleep', return_value=None)
def test_safe_click_intercepted_then_success(mock_sleep):
    """Test safe_click succeeds after scrolling on ElementClickInterceptedException."""
    mock_driver = MagicMock()
    mock_element = MagicMock()
    # First click raises, second (after scroll) succeeds
    mock_element.click.side_effect = [ElementClickInterceptedException("Intercepted"), None] 
    
    result = safe_click(mock_driver, mock_element)
    assert result is True
    assert mock_element.click.call_count == 2
    mock_driver.execute_script.assert_called_once_with("arguments[0].scrollIntoView(true);", mock_element)
    mock_sleep.assert_called_once_with(1)

@patch('time.sleep', return_value=None)
@patch.object(utils_logger, 'error')
def test_safe_click_intercepted_then_fail(mock_logger_error, mock_sleep):
    """Test safe_click fails if scrolling and retrying click also fails."""
    mock_driver = MagicMock()
    mock_element = MagicMock()
    # Both click attempts fail
    mock_element.click.side_effect = [
        ElementClickInterceptedException("Intercepted"), 
        WebDriverException("Second click failed")
    ]
    
    result = safe_click(mock_driver, mock_element)
    assert result is False
    assert mock_element.click.call_count == 2
    mock_driver.execute_script.assert_called_once_with("arguments[0].scrollIntoView(true);", mock_element)
    mock_logger_error.assert_called_once_with("Failed to click element after scrolling: Message: Second click failed\n")

@patch.object(utils_logger, 'error')
def test_safe_click_other_exception(mock_logger_error):
    """Test safe_click fails on other exceptions during the first click."""
    mock_driver = MagicMock()
    mock_element = MagicMock()
    mock_element.click.side_effect = WebDriverException("Generic WebDriver error")
    
    result = safe_click(mock_driver, mock_element)
    assert result is False
    mock_element.click.assert_called_once()
    mock_driver.execute_script.assert_not_called()
    mock_logger_error.assert_called_once_with("Failed to click element: Message: Generic WebDriver error\n")
