import pytest
import json
from unittest.mock import patch, MagicMock

SAMPLE_SKILLS_ANALYSIS = {
    "matching_skills": ["Python", "Django", "AWS"],
    "missing_skills": ["Kubernetes", "GraphQL"],
    "recommendations": [
        "Learn Kubernetes for container orchestration",
        "Study GraphQL for modern API development"
    ]
}

@pytest.fixture
def mock_openai_key(monkeypatch):
    """Set a dummy OpenAI API key for tests that might instantiate the client directly."""
    monkeypatch.setenv("OPENAI_API_KEY", "test_api_key_from_conftest")

@pytest.fixture
def mock_openai_client(mock_openai_key): # Depends on the key being set if real client init is hit
    """
    Mock the OpenAI client instance and its chat.completions.create method.
    Yields the instance mock.
    """
    with patch('job_recommender.job_analyzer.OpenAI') as mock_openai_class:
        mock_instance = mock_openai_class.return_value  # This is the mock for an OpenAI() instance
        
        # Configure the response for chat.completions.create
        mock_api_response = MagicMock()
        mock_api_response.choices = [
            MagicMock(
                message=MagicMock(content=json.dumps(SAMPLE_SKILLS_ANALYSIS))
            )
        ]
        mock_instance.chat.completions.create.return_value = mock_api_response
        yield mock_instance

@pytest.fixture
def temp_output_dir_conftest(tmp_path_factory):
    """Create a temporary directory for test output using tmp_path_factory."""
    output_dir = tmp_path_factory.mktemp("test_output")
    return str(output_dir)

@pytest.fixture
def temp_job_descriptions_conftest(tmp_path_factory):
    """Create temporary job description files for integration tests."""
    job_dir = tmp_path_factory.mktemp("integration_job_descriptions")
    sample_descriptions = [
        "Job 1: Requires Python, SQL, and communication skills.",
        "Job 2: Needs Java, Spring, and problem-solving abilities.",
        "Job 3: Python and data analysis are key."
    ]
    for i, desc in enumerate(sample_descriptions):
        with open(job_dir / f"job_{i+1}.txt", "w", encoding="utf-8") as f:
            # Mimic saved job file structure somewhat
            f.write(f"Site: test_site\n")
            f.write(f"Title: Test Job {i+1}\n")
            f.write(f"Company: Test Company {i+1}\n")
            f.write(f"URL: http://test.com/job{i+1}\n")
            f.write(f"Scraped Date: 2023-01-01T00:00:00\n")
            f.write("\nDescription:\n")
            f.write(desc)
    return str(job_dir)

@pytest.fixture
def sample_resume_text_conftest():
    return """
    John Doe
    Software Engineer with experience in Python and Java.
    Good communication skills.
    """

@pytest.fixture
def temp_resume_file_conftest(tmp_path_factory, sample_resume_text_conftest):
    """Create a temporary resume file for integration tests."""
    resume_file = tmp_path_factory.mktemp("resume_data") / "resume.txt"
    resume_file.write_text(sample_resume_text_conftest)
    return str(resume_file)

@pytest.fixture
def temp_cache_dir_conftest(tmp_path_factory):
    """Create a temporary cache directory for integration tests."""
    cache_dir = tmp_path_factory.mktemp("integration_cache")
    return str(cache_dir)
