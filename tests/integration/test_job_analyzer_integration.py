import os
import pytest
from unittest.mock import patch # Keep patch for mocking click.echo
from job_recommender.job_analyzer import main

# Sample test data (used by fixtures)
SAMPLE_JOB_DESCRIPTIONS = [
    "Looking for a Python developer with experience in Django and Flask",
    "Senior Software Engineer needed with expertise in Python and AWS",
    "Full Stack Developer position requiring Python and React skills"
]

SAMPLE_RESUME = """
PROFESSIONAL SUMMARY
Experienced software developer with expertise in Python, Django, and AWS.

SKILLS
- Python, Django, Flask
- AWS, Docker
- JavaScript, React
- SQL, PostgreSQL
"""

@pytest.fixture
def temp_job_descriptions(tmp_path):
    # Create temporary job description files.
    job_dir = tmp_path / "test_job_descriptions"
    job_dir.mkdir()
    
    for i, desc in enumerate(SAMPLE_JOB_DESCRIPTIONS):
        with open(job_dir / f"job_{i}.txt", "w", encoding="utf-8") as f:
            f.write(desc)
    
    return str(job_dir)

@pytest.fixture
def temp_resume(tmp_path):
    #Create a temporary resume file.
    resume_path = tmp_path / "test_resume.txt"
    with open(resume_path, "w", encoding="utf-8") as f:
        f.write(SAMPLE_RESUME)
    return str(resume_path)

@pytest.mark.integration
def test_full_analysis_process(temp_job_descriptions, temp_resume):
    # Integration test for the complete analysis process.
    # This test will make a real OpenAI API call.
    # Ensure OPENAI_API_KEY is set in the environment.
    if not os.getenv('OPENAI_API_KEY'):
        pytest.skip("Skipping test: OPENAI_API_KEY is not set in the environment.")
    
    # Test the CLI interface
    with patch('click.echo') as mock_echo:
        main(job_folder=temp_job_descriptions, resume=temp_resume)
        
        # Verify that output was printed
        assert mock_echo.call_count > 0
        
        # Verify the content of the output
        output_calls = [call[0][0] for call in mock_echo.call_args_list]
        assert any("Top 10 Required Skills:" in str(call) for call in output_calls)
        assert any("Matching Skills:" in str(call) for call in output_calls)
        assert any("Areas for Growth:" in str(call) for call in output_calls)
        assert any("Recommendations:" in str(call) for call in output_calls)
