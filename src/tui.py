#!/usr/bin/env python3
"""
Interactive TUI for Job Agent Pipeline
Allows selecting profiles, sources, and running jobs/digests
"""

import os
import subprocess
import sys
from pathlib import Path

from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

console = Console()


def clear_screen():
    """Clear the terminal screen"""
    os.system("clear" if os.name != "nt" else "cls")  # nosec B605


def show_header():
    """Display the application header"""
    clear_screen()
    header = """
[bold cyan]╔═══════════════════════════════════════════════╗[/bold cyan]
[bold cyan]║[/bold cyan]     [bold white]Job Agent Pipeline Controller[/bold white]       [bold cyan]║[/bold cyan]
[bold cyan]╚═══════════════════════════════════════════════╝[/bold cyan]
    """
    console.print(header)


def select_profile() -> str | None:
    """Select user profile (Wes or Adam)"""
    console.print("\n[bold yellow]Step 1:[/bold yellow] Select Profile\n")

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Option", style="cyan", width=8)
    table.add_column("Profile", style="green", width=20)
    table.add_column("Email", style="blue", width=30)
    table.add_column("Focus", style="yellow")

    table.add_row(
        "1", "Wesley van Ooyen", "wesvanooyen@gmail.com", "Robotics/Hardware (VP/Director)"
    )
    table.add_row("2", "Adam White", "adamkwhite@gmail.com", "Software/Product (Senior/Staff)")
    table.add_row("q", "Quit", "", "")

    console.print(table)
    console.print(
        "\n[dim]Note: Profile selection determines which email inbox to check and where digests are sent.[/dim]"
    )

    choice = Prompt.ask("\n[bold]Select profile[/bold]", choices=["1", "2", "q"], default="1")

    if choice == "q":
        return None
    elif choice == "1":
        return "wes"
    else:
        return "adam"


def select_sources(profile: str) -> list[str]:
    """Select job sources to scrape"""
    console.print("\n[bold yellow]Step 2:[/bold yellow] Select Sources\n")

    # Column 1: Sources table (compact for side-by-side layout)
    sources_table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    sources_table.add_column("Source", style="cyan", width=10)
    sources_table.add_column("Description", style="white", width=20)
    sources_table.add_column("Vol", style="green", width=8)

    # Profile-specific email source
    email_inbox = (
        "Wes.jobalerts@\ngmail.com" if profile == "wes" else "adamwhite.\njobalerts@\ngmail.com"
    )

    sources_table.add_row("Email", f"{email_inbox}\n(LinkedIn, etc.)", "~50-100")
    sources_table.add_row("Robotics", "Sheet\n(1,092 jobs)", "~10-20")
    sources_table.add_row("Companies", "26+ pages", "~5-15")

    sources_panel = Panel(
        sources_table,
        title="[bold magenta]Job Sources[/bold magenta]",
        border_style="magenta",
        expand=False,
        width=52,
    )

    # Column 2: Scoring criteria summary (profile-specific)
    if profile == "wes":
        criteria_content = """[bold yellow]📊 Scoring (0-115 pts)[/bold yellow]

[cyan]Seniority (30):[/cyan] VP/Director

[cyan]Domain (25):[/cyan] Robotics/IoT

[cyan]Role (20):[/cyan] Engineering>Product

[cyan]Location (15):[/cyan] Remote/Ontario

[bold yellow]🎓 Grades[/bold yellow]
[green]A (98+)[/green] Notify + Digest
[green]B (80+)[/green] Notify + Digest
[yellow]C (63+)[/yellow] Digest only
[dim]D/F[/dim] Stored/Filtered

[bold yellow]📧 Sent to:[/bold yellow]
wesvanooyen@gmail.com
[dim]CC:[/dim] adamkwhite@gmail.com"""
        panel_title = "[bold cyan]Wes's Scoring Criteria[/bold cyan]"
    else:  # adam
        criteria_content = """[bold yellow]📊 Scoring (0-115 pts)[/bold yellow]

[cyan]Seniority (30):[/cyan] Senior/Staff/Lead

[cyan]Domain (25):[/cyan] Software/Cloud/Data

[cyan]Role (20):[/cyan] Engineering>Product

[cyan]Location (15):[/cyan] Remote/Ontario

[bold yellow]🎓 Grades[/bold yellow]
[green]A (98+)[/green] Notify + Digest
[green]B (80+)[/green] Notify + Digest
[yellow]C (63+)[/yellow] Digest only
[dim]D/F[/dim] Stored/Filtered

[bold yellow]📧 Sent to:[/bold yellow]
adamkwhite@gmail.com
[dim]CC:[/dim] adamkwhite@gmail.com"""
        panel_title = "[bold cyan]Adam's Scoring Criteria[/bold cyan]"

    criteria_panel = Panel(
        criteria_content,
        title=panel_title,
        border_style="cyan",
        padding=(0, 1),
        expand=False,
        width=38,
    )

    # Display in 2 columns side by side
    # Don't expand so panels only take space they need
    console.print(Columns([sources_panel, criteria_panel], padding=(0, 1)))

    console.print("\n[dim]Enter comma-separated options (e.g., 'email,robotics' or 'all')[/dim]")
    choice = Prompt.ask("\n[bold]Select sources[/bold]", default="all").lower().strip()

    if choice == "all":
        return ["email", "robotics", "companies"]
    else:
        sources = [s.strip() for s in choice.split(",")]
        valid_sources = []
        for s in sources:
            if s in ["email", "robotics", "companies"]:
                valid_sources.append(s)
        return valid_sources if valid_sources else ["email"]


