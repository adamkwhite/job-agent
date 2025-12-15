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
    sources_table.add_row("Companies", "68 monitored companies", "~20-40")

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

    console.print("\n[dim]Enter comma-separated options (e.g., 'email,companies' or 'all')[/dim]")
    choice = Prompt.ask("\n[bold]Select sources[/bold]", default="all").lower().strip()

    if choice == "all":
        return ["email", "companies"]
    else:
        sources = [s.strip() for s in choice.split(",")]
        valid_sources = []
        for s in sources:
            if s in ["email", "companies"]:
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
    source_table.add_row("Company monitoring", "50+ (D)", "68 monitored companies")

    console.print(source_table)

    # Notifications
    console.print("\n[bold yellow]📧 Notification Rules[/bold yellow]\n")
    console.print("  • Immediate SMS/Email: A/B grade jobs (80+) only")
    console.print("  • Weekly Digest: C+ grade jobs (63+)")
    console.print("  • To: wesvanooyen@gmail.com")
    console.print("  • CC: adamkwhite@gmail.com")

    console.print("\n[bold cyan]═══════════════════════════════════════════════[/bold cyan]\n")

    input("\n[dim]Press Enter to return to menu...[/dim]")


def review_llm_failures():  # pragma: no cover
    """Interactive interface for reviewing LLM extraction failures

    Note: TUI functions are excluded from coverage requirements as they will be
    replaced with Textual framework (Issue #119). Manual testing confirms functionality.
    """

    from database import JobDatabase

    db = JobDatabase()

    while True:
        console.clear()
        console.print(
            "\n[bold magenta]═══════════════════════════════════════════════[/bold magenta]"
        )
        console.print(
            "[bold magenta]           LLM EXTRACTION FAILURES REVIEW           [/bold magenta]"
        )
        console.print(
            "[bold magenta]═══════════════════════════════════════════════[/bold magenta]\n"
        )

        # Get pending failures
        failures = db.get_llm_failures(review_action="pending", limit=50)

        if not failures:
            console.print("[green]✅ No pending LLM extraction failures to review![/green]\n")
            input("\n[dim]Press Enter to return to menu...[/dim]")
            return

        # Summary stats
        console.print(f"[bold yellow]📊 Summary:[/bold yellow] {len(failures)} pending failures\n")

        # Display failures table
        table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
        table.add_column("#", style="cyan", width=4)
        table.add_column("Company", style="white", width=25)
        table.add_column("Failure Reason", style="yellow", width=30)
        table.add_column("Occurred", style="dim", width=12)

        for idx, failure in enumerate(failures[:20], 1):  # Show first 20
            occurred = failure["occurred_at"][:10] if failure["occurred_at"] else "Unknown"
            reason = (
                (failure["failure_reason"][:27] + "...")
                if len(failure["failure_reason"]) > 30
                else failure["failure_reason"]
            )
            table.add_row(
                str(idx),
                failure["company_name"],
                reason,
                occurred,
            )

        console.print(table)

        if len(failures) > 20:
            console.print(f"\n[dim]Showing 20 of {len(failures)} failures...[/dim]")

        # Action menu
        console.print("\n[bold yellow]Actions:[/bold yellow]")
        console.print("  [r] Review specific failure (view details, retry, skip)")
        console.print("  [a] Retry all pending failures")
        console.print("  [s] Skip all pending failures")
        console.print("  [b] Back to main menu")

        choice = Prompt.ask(
            "\n[bold]Select action[/bold]", choices=["r", "a", "s", "b"], default="b"
        )

        if choice == "b":
            return
        elif choice == "a":
            _retry_all_failures(db, failures)
        elif choice == "s":
            _skip_all_failures(db, failures)
        elif choice == "r":
            _review_single_failure(db, failures)


