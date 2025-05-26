import os
import pytest
from unittest.mock import patch, MagicMock

from sqlalchemy.engine import Engine
import sqlalchemy

# Assuming job_recommender package is in PYTHONPATH
# Adjust if your project structure requires different import paths for tests
from job_recommender.db_utils import create_db_engine, create_tables
from job_recommender.db_schema import Base # Needed for mocking Base.metadata.create_all

# Define valid environment variables for testing
VALID_DB_ENV_VARS = {
    "DB_USER": "testuser",
    "DB_PASSWORD": "testpassword",
    "DB_HOST": "localhost",
    "DB_PORT": "5432",
    "DB_NAME": "testdb",
}

class TestDbUtils:

    @patch.dict(os.environ, VALID_DB_ENV_VARS, clear=True)
    @patch('job_recommender.db_utils.create_engine') # Mock actual create_engine call
    def test_create_db_engine_success(self, mock_sqlalchemy_create_engine, mocker):
        """Test create_db_engine successfully creates an engine with correct URL."""
        # Configure the mock_sqlalchemy_create_engine to return a MagicMock (simulating an Engine)
        mock_engine_instance = MagicMock(spec=Engine)
        mock_sqlalchemy_create_engine.return_value = mock_engine_instance

        engine = create_db_engine()

        # Verify create_engine was called once
        mock_sqlalchemy_create_engine.assert_called_once()
        
        # Verify the URL passed to create_engine
        expected_url_pattern = f"postgresql+psycopg2://{VALID_DB_ENV_VARS['DB_USER']}:{VALID_DB_ENV_VARS['DB_PASSWORD']}@{VALID_DB_ENV_VARS['DB_HOST']}:{VALID_DB_ENV_VARS['DB_PORT']}/{VALID_DB_ENV_VARS['DB_NAME']}"
        args, _ = mock_sqlalchemy_create_engine.call_args
        assert args[0] == expected_url_pattern
        
        # Verify the returned object is what create_engine returned
        assert engine is mock_engine_instance

    @patch.dict(os.environ, {}, clear=True) # Ensure all env vars are cleared
    def test_create_db_engine_missing_env_vars(self):
        """Test create_db_engine raises ValueError if environment variables are missing."""
        with pytest.raises(ValueError) as excinfo:
            create_db_engine()
        assert "Missing required environment variables" in str(excinfo.value)
        # Check for one of the specific missing variables
        assert "DB_USER" in str(excinfo.value)

    @patch.dict(os.environ, {"DB_USER": "test"}, clear=True) # Only one var set
    def test_create_db_engine_some_missing_env_vars(self):
        """Test create_db_engine raises ValueError if some environment variables are missing."""
        with pytest.raises(ValueError) as excinfo:
            create_db_engine()
        assert "Missing required environment variables" in str(excinfo.value)
        assert "DB_PASSWORD" in str(excinfo.value) # Example of another missing var
        assert "DB_HOST" in str(excinfo.value)

    @patch('job_recommender.db_utils.Base') # Mock the Base object from db_schema used in db_utils
    def test_create_tables(self, mock_base, mocker):
        """Test create_tables calls Base.metadata.create_all with the provided engine."""
        mock_engine = MagicMock(spec=Engine)
        
        # mock_base.metadata is an attribute of the mocked Base.
        # We need to ensure this attribute itself has a create_all method that can be asserted.
        mock_base.metadata = MagicMock(spec=sqlalchemy.MetaData)
        # mock_base.metadata.create_all = MagicMock() # This is done automatically by MagicMock if spec is good

        create_tables(mock_engine)

        # Verify that Base.metadata.create_all was called once with the mock_engine
        mock_base.metadata.create_all.assert_called_once_with(mock_engine)

    @patch.dict(os.environ, VALID_DB_ENV_VARS, clear=True)
    @patch('job_recommender.db_utils.create_engine', side_effect=Exception("Connection failed"))
    def test_create_db_engine_connection_error(self, mock_sqlalchemy_create_engine):
        """Test create_db_engine handles exceptions from sqlalchemy.create_engine."""
        with pytest.raises(Exception) as excinfo:
            create_db_engine()
        assert "Connection failed" in str(excinfo.value)
        mock_sqlalchemy_create_engine.assert_called_once()

# To run these tests:
# Ensure pytest and pytest-mock are installed.
# Navigate to the root directory of the project.
# Run `pytest tests/test_db_utils.py`
# Or simply `pytest` to run all tests.