def show_criteria():
    """Display scoring criteria and grading information"""
    clear_screen()

    console.print("\n[bold cyan]═══════════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]         JOB SCORING CRITERIA (Wesley)         [/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════════════[/bold cyan]\n")

    # Scoring breakdown
    console.print("[bold yellow]📊 Scoring System (0-115 points)[/bold yellow]\n")

    scoring_table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    scoring_table.add_column("Category", style="cyan", width=20)
    scoring_table.add_column("Max Points", style="green", width=12)
    scoring_table.add_column("Criteria", style="white")

    scoring_table.add_row("Seniority", "30", "VP/Director/Head of > Senior Manager > Manager")
    scoring_table.add_row("Domain", "25", "Robotics, hardware, IoT, MedTech, automation")
    scoring_table.add_row("Role Type", "20", "Engineering leadership > Product leadership")
    scoring_table.add_row("Location", "15", "Remote/Hybrid Ontario > Ontario cities > Canada")
    scoring_table.add_row("Company Stage", "15", "Series A-C, growth stage, funded")
    scoring_table.add_row("Technical", "10", "Mechatronics, embedded, manufacturing, DFM/DFA")

    console.print(scoring_table)

    # Grading scale
    console.print("\n[bold yellow]🎓 Grading Scale[/bold yellow]\n")

    grade_table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    grade_table.add_column("Grade", style="cyan", width=8)
    grade_table.add_column("Score", style="green", width=10)
    grade_table.add_column("Action", style="white")

    grade_table.add_row("A", "98-115", "Immediate notification + digest")
    grade_table.add_row("B", "80-97", "Immediate notification + digest")
    grade_table.add_row("C", "63-79", "Digest only")
    grade_table.add_row("D", "46-62", "Stored, not sent")
    grade_table.add_row("F", "0-45", "Filtered out")

    console.print(grade_table)

    # Source thresholds
    console.print("\n[bold yellow]📈 Source-Specific Thresholds[/bold yellow]\n")

    source_table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    source_table.add_column("Source", style="cyan", width=20)
    source_table.add_column("Min Score", style="green", width=12)
    source_table.add_column("Reasoning", style="white")

    source_table.add_row("Email newsletters", "All", "High signal newsletters")
    source_table.add_row("Robotics sheet", "70+ (B)", "1,092 jobs need quality filter")
    source_table.add_row("Company monitoring", "50+ (D)", "Wes's curated companies")

    console.print(source_table)

    # Notifications
    console.print("\n[bold yellow]📧 Notification Rules[/bold yellow]\n")
    console.print("  • Immediate SMS/Email: A/B grade jobs (80+) only")
    console.print("  • Weekly Digest: C+ grade jobs (63+)")
    console.print("  • To: wesvanooyen@gmail.com")
    console.print("  • CC: adamkwhite@gmail.com")

    console.print("\n[bold cyan]═══════════════════════════════════════════════[/bold cyan]\n")

    input("\n[dim]Press Enter to return to menu...[/dim]")


