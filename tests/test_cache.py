import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timedelta

# Assuming job_recommender package is in PYTHONPATH
from job_recommender.cache import JobCache
from job_recommender.db_schema import CachedSearches # Model to be mocked

# Test data
SITE_NAME = "test_site"
QUERY = "test_query"
LOCATION = "test_location"
JOB_LIST_DATA = [{"title": "Job 1", "company": "Company A"}, {"title": "Job 2", "company": "Company B"}]
CACHE_DURATION_HOURS = 24

@pytest.fixture
def mock_engine():
    """Fixture for a mocked SQLAlchemy engine."""
    return MagicMock()

@pytest.fixture
def mock_session():
    """Fixture for a mocked SQLAlchemy session."""
    session = MagicMock()
    # Ensure query().filter_by().first() is a chainable mock
    session.query.return_value.filter_by.return_value.first.return_value = None
    # Ensure query().delete() and query().filter().delete() are chainable and return a value
    session.query.return_value.delete.return_value = 0 
    session.query.return_value.filter.return_value.delete.return_value = 0
    return session

@pytest.fixture
@patch('job_recommender.cache.create_db_engine') # Mock create_db_engine in cache.py
def job_cache_instance(mock_create_db_engine, mock_engine, mock_session):
    """Fixture for a JobCache instance with mocked engine and session factory."""
    # Ensure create_db_engine (if called by JobCache.__init__) returns our mock_engine
    mock_create_db_engine.return_value = mock_engine 
    
    cache = JobCache(cache_duration=CACHE_DURATION_HOURS, engine=mock_engine)
    
    # Replace the session factory with one that returns our mock_session
    cache.Session = MagicMock(return_value=mock_session)
    return cache

