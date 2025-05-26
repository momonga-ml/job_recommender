import os
import json
import click
from typing import List, Dict, Optional # Added Optional
from collections import Counter
import nltk

from sqlalchemy.orm import sessionmaker
from .db_schema import JobDetails
from .db_utils import create_db_engine
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from openai import OpenAI
from dotenv import load_dotenv
from PyPDF2 import PdfReader

# Download required NLTK data
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('averaged_perceptron_tagger')

class JobAnalyzer:
    def __init__(self, max_skills: int = 20, model_name: str = "gpt-4-turbo-preview", engine=None):
        load_dotenv()
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.engine = engine or create_db_engine()
        self.Session = sessionmaker(bind=self.engine)
        self.stop_words = set(stopwords.words('english'))
        self.vectorizer = TfidfVectorizer(
            max_features=100,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.max_skills = max_skills
        self.model_name = model_name

    def read_job_descriptions(self, job_ids: Optional[List[str]] = None) -> List[str]:
        """Read job descriptions from the database."""
        session = self.Session()
        descriptions = []
        try:
            query = session.query(JobDetails.description)
            if job_ids:
                # Assuming job_ids are URLs for now, as per typical usage context
                # If they are primary keys (JobDetails.job_id), this filter needs adjustment.
                query = query.filter(JobDetails.url.in_(job_ids))
            
            results = query.all()
            descriptions = [row.description for row in results if row.description] # Ensure description is not None
            if not descriptions:
                click.echo("No job descriptions found in the database matching the criteria.", err=True)
        except Exception as e:
            click.echo(f"Error reading job descriptions from database: {e}", err=True)
        finally:
            session.close()
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

def analyze_jobs_and_resume(resume_path: str, max_skills: int = 20, model_name: str = "gpt-4-turbo-preview", job_ids: Optional[List[str]] = None):
    """Main function to analyze jobs and resume."""
    # Initialize the analyzer (engine will be created by default if not passed)
    analyzer = JobAnalyzer(max_skills=max_skills, model_name=model_name)
    
    # Read job descriptions from database
    # Pass job_ids if provided, otherwise it fetches all (or based on default behavior in read_job_descriptions)
    descriptions = analyzer.read_job_descriptions(job_ids=job_ids)
    if not descriptions:
        # Error messages are now handled within read_job_descriptions or if it returns empty.
        # click.echo("No job descriptions found to analyze.") # Redundant if read_job_descriptions handles it
        return
    
    # Extract skills
    skills_dict = analyzer.extract_skills(descriptions)
    click.echo("\nTop 10 Required Skills:")
    for skill, score in list(skills_dict.items())[:10]:
        click.echo(f"- {skill}: {score:.2f}")
    
    # Read and analyze resume
    try:
        resume_text = analyzer.read_resume(resume_path)
        analysis = analyzer.analyze_resume(resume_text, skills_dict)
        
        # Print results
        click.echo("\nResume Analysis Results:")
        click.echo("\nMatching Skills:")
        for skill in analysis['matching_skills']:
            click.echo(f"- {skill}")
        
        click.echo("\nAreas for Growth:")
        for skill in analysis['missing_skills']:
            click.echo(f"- {skill}")
        
        click.echo("\nRecommendations:")
        for rec in analysis['recommendations']:
            click.echo(f"- {rec}")
    except Exception as e:
        click.echo(f"Error processing resume: {str(e)}", err=True)

@click.command()
# Removed --job-folder option
@click.option('--resume', required=True,
              help='Path to resume file (PDF or TXT)')
@click.option('--max-skills', default=20,
              help='Maximum number of skills to analyze')
@click.option('--model', default='gpt-4-turbo-preview',
              help='OpenAI model to use for analysis')
@click.option('--job-ids', default=None, multiple=True, help='Optional list of job URLs to analyze. If not provided, analyzes all jobs.')
def main(resume: str, max_skills: int, model: str, job_ids: Optional[List[str]]):
    """Job Skills Analyzer and Resume Comparator CLI tool."""
    # Convert tuple from multiple=True to list, or None if empty
    job_ids_list = list(job_ids) if job_ids else None
    analyze_jobs_and_resume(resume, max_skills, model, job_ids=job_ids_list)

if __name__ == "__main__":
    main() 