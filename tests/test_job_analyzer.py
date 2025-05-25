import os
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from job_recommender.job_analyzer import JobAnalyzer
from click.testing import CliRunner # Added CliRunner import

# Sample test data
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
def mock_openai(monkeypatch):
    """Mock OpenAI API responses."""
    # monkeypatch.setenv("OPENAI_API_KEY", "test_api_key") # Keep this to satisfy potential direct os.getenv checks if any
    with patch('job_recommender.job_analyzer.OpenAI') as mock_client_class: # Patched where it's used
        mock_instance = mock_client_class.return_value # This is the instance mock
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "matching_skills": ["Python", "Django", "AWS"],
                        "missing_skills": ["Kubernetes", "GraphQL"],
                        "recommendations": [
                            "Learn Kubernetes for container orchestration",
                            "Study GraphQL for modern API development"
                        ]
                    })
                )
            )
        ]
        mock_instance.chat.completions.create.return_value = mock_response
        yield mock_instance # Yield the instance mock for easier use in tests

@pytest.fixture
def temp_job_descriptions(tmp_path):
    """Create temporary job description files."""
    job_dir = tmp_path / "test_job_descriptions"
    job_dir.mkdir()
    
    for i, desc in enumerate(SAMPLE_JOB_DESCRIPTIONS):
        with open(job_dir / f"job_{i}.txt", "w", encoding="utf-8") as f:
            f.write(desc)
    
    return str(job_dir)

@pytest.fixture
def temp_resume(tmp_path):
    """Create a temporary resume file."""
    resume_path = tmp_path / "test_resume.txt"
    with open(resume_path, "w", encoding="utf-8") as f:
        f.write(SAMPLE_RESUME)
    return str(resume_path)

