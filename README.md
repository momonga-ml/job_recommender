# Job Recommender

A powerful Python CLI tool for analyzing job descriptions and comparing them against resumes to identify matching skills, areas for improvement, and personalized recommendations.

## ✨ Features

- **Smart Resume Analysis**: Compare your resume against job requirements using AI
- **Multiple Output Formats**:
  - Beautiful console output with colors and formatting
  - JSON for programmatic use
  - Plain text for easy reading

- **Smart Resume Analysis** - AI-powered analysis of your resume against job requirements
- **Multiple Output Formats** - Console, JSON, text, and CSV output options
- **Rich CLI Experience** - Beautiful terminal output with colors and progress indicators
- **Skill Matching** - Identifies both matching and missing skills
- **Personalized Recommendations** - Get actionable insights to improve your resume
- **Fast & Efficient** - Processes multiple job descriptions quickly
- **Easy to Use** - Simple command-line interface with helpful feedback

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/job_recommender.git
cd job_recommender
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv .venv
.venv\Scripts\activate  # On Windows
# or
source .venv/bin/activate  # On macOS/Linux
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up your environment variables:
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
OPENAI_API_KEY=your-api-key-here
```

## Usage

### Basic Usage

```bash
python -m job_recommender.job_analyzer path/to/your/resume.pdf
```

### Job Scraping

```bash
# Scrape jobs from multiple sites
python -m job_recommender.job_scraper --query "software engineer" --location "New York" --sites indeed linkedin glassdoor

# Scrape with custom options
python -m job_recommender.job_scraper --query "data scientist" --location "San Francisco" --num-jobs 20 --output-dir my_jobs --cache-duration 12
```

### Resume Analysis Advanced Options

```bash
# Custom job descriptions folder and output format
python -m job_recommender.job_analyzer --job-folder my_jobs --format json --output results.json path/to/your/resume.pdf

# Limit number of skills to analyze
python -m job_recommender.job_analyzer --max-skills 15 path/to/your/resume.pdf

# Enable verbose output for debugging
python -m job_recommender.job_analyzer -v --job-folder job_descriptions path/to/your/resume.pdf

# Show help
python -m job_recommender.job_analyzer --help
python -m job_recommender.job_scraper --help
```

### Job Descriptions Format

Place your job descriptions as `.txt` files in a folder (default: `job_descriptions/`). Each file should contain the text of one job description.

### Output Formats

- `console`: Beautifully formatted console output (default)
- `json`: Machine-readable JSON format
- `text`: Plain text format
- `csv`: Comma-separated values for spreadsheets

## Development

### Project Structure

```
job_recommender/
├── job_recommender/            # Main package
│   ├── __init__.py            # Package initialization
│   ├── job_analyzer.py        # Resume analysis CLI and logic
│   ├── job_scraper.py         # Web scraping CLI and scrapers
│   ├── parallel_scraper.py    # Parallel scraping coordination
│   ├── cache.py               # Job caching system
│   ├── utils.py               # Utility functions and exceptions
│   ├── rich_utils.py          # Rich console formatting
│   ├── scraper_factory.py     # Scraper factory pattern
│   └── logging_config.py      # Comprehensive logging setup
├── tests/                     # Test suite
│   ├── __init__.py
│   ├── test_job_analyzer.py   # Analysis tests
│   └── test_job_scraper.py    # Scraping tests
├── job_descriptions/          # Sample job descriptions
├── resumes/                   # Sample resumes
├── example.env                # Example environment variables
├── requirements.txt           # Production dependencies
├── setup.py                   # Package configuration
├── README.md                  # This file
└── test_basic_functionality.py # Basic functionality tests
```

### Setting Up for Development

1. Clone the repository and set up a virtual environment as shown in the Installation section.

2. Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

3. Install the package in development mode:
```bash
pip install -e .
```

### Running Tests

```bash
# Run all tests with coverage
pytest --cov=job_recommender --cov-report=term-missing

# Run tests with detailed output
pytest -v

# Run a specific test file
pytest tests/test_job_analyzer.py -v

# Run tests with coverage report in HTML
pytest --cov=job_recommender --cov-report=html
# Then open htmlcov/index.html in your browser
```

### Code Style

This project uses:
- **Black** for code formatting
- **isort** for import sorting
- **Flake8** for linting

```bash
# Format code with Black
black .


# Sort imports with isort
isort .


# Check for style issues with flake8
flake8

# Run all code quality checks
pre-commit run --all-files
```

## Contributing

We welcome contributions! Here's how to get started:

1. **Fork** the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes and commit them: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature/your-feature-name`
5. Open a **Pull Request**

### Pull Request Guidelines

- Ensure your code passes all tests
- Update the documentation if needed
- Add tests for new features
- Keep commits small and focused
- Write clear commit messages

### Reporting Issues

Found a bug? Please open an issue with:
- A clear description of the problem
- Steps to reproduce the issue
- Expected vs actual behavior
- Any relevant error messages

## Documentation

### How It Works

1. **Input**: Provide your resume and a folder containing job descriptions
2. **Analysis**: The tool extracts key skills from job descriptions
3. **Matching**: Your resume is analyzed against these skills
4. **Insights**: Get detailed feedback on your fit for the positions

### Example Output

```
 Resume Analysis Results

 Position: Senior Software Engineer
 Matching Skills (8/12):
   • Python (3 years)
   • Machine Learning (2 years)
   • SQL (3 years)
   • Git (4 years)
   • Docker (2 years)
   • REST APIs (3 years)
   • AWS (2 years)
   • CI/CD (2 years)

 Missing Skills (4):
   • Kubernetes (High importance)
   • GraphQL (Medium importance)
   • TypeScript (Medium importance)
   • Terraform (Low importance)

 Recommendations:
   • Add Kubernetes experience to match 90% of job requirements
   • Consider learning GraphQL as it's mentioned in 70% of job postings
   • Highlight your AWS experience with specific projects

 Overall Match: 75%
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

Made with by [Your Name] | [![Twitter](https://img.shields.io/twitter/url?style=social&url=https%3A%2F%2Ftwitter.com%2Fyourhandle)](https://twitter.com/yourhandle)
