from rich.console import Console, Group
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, ProgressColumn
from rich.panel import Panel
from rich.table import Table, Column
from rich.text import Text
from rich import print as rprint
from rich.box import ROUNDED
from typing import Optional, Dict, List, Any, Union, Tuple
import json
from enum import Enum
from pathlib import Path

class OutputFormat(str, Enum):
    CONSOLE = "console"
    JSON = "json"
    TEXT = "text"
    CSV = "csv"

console = Console()

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

def print_error(message: str, details: str = ""):
    """Print an error message in red with optional details."""
    console.print(f"[red]✗[/red] {message}")
    if details:
        console.print(Panel(details, title="Details", border_style="red", style="red"))

def print_info(message: str):
    """Print an info message in blue."""
    console.print(f"[blue]ℹ[/blue] {message}")

def print_step(message: str):
    """Print a step indicator with a spinner."""
    console.print(f"[cyan]→[/cyan] {message}")

def print_substep(message: str, level: int = 1):
    """Print an indented substep message."""
    indent = "  " * level
    console.print(f"{indent}[dim]↳[/dim] {message}")

def print_result(title: str, result: Any, format: OutputFormat = OutputFormat.CONSOLE):
    """Print analysis results in the specified format."""
    if format == OutputFormat.JSON:
        console.print(json.dumps(result, indent=2))
    elif format == OutputFormat.TEXT:
        print_text_result(title, result)
    elif format == OutputFormat.CSV:
        print_csv_result(result)
    else:  # CONSOLE (default)
        print_console_result(title, result)

def print_console_result(title: str, result: Dict):
    """Print analysis results in a rich console format."""
    from rich import box
    
    # Create a panel for the overall result
    result_panels = []
    
    # Matching skills section
    if 'matching_skills' in result and result['matching_skills']:
        matches = "\n".join(f"• {skill}" for skill in result['matching_skills'])
        result_panels.append(Panel(matches, title="[green]✓ Matching Skills", border_style="green"))
    
    # Missing skills section
    if 'missing_skills' in result and result['missing_skills']:
        missing = "\n".join(f"• {skill}" for skill in result['missing_skills'])
        result_panels.append(Panel(missing, title="[yellow]⚠ Areas for Growth", border_style="yellow"))
    
    # Recommendations section
    if 'recommendations' in result and result['recommendations']:
        recs = "\n".join(f"• {rec}" for rec in result['recommendations'])
        result_panels.append(Panel(recs, title="[blue]💡 Recommendations", border_style="blue"))
    
    # Print all panels in a group
    if result_panels:
        console.print(Panel(Group(*result_panels), title=f"[bold]📊 {title}", border_style="cyan", padding=(1, 2)))

def print_text_result(title: str, result: Dict):
    """Print analysis results in plain text format."""
    print(f"=== {title} ===\n")
    
    if 'matching_skills' in result and result['matching_skills']:
        print("MATCHING SKILLS:")
        for skill in result['matching_skills']:
            print(f"- {skill}")
        print()
    
    if 'missing_skills' in result and result['missing_skills']:
        print("AREAS FOR GROWTH:")
        for skill in result['missing_skills']:
            print(f"- {skill}")
        print()
    
    if 'recommendations' in result and result['recommendations']:
        print("RECOMMENDATIONS:")
        for rec in result['recommendations']:
            print(f"- {rec}")
        print()

def print_csv_result(result: Dict):
    """Print analysis results in CSV format."""
    import csv
    import sys
    
    writer = csv.writer(sys.stdout)
    
    # Write header
    writer.writerow(["Type", "Item"])
    
    # Write matching skills
    if 'matching_skills' in result and result['matching_skills']:
        for skill in result['matching_skills']:
            writer.writerow(["Matching Skill", skill])
    
    # Write missing skills
    if 'missing_skills' in result and result['missing_skills']:
        for skill in result['missing_skills']:
            writer.writerow(["Missing Skill", skill])
    
    # Write recommendations
    if 'recommendations' in result and result['recommendations']:
        for rec in result['recommendations']:
            writer.writerow(["Recommendation", rec])

