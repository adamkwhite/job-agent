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
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

# Add to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils.profile_manager import get_profile_manager

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
    """Select user profile dynamically from enabled profiles"""
    console.print("\n[bold yellow]Step 1:[/bold yellow] Select Profile\n")

    # Load profiles from profile manager
    pm = get_profile_manager()
    enabled_profiles = pm.get_enabled_profiles()

    if not enabled_profiles:
        console.print("[bold red]No enabled profiles found![/bold red]")
        return None

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Option", style="cyan", width=8)
    table.add_column("Profile", style="green", width=20)
    table.add_column("Email", style="blue", width=30)
    table.add_column("Focus", style="yellow")

    # Build profile focus descriptions
    focus_map = {
        "wes": "Robotics/Hardware (VP/Director)",
        "adam": "Software/Product (Senior/Staff)",
        "eli": "Fintech/Healthtech (Director/VP/CTO)",
    }

    # Add profile rows
    profile_map = {}
    for i, profile in enumerate(enabled_profiles, 1):
        focus = focus_map.get(
            profile.id,
            f"{', '.join(profile.get_domain_keywords()[:2])} ({', '.join(profile.get_target_seniority()[:2])})",
        )
        table.add_row(str(i), profile.name, profile.email, focus)
        profile_map[str(i)] = profile.id

    table.add_row("q", "Quit", "", "")

    console.print(table)
    console.print(
        "\n[dim]Note: Profile selection determines which email inbox to check and where digests are sent.[/dim]"
    )

    choices = list(profile_map.keys()) + ["q"]
    choice = Prompt.ask("\n[bold]Select profile[/bold]", choices=choices, default="1")

    if choice == "q":
        return None
    else:
        return profile_map[choice]


def select_sources(profile: str) -> list[str]:
    """Select job sources to scrape"""
    console.print("\n[bold yellow]Step 2:[/bold yellow] Select Sources\n")

    # Get profile object
    pm = get_profile_manager()
    profile_obj = pm.get_profile(profile)

    # Column 1: Sources table (compact for side-by-side layout)
    sources_table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    sources_table.add_column("Source", style="cyan", width=12)
    sources_table.add_column("Description", style="white", width=35)
    sources_table.add_column("Vol", style="green", width=10)

    # Profile-specific email source (only show if profile has email credentials)
    if profile_obj and hasattr(profile_obj, "email_username") and profile_obj.email_username:
        email_inbox = profile_obj.email_username
    else:
        email_inbox = "No inbox configured"

    sources_table.add_row("Email", f"{email_inbox} (LinkedIn, etc.)", "~50-100")
    sources_table.add_row("Robotics", "Sheet (1,092 jobs)", "~10-20")
    sources_table.add_row("Companies", "68 pages (15 robotics)", "~20-40")

    sources_panel = Panel(
        sources_table,
        title="[bold magenta]Job Sources[/bold magenta]",
        border_style="magenta",
        expand=False,
        width=65,
    )

    # Column 2: Scoring criteria summary (dynamically from profile)
    if profile_obj:
        seniority_display = "/".join(profile_obj.get_target_seniority()[:3])
        domain_display = "/".join(profile_obj.get_domain_keywords()[:3])
        location_prefs = profile_obj.scoring.get("location_preferences", {})
        location_display = "Remote" if location_prefs.get("remote_keywords") else "N/A"
        if location_prefs.get("preferred_cities"):
            location_display += f"/{location_prefs['preferred_cities'][0].title()}"

        criteria_content = f"""[bold yellow]📊 Scoring (0-115 pts)[/bold yellow]

[cyan]Seniority (30):[/cyan] {seniority_display}

[cyan]Domain (25):[/cyan] {domain_display}

[cyan]Role (20):[/cyan] Engineering

[cyan]Location (15):[/cyan] {location_display}

[bold yellow]🎓 Grades[/bold yellow]
[green]A (98+)[/green] Notify + Digest
[green]B (80+)[/green] Notify + Digest
[yellow]C (63+)[/yellow] Digest only
[dim]D/F[/dim] Stored/Filtered

[bold yellow]📧 Sent to:[/bold yellow]
{profile_obj.email}
[dim]CC:[/dim] adamkwhite@gmail.com"""
        panel_title = f"[bold cyan]{profile_obj.name}'s Scoring[/bold cyan]"
    else:
        criteria_content = "[red]Profile not found[/red]"
        panel_title = "[red]Error[/red]"

    criteria_panel = Panel(
        criteria_content,
        title=panel_title,
        border_style="cyan",
        padding=(0, 1),
        expand=False,
        width=50,
    )

    # Display panels stacked vertically
    console.print(sources_panel)
    console.print(criteria_panel)

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
    source_table.add_row("Company monitoring", "50+ (D)", "68 companies (15 robotics)")

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

    table.add_row("1", "Production", "✅ Yes", "✅ Yes", "Real digest")
    table.add_row("2", "Dry Run", "❌ No", "❌ No", "Testing/preview (default)")
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

    # Get profile object
    pm = get_profile_manager()
    profile_obj = pm.get_profile(profile)
    profile_name = profile_obj.name if profile_obj else profile.title()
    profile_email = profile_obj.email if profile_obj else "unknown"

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
    pm = get_profile_manager()
    profile_obj = pm.get_profile(profile)
    email_inbox = (
        profile_obj.email_username
        if (profile_obj and hasattr(profile_obj, "email_username") and profile_obj.email_username)
        else "No inbox configured"
    )

    console.print(f"[dim]Command: {' '.join(cmd)}[/dim]\n")
    console.print(f"[dim]Note: Using {email_inbox} (profile: {profile})[/dim]\n")

    # Execute
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd())

    result = subprocess.run(cmd, env=env)
    return result.returncode


