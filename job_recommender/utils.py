import time
import logging
from functools import wraps
from typing import Type, Callable, Any
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
    ElementClickInterceptedException
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ScraperError(Exception):
    """Base exception for scraper-related errors."""
    pass

class RateLimitError(ScraperError):
    """Raised when we hit rate limits on job sites."""
    pass

class ScraperTimeoutError(ScraperError):
    """Raised when scraping operations timeout."""
    pass

def retry_on_exception(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (TimeoutException, NoSuchElementException, WebDriverException)
) -> Callable:
    """
    Decorator that retries a function on specified exceptions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry on
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}. "
                            f"Retrying in {current_delay} seconds..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_retries} attempts failed. Last error: {str(e)}")
                        raise ScraperError(f"Failed after {max_retries} attempts: {str(e)}")
            
            raise last_exception
        return wrapper
    return decorator

def handle_rate_limit(func: Callable) -> Callable:
    """
    Decorator to handle rate limiting by adding appropriate delays.
    
    Args:
        func: Function to decorate
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if "rate limit" in str(e).lower() or "too many requests" in str(e).lower():
                logger.warning("Rate limit detected. Waiting for 60 seconds...")
                time.sleep(60)
                return func(*args, **kwargs)
            raise
    return wrapper

def safe_click(driver: Any, element: Any) -> bool:
    """
    Safely click an element with fallback mechanisms.
    
    Args:
        driver: Selenium WebDriver instance
        element: Element to click
    
    Returns:
        bool: True if click was successful, False otherwise
    """
    try:
        element.click()
        return True
    except ElementClickInterceptedException:
        try:
            # Try scrolling element into view
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(1)
            element.click()
            return True
        except Exception as e:
            logger.error(f"Failed to click element after scrolling: {str(e)}")
            return False
    except Exception as e:
        logger.error(f"Failed to click element: {str(e)}")
        return False 