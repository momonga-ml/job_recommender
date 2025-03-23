from setuptools import setup, find_packages

setup(
    name="job_recommender",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
        "nltk>=3.6.0",
        "scikit-learn>=1.0.0",
        "openai>=1.0.0",
        "python-dotenv>=0.19.0",
        "PyPDF2>=3.0.0",
        "selenium>=4.0.0",
        "webdriver-manager>=3.8.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-mock>=3.10.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "job-scraper=job_recommender.job_scraper:main",
            "job-analyzer=job_recommender.job_analyzer:main",
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="A tool for scraping job descriptions and analyzing resumes",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/job_recommender",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
) 