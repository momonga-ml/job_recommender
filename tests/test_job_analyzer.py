import os
import json
import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime importdatetime
from job_recommender.job_analyzer import JobAnalyzer, analyze_jobs_and_resume
from job_recommender.db_schema import JobDetails # For mocking

# Sample test data
SAMPLE_JOB_DESCRIPTIONS_FROM_DB = [ # For mocking DB results
    ("Python dev skilled in Django.",), 
    ("AWS expert needed.",)
]
EXPECTED_DESCRIPTIONS_LIST = [
    "Python dev skilled in Django.",
    "AWS expert needed."
]

SAMPLE_JOB_DESCRIPTIONS = [ # Old sample, can be used if file tests are kept separate
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
def mock_engine_and_session_analyzer():
    """Fixture for a mocked SQLAlchemy engine and session factory for JobAnalyzer."""
    mock_engine_instance = MagicMock()
    mock_session_instance = MagicMock()
    
    # Setup mock for query results for JobDetails.description
    # query(JobDetails.description).all() or query(JobDetails.description).filter().all()
    mock_query_result = MagicMock()
    mock_query_result.all.return_value = [] # Default to no results
    
    mock_session_instance.query.return_value.filter.return_value = mock_query_result
    mock_session_instance.query.return_value = mock_query_result # For query without filter

    mock_session_factory = MagicMock(return_value=mock_session_instance)
    return mock_engine_instance, mock_session_factory, mock_session_instance

@pytest.fixture
def mock_openai():
    """Mock OpenAI API responses."""
    with patch('job_recommender.job_analyzer.OpenAI') as mock_client_constructor: # Patch where it's imported
        mock_openai_instance = MagicMock()
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
        mock_openai_instance.chat.completions.create.return_value = mock_response
        mock_client_constructor.return_value = mock_openai_instance
        yield mock_openai_instance


# Keep temp_job_descriptions if file-based tests are to be maintained separately
@pytest.fixture
def temp_job_descriptions_files(tmp_path):
    """Create temporary job description files (for legacy tests if any)."""
    job_dir = tmp_path / "test_job_descriptions_files"
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

    @patch('job_recommender.job_analyzer.create_db_engine') # Mock at source
    def test_init_db(self, mock_create_db_engine_func, mock_engine_and_session_analyzer, mock_openai):
        """Test JobAnalyzer initialization with DB engine."""
        mock_engine, mock_session_factory, _ = mock_engine_and_session_analyzer
        mock_create_db_engine_func.return_value = mock_engine

        # Test with engine passed explicitly
        analyzer = JobAnalyzer(engine=mock_engine, session_factory=mock_session_factory) # Custom session_factory for testing
        assert analyzer.engine is mock_engine
        assert analyzer.Session is mock_session_factory
        mock_create_db_engine_func.assert_not_called()

        # Test with engine created by __init__
        analyzer_creates_engine = JobAnalyzer(session_factory=mock_session_factory)
        assert analyzer_creates_engine.engine is mock_engine # Because create_db_engine is mocked
        assert analyzer_creates_engine.Session is mock_session_factory
        mock_create_db_engine_func.assert_called_once()
        # Ensure OpenAI client is also initialized
        assert analyzer.client is not None 


    def test_read_job_descriptions_all_from_db(self, mock_engine_and_session_analyzer, mock_openai):
        """Test reading all job descriptions from the database."""
        mock_engine, mock_session_factory, mock_session = mock_engine_and_session_analyzer
        analyzer = JobAnalyzer(engine=mock_engine, session_factory=mock_session_factory)

        # Mock the return value of session.query(...).all()
        mock_query_result = MagicMock()
        mock_query_result.all.return_value = [MagicMock(description=d[0]) for d in SAMPLE_JOB_DESCRIPTIONS_FROM_DB]
        mock_session.query.return_value = mock_query_result # For query without filter

        descriptions = analyzer.read_job_descriptions()
        
        assert descriptions == EXPECTED_DESCRIPTIONS_LIST
        mock_session.query.assert_called_once_with(JobDetails.description)
        mock_query_result.all.assert_called_once()
        mock_session.close.assert_called_once()

    def test_read_job_descriptions_with_job_ids_from_db(self, mock_engine_and_session_analyzer, mock_openai):
        """Test reading job descriptions for specific job IDs (URLs) from the database."""
        mock_engine, mock_session_factory, mock_session = mock_engine_and_session_analyzer
        analyzer = JobAnalyzer(engine=mock_engine, session_factory=mock_session_factory)
        
        job_ids_to_filter = ["http://example.com/job1", "http://example.com/job2"]
        
        # Mock the return value of session.query(...).filter(...).all()
        mock_filtered_query_result = MagicMock()
        mock_filtered_query_result.all.return_value = [MagicMock(description=d[0]) for d in SAMPLE_JOB_DESCRIPTIONS_FROM_DB] # Simulate it returns something
        mock_session.query.return_value.filter.return_value = mock_filtered_query_result

        descriptions = analyzer.read_job_descriptions(job_ids=job_ids_to_filter)
        
        assert descriptions == EXPECTED_DESCRIPTIONS_LIST
        mock_session.query.assert_called_once_with(JobDetails.description)
        # Check that filter was called, ideally with JobDetails.url.in_(job_ids_to_filter)
        # This requires a bit more advanced mocking for sqlalchemy.Column.in_() if precise check is needed.
        # For now, checking that filter().all() was called is a good step.
        mock_session.query.return_value.filter.assert_called_once()
        mock_filtered_query_result.all.assert_called_once()
        mock_session.close.assert_called_once()

    def test_read_job_descriptions_no_results_from_db(self, mock_engine_and_session_analyzer, mock_openai):
        """Test reading job descriptions from DB when no results are found."""
        mock_engine, mock_session_factory, mock_session = mock_engine_and_session_analyzer
        analyzer = JobAnalyzer(engine=mock_engine, session_factory=mock_session_factory)

        # Mock query(...).all() to return an empty list
        mock_query_result = MagicMock()
        mock_query_result.all.return_value = []
        mock_session.query.return_value = mock_query_result

        descriptions = analyzer.read_job_descriptions()
        
        assert descriptions == []
        mock_session.query.assert_called_once_with(JobDetails.description)
        mock_query_result.all.assert_called_once()
        mock_session.close.assert_called_once()

    def test_read_job_descriptions_db_error(self, mock_engine_and_session_analyzer, mock_openai):
        """Test handling of database error during read_job_descriptions."""
        mock_engine, mock_session_factory, mock_session = mock_engine_and_session_analyzer
        analyzer = JobAnalyzer(engine=mock_engine, session_factory=mock_session_factory)

        mock_session.query.side_effect = Exception("DB Error")

        with patch('click.echo') as mock_click_echo:
            descriptions = analyzer.read_job_descriptions()
        
        assert descriptions == []
        mock_click_echo.assert_any_call("Error reading job descriptions from database: DB Error", err=True)
        mock_session.close.assert_called_once()


    # This test now uses the DB-backed read_job_descriptions.
    # It needs the mock_engine_and_session_analyzer fixture.
    def test_extract_skills(self, mock_engine_and_session_analyzer, mock_openai):
        """Test skill extraction from job descriptions (read from mocked DB)."""
        mock_engine, mock_session_factory, mock_session = mock_engine_and_session_analyzer
        analyzer = JobAnalyzer(engine=mock_engine, session_factory=mock_session_factory)

        # Mock the descriptions returned by read_job_descriptions
        # This implicitly tests that extract_skills works with what read_job_descriptions (DB version) provides.
        with patch.object(analyzer, 'read_job_descriptions', return_value=EXPECTED_DESCRIPTIONS_LIST) as mock_read_desc:
            skills_dict = analyzer.extract_skills(EXPECTED_DESCRIPTIONS_LIST) # Pass descriptions directly
        
        # mock_read_desc.assert_called_once() # Not called if descriptions are passed directly
        assert isinstance(skills_dict, dict)
        assert len(skills_dict) > 0
        # Check for some expected skills based on SAMPLE_JOB_DESCRIPTIONS_FROM_DB
        assert "python" in skills_dict 
        assert "django" in skills_dict
        assert "aws" in skills_dict

    def test_read_resume_txt(self, temp_resume, mock_engine_and_session_analyzer): # Added mock_engine fixture
        """Test reading resume from text file."""
        mock_engine, mock_session_factory, _ = mock_engine_and_session_analyzer
        analyzer = JobAnalyzer(engine=mock_engine, session_factory=mock_session_factory)
        resume_text = analyzer.read_resume(temp_resume)
        
        assert isinstance(resume_text, str)
        assert "PROFESSIONAL SUMMARY" in resume_text
        assert "SKILLS" in resume_text
        assert "Python" in resume_text

    @patch('job_recommender.job_analyzer.PdfReader') # Patch where PdfReader is imported
    def test_read_resume_pdf(self, mock_pdf_reader_constructor, tmp_path, mock_engine_and_session_analyzer):
        """Test reading resume from PDF file."""
        mock_engine, mock_session_factory, _ = mock_engine_and_session_analyzer
        
        # Setup mock for PdfReader instance and its methods
        mock_pdf_instance = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = SAMPLE_RESUME
        mock_pdf_instance.pages = [mock_page]
        mock_pdf_reader_constructor.return_value = mock_pdf_instance # PdfReader(resume_path) returns this
        
        analyzer = JobAnalyzer(engine=mock_engine, session_factory=mock_session_factory)
        resume_path = tmp_path / "test_resume.pdf" # File doesn't need to exist due to mock
        resume_text = analyzer.read_resume(str(resume_path))
        
        assert isinstance(resume_text, str)
        assert "PROFESSIONAL SUMMARY" in resume_text
        assert "SKILLS" in resume_text
        assert "Python" in resume_text

    def test_analyze_resume(self, mock_openai, mock_engine_and_session_analyzer):
        """Test resume analysis against job skills (skills from mocked DB descriptions)."""
        mock_engine, mock_session_factory, _ = mock_engine_and_session_analyzer
        analyzer = JobAnalyzer(engine=mock_engine, session_factory=mock_session_factory)

        # Mock read_job_descriptions to provide consistent input for extract_skills
        with patch.object(analyzer, 'read_job_descriptions', return_value=EXPECTED_DESCRIPTIONS_LIST):
            # Extract skills uses the descriptions passed to it or calls read_job_descriptions.
            # Here, we rely on the fact that analyze_jobs_and_resume calls read_job_descriptions,
            # then extract_skills, then analyze_resume.
            # For a unit test of analyze_resume, we should provide skills_dict directly.
            
            # Let's create a dummy skills_dict for direct testing of analyze_resume
            dummy_skills_dict = analyzer.extract_skills(EXPECTED_DESCRIPTIONS_LIST)
            analysis = analyzer.analyze_resume(SAMPLE_RESUME, dummy_skills_dict)
        
        assert isinstance(analysis, dict)
        assert "matching_skills" in analysis
        assert "missing_skills" in analysis
        assert "recommendations" in analysis
        assert len(analysis["matching_skills"]) > 0
        assert len(analysis["missing_skills"]) > 0
        assert len(analysis["recommendations"]) > 0

    @patch('job_recommender.job_analyzer.JobAnalyzer') # Mock the JobAnalyzer class itself
    def test_analyze_jobs_and_resume_flow(self, MockJobAnalyzer, temp_resume, mock_openai):
        """Test the main helper function analyze_jobs_and_resume flow."""
        mock_analyzer_instance = MockJobAnalyzer.return_value
        mock_analyzer_instance.read_job_descriptions.return_value = EXPECTED_DESCRIPTIONS_LIST
        mock_analyzer_instance.extract_skills.return_value = {"python": 1.0, "aws": 0.8}
        mock_analyzer_instance.read_resume.return_value = SAMPLE_RESUME
        mock_analyzer_instance.analyze_resume.return_value = {
            "matching_skills": ["python"], "missing_skills": ["aws"], "recommendations": ["learn more aws"]
        }

        analyze_jobs_and_resume(
            resume_path=temp_resume,
            max_skills=10,
            model_name="gpt-4",
            job_ids=None # Test with no specific job IDs
        )
        
        MockJobAnalyzer.assert_called_once_with(max_skills=10, model_name="gpt-4")
        mock_analyzer_instance.read_job_descriptions.assert_called_once_with(job_ids=None)
        mock_analyzer_instance.extract_skills.assert_called_once_with(EXPECTED_DESCRIPTIONS_LIST)
        mock_analyzer_instance.read_resume.assert_called_once_with(temp_resume)
        mock_analyzer_instance.analyze_resume.assert_called_once_with(SAMPLE_RESUME, {"python": 1.0, "aws": 0.8})


    def test_error_handling_resume(self, mock_engine_and_session_analyzer, mock_openai, tmp_path):
        """Test error handling for resume processing."""
        mock_engine, mock_session_factory, _ = mock_engine_and_session_analyzer
        analyzer = JobAnalyzer(engine=mock_engine, session_factory=mock_session_factory)
        
        # Test non-existent resume file
        with pytest.raises(FileNotFoundError): # This is raised by open()
            analyzer.read_resume("non_existent_resume.pdf")
        
        # Test OpenAI API error during analyze_resume
        mock_openai.chat.completions.create.side_effect = Exception("API Error")
        with pytest.raises(Exception, match="API Error"):
             analyzer.analyze_resume(SAMPLE_RESUME, {"python": 1.0})


@pytest.mark.integration
@patch('job_recommender.job_analyzer.analyze_jobs_and_resume') # Mock the main worker function
def test_cli_main_invocation(mock_analyze_jobs_and_resume_func, temp_resume):
    """Integration test for the CLI main function invocation."""
    from job_recommender.job_analyzer import main as cli_main_func # Click command object
    from click.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(cli_main_func, [
        '--resume', temp_resume,
        '--max-skills', '15',
        '--model', 'gpt-test',
        '--job-ids', 'url1', 
        '--job-ids', 'url2'
    ])

    assert result.exit_code == 0, f"CLI execution failed: {result.output}"
    mock_analyze_jobs_and_resume_func.assert_called_once_with(
        resume_path=temp_resume,
        max_skills=15,
        model_name='gpt-test',
        job_ids=['url1', 'url2'] # Click passes multiple as tuple, then converted to list in main
    )