class TestJobCache:

    def test_get_cache_key(self, job_cache_instance):
        """Test _get_cache_key generates a consistent MD5 hash."""
        key1 = job_cache_instance._get_cache_key(SITE_NAME, QUERY, LOCATION)
        key2 = job_cache_instance._get_cache_key(SITE_NAME, QUERY, LOCATION)
        key3 = job_cache_instance._get_cache_key("another_site", QUERY, LOCATION)
        
        assert isinstance(key1, str)
        assert len(key1) == 32 # MD5 hash length
        assert key1 == key2
        assert key1 != key3

    def test_get_cached_jobs_found_not_expired(self, job_cache_instance, mock_session):
        """Test retrieving jobs from cache that are found and not expired."""
        cache_key = job_cache_instance._get_cache_key(SITE_NAME, QUERY, LOCATION)
        
        mock_cached_entry = MagicMock(spec=CachedSearches)
        mock_cached_entry.search_hash = cache_key
        mock_cached_entry.job_data = JOB_LIST_DATA
        # Timestamp well within the cache duration
        mock_cached_entry.timestamp = datetime.utcnow() - timedelta(hours=CACHE_DURATION_HOURS / 2)
        
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_cached_entry
        
        result = job_cache_instance.get_cached_jobs(SITE_NAME, QUERY, LOCATION)
        
        mock_session.query.assert_called_once_with(CachedSearches)
        mock_session.query.return_value.filter_by.assert_called_once_with(search_hash=cache_key)
        assert result == JOB_LIST_DATA
        mock_session.delete.assert_not_called() # Should not delete if not expired
        mock_session.commit.assert_not_called() # Should not commit if not expired and not deleted

    def test_get_cached_jobs_found_expired(self, job_cache_instance, mock_session):
        """Test retrieving jobs from cache that are found but expired."""
        cache_key = job_cache_instance._get_cache_key(SITE_NAME, QUERY, LOCATION)
        
        mock_cached_entry = MagicMock(spec=CachedSearches)
        mock_cached_entry.search_hash = cache_key
        mock_cached_entry.job_data = JOB_LIST_DATA
        # Timestamp older than cache duration
        mock_cached_entry.timestamp = datetime.utcnow() - timedelta(hours=CACHE_DURATION_HOURS + 1)
        
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_cached_entry
        
        result = job_cache_instance.get_cached_jobs(SITE_NAME, QUERY, LOCATION)
        
        mock_session.query.assert_called_once_with(CachedSearches)
        mock_session.query.return_value.filter_by.assert_called_once_with(search_hash=cache_key)
        assert result is None
        mock_session.delete.assert_called_once_with(mock_cached_entry)
        mock_session.commit.assert_called_once() # Commit after deletion

    def test_get_cached_jobs_not_found(self, job_cache_instance, mock_session):
        """Test retrieving jobs when no cache entry is found."""
        cache_key = job_cache_instance._get_cache_key(SITE_NAME, QUERY, LOCATION)
        mock_session.query.return_value.filter_by.return_value.first.return_value = None # Simulate not found
        
        result = job_cache_instance.get_cached_jobs(SITE_NAME, QUERY, LOCATION)
        
        mock_session.query.assert_called_once_with(CachedSearches)
        mock_session.query.return_value.filter_by.assert_called_once_with(search_hash=cache_key)
        assert result is None
        mock_session.delete.assert_not_called()
        mock_session.commit.assert_not_called()

    def test_cache_jobs_new_entry(self, job_cache_instance, mock_session):
        """Test caching jobs when no existing entry is found (new entry)."""
        cache_key = job_cache_instance._get_cache_key(SITE_NAME, QUERY, LOCATION)
        mock_session.query.return_value.filter_by.return_value.first.return_value = None # Simulate new entry
        
        job_cache_instance.cache_jobs(SITE_NAME, QUERY, LOCATION, JOB_LIST_DATA)
        
        mock_session.query.assert_called_once_with(CachedSearches)
        mock_session.query.return_value.filter_by.assert_called_once_with(search_hash=cache_key)
        
        # Check that session.add was called with a CachedSearches instance
        mock_session.add.assert_called_once()
        added_object = mock_session.add.call_args[0][0]
        assert isinstance(added_object, CachedSearches)
        assert added_object.search_hash == cache_key
        assert added_object.site_name == SITE_NAME
        assert added_object.query_string == QUERY
        assert added_object.location_string == LOCATION
        assert added_object.job_data == JOB_LIST_DATA
        # Check timestamp is recent (within a small delta)
        assert (datetime.utcnow() - added_object.timestamp) < timedelta(seconds=5)
        
        mock_session.commit.assert_called_once()

    def test_cache_jobs_update_existing(self, job_cache_instance, mock_session):
        """Test caching jobs when an existing entry is found (update)."""
        cache_key = job_cache_instance._get_cache_key(SITE_NAME, QUERY, LOCATION)
        
        mock_existing_entry = MagicMock(spec=CachedSearches)
        mock_existing_entry.search_hash = cache_key
        mock_existing_entry.site_name = SITE_NAME
        mock_existing_entry.query_string = QUERY
        mock_existing_entry.location_string = LOCATION
        mock_existing_entry.job_data = [{"old": "data"}] # Some old data
        original_timestamp = datetime.utcnow() - timedelta(hours=1)
        mock_existing_entry.timestamp = original_timestamp
        
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_existing_entry
        
        new_job_data = [{"new": "data"}]
        job_cache_instance.cache_jobs(SITE_NAME, QUERY, LOCATION, new_job_data)
        
        mock_session.query.assert_called_once_with(CachedSearches)
        mock_session.query.return_value.filter_by.assert_called_once_with(search_hash=cache_key)
        
        mock_session.add.assert_not_called() # Should not add a new object
        
        # Verify the existing entry was updated
        assert mock_existing_entry.job_data == new_job_data
        assert mock_existing_entry.timestamp > original_timestamp # Timestamp should be updated
        assert (datetime.utcnow() - mock_existing_entry.timestamp) < timedelta(seconds=5) # New timestamp is recent
        
        mock_session.commit.assert_called_once()

    def test_clear_cache_all(self, job_cache_instance, mock_session):
        """Test clearing all cache entries."""
        mock_session.query.return_value.delete.return_value = 5 # Simulate 5 rows deleted
        
        job_cache_instance.clear_cache()
        
        mock_session.query.assert_called_once_with(CachedSearches)
        # Ensure .delete() was called on the query object
        mock_session.query.return_value.delete.assert_called_once_with(synchronize_session=False)
        mock_session.commit.assert_called_once()

    def test_clear_cache_specific_site(self, job_cache_instance, mock_session):
        """Test clearing cache entries for a specific site."""
        mock_session.query.return_value.filter.return_value.delete.return_value = 2 # Simulate 2 rows deleted
        
        job_cache_instance.clear_cache(site=SITE_NAME)
        
        mock_session.query.assert_called_once_with(CachedSearches)
        # Ensure .filter was called on the query object
        mock_session.query.return_value.filter.assert_called_once()
        # Check the filter condition if possible, or rely on filter().delete() chain
        # Example: mock_session.query.return_value.filter.assert_called_once_with(CachedSearches.site_name == SITE_NAME)
        # This requires more complex mocking of the filter condition itself.
        # For now, checking the chain is a good start.
        mock_session.query.return_value.filter.return_value.delete.assert_called_once_with(synchronize_session=False)
        mock_session.commit.assert_called_once()

    def test_get_cached_jobs_handles_sqlalchemy_error(self, job_cache_instance, mock_session):
        """Test get_cached_jobs handles SQLAlchemyError and rolls back."""
        cache_key = job_cache_instance._get_cache_key(SITE_NAME, QUERY, LOCATION)
        mock_session.query.return_value.filter_by.side_effect = Exception("DB Read Error!") # Simulate SQLAlchemyError

        result = job_cache_instance.get_cached_jobs(SITE_NAME, QUERY, LOCATION)

        assert result is None
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once() # Ensure session is closed

    def test_cache_jobs_handles_sqlalchemy_error(self, job_cache_instance, mock_session):
        """Test cache_jobs handles SQLAlchemyError and rolls back."""
        mock_session.commit.side_effect = Exception("DB Write Error!") # Simulate error on commit

        job_cache_instance.cache_jobs(SITE_NAME, QUERY, LOCATION, JOB_LIST_DATA)

        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

    def test_clear_cache_handles_sqlalchemy_error(self, job_cache_instance, mock_session):
        """Test clear_cache handles SQLAlchemyError and rolls back."""
        mock_session.commit.side_effect = Exception("DB Clear Error!") # Simulate error on commit

        job_cache_instance.clear_cache(site=SITE_NAME)

        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

# To run these tests:
# Ensure pytest and pytest-mock are installed.
# Navigate to the root directory of the project.
# Run `pytest tests/test_cache.py`
# Or simply `pytest` to run all tests.
