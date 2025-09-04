"""
Comprehensive logging configuration for the job recommender project.
"""
import os
import logging
import logging.handlers
from pathlib import Path
from typing import Optional


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_to_console: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Set up comprehensive logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file. If None, logs to 'job_recommender.log'
        log_to_console: Whether to also log to console
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
    
    Returns:
        Configured logger instance
    """
    # Convert log level string to logging constant
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Set default log file
    if log_file is None:
        log_file = logs_dir / "job_recommender.log"
    else:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create detailed formatter for file logging
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s - [%(process)d:%(thread)d]',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Add file handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)
    
    # Add console handler if requested
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # Configure specific loggers
    configure_third_party_loggers(level)
    
    # Log the configuration
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Level: {log_level}, File: {log_file}")
    
    return root_logger


def configure_third_party_loggers(level: int):
    """
    Configure logging levels for third-party libraries to reduce noise.
    
    Args:
        level: Base logging level
    """
    # Selenium can be very verbose, so set it to WARNING unless we're in DEBUG mode
    selenium_level = logging.DEBUG if level == logging.DEBUG else logging.WARNING
    logging.getLogger('selenium').setLevel(selenium_level)
    logging.getLogger('urllib3').setLevel(selenium_level)
    
    # OpenAI API logging
    openai_level = logging.DEBUG if level == logging.DEBUG else logging.INFO
    logging.getLogger('openai').setLevel(openai_level)
    logging.getLogger('httpx').setLevel(openai_level)
    
    # NLTK can be verbose during downloads
    nltk_level = logging.DEBUG if level == logging.DEBUG else logging.WARNING
    logging.getLogger('nltk').setLevel(nltk_level)
    
    # Suppress some noisy loggers
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class ContextFilter(logging.Filter):
    """
    A filter that adds contextual information to log records.
    """
    
    def __init__(self, context: Optional[dict] = None):
        """
        Initialize the context filter.
        
        Args:
            context: Dictionary of context information to add to log records
        """
        super().__init__()
        self.context = context or {}
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add context information to the log record.
        
        Args:
            record: The log record to filter
        
        Returns:
            True to include the record, False to exclude it
        """
        # Add context information to the record
        for key, value in self.context.items():
            setattr(record, key, value)
        return True


def add_context_filter(logger: logging.Logger, context: dict):
    """
    Add a context filter to a logger.
    
    Args:
        logger: Logger to add the filter to
        context: Context information to add to log records
    """
    context_filter = ContextFilter(context)
    logger.addFilter(context_filter)


def setup_scraper_logging(scraper_name: str, query: str, location: str) -> logging.Logger:
    """
    Set up logging with context for a specific scraper.
    
    Args:
        scraper_name: Name of the scraper (e.g., 'indeed', 'linkedin')
        query: Search query being used
        location: Location being searched
    
    Returns:
        Logger with context information
    """
    logger = get_logger(f"job_recommender.scrapers.{scraper_name}")
    
    # Add context filter
    context = {
        'scraper': scraper_name,
        'query': query,
        'location': location
    }
    add_context_filter(logger, context)
    
    return logger


def log_performance(func_name: str, duration: float, **kwargs):
    """
    Log performance information for a function.
    
    Args:
        func_name: Name of the function
        duration: Execution duration in seconds
        **kwargs: Additional context information
    """
    logger = get_logger("job_recommender.performance")
    
    context_info = " ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.info(f"Performance - {func_name}: {duration:.3f}s {context_info}")


def log_scraping_stats(site: str, success_count: int, error_count: int, duration: float):
    """
    Log scraping statistics.
    
    Args:
        site: Name of the job site
        success_count: Number of successfully scraped jobs
        error_count: Number of errors encountered
        duration: Total scraping duration
    """
    logger = get_logger("job_recommender.stats")
    
    total = success_count + error_count
    success_rate = (success_count / total * 100) if total > 0 else 0
    
    logger.info(
        f"Scraping Stats - {site}: "
        f"Success: {success_count}, Errors: {error_count}, "
        f"Success Rate: {success_rate:.1f}%, Duration: {duration:.3f}s"
    )