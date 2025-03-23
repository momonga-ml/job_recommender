import os
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from job_recommender.job_analyzer import JobAnalyzer

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
def mock_openai():
    """Mock OpenAI API responses."""
    with patch('openai.OpenAI') as mock_client:
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
        mock_client.return_value.chat.completions.create.return_value = mock_response
        yield mock_client

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

    def test_read_job_descriptions(self, temp_job_descriptions):
        """Test reading job descriptions from files."""
        analyzer = JobAnalyzer()
        descriptions = analyzer.read_job_descriptions(temp_job_descriptions)
        
        assert len(descriptions) == 3
        assert all(isinstance(desc, str) for desc in descriptions)
        assert "Python developer" in descriptions[0]
        assert "Senior Software Engineer" in descriptions[1]
        assert "Full Stack Developer" in descriptions[2]

    def test_extract_skills(self, temp_job_descriptions):
        """Test skill extraction from job descriptions."""
        analyzer = JobAnalyzer()
        descriptions = analyzer.read_job_descriptions(temp_job_descriptions)
        skills_dict = analyzer.extract_skills(descriptions)
        
        assert isinstance(skills_dict, dict)
        assert len(skills_dict) > 0
        assert "python" in skills_dict
        assert "django" in skills_dict
        assert "aws" in skills_dict

    def test_read_resume_txt(self, temp_resume):
        """Test reading resume from text file."""
        analyzer = JobAnalyzer()
        resume_text = analyzer.read_resume(temp_resume)
        
        assert isinstance(resume_text, str)
        assert "PROFESSIONAL SUMMARY" in resume_text
        assert "SKILLS" in resume_text
        assert "Python" in resume_text

    @patch('PyPDF2.PdfReader')
    def test_read_resume_pdf(self, mock_pdf_reader, tmp_path):
        """Test reading resume from PDF file."""
        # Create a mock PDF
        mock_page = MagicMock()
        mock_page.extract_text.return_value = SAMPLE_RESUME
        mock_pdf_reader.return_value.pages = [mock_page]
        
        analyzer = JobAnalyzer()
        resume_path = tmp_path / "test_resume.pdf"
        resume_text = analyzer.read_resume(str(resume_path))
        
        assert isinstance(resume_text, str)
        assert "PROFESSIONAL SUMMARY" in resume_text
        assert "SKILLS" in resume_text
        assert "Python" in resume_text

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

    def test_analyze_jobs_and_resume(self, mock_openai, temp_job_descriptions, temp_resume):
        """Test the complete analysis process."""
        from job_recommender.job_analyzer import analyze_jobs_and_resume
        
        analyze_jobs_and_resume(
            job_folder=temp_job_descriptions,
            resume_path=temp_resume,
            max_skills=10,
            model_name="gpt-4"
        )
        
        # Verify OpenAI API was called
        mock_openai.return_value.chat.completions.create.assert_called_once()

    def test_error_handling(self, mock_openai, tmp_path):
        """Test error handling in various scenarios."""
        analyzer = JobAnalyzer()
        
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
        mock_openai.return_value.chat.completions.create.side_effect = Exception("API Error")
        with pytest.raises(Exception):
            analyzer.analyze_resume(str(invalid_resume), {"python": 1.0})

@pytest.mark.integration
def test_full_analysis_process(mock_openai, temp_job_descriptions, temp_resume):
    """Integration test for the complete analysis process."""
    from job_recommender.job_analyzer import main
    
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