def _review_single_failure(db, failures):  # pragma: no cover
    """Review a single LLM extraction failure"""

    # Select failure
    failure_num = Prompt.ask(
        "\n[bold]Enter failure number to review[/bold]",
        default="1",
    )

    try:
        failure_idx = int(failure_num) - 1
        if failure_idx < 0 or failure_idx >= len(failures):
            console.print(f"[red]❌ Invalid failure number. Must be 1-{len(failures)}[/red]")
            input("\n[dim]Press Enter to continue...[/dim]")
            return

        failure = failures[failure_idx]
    except ValueError:
        console.print("[red]❌ Invalid input. Enter a number.[/red]")
        input("\n[dim]Press Enter to continue...[/dim]")
        return

    # Show failure details
    console.clear()
    console.print("\n[bold cyan]═══════════════════════════════════════════════[/bold cyan]")
    console.print(f"[bold cyan]      FAILURE DETAILS - {failure['company_name']}      [/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════════════[/bold cyan]\n")

    detail_table = Table(box=box.ROUNDED, show_header=False)
    detail_table.add_column("Field", style="cyan", width=20)
    detail_table.add_column("Value", style="white")

    detail_table.add_row("Company", failure["company_name"])
    detail_table.add_row("Occurred At", failure["occurred_at"] or "Unknown")
    detail_table.add_row("Failure Reason", failure["failure_reason"])
    detail_table.add_row("Markdown Path", failure["markdown_path"] or "N/A")

    console.print(detail_table)

    # Action menu - conditionally show "View markdown" based on availability
    has_markdown = failure.get("markdown_path") and failure["markdown_path"] != "N/A"

    console.print("\n[bold yellow]Actions:[/bold yellow]")
    if has_markdown:
        console.print("  [v] View markdown content")
    console.print("  [r] Retry extraction")
    console.print("  [s] Skip permanently")
    console.print("  [b] Back to failure list")

    # Build choices list dynamically
    choices = ["r", "s", "b"]
    if has_markdown:
        choices.insert(0, "v")

    action = Prompt.ask("\n[bold]Select action[/bold]", choices=choices, default="b")

    if action == "b":
        return
    elif action == "v":
        _view_markdown(failure)
        input("\n[dim]Press Enter to continue...[/dim]")
    elif action == "r":
        if db.update_llm_failure(failure["id"], "retry"):
            console.print(f"\n[green]✅ Marked {failure['company_name']} for retry[/green]")
        else:
            console.print("\n[red]❌ Failed to update failure record[/red]")
        input("\n[dim]Press Enter to continue...[/dim]")
    elif action == "s":
        if db.update_llm_failure(failure["id"], "skip"):
            console.print(f"\n[yellow]⏭️  Skipped {failure['company_name']} permanently[/yellow]")
        else:
            console.print("\n[red]❌ Failed to update failure record[/red]")
        input("\n[dim]Press Enter to continue...[/dim]")


def _view_markdown(failure):
    """View the markdown content of a failed extraction"""
    from pathlib import Path

    markdown_path = failure.get("markdown_path")
    if not markdown_path:
        console.print("\n[red]❌ No markdown path available for this failure[/red]")
        return

    md_file = Path(markdown_path)
    if not md_file.exists():
        console.print(f"\n[red]❌ Markdown file not found: {markdown_path}[/red]")
        return

    try:
        content = md_file.read_text()
        # Show first 1000 characters
        preview = content[:1000]
        if len(content) > 1000:
            preview += "\n\n[dim]... (truncated, showing first 1000 chars)[/dim]"

        console.print("\n[bold yellow]📄 Markdown Preview:[/bold yellow]\n")
        console.print(Panel(preview, title=f"[cyan]{md_file.name}[/cyan]", border_style="cyan"))
    except Exception as e:
        console.print(f"\n[red]❌ Error reading markdown: {e}[/red]")


def _retry_all_failures(db, failures):  # pragma: no cover
    """Mark all pending failures for retry"""
    confirm = Prompt.ask(
        f"\n[bold yellow]⚠️  Retry all {len(failures)} pending failures?[/bold yellow]",
        choices=["y", "n"],
        default="n",
    )

    if confirm == "y":
        success_count = 0
        for failure in failures:
            if db.update_llm_failure(failure["id"], "retry"):
                success_count += 1

        console.print(
            f"\n[green]✅ Marked {success_count}/{len(failures)} failures for retry[/green]"
        )
        input("\n[dim]Press Enter to continue...[/dim]")


def _skip_all_failures(db, failures):  # pragma: no cover
    """Skip all pending failures permanently"""
    confirm = Prompt.ask(
        f"\n[bold yellow]⚠️  Skip all {len(failures)} pending failures permanently?[/bold yellow]",
        choices=["y", "n"],
        default="n",
    )

    if confirm == "y":
        success_count = 0
        for failure in failures:
            if db.update_llm_failure(failure["id"], "skip"):
                success_count += 1

        console.print(
            f"\n[yellow]⏭️  Skipped {success_count}/{len(failures)} failures permanently[/yellow]"
        )
        input("\n[dim]Press Enter to continue...[/dim]")


def select_advanced_options(sources: list[str]) -> dict:
    """Select advanced options for company scraping"""
    console.print("\n[bold yellow]Step 3:[/bold yellow] Advanced Options\n")

    options = {"llm_extraction": False}

    # Only show if Companies source is selected
    if "companies" not in sources:
        return options

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Feature", style="cyan", width=25)
    table.add_column("Status", style="green", width=12)
    table.add_column("Description", style="white")

    # LLM Extraction option
    table.add_row(
        "🤖 LLM Extraction",
        "Experimental",
        "Use Claude 3.5 Sonnet for job extraction (OpenRouter API)",
    )

    console.print(table)

    info = """[bold yellow]About LLM Extraction:[/bold yellow]

[cyan]What it does:[/cyan]
  • Runs Claude 3.5 Sonnet alongside regex extraction
  • Compares LLM vs regex results for validation
  • Stores extraction method for each job ('llm' vs 'regex')

[cyan]Requirements:[/cyan]
  • OpenRouter API key in .env (OPENROUTER_API_KEY)
  • Budget: $5/month limit (tracked automatically)
  • Each company extraction uses ~1-2 cents

[cyan]Status:[/cyan]
  • Both methods run in parallel (dual extraction)
  • LLM failures gracefully fall back to regex
  • Budget exceeded = auto-switches to regex only

[yellow]Note: This is experimental. Regex is the production method.[/yellow]"""

    console.print(Panel(info, border_style="yellow", padding=(0, 1)))

    # Ask user
    enable_llm = Confirm.ask("\n[bold]Enable LLM extraction for this run?[/bold]", default=False)
    options["llm_extraction"] = enable_llm

    if enable_llm:
        console.print("\n[green]✓ LLM extraction enabled (dual extraction mode)[/green]")
    else:
        console.print("\n[dim]Using regex extraction only (production mode)[/dim]")

    return options