def select_action() -> str | None:
    """Select what action to perform"""
    console.print("\n[bold yellow]Step 3:[/bold yellow] Select Action\n")

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Option", style="cyan", width=8)
    table.add_column("Action", style="green", width=20)
    table.add_column("Description", style="white")

    table.add_row("1", "Scrape Only", "Fetch and score jobs, store in database")
    table.add_row("2", "Send Digest", "Send email digest with stored jobs")
    table.add_row("3", "Scrape + Digest", "Run scraper then send digest email")
    table.add_row("c", "View Criteria", "Show scoring criteria and grading scale")
    table.add_row("b", "Back", "Return to profile selection")
    table.add_row("q", "Quit", "Exit application")

    console.print(table)

    choice = Prompt.ask(
        "\n[bold]Select action[/bold]", choices=["1", "2", "3", "c", "b", "q"], default="3"
    )

    # Map choices to actions
    choice_map = {
        "q": None,
        "b": "back",
        "c": "criteria",
        "1": "scrape",
        "2": "digest",
        "3": "both",
    }

    return choice_map.get(choice, "both")


def select_digest_options() -> dict:
    """Select digest options (dry-run, force-resend)"""
    console.print("\n[bold yellow]Step 4:[/bold yellow] Digest Options\n")

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Option", style="cyan", width=8)
    table.add_column("Mode", style="green", width=20)
    table.add_column("Sends Email?", style="white", width=14)
    table.add_column("Marks Sent?", style="white", width=14)
    table.add_column("Use Case", style="yellow")

    table.add_row("1", "Production", "✅ Yes", "✅ Yes", "Real digest (default)")
    table.add_row("2", "Dry Run", "❌ No", "❌ No", "Testing/preview")
    table.add_row("3", "Force Resend", "✅ Yes", "❌ No", "Re-send previous jobs")

    console.print(table)
    console.print("\n[dim]Note: Use 'Dry Run' during testing to avoid marking jobs as sent.[/dim]")

    choice = Prompt.ask("\n[bold]Select digest mode[/bold]", choices=["1", "2", "3"], default="2")

    return {
        "dry_run": choice == "2",
        "force_resend": choice == "3",
    }


def confirm_execution(
    profile: str, sources: list[str], action: str, digest_options: dict | None = None
) -> bool:
    """Show summary and confirm execution"""
    console.print("\n[bold yellow]Summary:[/bold yellow]\n")

    profile_name = "Wesley van Ooyen" if profile == "wes" else "Adam White"
    profile_email = "wesvanooyen@gmail.com" if profile == "wes" else "adamkwhite@gmail.com"

    # Map action codes to display names
    action_display = {
        "scrape": "Scrape Only",
        "digest": "Send Digest",
        "both": "Scrape and Send Digest",
    }
    action_text = action_display.get(action, action.title())

    # Build summary text
    summary_text = (
        f"[bold]Profile:[/bold] {profile_name} ({profile_email})\n"
        f"[bold]Sources:[/bold] {', '.join(sources).title()}\n"
        f"[bold]Action:[/bold] {action_text}"
    )

    # Add digest mode if applicable
    if digest_options and action in ["digest", "both"]:
        if digest_options.get("dry_run"):
            digest_mode = "Dry Run (testing)"
        elif digest_options.get("force_resend"):
            digest_mode = "Force Resend (re-send previous jobs)"
        else:
            digest_mode = "Production (real digest)"
        summary_text += f"\n[bold]Digest Mode:[/bold] {digest_mode}"

    summary = Panel(
        summary_text,
        title="[bold cyan]Execution Plan[/bold cyan]",
        border_style="cyan",
    )

    console.print(summary)

    return Confirm.ask("\n[bold green]Proceed with execution?[/bold green]", default=True)


