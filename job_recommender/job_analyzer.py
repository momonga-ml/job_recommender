import os
import json
import click
from typing import List, Dict
from collections import Counter
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from openai import OpenAI
from dotenv import load_dotenv
from PyPDF2 import PdfReader

# Download required NLTK data
# nltk.download('punkt') # Moved to a function
# nltk.download('stopwords')
# nltk.download('averaged_perceptron_tagger')

def download_nltk_data():
    """Download necessary NLTK data if not already present."""
    # Check and download 'punkt'
    try:
        nltk.data.find('tokenizers/punkt.zip')
    except LookupError: # Handle resource not found
        nltk.download('punkt', quiet=True)
    
    # Check and download 'stopwords'
    try:
        nltk.data.find('corpora/stopwords.zip')
    except LookupError: # Handle resource not found
        nltk.download('stopwords', quiet=True)
        
    # Check and download 'averaged_perceptron_tagger'
    try:
        nltk.data.find('taggers/averaged_perceptron_tagger.zip')
    except LookupError: # Handle resource not found
        nltk.download('averaged_perceptron_tagger', quiet=True)

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
        """Read all job descriptions from a folder."""
        descriptions = []
        for filename in os.listdir(folder_path):
            if filename.endswith('.txt'):
                with open(os.path.join(folder_path, filename), 'r', encoding='utf-8') as f:
                    descriptions.append(f.read())
        return descriptions

    def extract_skills(self, descriptions: List[str]) -> Dict[str, float]:
        """Extract and rank skills from job descriptions using TF-IDF."""
        # Fit and transform the descriptions
        tfidf_matrix = self.vectorizer.fit_transform(descriptions)
        
        # Get feature names (words/phrases)
        feature_names = self.vectorizer.get_feature_names_out()
        
        # Calculate average TF-IDF scores across all documents
        avg_tfidf = tfidf_matrix.mean(axis=0).A1
        
        # Create a dictionary of skills and their scores
        skills_dict = dict(zip(feature_names, avg_tfidf))
        
        # Sort by score in descending order
        return dict(sorted(skills_dict.items(), key=lambda x: x[1], reverse=True))

    def read_resume(self, resume_path: str) -> str:
        """Read resume content from either PDF or text file."""
        if resume_path.lower().endswith('.pdf'):
            reader = PdfReader(resume_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text
        else:
            with open(resume_path, 'r', encoding='utf-8') as f:
                return f.read()

    def analyze_resume(self, resume_text: str, skills_dict: Dict[str, float]) -> Dict:
        """Analyze resume against job skills using OpenAI API."""
        # Prepare the prompt
        skills_list = list(skills_dict.keys())[:self.max_skills]  # Top N skills
        prompt = f"""Analyze this resume against the following required skills for the job:
        
Required Skills: {', '.join(skills_list)}

Resume:
{resume_text}

Please provide a JSON response with the following structure:
{{
    "matching_skills": [list of skills the candidate has],
    "missing_skills": [list of skills the candidate needs to develop],
    "recommendations": [list of specific recommendations for improvement]
}}"""

        # Call OpenAI API
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are a professional career advisor analyzing resumes against job requirements."},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" }
        )

        return json.loads(response.choices[0].message.content)

def format_results_to_markdown(results: dict) -> str:
    """Formats the analysis results into a Markdown string."""
    md_lines = ["# Job Analysis Report"]

    if "error" in results:
        md_lines.append("\n## Errors")
        md_lines.append(f"- {results['error']}")
        return "\n".join(md_lines)

    if "top_skills" in results:
        md_lines.append("\n## Top Required Skills")
        for skill_info in results["top_skills"][:10]: # Display top 10 as per console output
            md_lines.append(f"- {skill_info['skill']}: {skill_info['score']:.2f}")

    if "resume_analysis_error" in results:
        md_lines.append("\n## Resume Analysis")
        md_lines.append(f"- Error: {results['resume_analysis_error']}")
    elif "resume_analysis" in results:
        analysis = results["resume_analysis"]
        md_lines.append("\n## Resume Analysis")

        if "matching_skills" in analysis and analysis["matching_skills"]:
            md_lines.append("\n### Matching Skills")
            for skill in analysis["matching_skills"]:
                md_lines.append(f"- {skill}")
        
        if "missing_skills" in analysis and analysis["missing_skills"]:
            md_lines.append("\n### Missing Skills (Areas for Growth)")
            for skill in analysis["missing_skills"]:
                md_lines.append(f"- {skill}")

        if "recommendations" in analysis and analysis["recommendations"]:
            md_lines.append("\n### Recommendations")
            for rec in analysis["recommendations"]:
                md_lines.append(f"- {rec}")
                
    return "\n".join(md_lines)