def select_action() -> str | None:
    """Select what action to perform"""
    console.print("\n[bold yellow]Step 4:[/bold yellow] Select Action\n")

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Option", style="cyan", width=8)
    table.add_column("Action", style="green", width=20)
    table.add_column("Description", style="white")

    table.add_row("1", "Scrape Only", "Fetch and score jobs, store in database")
    table.add_row("2", "Send Digest", "Send email digest with stored jobs")
    table.add_row("3", "Scrape + Digest", "Run scraper then send digest email")
    table.add_row("c", "View Criteria", "Show scoring criteria and grading scale")
    table.add_row("f", "LLM Failures", "Review and retry failed LLM extractions")
    table.add_row("b", "Back", "Return to profile selection")
    table.add_row("q", "Quit", "Exit application")

    console.print(table)

    choice = Prompt.ask(
        "\n[bold]Select action[/bold]",
        choices=["1", "2", "3", "c", "f", "b", "q"],
        default="3",
    )

    # Map choices to actions
    choice_map = {
        "q": None,
        "b": "back",
        "c": "criteria",
        "f": "failures",
        "1": "scrape",
        "2": "digest",
        "3": "both",
    }

    return choice_map.get(choice, "both")


def select_digest_options() -> dict:
    """Select digest options (dry-run, force-resend)"""
    console.print("\n[bold yellow]Step 5:[/bold yellow] Digest Options\n")

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
    profile: str,
    sources: list[str],
    action: str,
    advanced_options: dict | None = None,
    digest_options: dict | None = None,
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

    # Add advanced options if applicable
    if advanced_options and advanced_options.get("llm_extraction"):
        summary_text += "\n[bold]Advanced:[/bold] 🤖 LLM Extraction Enabled"

    # Add digest mode if applicable
    if digest_options and action in ["digest", "both"]:
        if digest_options.get("dry_run"):
            digest_mode = "Dry Run (testing)"
        elif digest_options.get("force_resend"):
            digest_mode = "Force Resend (re-send previous jobs)"
        else:
            digest_mode = "Production (real digest)"
        summary_text += f"\n[bold]Digest Mode:[/bold] {digest_mode}"
        summary_text += "\n[bold]CC:[/bold] adamkwhite@gmail.com"

    summary = Panel(
        summary_text,
        title="[bold cyan]Execution Plan[/bold cyan]",
        border_style="cyan",
    )

    console.print(summary)

    return Confirm.ask("\n[bold green]Proceed with execution?[/bold green]", default=True)


def run_scraper(profile: str, sources: list[str], advanced_options: dict | None = None) -> int:
    """Execute the unified scraper"""
    console.print("\n[bold green]Running Job Scraper...[/bold green]\n")

    # Build command
    cmd = ["job-agent-venv/bin/python", "src/jobs/weekly_unified_scraper.py", "--profile", profile]

    # Add source-specific flags
    if len(sources) < 2:  # Not "all" (only 2 sources now: email + companies)
        if "email" in sources and len(sources) == 1:
            cmd.append("--email-only")
        elif "companies" in sources and len(sources) == 1:
            cmd.append("--companies-only")

    # Add advanced options
    if advanced_options and advanced_options.get("llm_extraction"):
        cmd.append("--llm-extraction")
        console.print("[yellow]🤖 LLM Extraction: ENABLED (dual extraction mode)[/yellow]")

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

            # Step 3: Advanced options (if applicable)
            advanced_options = select_advanced_options(sources)

            # Step 4: Select action
            action = select_action()
            if action is None:
                console.print("\n[yellow]Goodbye![/yellow]\n")
                sys.exit(0)
            elif action == "back":
                continue
            elif action == "criteria":
                show_criteria()
                continue
            elif action == "failures":
                review_llm_failures()
                continue

            # Step 5: Select digest options (if sending digest)
            digest_options = {}
            if action in ["digest", "both"]:
                digest_options = select_digest_options()

            # Step 6: Confirm and execute
            if not confirm_execution(profile, sources, action, advanced_options, digest_options):
                console.print("\n[yellow]Cancelled. Returning to menu...[/yellow]\n")
                input("Press Enter to continue...")
                continue

            # Execute
            success = True

            if action in ["scrape", "both"]:
                returncode = run_scraper(profile, sources, advanced_options)
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
