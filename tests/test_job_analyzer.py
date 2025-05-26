import os
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner
from PyPDF2 import PdfReader # Import PdfReader
from job_recommender.job_analyzer import JobAnalyzer, analyze_jobs_and_resume, format_results_to_markdown, main as cli_main

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
    """Mock OpenAI API responses.
    Patches OpenAI where it's imported and used in job_analyzer.py.
    """
    # Patching 'job_recommender.job_analyzer.OpenAI' ensures that when JobAnalyzer
    # (or any code in job_analyzer.py) instantiates OpenAI, it gets this mock.
    with patch('job_recommender.job_analyzer.OpenAI') as mock_openai_class:
        mock_client_instance = MagicMock()
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
        mock_client_instance.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client_instance # OpenAI() call returns this mock_client_instance
        yield mock_openai_class # Yield the patched class mock itself

@pytest.fixture
def runner():
    """Fixture for CliRunner."""
    return CliRunner()

@pytest.fixture
def expected_analysis_results(): # No longer depends on temp_job_descriptions
    """
    Provides a sample of what the 'results' dictionary would look like for successful analysis.
    This needs to be kept in sync with SAMPLE_RESUME and mock_openai response.
    Uses a fixed list for top_skills for predictability.
    """
    # This fixture now returns a completely fixed dictionary. Tests requiring dynamic
    # skill extraction from temp_job_descriptions will need to do that within the test itself
    # or use a separate fixture if JobAnalyzer's direct output is needed.
    # Most tests for output formatting/CLI handling benefit from a predictable input.
    fixed_top_skills = [
        {"skill": "python", "score": 0.85},
        {"skill": "django", "score": 0.70},
        {"skill": "aws", "score": 0.65},
        {"skill": "flask", "score": 0.50},
        {"skill": "react", "score": 0.40},
        {"skill": "software engineer", "score": 0.35},
        {"skill": "developer", "score": 0.30},
        {"skill": "experience", "score": 0.25},
        {"skill": "javascript", "score": 0.20}, # Example, ensure it aligns with mock if used
        {"skill": "apis", "score": 0.15}      # Example
    ]
    return {
        "top_skills": fixed_top_skills,
        "resume_analysis": {
            "matching_skills": ["Python", "Django", "AWS"],
            "missing_skills": ["Kubernetes", "GraphQL"],
            "recommendations": [
                "Learn Kubernetes for container orchestration",
                "Study GraphQL for modern API development"
            ]
        }
    }

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

    def test_read_job_descriptions(self, temp_job_descriptions, mock_openai): # Added mock_openai
        """Test reading job descriptions from files."""
        analyzer = JobAnalyzer() # mock_openai ensures this init is safe
        descriptions = analyzer.read_job_descriptions(temp_job_descriptions)
        
        assert len(descriptions) == 3
        assert all(isinstance(desc, str) for desc in descriptions)
        # Sort descriptions to make assertions order-independent due to os.listdir behavior
        descriptions.sort()
        assert "Full Stack Developer position requiring Python and React skills" in descriptions[0]
        assert "Looking for a Python developer with experience in Django and Flask" in descriptions[1]
        assert "Senior Software Engineer needed with expertise in Python and AWS" in descriptions[2]

    def test_extract_skills(self, temp_job_descriptions, mock_openai): # Added mock_openai
        """Test skill extraction from job descriptions."""
        analyzer = JobAnalyzer() # mock_openai ensures this init is safe
        descriptions = analyzer.read_job_descriptions(temp_job_descriptions)
        skills_dict = analyzer.extract_skills(descriptions)
        
        assert isinstance(skills_dict, dict)
        assert len(skills_dict) > 0
        assert "python" in skills_dict
        assert "django" in skills_dict
        assert "aws" in skills_dict

    def test_read_resume_txt(self, temp_resume, mock_openai): # Added mock_openai
        """Test reading resume from text file."""
        analyzer = JobAnalyzer() # mock_openai ensures this init is safe
        resume_text = analyzer.read_resume(temp_resume)
        
        assert isinstance(resume_text, str)
        assert "PROFESSIONAL SUMMARY" in resume_text
        assert "SKILLS" in resume_text
        assert "Python" in resume_text

    @patch('PyPDF2.PdfReader')
    def test_read_resume_pdf(self, mock_pdf_reader_class, tmp_path, mock_openai):
        """Test reading resume from PDF file."""
        pdf_file_path = tmp_path / "test_resume.pdf"
        # Create a minimal valid PDF structure as a byte string to avoid EOF errors.
        pdf_file_path.write_bytes(b"%PDF-1.0\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF")

        mock_pdf_instance = MagicMock(spec=PdfReader) # Use spec for better mocking
        mock_page = MagicMock()
        mock_page.extract_text.return_value = SAMPLE_RESUME
        mock_pdf_instance.pages = [mock_page]
        mock_pdf_reader_class.return_value = mock_pdf_instance
        
        analyzer = JobAnalyzer()
        resume_text = analyzer.read_resume(str(pdf_file_path))
        
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

    def test_analyze_jobs_and_resume_console_output(self, mock_openai, temp_job_descriptions, temp_resume, capsys):
        """Test the complete analysis process with console output."""
        # This test is modified to check console output via capsys or click.echo mock
        # For now, let's use capsys to capture stdout.
        
        analyze_jobs_and_resume(
            job_folder=temp_job_descriptions,
            resume_path=temp_resume,
            # No output_file or output_format specified
            max_skills=10,
            model_name="gpt-4"
        )
        
        # Verify OpenAI API was called
        mock_openai.return_value.chat.completions.create.assert_called_once()

        # Check console output
        captured = capsys.readouterr()
        assert "Top 10 Required Skills:" in captured.out
        assert "Python" in captured.out # From mock_openai matching skills
        assert "Kubernetes" in captured.out # From mock_openai missing skills
        assert "Learn Kubernetes" in captured.out # From mock_openai recommendations

    # Keep the original test_analyze_jobs_and_resume if it serves a different purpose,
    # or integrate its assertions if they are still relevant.
    # For now, the above test covers console output.
    def test_analyze_jobs_and_resume_api_call(self, mock_openai, temp_job_descriptions, temp_resume):
        """Test that analyze_jobs_and_resume calls the OpenAI API correctly."""
        analyze_jobs_and_resume(
            job_folder=temp_job_descriptions,
            resume_path=temp_resume,
            max_skills=10,
            model_name="gpt-4"
        )
        
        # Verify OpenAI API was called
        mock_openai.return_value.chat.completions.create.assert_called_once()

    # The existing test_error_handling seems to test class methods, not analyze_jobs_and_resume directly.
    # We might need new tests for error handling within analyze_jobs_and_resume,
    # especially concerning file output and API errors when output files are specified.

    def test_analyze_jobs_and_resume_no_job_descriptions(self, mock_openai, tmp_path, temp_resume, capsys):
        """Test behavior when no job description files are found (console output)."""
        empty_job_dir = tmp_path / "empty_job_descriptions"
        empty_job_dir.mkdir()
        
        analyze_jobs_and_resume(
            job_folder=str(empty_job_dir),
            resume_path=temp_resume
        )
        
        captured = capsys.readouterr()
        assert f"No job descriptions found in '{str(empty_job_dir)}' folder." in captured.out
        mock_openai.return_value.chat.completions.create.assert_not_called()

    def test_analyze_jobs_and_resume_no_job_descriptions_file_output(self, mock_openai, tmp_path, temp_resume):
        """Test behavior with no job descriptions and file output specified."""
        empty_job_dir = tmp_path / "empty_job_descriptions_file"
        empty_job_dir.mkdir()
        output_file_path = tmp_path / "error_output.json"

        analyze_jobs_and_resume(
            job_folder=str(empty_job_dir),
            resume_path=temp_resume,
            output_file=str(output_file_path),
            output_format='json'
        )
        
        assert output_file_path.exists()
        with open(output_file_path, 'r') as f:
            content = json.load(f)
        assert "error" in content
        assert f"No job descriptions found in '{str(empty_job_dir)}' folder." in content["error"]
        mock_openai.return_value.chat.completions.create.assert_not_called()

    def test_analyze_jobs_and_resume_resume_processing_error_console(self, mock_openai, temp_job_descriptions, tmp_path, capsys):
        """Test handling of resume processing error with console output."""
        mock_openai.return_value.chat.completions.create.side_effect = Exception("OpenAI API Error")
        
        # Create a dummy resume file
        faulty_resume_path = tmp_path / "faulty_resume.txt"
        faulty_resume_path.write_text("This is a resume, but API will fail.")

        analyze_jobs_and_resume(
            job_folder=temp_job_descriptions,
            resume_path=str(faulty_resume_path)
        )
        captured = capsys.readouterr()
        assert "Error processing resume: OpenAI API Error" in captured.out
        # Check that top skills were still printed
        assert "Top 10 Required Skills:" in captured.out
        assert "Error processing resume: OpenAI API Error" in captured.err # Check stderr for the error message


    def test_analyze_jobs_and_resume_resume_processing_error_file_output(self, mock_openai, temp_job_descriptions, tmp_path):
        """Test handling of resume processing error with file output."""
        mock_openai.return_value.chat.completions.create.side_effect = Exception("OpenAI API Error")
        
        faulty_resume_path = tmp_path / "faulty_resume_for_file.txt"
        faulty_resume_path.write_text("This is a resume, but API will fail for file output.")
        output_file_path = tmp_path / "resume_error_output.json"

        analyze_jobs_and_resume(
            job_folder=temp_job_descriptions,
            resume_path=str(faulty_resume_path),
            output_file=str(output_file_path),
            output_format='json'
        )

        assert output_file_path.exists()
        with open(output_file_path, 'r') as f:
            content = json.load(f)
        
        assert "top_skills" in content # Skills should still be there
        assert "resume_analysis_error" in content
        assert "Error processing resume: OpenAI API Error" in content["resume_analysis_error"]