def prompt_firecrawl_scraping() -> bool:
    """Ask user if they want to run Firecrawl scraping for career pages (DEPRECATED - now automatic)"""
    console.print("\n[bold yellow]Note: Robotics Companies Integrated[/bold yellow]\n")

    info_text = """[cyan]✓ 15 priority robotics companies have been added to the database![/cyan]

[yellow]What happens now:[/yellow]
  • Robotics companies are automatically scraped when you select "Companies" source
  • Uses Firecrawl to handle JavaScript-heavy pages
  • Extracts job listings, scores, and stores in database
  • No separate manual step needed!

[yellow]Robotics companies in database:[/yellow]
  • Humanoid: Figure, Sanctuary AI, 1X Technologies, Apptronik
  • Warehouse: Robust AI, Dexterity, Veo, Covariant, RightHand, Nimble
  • Specialized: Chef Robotics, Gecko Robotics, Machina Labs, Nuro, Skild AI

[green]Everything is now automated via the "Companies" source![/green]"""

    console.print(Panel(info_text, border_style="green"))

    input("\n[dim]Press Enter to continue...[/dim]")
    return False  # Don't show Firecrawl instructions anymore


def show_firecrawl_instructions():
    """Display instructions for running Firecrawl via Claude Code"""
    console.print("\n[bold green]Firecrawl Scraping Queued[/bold green]\n")

    instructions = """[bold yellow]📋 Next Steps:[/bold yellow]

[cyan]1. Return to your Claude Code conversation[/cyan]

[cyan]2. Ask Claude:[/cyan]
   [white]"Run Firecrawl scraping for the 20 robotics career pages"[/white]

[cyan]3. Claude will:[/cyan]
   • Execute Firecrawl MCP commands for 20 companies
   • Save markdown outputs to data/firecrawl_cache/
   • Process markdown to extract job listings
   • Score and store jobs in database
   • Send notifications for A/B grade jobs

[yellow]After Firecrawl completes, you can return to TUI to send digest[/yellow]

[dim]Press Enter to continue with current workflow...[/dim]"""

    console.print(
        Panel(
            instructions, title="[bold cyan]Firecrawl Instructions[/bold cyan]", border_style="cyan"
        )
    )
    input()


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

                    # Prompt for Firecrawl scraping if robotics source was used
                    if success and "robotics" in sources and prompt_firecrawl_scraping():
                        show_firecrawl_instructions()

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
