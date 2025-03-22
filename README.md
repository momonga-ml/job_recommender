# Job Skills Analyzer and Resume Comparator

This tool helps analyze job descriptions and compare them against a resume to identify matching skills and areas for growth.

## Features

- Extracts and ranks important skills from multiple job descriptions
- Analyzes a resume against the required skills (supports PDF and TXT formats)
- Provides detailed recommendations for skill development
- Uses OpenAI's GPT-4 for intelligent analysis
- Flexible CLI interface with configurable options

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Copy `example.env` to `.env` and add your OpenAI API key:
```bash
cp example.env .env
```
Then edit `.env` and add your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

3. Create a `job_descriptions` folder and add your job description text files (`.txt` format)

4. Place your resume in the `resumes` folder (supports both PDF and TXT formats)

## Usage

Basic usage:
```bash
python job_analyzer.py --resume path/to/your/resume.pdf
```

Advanced options:
```bash
python job_analyzer.py \
    --resume path/to/your/resume.pdf \
    --job-folder custom/job/folder \
    --max-skills 30 \
    --model gpt-4-turbo-preview
```

### Command Line Options

- `--resume`: Path to your resume file (PDF or TXT) [required]
- `--job-folder`: Folder containing job descriptions (default: 'job_descriptions')
- `--max-skills`: Maximum number of skills to analyze (default: 20)
- `--model`: OpenAI model to use for analysis (default: 'gpt-4-turbo-preview')

The tool will:
1. Analyze all job descriptions in the specified folder
2. Extract and rank the most important skills
3. Compare your resume against these skills
4. Provide a detailed analysis including:
   - Matching skills
   - Areas for growth
   - Specific recommendations

## File Structure

- `job_descriptions/` - Folder containing job description text files
- `resumes/` - Folder for storing resume files (PDF or TXT)
- `.env` - OpenAI API key configuration (copy from example.env)
- `job_analyzer.py` - Main script
- `requirements.txt` - Project dependencies