# Tests for CLI using CliRunner
class TestCli:
    # Tests for CLI option parsing (mocking out the main analysis function)
    # These do not need mock_openai as analyze_jobs_and_resume is mocked.
    @patch('job_recommender.job_analyzer.analyze_jobs_and_resume')
    def test_cli_default_options(self, mock_analyze_func, runner, temp_job_descriptions, temp_resume):
        result = runner.invoke(cli_main, ['--resume', temp_resume, '--job-folder', temp_job_descriptions])
        assert result.exit_code == 0
        # Click invokes `main` which then calls `analyze_jobs_and_resume`.
        # `main` calls `analyze_jobs_and_resume` with positional arguments for those in its signature.
        mock_analyze_func.assert_called_once_with(
            temp_job_descriptions,    # job_folder
            temp_resume,              # resume
            20,                       # max_skills (default)
            'gpt-4-turbo-preview',    # model (default)
            None,                     # output_file (default)
            None                      # output_format (default)
        )

    @patch('job_recommender.job_analyzer.analyze_jobs_and_resume')
    def test_cli_with_output_options_json(self, mock_analyze_func, runner, temp_job_descriptions, temp_resume, tmp_path):
        output_file = str(tmp_path / "cli_output.json")
        result = runner.invoke(cli_main, [
            '--resume', temp_resume,
            '--job-folder', temp_job_descriptions,
            '--output-file', output_file,
            '--output-format', 'json'
        ])
        assert result.exit_code == 0
        mock_analyze_func.assert_called_once_with(
            temp_job_descriptions,
            temp_resume,
            20,
            'gpt-4-turbo-preview',
            output_file,
            'json'
        )

    @patch('job_recommender.job_analyzer.analyze_jobs_and_resume')
    def test_cli_with_output_options_md(self, mock_analyze_func, runner, temp_job_descriptions, temp_resume, tmp_path):
        output_file = str(tmp_path / "cli_output.md")
        result = runner.invoke(cli_main, [
            '--resume', temp_resume,
            '--job-folder', temp_job_descriptions,
            '--output-file', output_file,
            '--output-format', 'md'
        ])
        assert result.exit_code == 0
        mock_analyze_func.assert_called_once_with(
            temp_job_descriptions,
            temp_resume,
            20,
            'gpt-4-turbo-preview',
            output_file,
            'md'
        )
    
    @patch('job_recommender.job_analyzer.analyze_jobs_and_resume')
    def test_cli_output_file_no_format(self, mock_analyze_func, runner, temp_job_descriptions, temp_resume, tmp_path):
        output_file = str(tmp_path / "cli_output_default.json")
        result = runner.invoke(cli_main, [
            '--resume', temp_resume,
            '--job-folder', temp_job_descriptions,
            '--output-file', output_file
        ])
        assert result.exit_code == 0
        mock_analyze_func.assert_called_once_with(
            temp_job_descriptions,
            temp_resume,
            20,
            'gpt-4-turbo-preview',
            output_file,
            None 
        )

    # Tests for actual CLI output generation (these need mock_openai)
    def test_cli_json_output_generation(self, mock_openai, runner, temp_job_descriptions, temp_resume, tmp_path, expected_analysis_results):
        """Test actual JSON file generation via CLI."""
        output_file_path = tmp_path / "cli_generated.json"
        # mock_openai is passed here, so it's active during cli_main -> analyze_jobs_and_resume
        result = runner.invoke(cli_main, [
            '--resume', temp_resume,
            '--job-folder', temp_job_descriptions,
            '--output-file', str(output_file_path),
            '--output-format', 'json'
        ])
        assert result.exit_code == 0
        assert output_file_path.exists()
        with open(output_file_path, 'r') as f:
            content = json.load(f)
        
        # Compare relevant parts of the content with expected_analysis_results
        # Note: top_skills in expected_analysis_results is fixed, actual one might vary slightly due to TF-IDF.
        # For robust testing, we might need to mock extract_skills or check structure/presence of keys.
        assert "top_skills" in content
        assert isinstance(content["top_skills"], list)
        if content["top_skills"]: # If skills were extracted
             assert "skill" in content["top_skills"][0]
             assert "score" in content["top_skills"][0]

        assert "resume_analysis" in content
        assert content["resume_analysis"]["matching_skills"] == expected_analysis_results["resume_analysis"]["matching_skills"]
        assert content["resume_analysis"]["missing_skills"] == expected_analysis_results["resume_analysis"]["missing_skills"]
        assert content["resume_analysis"]["recommendations"] == expected_analysis_results["resume_analysis"]["recommendations"]
        assert f"Results saved to {str(output_file_path)} in json format." in result.output


    def test_cli_md_output_generation(self, mock_openai, runner, temp_job_descriptions, temp_resume, tmp_path, expected_analysis_results):
        """Test actual Markdown file generation via CLI."""
        output_file_path = tmp_path / "cli_generated.md"
        result = runner.invoke(cli_main, [
            '--resume', temp_resume,
            '--job-folder', temp_job_descriptions,
            '--output-file', str(output_file_path),
            '--output-format', 'md'
        ])
        assert result.exit_code == 0
        assert output_file_path.exists()
        
        md_content = output_file_path.read_text()
        
        # Generate expected Markdown to compare
        # We need to mock extract_skills in analyze_jobs_and_resume for fully predictable results
        # or use a fixed result set for format_results_to_markdown.
        # For now, let's use expected_analysis_results.
        # The `top_skills` in `expected_analysis_results` is fixed.
        # The actual `top_skills` generated by `analyze_jobs_and_resume` might differ slightly
        # due to the live `extract_skills` call.
        # To make this test more robust, we would ideally mock `extract_skills` when calling `cli_main`
        # or ensure `expected_analysis_results` precisely matches.
        
        # For now, check for key markdown elements and content from resume_analysis
        assert "# Job Analysis Report" in md_content
        assert "## Top Required Skills" in md_content
        
        # Check for some skills from expected_analysis_results (assuming they'd be in top 10)
        # Only check for skill name, not score, due to dynamic TF-IDF scores in live run
        for skill_item in expected_analysis_results["top_skills"][:3]: # Check first few
            assert f"- {skill_item['skill']}:" in md_content # Removed score check

        assert "## Resume Analysis" in md_content
        assert "### Matching Skills" in md_content
        for skill in expected_analysis_results["resume_analysis"]["matching_skills"]:
            assert f"- {skill}" in md_content
        assert "### Missing Skills (Areas for Growth)" in md_content
        for skill in expected_analysis_results["resume_analysis"]["missing_skills"]:
            assert f"- {skill}" in md_content
        assert "### Recommendations" in md_content
        for rec in expected_analysis_results["resume_analysis"]["recommendations"]:
            assert f"- {rec}" in md_content
        assert f"Results saved to {str(output_file_path)} in md format." in result.output


    def test_cli_default_to_json_output(self, mock_openai, runner, temp_job_descriptions, temp_resume, tmp_path, expected_analysis_results):
        """Test CLI defaults to JSON when only output file is specified."""
        output_file_path = tmp_path / "cli_default_generated.json"
        result = runner.invoke(cli_main, [
            '--resume', temp_resume,
            '--job-folder', temp_job_descriptions,
            '--output-file', str(output_file_path)
            # No --output-format
        ])
        assert result.exit_code == 0
        assert output_file_path.exists()
        with open(output_file_path, 'r') as f:
            content = json.load(f)
        
        assert "resume_analysis" in content
        assert content["resume_analysis"]["matching_skills"] == expected_analysis_results["resume_analysis"]["matching_skills"]
        assert f"Results saved to {str(output_file_path)} in json format." in result.output # main code defaults to json

    def test_cli_console_output(self, mock_openai, runner, temp_job_descriptions, temp_resume, expected_analysis_results):
        """Test console output when no output file is specified using CLI."""
        result = runner.invoke(cli_main, [
            '--resume', temp_resume,
            '--job-folder', temp_job_descriptions
        ])
        assert result.exit_code == 0
        
        # Check console output
        assert "Top 10 Required Skills:" in result.output
        # Check for a few skills (assuming they are in the top 10 of the dynamic list)
        # This part is tricky without mocking extract_skills within the CLI call.
        # For now, we'll check for the section headers and resume analysis parts.
        
        assert "Resume Analysis Results:" in result.output
        assert "Matching Skills:" in result.output
        for skill in expected_analysis_results["resume_analysis"]["matching_skills"]:
            assert f"- {skill}" in result.output
        assert "Areas for Growth:" in result.output
        for skill in expected_analysis_results["resume_analysis"]["missing_skills"]:
            assert f"- {skill}" in result.output
        assert "Recommendations:" in result.output
        for rec in expected_analysis_results["resume_analysis"]["recommendations"]:
            assert f"- {rec}" in result.output

    # Test error handling for file output (e.g., invalid path)
    # This is hard to test reliably for permissions.
    # We can test what happens if an invalid format is somehow passed to analyze_jobs_and_resume
    # (though Click layer should prevent this for `main`).

    @patch('job_recommender.job_analyzer.click.echo') 
    def test_cli_invalid_output_format_message(self, mock_cli_echo, mock_openai, runner, temp_job_descriptions, temp_resume, tmp_path): # Added mock_openai
        """Test analyze_jobs_and_resume fallback with an invalid output format.
           Note: click.Choice in main() should prevent this via CLI, so testing analyze_jobs_and_resume directly.
        """
        output_file = str(tmp_path / "cli_invalid_format.txt")
        
        # We are testing analyze_jobs_and_resume's direct behavior here.
        # The mock_openai fixture will be active due to being a test parameter.
        analyze_jobs_and_resume(
            job_folder=temp_job_descriptions,
            resume_path=temp_resume,
            output_file=output_file,
            output_format="invalid_format_type", # Not 'json' or 'md'
            # Ensure all args for JobAnalyzer are passed if not relying on defaults,
            # or ensure mock_openai is used for its instantiation.
            # model_name="gpt-4-turbo-preview" # Already default in analyze_jobs_and_resume
        )
        
        # Check that an error message about unsupported format was printed by analyze_jobs_and_resume
        # (which uses click.echo internally)
        
        printed_messages = [call_args[0][0] for call_args in mock_cli_echo.call_args_list]
        
        # Check for the warning message
        assert any("Unsupported output format: invalid_format_type" in msg for msg in printed_messages)
        
        # Check if it fell back to console output.
        # This depends on whether other errors (like OpenAI auth) occurred.
        # If mock_openai is effective, resume analysis should proceed with mocked data.
        if mock_openai.return_value.chat.completions.create.side_effect is None:
             assert any("Top 10 Required Skills:" in msg for msg in printed_messages)
        else: # If OpenAI call was mocked to raise an error
             assert any("Error processing resume:" in msg for msg in printed_messages)

        # File should not be created if format is invalid and it fell back to console,
        # assuming no prior error caused an error file write.
        # The modified job_analyzer.py should prevent file write on invalid format.
        assert not os.path.exists(output_file), "File should not be created with invalid format if fallback to console occurs."