class TestJobAnalyzer:
    def test_init(self, mock_openai):
        """Test JobAnalyzer initialization."""
        analyzer = JobAnalyzer(max_skills=15, model_name="gpt-4")
        assert analyzer.max_skills == 15
        assert analyzer.model_name == "gpt-4"
        assert analyzer.client is not None
        assert analyzer.stop_words is not None
        assert analyzer.vectorizer is not None

    def test_read_job_descriptions(self, mock_openai, temp_job_descriptions):
        """Test reading job descriptions from files."""
        analyzer = JobAnalyzer() # mock_openai is implicitly used by JobAnalyzer's __init__
        descriptions = analyzer.read_job_descriptions(temp_job_descriptions)
        
        assert len(descriptions) == 3
        assert all(isinstance(desc, str) for desc in descriptions)
        # Check for presence of key phrases, order-independent
        desc_text_combined = " ".join(descriptions)
        assert "Python developer" in desc_text_combined
        assert "Senior Software Engineer" in desc_text_combined
        assert "Full Stack Developer" in desc_text_combined

    def test_extract_skills(self, mock_openai, temp_job_descriptions):
        """Test skill extraction from job descriptions."""
        analyzer = JobAnalyzer() # mock_openai is implicitly used
        descriptions = analyzer.read_job_descriptions(temp_job_descriptions)
        skills_dict = analyzer.extract_skills(descriptions)
        
        assert isinstance(skills_dict, dict)
        assert len(skills_dict) > 0
        assert "python" in skills_dict
        assert "django" in skills_dict
        assert "aws" in skills_dict

    def test_read_resume_txt(self, mock_openai, temp_resume):
        """Test reading resume from text file."""
        analyzer = JobAnalyzer() # mock_openai is implicitly used
        resume_text = analyzer.read_resume(temp_resume)
        
        assert isinstance(resume_text, str)
        assert "PROFESSIONAL SUMMARY" in resume_text
        assert "SKILLS" in resume_text
        assert "Python" in resume_text

    @patch('job_recommender.job_analyzer.PdfReader') # Removed autospec for manual instance control
    def test_read_resume_pdf(self, MockPdfReaderClass, mock_openai, tmp_path): # Renamed mock arg
        """Test reading resume from PDF file."""
        mock_pdf_instance = MagicMock() # This will be the PdfReader instance
        mock_page = MagicMock()
        mock_page.extract_text.return_value = SAMPLE_RESUME
        mock_pdf_instance.pages = [mock_page]
        MockPdfReaderClass.return_value = mock_pdf_instance # Ensure PdfReader(path) returns our mock_pdf_instance
        
        analyzer = JobAnalyzer() # mock_openai is implicitly used
        resume_path = tmp_path / "test_resume.pdf"
        # Create an empty file, just so os.path.exists might pass if checked by PdfReader path handling
        # The actual PdfReader.__init__ should not be called due to the patch.
        open(resume_path, "wb").close()
            
        resume_text = analyzer.read_resume(str(resume_path))
        
        assert isinstance(resume_text, str)
        assert "PROFESSIONAL SUMMARY" in resume_text
        assert "SKILLS" in resume_text
        assert "Python" in resume_text

    def test_analyze_resume(self, mock_openai, temp_job_descriptions):
        mock_page = MagicMock()
        mock_page.extract_text.return_value = SAMPLE_RESUME
        mock_pdf_reader.return_value.pages = [mock_page]
        
        analyzer = JobAnalyzer() # mock_openai is implicitly used
        resume_path = tmp_path / "test_resume.pdf"
        # Create an empty dummy PDF file. PdfReader might handle this by finding 0 pages.
        # The actual text extraction is mocked by mock_pdf_reader.return_value.pages.
        open(resume_path, "wb").close()
            
        resume_text = analyzer.read_resume(str(resume_path))
        
        assert isinstance(resume_text, str)
        assert "PROFESSIONAL SUMMARY" in resume_text
        assert "SKILLS" in resume_text
        assert "Python" in resume_text

    def test_extract_skills_empty_descriptions(self, mock_openai):
        """Test skill extraction with no job descriptions or empty content."""
        analyzer = JobAnalyzer()
        skills_dict_empty_list = analyzer.extract_skills([])
        assert skills_dict_empty_list == {}

        skills_dict_empty_content = analyzer.extract_skills(["", "   "])
        assert skills_dict_empty_content == {}

    @patch('job_recommender.job_analyzer.PdfReader')
    def test_read_resume_corrupted_pdf(self, MockPdfReaderClass, mock_openai, tmp_path):
        """Test reading a corrupted PDF file."""
        MockPdfReaderClass.side_effect = Exception("Corrupted PDF") # Simulate PyPDF2 error

        analyzer = JobAnalyzer()
        corrupted_pdf_path = tmp_path / "corrupted.pdf"
        with open(corrupted_pdf_path, "w") as f:
            f.write("this is not a pdf") # Content that would make PyPDF2 fail

        with pytest.raises(Exception, match="Corrupted PDF"):
            analyzer.read_resume(str(corrupted_pdf_path))
            
    def test_analyze_resume(self, mock_openai, temp_job_descriptions):
        """Test resume analysis against job skills."""
        analyzer = JobAnalyzer()
        descriptions = analyzer.read_job_descriptions(temp_job_descriptions)
        skills_dict = analyzer.extract_skills(descriptions)
        
        analysis = analyzer.analyze_resume(SAMPLE_RESUME, skills_dict)
        
        assert isinstance(analysis, dict)
        assert "matching_skills" in analysis
        assert "missing_skills" in analysis
        assert "recommendations" in analysis
        assert len(analysis["matching_skills"]) > 0
        assert len(analysis["missing_skills"]) > 0
        assert len(analysis["recommendations"]) > 0

    def test_analyze_resume_no_skills_extracted(self, mock_openai):
        """Test resume analysis when no skills are extracted from job descriptions."""
        analyzer = JobAnalyzer()
        # Simulate a scenario where skills_dict is empty
        empty_skills_dict = {}
        
        analysis = analyzer.analyze_resume(SAMPLE_RESUME, empty_skills_dict)
        
        # Ensure OpenAI API was still called
        mock_openai.chat.completions.create.assert_called_once()
        
        assert isinstance(analysis, dict)
        # Depending on implementation, matching_skills and missing_skills might be empty
        # or reflect that no job skills were provided for comparison.
        # For this test, we'll check they exist.
        assert "matching_skills" in analysis
        assert "missing_skills" in analysis
        assert "recommendations" in analysis
        # If no skills are provided, missing_skills might be empty or reflect all resume skills are "matching" in a void sense
        # Or it might list all resume skills as "missing" from the (empty) job requirement.
        # The current mock returns fixed values, so this part of the assertion is more about API call.

    def test_analyze_jobs_and_resume(self, mock_openai, temp_job_descriptions, temp_resume):
        """Test the complete analysis process."""
        from job_recommender.job_analyzer import analyze_jobs_and_resume
        
        analyze_jobs_and_resume(
            job_folder=temp_job_descriptions,
            resume_path=temp_resume,
            max_skills=10,
            model_name="gpt-4"
        )
        
        # Verify OpenAI API was called (mock_openai is the instance mock now)
        mock_openai.chat.completions.create.assert_called_once()

    def test_error_handling(self, mock_openai, tmp_path):
        """Test error handling in various scenarios."""
        analyzer = JobAnalyzer() # analyzer.client is mock_openai (the instance mock)
        
        # Test non-existent job folder
        with pytest.raises(FileNotFoundError):
            analyzer.read_job_descriptions("non_existent_folder")
        
        # Test non-existent resume file
        with pytest.raises(FileNotFoundError):
            analyzer.read_resume("non_existent_resume.pdf")
        
        # Test invalid resume format
        invalid_resume = tmp_path / "invalid_resume.txt"
        with open(invalid_resume, "w", encoding="utf-8") as f:
            f.write("Invalid resume content")
        
        # Test OpenAI API error
        # mock_openai is the instance mock, so we set side_effect directly on its method
        mock_openai.chat.completions.create.side_effect = Exception("API Error")
        with pytest.raises(Exception, match="API Error"): # check for specific error message
            analyzer.analyze_resume(SAMPLE_RESUME, {"python": 1.0}) # Use SAMPLE_RESUME for valid input

@pytest.mark.integration
def test_full_analysis_process_cli(mock_openai, temp_job_descriptions, temp_resume, tmp_path): # Renamed
    """Integration test for the CLI of the analysis process."""
    from job_recommender.job_analyzer import main as analyzer_main_cli
    runner = CliRunner()

    # Ensure job files and resume file are correctly set up from fixtures
    # temp_job_descriptions is a dir path, temp_resume is a file path

    with patch('click.echo') as mock_echo:
        result = runner.invoke(analyzer_main_cli, [
            '--job-folder', temp_job_descriptions,
            '--resume', temp_resume,
            '--max-skills', '5', # Use a smaller number for faster test
            '--model', 'gpt-test-model' # Use a test model name
        ], catch_exceptions=False) # See full traceback if Click has issues
        
        assert result.exit_code == 0, f"CLI Error: {result.output}"
        
        # Verify that output was printed via click.echo
        assert mock_echo.call_count > 0
        
        output_text = "".join(str(call_args[0][0]) for call_args in mock_echo.call_args_list)
        assert "Top 5 Required Skills:" in output_text # Adjusted for max_skills
        assert "Matching Skills:" in output_text
        assert "Areas for Growth:" in output_text
        assert "Recommendations:" in output_text
        
        # Verify OpenAI API was called via the analyzer used by CLI
        # mock_openai is the instance mock from the fixture
        mock_openai.chat.completions.create.assert_called_once()