def analyze_jobs_and_resume(job_folder: str, resume_path: str, max_skills: int = 20, model_name: str = "gpt-4-turbo-preview", output_file: str = None, output_format: str = None):
    """Main function to analyze jobs and resume."""
    analyzer = JobAnalyzer(max_skills=max_skills, model_name=model_name)
    results = {}

    # Read job descriptions
    descriptions = analyzer.read_job_descriptions(job_folder)
    if not descriptions:
        error_message = f"No job descriptions found in '{job_folder}' folder. Please add .txt files containing job descriptions to that folder."
        results["error"] = error_message
        if output_file:
            # Determine format, default to 'json' if not specified
            actual_format = 'json'
            if output_format:
                actual_format = output_format.lower()
            
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    if actual_format == 'json':
                        json.dump(results, f, indent=4)
                        click.echo(f"Results (error) saved to {output_file} in json format.")
                    elif actual_format == 'md':
                        md_output = format_results_to_markdown(results)
                        f.write(md_output)
                        click.echo(f"Results (error) saved to {output_file} in md format.")
                    else:
                        # This case should ideally not be reached if click.Choice is effective
                        # and output_format is None for default json.
                        # However, as a fallback, we'll write JSON.
                        json.dump(results, f, indent=4)
                        click.echo(f"Results (error) saved to {output_file} in json format (defaulted due to unspecified or unknown format).")
            except IOError as e:
                click.echo(f"Error writing to file {output_file}: {str(e)}", err=True)
        else:
            click.echo(error_message)
        return

    # Extract skills
    skills_dict = analyzer.extract_skills(descriptions)
    results["top_skills"] = [{"skill": skill, "score": float(f"{score:.2f}")} for skill, score in list(skills_dict.items())]

    # Read and analyze resume
    try:
        resume_text = analyzer.read_resume(resume_path)
        analysis = analyzer.analyze_resume(resume_text, skills_dict)
        results["resume_analysis"] = analysis
    except Exception as e:
        error_message = f"Error processing resume: {str(e)}"
        results["resume_analysis_error"] = error_message
        # Decide if we should return or continue to write partial results
        # For now, let's assume we write what we have so far

    # Output logic
    if output_file:
        actual_format = 'json' # Default format
        if output_format:
            actual_format = output_format.lower()

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                if actual_format == 'json':
                    json.dump(results, f, indent=4)
                    click.echo(f"Results saved to {output_file} in json format.")
                elif actual_format == 'md':
                    md_output = format_results_to_markdown(results)
                    f.write(md_output)
                    click.echo(f"Results saved to {output_file} in md format.")
                else:
                    # This case should ideally not be reached due to click.Choice.
                    # If it is, it means output_format was something unexpected.
                    # We'll default to console output by setting output_file to None.
                    click.echo(f"Unsupported output format: {actual_format}. Defaulting to console output.", err=True)
                    output_file = None # Force console output
        except IOError as e:
            click.echo(f"Error writing to file {output_file}: {str(e)}", err=True)
            output_file = None # Force console output on error as well

    if not output_file: # This condition allows fallback or if no output_file was specified initially
        click.echo("\nTop 10 Required Skills:")
        for item in results.get("top_skills", [])[:10]: # Display only top 10 for console
            click.echo(f"- {item['skill']}: {item['score']:.2f}")

        if "resume_analysis_error" in results:
            click.echo(f"\nError in resume analysis: {results['resume_analysis_error']}", err=True)
        elif "resume_analysis" in results:
            analysis_data = results["resume_analysis"]
            click.echo("\nResume Analysis Results:")
            click.echo("\nMatching Skills:")
            for skill in analysis_data.get('matching_skills', []):
                click.echo(f"- {skill}")
            
            click.echo("\nAreas for Growth:")
            for skill in analysis_data.get('missing_skills', []):
                click.echo(f"- {skill}")
            
            click.echo("\nRecommendations:")
            for rec in analysis_data.get('recommendations', []):
                click.echo(f"- {rec}")

@click.command()
@click.option('--job-folder', default='job_descriptions',
              help='Folder containing job description text files')
@click.option('--resume', required=True,
              help='Path to resume file (PDF or TXT)')
@click.option('--max-skills', default=20,
              help='Maximum number of skills to analyze')
@click.option('--model', default='gpt-4-turbo-preview',
              help='OpenAI model to use for analysis')
@click.option('--output-file', '-o', default=None, required=False, type=str,
              help='Path to the output file (e.g., results.json, report.md).')
@click.option('--output-format', '-f', default=None, required=False,
              type=click.Choice(['json', 'md'], case_sensitive=False),
              help='Format for the output file (json or md).')
def main(job_folder: str, resume: str, max_skills: int, model: str, output_file: str, output_format: str):
    """Job Skills Analyzer and Resume Comparator CLI tool."""
    download_nltk_data()  # Ensure NLTK data is available before analysis
    analyze_jobs_and_resume(job_folder, resume, max_skills, model, output_file, output_format)

if __name__ == "__main__":
    main() 