# Direct function call tests for analyze_jobs_and_resume output generation
# These tests use mock_openai passed as a fixture, so JobAnalyzer instantiation within
# analyze_jobs_and_resume should use the mock correctly.
class TestAnalyzeJobsAndResumeOutput:

    def test_json_output_generation_direct(self, mock_openai, temp_job_descriptions, temp_resume, tmp_path, expected_analysis_results):
        output_file_path = tmp_path / "direct_generated.json"
        
        analyze_jobs_and_resume(
            job_folder=temp_job_descriptions,
            resume_path=temp_resume,
            output_file=str(output_file_path),
            output_format='json',
            # Use fixed skills for this test by mocking extract_skills if needed, or accept variability
        )
        
        assert output_file_path.exists()
        with open(output_file_path, 'r') as f:
            content = json.load(f)

        assert "top_skills" in content # Check structure
        assert "resume_analysis" in content
        assert content["resume_analysis"]["matching_skills"] == expected_analysis_results["resume_analysis"]["matching_skills"]
        # Add more assertions for top_skills if its generation can be made predictable for tests

    def test_md_output_generation_direct(self, mock_openai, temp_job_descriptions, temp_resume, tmp_path, expected_analysis_results):
        output_file_path = tmp_path / "direct_generated.md"
        
        # For a fully predictable MD, we'd need results['top_skills'] to be predictable.
        # This means either mocking analyzer.extract_skills within analyze_jobs_and_resume,
        # or accepting that this part of the MD content will be dynamic.
        # We will use expected_analysis_results for the comparison of resume_analysis part.

        analyze_jobs_and_resume(
            job_folder=temp_job_descriptions,
            resume_path=temp_resume,
            output_file=str(output_file_path),
            output_format='md'
        )
        
        assert output_file_path.exists()
        md_content = output_file_path.read_text()
        
        # Create a results dict that `format_results_to_markdown` would use.
        # This needs to be as close as possible to what analyze_jobs_and_resume would generate.
        # The challenge is results["top_skills"] which is dynamic.
        # For now, we check structure and the resume_analysis part.
        
        # Reconstruct a plausible results dictionary for format_results_to_markdown
        # This is tricky because extract_skills is called inside.
        # A simpler approach for MD is to check for key phrases and structure.
        assert "# Job Analysis Report" in md_content
        assert "## Top Required Skills" in md_content
        # Cannot easily assert specific skills here without more mocking.
        
        assert "## Resume Analysis" in md_content
        assert "### Matching Skills" in md_content
        for skill in expected_analysis_results["resume_analysis"]["matching_skills"]:
            assert f"- {skill}" in md_content
        # ... and so on for missing_skills and recommendations

    def test_default_to_json_output_direct(self, mock_openai, temp_job_descriptions, temp_resume, tmp_path, expected_analysis_results):
        output_file_path = tmp_path / "direct_default_generated.json"
        
        analyze_jobs_and_resume(
            job_folder=temp_job_descriptions,
            resume_path=temp_resume,
            output_file=str(output_file_path),
            output_format=None # Explicitly None
        )
        
        assert output_file_path.exists()
        with open(output_file_path, 'r') as f:
            content = json.load(f)
        assert "resume_analysis" in content
        assert content["resume_analysis"]["matching_skills"] == expected_analysis_results["resume_analysis"]["matching_skills"]

    @patch('job_recommender.job_analyzer.click.echo')
    def test_console_output_direct(self, mock_echo, mock_openai, temp_job_descriptions, temp_resume, expected_analysis_results):
        analyze_jobs_and_resume(
            job_folder=temp_job_descriptions,
            resume_path=temp_resume
            # No output_file or output_format
        )
        
        # Verify click.echo was called with expected content
        # This is more precise than capsys for direct calls if click.echo is used consistently.
        output_accumulator = ""
        for call_args in mock_echo.call_args_list:
            output_accumulator += call_args[0][0] + "\n" # click.echo usually adds a newline

        assert "Top 10 Required Skills:" in output_accumulator
        assert "Resume Analysis Results:" in output_accumulator
        assert "Matching Skills:" in output_accumulator
        for skill in expected_analysis_results["resume_analysis"]["matching_skills"]:
            assert f"- {skill}" in output_accumulator


# The old integration test test_full_analysis_process might be redundant now
# or could be adapted. The new CLI tests are more specific.
# For now, I'll comment out the old one if it's fully covered.
# The test_error_handling also needs review as it tests class methods, not the main flow.

# Commenting out the old test_full_analysis_process as it's covered by new CLI tests
# @pytest.mark.integration
# def test_full_analysis_process(mock_openai, temp_job_descriptions, temp_resume):
#     """Integration test for the complete analysis process."""
# ... (original content) ...

# The test_error_handling tests specific methods of JobAnalyzer, not analyze_jobs_and_resume flow.
# We've added specific error handling tests for analyze_jobs_and_resume like
# test_analyze_jobs_and_resume_no_job_descriptions and test_analyze_jobs_and_resume_resume_processing_error
# These should be sufficient for that function's error paths.
# The original test_error_handling can remain for unit testing the class methods.