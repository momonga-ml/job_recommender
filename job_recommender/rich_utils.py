from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import print as rprint
from typing import Optional, Dict, List

console = Console()

def create_progress_bar(description: str, total: int, unit: str = "items") -> Progress:
    """Create a rich progress bar with custom styling."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("•"),
        TextColumn("[bold blue]{task.fields[count]}"),
        TextColumn("•"),
        TimeElapsedColumn(),
        console=console,
        expand=True
    )

def print_success(message: str):
    """Print a success message in green."""
    console.print(f"[green]✓[/green] {message}")

def print_warning(message: str):
    """Print a warning message in yellow."""
    console.print(f"[yellow]⚠[/yellow] {message}")

def print_error(message: str):
    """Print an error message in red."""
    console.print(f"[red]✗[/red] {message}")

def print_info(message: str):
    """Print an info message in blue."""
    console.print(f"[blue]ℹ[/blue] {message}")

def print_job_summary(jobs: List[Dict]):
    """Print a summary of scraped jobs in a table format."""
    table = Table(title="Job Scraping Summary", show_header=True, header_style="bold magenta")
    table.add_column("Site", style="cyan")
    table.add_column("Jobs Scraped", justify="right", style="green")
    table.add_column("Success Rate", justify="right", style="yellow")
    
    # Group jobs by site
    jobs_by_site = {}
    for job in jobs:
        site = job['site']
        if site not in jobs_by_site:
            jobs_by_site[site] = []
        jobs_by_site[site].append(job)
    
    # Calculate statistics
    for site, site_jobs in jobs_by_site.items():
        total_jobs = len(site_jobs)
        success_rate = f"{(total_jobs / total_jobs) * 100:.1f}%"
        table.add_row(site, str(total_jobs), success_rate)
    
    console.print(table)

def print_job_details(job: Dict):
    """Print detailed information about a job in a panel."""
    title = Text(f"{job['title']} at {job['company']}", style="bold cyan")
    content = f"""
    [bold blue]Site:[/bold blue] {job['site']}
    [bold blue]URL:[/bold blue] {job['url']}
    [bold blue]Scraped:[/bold blue] {job['scraped_date']}
    
    [bold yellow]Description:[/bold yellow]
    {job['description'][:200]}...
    """
    
    panel = Panel(content, title=title, border_style="blue")
    console.print(panel)

def print_scraping_start(sites: List[str], query: str, location: str):
    """Print a header for the scraping process."""
    header = f"""
    [bold cyan]Starting Job Scraping[/bold cyan]
    [bold green]Query:[/bold green] {query}
    [bold green]Location:[/bold green] {location}
    [bold green]Sites:[/bold green] {', '.join(sites)}
    """
    console.print(Panel(header, border_style="cyan"))

def print_scraping_complete(total_jobs: int, duration: float):
    """Print a summary of the completed scraping process."""
    summary = f"""
    [bold green]Scraping Complete![/bold green]
    [bold blue]Total Jobs:[/bold blue] {total_jobs}
    [bold blue]Duration:[/bold blue] {duration:.1f} seconds
    """
    console.print(Panel(summary, border_style="green")) 