def run_scraper(profile: str, sources: list[str]) -> int:
    """Execute the unified scraper"""
    console.print("\n[bold green]Running Job Scraper...[/bold green]\n")

    # Build command
    cmd = ["job-agent-venv/bin/python", "src/jobs/weekly_unified_scraper.py", "--profile", profile]

    # Add source-specific flags
    if len(sources) < 3:  # Not "all"
        if "email" in sources and len(sources) == 1:
            cmd.append("--email-only")
        elif "robotics" in sources and len(sources) == 1:
            cmd.append("--robotics-only")
        elif "companies" in sources and len(sources) == 1:
            cmd.append("--companies-only")

    # Profile-specific email inbox
    email_inbox = "Wes.jobalerts@gmail.com" if profile == "wes" else "adamwhite.jobalerts@gmail.com"

    console.print(f"[dim]Command: {' '.join(cmd)}[/dim]\n")
    console.print(f"[dim]Note: Using {email_inbox} (profile: {profile})[/dim]\n")

    # Execute
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd())

    result = subprocess.run(cmd, env=env)
    return result.returncode


def send_digest(profile: str, dry_run: bool = False, force_resend: bool = False) -> int:
    """Send email digest"""
    mode = "DRY RUN" if dry_run else "FORCE RESEND" if force_resend else "PRODUCTION"
    console.print(f"\n[bold green]Sending Email Digest ({mode})...[/bold green]\n")

    # Build command
    cmd = ["job-agent-venv/bin/python", "src/send_profile_digest.py", "--profile", profile]

    if dry_run:
        cmd.append("--dry-run")
    if force_resend:
        cmd.append("--force-resend")

    console.print(f"[dim]Command: {' '.join(cmd)}[/dim]\n")

    # Execute
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd())

    result = subprocess.run(cmd, env=env)
    return result.returncode


def main():
    """Main TUI loop"""
    try:
        while True:
            show_header()

            # Step 1: Select profile
            profile = select_profile()
            if profile is None:
                console.print("\n[yellow]Goodbye![/yellow]\n")
                sys.exit(0)

            # Step 2: Select sources
            sources = select_sources(profile)
            if not sources:
                console.print("\n[red]No valid sources selected. Please try again.[/red]")
                continue

            # Step 3: Select action
            action = select_action()
            if action is None:
                console.print("\n[yellow]Goodbye![/yellow]\n")
                sys.exit(0)
            elif action == "back":
                continue
            elif action == "criteria":
                show_criteria()
                continue

            # Step 4: Select digest options (if sending digest)
            digest_options = {}
            if action in ["digest", "both"]:
                digest_options = select_digest_options()

            # Step 5: Confirm and execute
            if not confirm_execution(profile, sources, action, digest_options):
                console.print("\n[yellow]Cancelled. Returning to menu...[/yellow]\n")
                input("Press Enter to continue...")
                continue

            # Execute
            success = True

            if action in ["scrape", "both"]:
                returncode = run_scraper(profile, sources)
                if returncode != 0:
                    console.print("\n[red]✗ Scraper failed![/red]")
                    success = False
                else:
                    console.print("\n[green]✓ Scraper completed successfully![/green]")

            if action in ["digest", "both"] and success:
                returncode = send_digest(
                    profile,
                    dry_run=digest_options.get("dry_run", False),
                    force_resend=digest_options.get("force_resend", False),
                )
                if returncode != 0:
                    console.print("\n[red]✗ Digest send failed![/red]")
                    success = False
                else:
                    console.print("\n[green]✓ Digest sent successfully![/green]")

            # Show results and prompt
            if success:
                console.print("\n[bold green]All operations completed successfully![/bold green]")
            else:
                console.print(
                    "\n[bold red]Some operations failed. Check logs for details.[/bold red]"
                )

            # Ask to continue or quit
            if not Confirm.ask("\n[bold]Run another job?[/bold]", default=True):
                console.print("\n[yellow]Goodbye![/yellow]\n")
                break

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Interrupted by user. Goodbye![/yellow]\n")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]Error: {e}[/bold red]\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
