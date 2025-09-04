#!/usr/bin/env python3
"""
Basic functionality test script for the job recommender package.
This script tests imports and basic functionality without requiring external services.
"""

import sys
import traceback
from pathlib import Path

def test_imports():
    """Test that all main modules can be imported without errors."""
    print("Testing imports...")
    
    try:
        # Test individual module imports
        from job_recommender import utils
        print("✓ utils module imported successfully")
        
        from job_recommender import cache
        print("✓ cache module imported successfully")
        
        from job_recommender import rich_utils
        print("✓ rich_utils module imported successfully")
        
        from job_recommender import scraper_factory
        print("✓ scraper_factory module imported successfully")
        
        from job_recommender import logging_config
        print("✓ logging_config module imported successfully")
        
        # Test main package imports
        from job_recommender import JobCache, get_scraper
        print("✓ Main package imports successful")
        
        # Test exception classes
        from job_recommender import ScraperError, RateLimitError, ScraperTimeoutError
        print("✓ Exception classes imported successfully")
        
        assert True
        return True
        
    except Exception as e:
        print(f"✗ Import failed: {e}")
        traceback.print_exc()
        assert False, f"Import failed: {e}"
        return False


def test_cache_functionality():
    """Test basic cache functionality."""
    print("\nTesting cache functionality...")
    
    try:
        from job_recommender import JobCache
        
        # Create cache instance
        cache = JobCache()
        print("✓ Cache created successfully")
        
        # Test cache availability and basic operations
        if cache.is_available():
            # Redis is available, test normal operations
            test_key = "test_key"
            test_value = {"id": "1", "title": "Test Job", "company": "Test Corp"}
            
            cache.set(test_key, test_value)
            print("✓ Data cached successfully")
            
            cached = cache.get(test_key)
            assert cached == test_value, "Cache retrieval failed"
            print("✓ Cached data retrieved successfully")
            
            # Clean up
            cache.delete(test_key)
            print("✓ Cache entry deleted successfully")
        else:
            # Redis is not available, test graceful degradation
            test_key = "test_key"
            test_value = {"id": "1", "title": "Test Job", "company": "Test Corp"}
            
            result = cache.set(test_key, test_value)
            assert result == False, "Cache should return False when unavailable"
            print("✓ Cache gracefully handles unavailability")
            
            cached = cache.get(test_key)
            assert cached is None, "Cache should return None when unavailable"
            print("✓ Cache gracefully returns None when unavailable")
        
        assert True
        return True
        
    except Exception as e:
        print(f"✗ Cache test failed: {e}")
        traceback.print_exc()
        assert False, f"Cache test failed: {e}"
        return False


def test_scraper_factory():
    """Test scraper factory functionality."""
    print("\nTesting scraper factory...")
    
    try:
        from job_recommender import get_scraper
        
        # Test supported scrapers
        indeed_scraper = get_scraper("indeed")
        assert indeed_scraper is not None, "Indeed scraper not found"
        print("✓ Indeed scraper factory works")
            
        linkedin_scraper = get_scraper("linkedin")
        assert linkedin_scraper is not None, "LinkedIn scraper not found"
        print("✓ LinkedIn scraper factory works")
            
        glassdoor_scraper = get_scraper("glassdoor")
        assert glassdoor_scraper is not None, "Glassdoor scraper not found"
        print("✓ Glassdoor scraper factory works")
        
        # Test unsupported scraper
        unknown_scraper = get_scraper("unknown")
        assert unknown_scraper is None, "Unknown scraper should return None"
        print("✓ Unknown scraper correctly returns None")
            
        assert True
        return True
        
    except Exception as e:
        print(f"✗ Scraper factory test failed: {e}")
        traceback.print_exc()
        assert False, f"Scraper factory test failed: {e}"
        return False


def test_logging_setup():
    """Test logging configuration."""
    print("\nTesting logging setup...")
    
    try:
        from job_recommender import setup_logging, get_logger
        
        # Setup logging
        logger = setup_logging(log_level="INFO", log_to_console=False)
        print("✓ Logging setup successful")
        
        # Get a specific logger
        test_logger = get_logger("test_module")
        test_logger.info("Test log message")
        print("✓ Logger creation and usage successful")
        
        assert True
        return True
        
    except Exception as e:
        print(f"✗ Logging test failed: {e}")
        traceback.print_exc()
        assert False, f"Logging test failed: {e}"
        return False


def test_rich_utils():
    """Test rich utilities."""
    print("\nTesting rich utilities...")
    
    try:
        from job_recommender.rich_utils import (
            print_success, print_warning, print_error, print_info,
            create_progress_bar, format_duration
        )
        
        # Test basic print functions
        print("Testing rich print functions:")
        print_success("This is a success message")
        print_warning("This is a warning message")  
        print_info("This is an info message")
        print("✓ Rich print functions work")
        
        # Test format_duration
        duration_str = format_duration(65.5)
        assert "1m" in duration_str and "s" in duration_str, f"Duration formatting failed: {duration_str}"
        print("✓ Duration formatting works")
            
        assert True
        return True
        
    except Exception as e:
        print(f"✗ Rich utils test failed: {e}")
        traceback.print_exc()
        assert False, f"Rich utils test failed: {e}"
        return False


def main():
    """Run all tests."""
    print("=== Job Recommender Basic Functionality Tests ===\n")
    
    tests = [
        test_imports,
        test_cache_functionality,
        test_scraper_factory,
        test_logging_setup,
        test_rich_utils
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()  # Add spacing between tests
    
    print("=" * 50)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! The basic functionality is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())