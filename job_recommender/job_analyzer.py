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
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('averaged_perceptron_tagger')

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

def analyze_jobs_and_resume(job_folder: str, resume_path: str, max_skills: int = 20, model_name: str = "gpt-4-turbo-preview"):
    """Main function to analyze jobs and resume."""
    # Initialize the analyzer
    analyzer = JobAnalyzer(max_skills=max_skills, model_name=model_name)
    
    # Read job descriptions
    descriptions = analyzer.read_job_descriptions(job_folder)
    if not descriptions:
        click.echo(f"No job descriptions found in '{job_folder}' folder.")
        click.echo("Please add .txt files containing job descriptions to that folder.")
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
@click.option('--job-folder', default='job_descriptions',
              help='Folder containing job description text files')
@click.option('--resume', required=True,
              help='Path to resume file (PDF or TXT)')
@click.option('--max-skills', default=20,
              help='Maximum number of skills to analyze')
@click.option('--model', default='gpt-4-turbo-preview',
              help='OpenAI model to use for analysis')
def main(job_folder: str, resume: str, max_skills: int, model: str):
    """Job Skills Analyzer and Resume Comparator CLI tool."""
    analyze_jobs_and_resume(job_folder, resume, max_skills, model)

if __name__ == "__main__":
    main() 