def print_job_summary(jobs: List[Dict], format: OutputFormat = OutputFormat.CONSOLE):
    """Print a summary of scraped jobs in the specified format."""
    # Group jobs by site
    jobs_by_site = {}
    for job in jobs:
        site = job.get('site', 'unknown')
        if site not in jobs_by_site:
            jobs_by_site[site] = []
        jobs_by_site[site].append(job)
    
    # Prepare data based on format
    if format == OutputFormat.JSON:
        summary = {
            "total_jobs": len(jobs),
            "sites": {
                site: {"count": len(site_jobs)}
                for site, site_jobs in jobs_by_site.items()
            }
        }
        console.print(json.dumps(summary, indent=2))
        return
    
    # For console and text formats
    if format == OutputFormat.CONSOLE:
        table = Table(
            title="Job Scraping Summary", 
            show_header=True, 
            header_style="bold magenta",
            box=ROUNDED
        )
        table.add_column("Site", style="cyan")
        table.add_column("Jobs Scraped", justify="right", style="green")
        table.add_column("Success Rate", justify="right", style="yellow")
        
        for site, site_jobs in jobs_by_site.items():
            total_jobs = len(site_jobs)
            success_rate = f"{(total_jobs / total_jobs) * 100:.1f}%"
            table.add_row(site, str(total_jobs), success_rate)
        
        console.print(table)
    else:  # TEXT or CSV
        if format == OutputFormat.TEXT:
            print(f"=== Job Scraping Summary ===\n")
            print(f"{'Site':<20} {'Jobs':>10} {'Success Rate':>15}")
            print("-" * 50)
            for site, site_jobs in jobs_by_site.items():
                total_jobs = len(site_jobs)
                success_rate = f"{(total_jobs / total_jobs) * 100:.1f}%"
                print(f"{site:<20} {total_jobs:>10} {success_rate:>15}")
        else:  # CSV
            import csv
            import sys
            writer = csv.writer(sys.stdout)
            writer.writerow(["Site", "Jobs_Scraped", "Success_Rate"])
            for site, site_jobs in jobs_by_site.items():
                total_jobs = len(site_jobs)
                success_rate = f"{(total_jobs / total_jobs) * 100:.1f}%"
                writer.writerow([site, total_jobs, success_rate])

def print_job_details(job: Dict, format: OutputFormat = OutputFormat.CONSOLE):
    """Print detailed information about a job in the specified format."""
    job_title = job.get('title', 'No Title')
    company = job.get('company', 'Unknown Company')
    site = job.get('site', 'unknown')
    url = job.get('url', 'N/A')
    scraped_date = job.get('scraped_date', 'N/A')
    description = job.get('description', 'No description available')
    
    if format == OutputFormat.JSON:
        console.print(json.dumps({
            "title": job_title,
            "company": company,
            "site": site,
            "url": url,
            "scraped_date": scraped_date,
            "description": description[:500] + ("..." if len(description) > 500 else "")
        }, indent=2))
    elif format == OutputFormat.CSV:
        import csv
        import sys
        writer = csv.writer(sys.stdout)
        writer.writerow(["Field", "Value"])
        writer.writerow(["Title", job_title])
        writer.writerow(["Company", company])
        writer.writerow(["Site", site])
        writer.writerow(["URL", url])
        writer.writerow(["Scraped Date", scraped_date])
        writer.writerow(["Description", description[:500] + ("..." if len(description) > 500 else "")])
    elif format == OutputFormat.TEXT:
        print(f"=== {job_title} at {company} ===")
        print(f"Site: {site}")
        print(f"URL: {url}")
        print(f"Scraped: {scraped_date}")
        print("\nDescription:")
        print(description[:500] + ("..." if len(description) > 500 else ""))
    else:  # CONSOLE (default)
        title = Text(f"{job_title} at {company}", style="bold cyan")
        content = f"""
        [bold blue]Site:[/bold blue] {site}
        [bold blue]URL:[/bold blue] {url}
        [bold blue]Scraped:[/bold blue] {scraped_date}
        
        [bold yellow]Description:[/bold yellow]
        {description[:500]}{'...' if len(description) > 500 else ''}
        """
        panel = Panel(content, title=title, border_style="blue", padding=(1, 2))
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