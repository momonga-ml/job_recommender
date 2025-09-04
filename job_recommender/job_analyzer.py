import os
import json
import time
import click
from typing import List, Dict, Optional, Tuple
from collections import Counter
from enum import Enum
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from openai import OpenAI, OpenAIError
from dotenv import load_dotenv
from pathlib import Path
import pypdf

# Import rich utilities
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table

# Output format options
class OutputFormat(str, Enum):
    CONSOLE = "console"
    JSON = "json"
    TEXT = "text"
    CSV = "csv"

# Initialize console
console = Console()

# Import rich utilities instead of redefining them
from .rich_utils import (
    print_success,
    print_warning, 
    print_error,
    print_info,
    print_step
)

def format_duration(seconds: float) -> str:
    """Format duration in seconds to a human-readable string."""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    else:
        minutes = int(seconds // 60)
        seconds = seconds % 60
        return f"{minutes}m {seconds:.0f}s"

# Download required NLTK data
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('averaged_perceptron_tagger', quiet=True)
except Exception as e:
    print_warning(f"NLTK data download warning: {str(e)}")
    print_info("Some NLTK features might not work as expected")

class JobAnalyzer:
    def __init__(self, max_skills: int = 20, model_name: str = "gpt-4-turbo-preview"):
        load_dotenv()
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.stop_words = set(stopwords.words('english'))
        self.vectorizer = TfidfVectorizer(
            max_features=100,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.max_skills = max_skills
        self.model_name = model_name

    def read_job_descriptions(self, folder_path: str) -> List[str]:
        """Read all job descriptions from a folder with progress feedback."""
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"Job descriptions folder not found: {folder_path}")
            
        txt_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.txt')]
        if not txt_files:
            raise FileNotFoundError(f"No .txt files found in folder: {folder_path}")
            
        descriptions = []
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Reading job descriptions...", total=len(txt_files))
            
            for filename in txt_files:
                try:
                    with open(os.path.join(folder_path, filename), 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:  # Only add non-empty files
                            descriptions.append(content)
                        else:
                            print_warning(f"Empty file skipped: {filename}")
                except Exception as e:
                    print_warning(f"Error reading {filename}: {str(e)}")
                finally:
                    progress.update(task, advance=1, refresh=True)
                    
        if not descriptions:
            raise ValueError("No valid job description content found in the provided files")
            
        print_success(f"Successfully read {len(descriptions)} job description(s)")
        return descriptions

    def extract_skills(self, descriptions: List[str]) -> Dict[str, float]:
        """Extract and rank skills from job descriptions using TF-IDF with progress feedback."""
        if not descriptions:
            raise ValueError("No job descriptions provided for skill extraction")
            
        print_step("Analyzing job descriptions to extract key skills...")
        start_time = time.time()
        
        try:
            # Fit and transform the descriptions
            with console.status("[cyan]Processing text with TF-IDF...") as status:
                tfidf_matrix = self.vectorizer.fit_transform(descriptions)
                
                # Get feature names (words/phrases)
                feature_names = self.vectorizer.get_feature_names_out()
                
                # Calculate average TF-IDF scores across all documents
                avg_tfidf = tfidf_matrix.mean(axis=0).A1
                
                # Create a dictionary of skills and their scores
                skills_dict = dict(zip(feature_names, avg_tfidf))
                
                # Sort by score in descending order
                sorted_skills = dict(sorted(skills_dict.items(), key=lambda x: x[1], reverse=True))
                
                duration = time.time() - start_time
                print_success(f"Extracted {len(sorted_skills)} skills in {format_duration(duration)}")
                
                # Show top skills
                if sorted_skills:
                    top_skills = list(sorted_skills.items())[:10]
                    table = Table(title="Top 10 Required Skills", show_header=True, header_style="bold magenta")
                    table.add_column("Skill", style="cyan")
                    table.add_column("TF-IDF Score", justify="right", style="green")
                    
                    for skill, score in top_skills:
                        table.add_row(skill, f"{score:.4f}")
                    
                    console.print(table)
                
                return sorted_skills
                
        except Exception as e:
            print_error("Error during skill extraction", str(e))
            raise

    def read_resume(self, resume_path: str) -> str:
        """Read resume content from either PDF or text file with progress feedback."""
        if not os.path.exists(resume_path):
            raise FileNotFoundError(f"Resume file not found: {resume_path}")
            
        print_step(f"Reading resume: {os.path.basename(resume_path)}")
        start_time = time.time()
        
        try:
            if resume_path.lower().endswith('.pdf'):
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                    transient=True
                ) as progress:
                    task = progress.add_task("[cyan]Extracting text from PDF...", total=None)
                    try:
                        with pypdf.PdfReader(resume_path) as reader:
                            text_parts = []
                            
                            for i, page in enumerate(reader.pages, 1):
                                page_text = page.extract_text() or ""
                                text_parts.append(page_text)
                                progress.update(task, description=f"[cyan]Extracted page {i}...")
                                
                            text = "\n".join(text_parts).strip()
                            if not text:
                                raise ValueError("No text could be extracted from the PDF")
                                
                            duration = time.time() - start_time
                            print_success(f"Extracted {len(text):,} characters from PDF in {format_duration(duration)}")
                            return text
                            
                    except Exception as e:
                        raise ValueError(f"Error reading PDF: {str(e)}") from e
                        
            else:  # Text file
                try:
                    with open(resume_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if not content:
                            raise ValueError("Resume file is empty")
                            
                        duration = time.time() - start_time
                        print_success(f"Read {len(content):,} characters from text file in {format_duration(duration)}")
                        return content
                        
                except UnicodeDecodeError:
                    raise ValueError("Could not read file as text (not UTF-8 encoded)")
                    
        except Exception as e:
            print_error(f"Failed to read resume: {str(e)}")
            raise

    def analyze_resume(self, resume_text: str, skills_dict: Dict[str, float]) -> Dict:
        """Analyze resume against job skills using OpenAI API with progress feedback."""
        if not resume_text.strip():
            raise ValueError("Resume text is empty")
            
        if not skills_dict:
            raise ValueError("No skills provided for analysis")
            
        print_step("Analyzing resume against job requirements...")
        start_time = time.time()
        
        # Prepare the prompt
        skills_list = list(skills_dict.keys())[:self.max_skills]  # Top N skills
        
        # Format the prompt for better readability in the console
        formatted_skills = "\n".join(f"- {skill}" for skill in skills_list)
        
        prompt = f"""# Resume Analysis Task

## Required Skills:
{formatted_skills}

## Resume Content:
{resume_text[:10000]}... [content truncated for display]

## Instructions:
Please analyze this resume against the required skills and provide a JSON response with:
1. matching_skills: List of skills the candidate demonstrates
2. missing_skills: List of important skills the candidate is missing
3. recommendations: Specific, actionable advice for improvement

Be concise but thorough in your analysis."""

        console.print(Panel(
            "Sending request to OpenAI API...",
            title="[bold blue]Analysis in Progress[/bold blue]",
            border_style="blue"
        ))
        
        try:
            with console.status(
                "[cyan]Analyzing with AI (this may take a minute)...",
                spinner="dots"
            ) as status:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": """You are a professional career advisor with expertise in resume analysis and job market trends. 
                            Provide specific, actionable feedback that helps candidates improve their resumes and better match job requirements."""
                        },
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.3,
                    max_tokens=1500
                )
                
                # Parse the response
                try:
                    result = json.loads(response.choices[0].message.content)
                    
                    # Validate the response structure
                    required_keys = {"matching_skills", "missing_skills", "recommendations"}
                    if not all(key in result for key in required_keys):
                        raise ValueError("Unexpected response format from API")
                        
                    duration = time.time() - start_time
                    print_success(f"Analysis completed in {format_duration(duration)}")
                    
                    return result
                    
                except json.JSONDecodeError as e:
                    print_error("Failed to parse API response")
                    print_info(f"Raw response: {response.choices[0].message.content}")
                    raise ValueError("Invalid JSON response from API") from e
                    
        except OpenAIError as e:
            error_msg = str(e)
            if "rate limit" in error_msg.lower():
                error_msg += "\n\nTip: You may need to wait before making more requests or check your API quota."
            print_error("OpenAI API Error", error_msg)
            raise
            
        except Exception as e:
            print_error("Analysis failed", str(e))
            raise

def format_analysis_results(analysis: Dict, output_format: OutputFormat = OutputFormat.CONSOLE) -> str:
    """Format analysis results based on the specified output format."""
    if output_format == OutputFormat.JSON:
        return json.dumps(analysis, indent=2)
        
    elif output_format == OutputFormat.CSV:
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(["Category", "Item"])
        
        # Write matching skills
        for skill in analysis.get('matching_skills', []):
            writer.writerow(["Matching Skill", f'"{skill}"'])
            
        # Write missing skills
        for skill in analysis.get('missing_skills', []):
            writer.writerow(["Missing Skill", f'"{skill}"'])
            
        # Write recommendations
        for rec in analysis.get('recommendations', []):
            writer.writerow(["Recommendation", f'"{rec}"'])
            
        return output.getvalue()
        
    elif output_format == OutputFormat.TEXT:
        lines = [
            "=" * 80,
            "RESUME ANALYSIS REPORT".center(80),
            "=" * 80,
            "\nMATCHING SKILLS:",
            "-" * 80
        ]
        
        if analysis.get('matching_skills'):
            lines.extend(f"• {skill}" for skill in analysis['matching_skills'])
        else:
            lines.append("No matching skills found.")
            
        lines.extend([
            "\nAREAS FOR GROWTH:",
            "-" * 80
        ])
        
        if analysis.get('missing_skills'):
            lines.extend(f"• {skill}" for skill in analysis['missing_skills'])
        else:
            lines.append("No specific areas for growth identified.")
            
        lines.extend([
            "\nRECOMMENDATIONS:",
            "-" * 80
        ])
        
        if analysis.get('recommendations'):
            for i, rec in enumerate(analysis['recommendations'], 1):
                lines.append(f"{i}. {rec}")
        else:
            lines.append("No specific recommendations available.")
            
        return "\n".join(lines)
        
    else:  # CONSOLE (default)
        # Create a rich panel for the results
        from rich.panel import Panel
        from rich.text import Text
        
        # Create sections with appropriate styling
        sections = []
        
        # Matching Skills
        matching_text = Text()
        if analysis.get('matching_skills'):
            for skill in analysis['matching_skills']:
                matching_text.append("• ", style="green")
                matching_text.append(f"{skill}\n", style="green")
        else:
            matching_text.append("No matching skills found.", style="italic")
            
        sections.append(("✅ MATCHING SKILLS", matching_text))
        
        # Missing Skills
        missing_text = Text()
        if analysis.get('missing_skills'):
            for skill in analysis['missing_skills']:
                missing_text.append("• ", style="yellow")
                missing_text.append(f"{skill}\n", style="yellow")
        else:
            missing_text.append("No specific areas for growth identified.", style="italic")
            
        sections.append(("⚠ AREAS FOR GROWTH", missing_text))
        
        # Recommendations
        rec_text = Text()
        if analysis.get('recommendations'):
            for i, rec in enumerate(analysis['recommendations'], 1):
                rec_text.append(f"{i}. ", style="cyan")
                rec_text.append(f"{rec}\n")
        else:
            rec_text.append("No specific recommendations available.", style="italic")
            
        sections.append(("💡 RECOMMENDATIONS", rec_text))
        
        # Create the final panel with all sections
        final_panel = "\n\n".join(
            f"[bold]{title}[/bold]\n{text}" 
            for title, text in sections
        )
        
        return Panel(
            final_panel,
            title="[bold blue]RESUME ANALYSIS REPORT[/bold blue]",
            border_style="blue",
            expand=False
        )

def analyze_jobs_and_resume(
    job_folder: str, 
    resume_path: str, 
    max_skills: int = 20, 
    model_name: str = "gpt-4-turbo-preview",
    output_format: OutputFormat = OutputFormat.CONSOLE,
    output_file: str = None
) -> None:
    """
    Main function to analyze jobs and resume with rich feedback and multiple output options.
    
    Args:
        job_folder: Path to folder containing job description text files
        resume_path: Path to the resume file (PDF or TXT)
        max_skills: Maximum number of skills to analyze
        model_name: Name of the OpenAI model to use
        output_format: Format for the analysis results
        output_file: Optional file path to save the results
    """
    console.print(Panel.fit(
        "[bold blue]Job Skills Analyzer and Resume Comparator[/bold blue]",
        border_style="blue"
    ))
    
    start_time = time.time()
    analyzer = None
    
    try:
        # Initialize the analyzer
        with console.status("[cyan]Initializing analyzer...") as status:
            analyzer = JobAnalyzer(max_skills=max_skills, model_name=model_name)
            print_success(f"Initialized analyzer with model: {model_name}")
        
        # Read and process job descriptions
        with console.status("[cyan]Processing job descriptions...") as status:
            try:
                descriptions = analyzer.read_job_descriptions(job_folder)
                print_success(f"Processed {len(descriptions)} job description(s) from '{job_folder}'")
                
                # Extract and analyze skills
                skills_dict = analyzer.extract_skills(descriptions)
                
            except Exception as e:
                print_error("Failed to process job descriptions", str(e))
                raise
        
        # Read and analyze resume
        with console.status("[cyan]Analyzing resume...") as status:
            try:
                resume_text = analyzer.read_resume(resume_path)
                print_success(f"Analyzing resume: {os.path.basename(resume_path)}")
                
                # Perform the analysis
                analysis = analyzer.analyze_resume(resume_text, skills_dict)
                
                # Format the results
                results = format_analysis_results(analysis, output_format)
                
                # Display or save results
                if output_file:
                    try:
                        with open(output_file, 'w', encoding='utf-8') as f:
                            f.write(str(results) if not isinstance(results, str) else results)
                        print_success(f"Results saved to: {output_file}")
                    except Exception as e:
                        print_error(f"Failed to save results to {output_file}", str(e))
                        raise
                
                # Print to console if not saving to file or if output format is CONSOLE
                if not output_file or output_format == OutputFormat.CONSOLE:
                    console.print(results)
                
                duration = time.time() - start_time
                print_success(f"Analysis completed in {format_duration(duration)}")
                
            except Exception as e:
                print_error("Resume analysis failed", str(e))
                raise
                
    except Exception as e:
        print_error("Analysis failed", str(e))
        raise
    finally:
        # Clean up resources if needed
        if analyzer:
            pass  # Add any cleanup code here if needed

@click.command()
@click.argument('resume', type=click.Path(exists=True, dir_okay=False, resolve_path=True))
@click.option('--job-folder', 
              default='job_descriptions',
              type=click.Path(exists=True, file_okay=False, resolve_path=True),
              help='Folder containing job description text files (default: job_descriptions)')
@click.option('--max-skills', 
              default=20,
              type=click.IntRange(5, 50),
              help='Maximum number of skills to analyze (5-50, default: 20)')
@click.option('--model', 
              default='gpt-4-turbo-preview',
              help='OpenAI model to use for analysis (default: gpt-4-turbo-preview)')
@click.option('--format',
              'output_format',
              type=click.Choice([f.value for f in OutputFormat], case_sensitive=False),
              default=OutputFormat.CONSOLE.value,
              help='Output format: console (default), json, text, or csv')
@click.option('--output',
              'output_file',
              type=click.Path(dir_okay=False, writable=True, resolve_path=True),
              help='Save results to file (path)')
@click.option('--verbose', '-v',
              is_flag=True,
              help='Enable verbose output')
@click.version_option(version='1.0.0')
def main(
    resume: str,
    job_folder: str,
    max_skills: int,
    model: str,
    output_format: str,
    output_file: str,
    verbose: bool
) -> None:
    """
    Job Skills Analyzer and Resume Comparator
    
    Analyzes job descriptions and compares them against a resume to identify
    matching skills, areas for improvement, and personalized recommendations.
    
    RESUME: Path to your resume file (PDF or TXT)
    """
    # Set logging level based on verbosity
    from .logging_config import setup_logging
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(log_level=log_level, log_to_console=False)  # Rich handles console output
    
    # Convert output format string to enum
    output_format_enum = OutputFormat(output_format.lower())
    
    try:
        analyze_jobs_and_resume(
            job_folder=job_folder,
            resume_path=resume,
            max_skills=max_skills,
            model_name=model,
            output_format=output_format_enum,
            output_file=output_file
        )
    except Exception as e:
        if verbose:
            import traceback
            console.print_exception(show_locals=True)
        else:
            print_error("An error occurred. Use --verbose for detailed error information.")
        raise SystemExit(1) from e

if __name__ == "__main__":
    main() 