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

from api.company_service import CompanyService
from utils.health_checker import SystemHealthChecker
from utils.profile_manager import get_profile_manager
from utils.score_thresholds import Grade

# Constants for duplicated string literals (SonarCloud S1192 fix)
SEPARATOR_TOP = "\n[bold cyan]═══════════════════════════════════════════════[/bold cyan]"
SEPARATOR_BOTTOM = "[bold cyan]═══════════════════════════════════════════════[/bold cyan]\n"
SEPARATOR_FULL = "\n[bold cyan]═══════════════════════════════════════════════[/bold cyan]\n"
SEPARATOR_MAGENTA_TOP = (
    "\n[bold magenta]═══════════════════════════════════════════════[/bold magenta]"
)
SEPARATOR_MAGENTA_BOTTOM = (
    "[bold magenta]═══════════════════════════════════════════════[/bold magenta]\n"
)
PYTHON_EXECUTABLE = "job-agent-venv/bin/python"
STYLE_BOLD_MAGENTA = "bold magenta"
LABEL_LAST_RUN = "Last Run"
PROMPT_SELECT_ACTION = "\n[bold]Select action[/bold]"
PROMPT_PRESS_ENTER = "\n[dim]Press Enter to continue...[/dim]"

console = Console()


def clear_screen():
    """Clear the terminal screen"""
    os.system("clear" if os.name != "nt" else "cls")  # nosec B605


def press_enter_to_continue():
    """Display styled 'Press Enter' prompt and wait for input"""
    console.print("\n[dim]Press Enter to return to menu...[/dim]")
    input()


def show_header():
    """Display the application header"""
    clear_screen()
    header = """
[bold cyan]╔═══════════════════════════════════════════════╗[/bold cyan]
[bold cyan]║[/bold cyan]     [bold white]Job Agent Pipeline Controller[/bold white]       [bold cyan]║[/bold cyan]
[bold cyan]╚═══════════════════════════════════════════════╝[/bold cyan]
    """
    console.print(header)


def _handle_utility_action(sources: list[str]) -> bool | None:
    """Handle utility actions from source selection menu

    Args:
        sources: Selected sources from select_sources()

    Returns:
        True: Utility action handled, continue to next iteration
        False: User quit application
        None: Not a utility action, proceed to main workflow
    """
    if not sources:  # User quit
        console.print("\n[yellow]Goodbye![/yellow]\n")
        return False
    elif sources == ["utility:credits"]:
        check_api_credits()
        return True
    elif sources == ["utility:companies"]:
        manage_companies()
        return True
    elif sources == ["utility:health"]:
        show_system_health()
        return True

    return None  # Not a utility action


def _handle_secondary_action(action: str | None) -> bool | None:
    """Handle secondary actions from action selection menu

    Args:
        action: Selected action from select_action()

    Returns:
        True: Secondary action handled, continue to next iteration
        False: User quit application
        None: Not a secondary action, proceed to main workflow
    """
    if action is None:  # User quit
        console.print("\n[yellow]Goodbye![/yellow]\n")
        return False
    elif action == "back":
        return True
    elif action == "criteria":
        show_criteria()
        return True
    elif action == "failures":
        review_llm_failures()
        return True
    elif action == "health":
        show_system_health()
        return True

    return None  # Main workflow action (scrape/digest/both)


def _run_scraper_if_needed(
    sources: list[str], inbox_profile: str | None, action: str
) -> tuple[bool, bool]:
    """Run the scraper step if required by action.

    Returns:
        Tuple of (scrape_success, should_continue).
        should_continue=False means caller should return early.
    """
    if action not in ["scrape", "both"]:
        return True, True

    scrape_success = run_scraper(sources, inbox_profile)
    if scrape_success:
        console.print("\n[green]✓ Scraper completed successfully![/green]")
        return True, True

    console.print("\n[red]✗ Scraper failed![/red]")
    if not Confirm.ask("\n[bold]Continue anyway?[/bold]", default=False):
        console.print("\n[yellow]Returning to menu...[/yellow]\n")
        press_enter_to_continue()
        return False, False
    return False, True


def _select_digest_recipients_if_needed(action: str) -> tuple[list[str] | None, bool]:
    """Select digest recipients if required by action.

    Returns:
        Tuple of (recipients, should_continue).
        should_continue=False means caller should return early.
    """
    if action not in ["digest", "both"]:
        return None, True

    recipients = select_digest_recipients()
    if not recipients:
        console.print("\n[yellow]Digest skipped. Returning to menu...[/yellow]\n")
        press_enter_to_continue()
        return None, False
    return recipients, True


def _execute_workflow(sources: list[str], inbox_profile: str | None, action: str) -> None:
    """Execute the scrape/digest workflow

    Args:
        sources: Selected job sources (companies, email)
        inbox_profile: Email inbox profile (None if email not selected)
        action: Action to perform ("scrape", "digest", or "both")
    """
    # Step 3: Run Scraper (if needed)
    scrape_success, should_continue = _run_scraper_if_needed(sources, inbox_profile, action)
    if not should_continue:
        return

    # Step 4: Select Digest Recipients (if needed)
    digest_recipients, should_continue = _select_digest_recipients_if_needed(action)
    if not should_continue:
        return

    # Step 5: Digest Options (if sending digest)
    digest_options = select_digest_options() if digest_recipients else {}

    # Step 6: Confirm & Execute
    if not confirm_execution(sources, inbox_profile, action, digest_recipients, digest_options):
        console.print("\n[yellow]Cancelled. Returning to menu...[/yellow]\n")
        press_enter_to_continue()
        return

    # Execute digest (scraping already done if needed) and show results
    digest_success = _send_digest_if_needed(digest_recipients, digest_options)

    # Show final results and wait
    _show_workflow_results(scrape_success, digest_success)


def _send_digest_if_needed(
    digest_recipients: list[str] | None,
    digest_options: dict,
) -> bool:
    """Send digest if recipients selected. Returns True if success (or no digest needed)."""
    if not digest_recipients:
        return True

    digest_success = send_digest(
        digest_recipients,
        dry_run=digest_options.get("dry_run", False),
        force_resend=digest_options.get("force_resend", False),
    )
    if not digest_success:
        console.print("\n[red]✗ Digest send failed![/red]")
    else:
        console.print("\n[green]✓ Digest sent successfully![/green]")
    return digest_success


def _show_workflow_results(scrape_success: bool, digest_success: bool) -> None:
    """Display final workflow results and wait for user."""
    if scrape_success and digest_success:
        console.print("\n[bold green]✓ All operations completed successfully![/bold green]")
    else:
        console.print("\n[bold red]✗ Some operations failed. Check logs for details.[/bold red]")
    console.print("\n[dim]Press Enter to continue (or Ctrl+C to exit)...[/dim]")
    input()


def select_sources() -> tuple[list[str], str | None]:
    """Select job sources to scrape (no profile needed upfront)

    Returns:
        (sources, inbox_profile):
            - sources: List of source codes ["companies", "email"]
                      Note: "companies" includes Ministry of Testing
            - inbox_profile: Profile ID if email selected, else None
    """
    console.print("\n[bold yellow]Step 1:[/bold yellow] Select Job Sources\n")

    table = Table(box=box.ROUNDED, show_header=True, header_style=STYLE_BOLD_MAGENTA)
    table.add_column("Source", style="cyan", width=8)
    table.add_column("Description", style="white", width=40)

    table.add_row("1", "Company Monitoring")
    table.add_row("2", "Email Processing")
    table.add_row("a", "Select All Sources")
    table.add_row("", "")  # Blank row separator
    table.add_row("api", "API Credits (Check LLM/Firecrawl status)")
    table.add_row("c", "Companies (Review auto-discovered)")
    table.add_row("h", "System Health")
    table.add_row("q", "Quit")

    console.print(table)
    console.print(
        "\n[dim]Note: Company monitoring is profile-agnostic (jobs scored for ALL profiles).[/dim]"
    )
    console.print("[dim]      Email processing requires selecting which inbox to check.[/dim]")
    console.print(
        "\n[dim]Enter comma-separated options (e.g., '1,2' or 'all'). Default is 'all'.[/dim]"
    )

    choice = Prompt.ask("\n[bold]Select sources[/bold]", default="a").lower().strip()

    # Handle utility actions
    utility_map = {
        "q": ([], None),
        "api": (["utility:credits"], None),
        "c": (["utility:companies"], None),
        "h": (["utility:health"], None),
    }
    if choice in utility_map:
        return utility_map[choice]

    # Parse source selections
    sources = []
    if choice == "a" or choice == "all":
        sources = ["companies", "email"]
    else:
        source_map = {
            "1": "companies",
            "2": "email",
        }
        for item in choice.split(","):
            item = item.strip()
            if item in source_map:
                source = source_map[item]
                if source not in sources:
                    sources.append(source)

    # If no valid sources selected, default to companies
    if not sources:
        console.print(
            "[yellow]No valid sources selected. Defaulting to Company Monitoring.[/yellow]"
        )
        sources = ["companies"]

    # If email selected, prompt for inbox
    inbox_profile = None
    if "email" in sources:
        inbox_profile = _select_inbox()
        if not inbox_profile:
            # Remove email from sources if no inbox selected
            sources.remove("email")
            console.print("[yellow]Email processing cancelled (no inbox selected).[/yellow]")

    return sources, inbox_profile


def _select_inbox() -> str | None:
    """Select which email inbox to check (only for email processing)

    Returns:
        Profile ID of selected inbox, "all" for all inboxes, or None if cancelled
    """
    console.print("\n[bold yellow]Email Inbox Selection:[/bold yellow]\n")

    # Load profiles with email credentials
    pm = get_profile_manager()
    enabled_profiles = pm.get_enabled_profiles()

    profiles_with_email = [
        p for p in enabled_profiles if hasattr(p, "email_username") and p.email_username
    ]

    if not profiles_with_email:
        console.print("[red]No email accounts configured in any profile![/red]")
        console.print("[dim]Check profiles/*/email_username in profile JSON files.[/dim]")
        return None

    table = Table(box=box.ROUNDED, show_header=True, header_style=STYLE_BOLD_MAGENTA)
    table.add_column("Option", style="cyan", width=8)
    table.add_column("Profile", style="green", width=20)
    table.add_column("Email Inbox", style="blue", width=35)

    profile_map = {}
    for i, profile in enumerate(profiles_with_email, 1):
        table.add_row(str(i), profile.name, profile.email_username)
        profile_map[str(i)] = profile.id

    table.add_row("a", "All Inboxes", f"Process all {len(profiles_with_email)} configured inboxes")
    table.add_row("c", "Cancel", "Skip email processing")

    console.print(table)

    choices = list(profile_map.keys()) + ["a", "c"]
    choice = Prompt.ask("\n[bold]Select inbox[/bold]", choices=choices, default="a")

    if choice == "c":
        return None
    elif choice == "a":
        return "all"  # Special value for all inboxes
    else:
        return profile_map[choice]


def select_digest_recipients() -> list[str] | None:
    """Select which profiles should receive digest emails

    Returns:
        List of profile IDs to send to, or None to skip digest
        Special value ["all"] means all enabled profiles
    """
    console.print("\n[bold yellow]Step 4:[/bold yellow] Select Digest Recipients\n")

    # Load enabled profiles
    pm = get_profile_manager()
    enabled_profiles = pm.get_enabled_profiles()

    if not enabled_profiles:
        console.print("[red]No enabled profiles found![/red]")
        return None

    table = Table(box=box.ROUNDED, show_header=True, header_style=STYLE_BOLD_MAGENTA)
    table.add_column("Option", style="cyan", width=8)
    table.add_column("Recipient", style="green", width=25)
    table.add_column("Email", style="blue", width=30)

    profile_map = {}
    for i, profile in enumerate(enabled_profiles, 1):
        table.add_row(str(i), profile.name, profile.email)
        profile_map[str(i)] = profile.id

    table.add_row("a", "All Enabled Profiles", f"Sends to {len(enabled_profiles)} profiles")
    table.add_row("s", "Skip Digest", "Don't send any digest")

    console.print(table)
    console.print(
        "\n[dim]Note: Multiple selections allowed (e.g., '1,2' sends to first two profiles).[/dim]"
    )
    console.print(
        "[dim]      Digest tracking is profile-specific (same job can go to multiple profiles).[/dim]"
    )

    choice = Prompt.ask("\n[bold]Select recipients[/bold]", default="a").lower().strip()

    if choice == "s":
        return None
    elif choice == "a" or choice == "all":
        return ["all"]
    else:
        # Parse comma-separated choices
        recipients = []
        for item in choice.split(","):
            item = item.strip()
            if item in profile_map:
                recipients.append(profile_map[item])

        if not recipients:
            console.print("[yellow]No valid recipients selected. Skipping digest.[/yellow]")
            return None

        return recipients


def show_criteria():
    """Display scoring criteria and grading information"""
    clear_screen()

    console.print(SEPARATOR_TOP)
    console.print("[bold cyan]         JOB SCORING CRITERIA (Wesley)         [/bold cyan]")
    console.print(SEPARATOR_BOTTOM)

    # Scoring breakdown
    console.print("[bold yellow]📊 Scoring System (0-115 points)[/bold yellow]\n")

    scoring_table = Table(box=box.ROUNDED, show_header=True, header_style=STYLE_BOLD_MAGENTA)
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

    grade_table = Table(box=box.ROUNDED, show_header=True, header_style=STYLE_BOLD_MAGENTA)
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

    source_table = Table(box=box.ROUNDED, show_header=True, header_style=STYLE_BOLD_MAGENTA)
    source_table.add_column("Source", style="cyan", width=20)
    source_table.add_column("Min Score", style="green", width=12)
    source_table.add_column("Reasoning", style="white")

    source_table.add_row("Email newsletters", "All", "High signal newsletters")
    source_table.add_row("Company monitoring", "50+ (D)", "68 monitored companies")

    console.print(source_table)

    # Notifications
    console.print("\n[bold yellow]📧 Notification Rules[/bold yellow]\n")
    console.print(f"  • Immediate SMS/Email: A/B grade jobs ({Grade.B.value}+) only")
    console.print(f"  • Weekly Digest: C+ grade jobs ({Grade.C.value}+)")
    console.print("  • To: wesvanooyen@gmail.com")
    console.print("  • CC: adamkwhite@gmail.com")

    console.print(SEPARATOR_FULL)

    press_enter_to_continue()


def show_system_health():  # pragma: no cover
    """Display system health dashboard with errors, budget, and activity

    Note: TUI functions are excluded from coverage requirements as they will be
    tested through manual testing and integration tests
    """
    clear_screen()
    show_header()

    # Import database locally
    from database import JobDatabase

    db = JobDatabase()
    health_checker = SystemHealthChecker(db)
    health = health_checker.get_health_summary()

    console.print(SEPARATOR_TOP)
    console.print("[bold cyan]            🔍 SYSTEM HEALTH CHECK              [/bold cyan]")
    console.print(SEPARATOR_BOTTOM)

    # Create main health table
    health_table = Table(box=box.ROUNDED, show_header=False)
    health_table.add_column("Metric", style="bold cyan", width=30)
    health_table.add_column("Status", width=50)

    # LLM Failures Section
    failures = health["llm_failures"]
    if failures["total_pending"] > 0:
        failure_color = "red" if failures["total_pending"] >= 10 else "yellow"
    else:
        failure_color = "green"

    health_table.add_row(
        "LLM Failures (Pending)",
        f"[{failure_color}]{failures['total_pending']}[/{failure_color}]",
    )
    health_table.add_row(
        "LLM Failures (Last 24h)",
        f"[dim]{failures['last_24h']}[/dim]",
    )

    if failures["most_common_error"]:
        health_table.add_row(
            "Most Common Error",
            f"[dim]{failures['most_common_error']} ({failures['most_common_count']} times)[/dim]",
        )

    # Budget Section
    health_table.add_row("", "")  # Blank row
    budget = health["budget"]
    budget_pct = budget["percentage_used"]

    if budget_pct >= 100:
        budget_color = "red"
    elif budget_pct >= 80:
        budget_color = "yellow"
    else:
        budget_color = "green"

    health_table.add_row(
        "Budget Usage",
        f"[{budget_color}]${budget['total_spent']:.2f} / ${budget['monthly_limit']:.2f} ({budget_pct:.1f}%)[/{budget_color}]",
    )
    health_table.add_row(
        "API Calls This Month",
        f"[dim]{budget['api_calls']}[/dim]",
    )
    health_table.add_row(
        "Remaining Budget",
        f"[dim]${budget['remaining']:.2f}[/dim]",
    )

    # Database Stats Section
    health_table.add_row("", "")  # Blank row
    db_stats = health["database"]
    health_table.add_row("Total Jobs in DB", f"[green]{db_stats['total_jobs']:,}[/green]")
    health_table.add_row("A/B Grade Jobs", f"[green]{db_stats['high_quality_jobs']:,}[/green]")

    # Grade breakdown
    by_grade = db_stats.get("by_grade", {})
    if by_grade:
        grade_str = ", ".join([f"{grade}: {count}" for grade, count in sorted(by_grade.items())])
        health_table.add_row("By Grade", f"[dim]{grade_str}[/dim]")

    # Recent Activity Section
    health_table.add_row("", "")  # Blank row
    activity = health["recent_activity"]
    if activity["last_run_time"]:
        from datetime import datetime

        try:
            last_run = datetime.fromisoformat(activity["last_run_time"])
            time_ago = datetime.now() - last_run
            if time_ago.days > 0:
                time_str = f"{time_ago.days} days ago"
            elif time_ago.seconds > 3600:
                time_str = f"{time_ago.seconds // 3600} hours ago"
            else:
                time_str = f"{time_ago.seconds // 60} minutes ago"
        except ValueError:
            time_str = activity["last_run_time"]

        health_table.add_row("Last Scraper Run", f"[green]{time_str}[/green]")
        health_table.add_row("Jobs Found", f"[dim]{activity['jobs_found_last_run']}[/dim]")
        if activity["last_run_source"]:
            health_table.add_row("Source", f"[dim]{activity['last_run_source']}[/dim]")
    else:
        health_table.add_row("Last Scraper Run", "[yellow]No runs found[/yellow]")

    # Company Scraper Section
    health_table.add_row("", "")  # Blank row
    company_health = health["company_scraper"]

    # Only display if companies are configured
    if company_health["total_companies"] > 0:
        # Success rate with color coding
        success_rate = company_health["success_rate"]
        if success_rate >= 90:
            success_color = "green"
        elif success_rate >= 75:
            success_color = "yellow"
        else:
            success_color = "red"

        health_table.add_row(
            "Company Scraper Success",
            f"[{success_color}]{success_rate:.1f}% ({company_health['active_companies'] - company_health['total_failures']}/{company_health['active_companies']})[/{success_color}]",
        )

        # At-risk companies
        if company_health["at_risk_count"] > 0:
            health_table.add_row(
                "At Risk (3-4 failures)",
                f"[yellow]{company_health['at_risk_count']} companies[/yellow]",
            )

        # Auto-disabled companies
        if company_health["auto_disabled_count"] > 0:
            health_table.add_row(
                "Auto-Disabled (5 failures)",
                f"[red]{company_health['auto_disabled_count']} companies[/red]",
            )

        # Companies checked recently
        health_table.add_row(
            "Scraped in Last 24h",
            f"[dim]{company_health['recent_scrape_count']}/{company_health['total_companies']}[/dim]",
        )

    console.print(health_table)

    # Critical Issues Section
    critical = health["critical_issues"]
    if critical:
        console.print("\n[bold red]⚠️  CRITICAL ISSUES:[/bold red]\n")

        issues_table = Table(box=box.ROUNDED, show_header=False)
        issues_table.add_column("Issue", style="white")

        for issue in critical:
            color = issue["severity"]
            issues_table.add_row(f"[{color}]• {issue['message']}[/{color}]")
            issues_table.add_row(f"[dim]  → {issue['action']}[/dim]")

        console.print(issues_table)
    else:
        console.print("\n[bold green]✅ No critical issues detected[/bold green]")

    console.print(SEPARATOR_FULL)

    # Offer options
    console.print(
        "[dim]Actions: \\[f] LLM failures | \\[c] Company failures | \\[b] Back to menu[/dim]"
    )
    choice = Prompt.ask("\n[bold]Action[/bold]", choices=["f", "c", "b"], default="b")

    if choice == "f":
        review_llm_failures()
    elif choice == "c":
        review_company_failures()


def check_api_credits():  # pragma: no cover
    """Display API credit status for LLM and Firecrawl

    Note: TUI functions are excluded from coverage requirements as they will be
    replaced with Textual framework (Issue #119). Manual testing confirms functionality.
    """
    import json
    from pathlib import Path

    console.clear()
    console.print(SEPARATOR_MAGENTA_TOP)
    console.print("[bold magenta]              API CREDIT STATUS                  [/bold magenta]")
    console.print(SEPARATOR_MAGENTA_BOTTOM)

    # Check LLM Budget (OpenRouter/Claude API)
    console.print("[bold yellow]🤖 LLM Extraction (Claude 3.5 Sonnet)[/bold yellow]\n")

    from datetime import datetime

    current_month = datetime.now().strftime("%Y-%m")
    llm_budget_file = Path(f"logs/llm-budget-{current_month}.json")
    if llm_budget_file.exists():
        try:
            with open(llm_budget_file) as f:
                data = json.load(f)

            total_cost = data.get("total_cost", 0)
            budget = 5.00  # From config

            remaining = budget - total_cost
            usage_pct = (total_cost / budget * 100) if budget > 0 else 0

            # Create status table
            llm_table = Table(box=box.ROUNDED, show_header=True, header_style=STYLE_BOLD_MAGENTA)
            llm_table.add_column("Metric", style="cyan", width=20)
            llm_table.add_column("Value", style="white", width=25)

            llm_table.add_row("Total Spent", f"${total_cost:.2f}")
            llm_table.add_row("Monthly Budget", f"${budget:.2f}")
            llm_table.add_row("Remaining", f"${remaining:.2f}")

            # Color code usage percentage
            if usage_pct < 50:
                usage_color = "green"
            elif usage_pct < 80:
                usage_color = "yellow"
            else:
                usage_color = "red"

            llm_table.add_row("Usage", f"[{usage_color}]{usage_pct:.1f}%[/{usage_color}]")
            llm_table.add_row("API Calls", str(len(data.get("requests", []))))

            console.print(llm_table)

            # Status indicator
            if remaining > 0:
                console.print(
                    f"\n[green]✓ {remaining / 0.01:.0f} more company scans available[/green]"
                )
            else:
                console.print("\n[red]⚠ Budget exceeded![/red]")

        except Exception as e:
            console.print(f"[red]Error reading LLM budget: {e}[/red]")
    else:
        console.print("[dim]No LLM budget data found (not used this month)[/dim]")

    # Check Firecrawl API status
    console.print("\n\n[bold yellow]🔥 Firecrawl API[/bold yellow]\n")

    firecrawl_table = Table(box=box.ROUNDED, show_header=True, header_style=STYLE_BOLD_MAGENTA)
    firecrawl_table.add_column("Metric", style="cyan", width=20)
    firecrawl_table.add_column("Status", style="white", width=25)

    # Check for recent successful runs
    import subprocess

    try:
        # Check most recent company scraper run
        result = subprocess.run(
            ["tail", "-100", "logs/unified_weekly_scraper.log"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0 and "companies checked:" in result.stdout.lower():
            # Extract last run stats
            lines = result.stdout.split("\n")
            for line in reversed(lines):
                if "companies checked:" in line.lower():
                    firecrawl_table.add_row("LABEL_LAST_RUN", "[green]✓ Successful[/green]")
                    break
            else:
                firecrawl_table.add_row("LABEL_LAST_RUN", "[dim]No recent runs[/dim]")
        else:
            firecrawl_table.add_row("LABEL_LAST_RUN", "[dim]No logs found[/dim]")

        firecrawl_table.add_row(
            "API Key",
            "[green]✓ Configured[/green]" if Path(".env").exists() else "[red]✗ Missing[/red]",
        )
        firecrawl_table.add_row("Rate Limits", "[dim]No known issues[/dim]")

    except Exception as e:
        firecrawl_table.add_row("Status", f"[red]Error: {e}[/red]")

    console.print(firecrawl_table)

    console.print(SEPARATOR_FULL)
    console.print(
        "[dim]Note: Firecrawl credits are managed through your Firecrawl account dashboard.[/dim]"
    )

    press_enter_to_continue()


def review_llm_failures():  # pragma: no cover
    """Interactive interface for reviewing LLM extraction failures

    Note: TUI functions are excluded from coverage requirements as they will be
    replaced with Textual framework (Issue #119). Manual testing confirms functionality.
    """

    from database import JobDatabase

    db = JobDatabase()

    while True:
        console.clear()
        console.print(SEPARATOR_MAGENTA_TOP)
        console.print(
            "[bold magenta]           LLM EXTRACTION FAILURES REVIEW           [/bold magenta]"
        )
        console.print(SEPARATOR_MAGENTA_BOTTOM)

        # Get pending failures
        failures = db.get_llm_failures(review_action="pending", limit=50)

        if not failures:
            console.print("[green]✅ No pending LLM extraction failures to review![/green]\n")
            press_enter_to_continue()
            return

        # Summary stats
        console.print(f"[bold yellow]📊 Summary:[/bold yellow] {len(failures)} pending failures\n")

        # Display failures table
        table = Table(box=box.ROUNDED, show_header=True, header_style=STYLE_BOLD_MAGENTA)
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
        console.print("  \\[r] Review specific failure (view details, retry, skip)")
        console.print("  \\[a] Retry all pending failures")
        console.print("  \\[s] Skip all pending failures")
        console.print("  \\[b] Back to main menu")

        choice = Prompt.ask(PROMPT_SELECT_ACTION, choices=["r", "a", "s", "b"], default="b")

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
            input(PROMPT_PRESS_ENTER)
            return

        failure = failures[failure_idx]
    except ValueError:
        console.print("[red]❌ Invalid input. Enter a number.[/red]")
        input(PROMPT_PRESS_ENTER)
        return

    # Show failure details
    console.clear()
    console.print(SEPARATOR_TOP)
    console.print(f"[bold cyan]      FAILURE DETAILS - {failure['company_name']}      [/bold cyan]")
    console.print(SEPARATOR_BOTTOM)

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
        console.print("  \\[v] View markdown content")
    console.print("  \\[r] Retry extraction")
    console.print("  \\[s] Skip permanently")
    console.print("  \\[b] Back to failure list")

    # Build choices list dynamically
    choices = ["r", "s", "b"]
    if has_markdown:
        choices.insert(0, "v")

    action = Prompt.ask(PROMPT_SELECT_ACTION, choices=choices, default="b")

    if action == "b":
        return
    elif action == "v":
        _view_markdown(failure)
        input(PROMPT_PRESS_ENTER)
    elif action == "r":
        if db.update_llm_failure(failure["id"], "retry"):
            console.print(f"\n[green]✅ Marked {failure['company_name']} for retry[/green]")
        else:
            console.print("\n[red]❌ Failed to update failure record[/red]")
        input(PROMPT_PRESS_ENTER)
    elif action == "s":
        if db.update_llm_failure(failure["id"], "skip"):
            console.print(f"\n[yellow]⏭️  Skipped {failure['company_name']} permanently[/yellow]")
        else:
            console.print("\n[red]❌ Failed to update failure record[/red]")
        input(PROMPT_PRESS_ENTER)


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
        input(PROMPT_PRESS_ENTER)


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
        input(PROMPT_PRESS_ENTER)


def review_company_failures():  # pragma: no cover
    """Display detailed view of company scraper failures

    Note: TUI functions are excluded from coverage requirements as they will be
    replaced with Textual framework (Issue #119). Manual testing confirms functionality.
    """
    import sqlite3

    from database import JobDatabase

    db = JobDatabase()
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()

    console.clear()
    console.print(SEPARATOR_MAGENTA_TOP)
    console.print("[bold magenta]         COMPANY SCRAPER FAILURES REVIEW         [/bold magenta]")
    console.print(SEPARATOR_MAGENTA_BOTTOM)

    # Get companies with failures
    cursor.execute("""
        SELECT
            name,
            consecutive_failures,
            last_error,
            last_checked,
            active,
            auto_disabled_at
        FROM companies
        WHERE consecutive_failures > 0
        ORDER BY consecutive_failures DESC, name ASC
    """)
    failures = cursor.fetchall()
    conn.close()

    if not failures:
        console.print("[green]✅ No company scraper failures! All companies healthy.[/green]\n")
        press_enter_to_continue()
        return

    # Summary stats
    at_risk = sum(1 for f in failures if 3 <= f[1] < 5 and f[4] == 1)
    auto_disabled = sum(1 for f in failures if f[1] >= 5 or f[5] is not None)
    active_failures = sum(1 for f in failures if f[4] == 1)

    console.print(
        f"[bold yellow]📊 Summary:[/bold yellow] {len(failures)} companies with failures\n"
    )
    console.print(f"  • [yellow]At Risk (3-4 failures):[/yellow] {at_risk} companies")
    console.print(f"  • [red]Auto-Disabled (5+ failures):[/red] {auto_disabled} companies")
    console.print(f"  • [dim]Active with failures:[/dim] {active_failures} companies\n")

    # Display failures table
    table = Table(box=box.ROUNDED, show_header=True, header_style=STYLE_BOLD_MAGENTA)
    table.add_column("Company", style="white", width=25)
    table.add_column("Failures", style="yellow", width=10, justify="center")
    table.add_column("Status", style="white", width=12)
    table.add_column("Last Error", style="dim", width=35)
    table.add_column("Last Checked", style="dim", width=12)

    for name, failures_count, error, checked, _active, disabled_at in failures[:30]:
        # Determine status color and text
        if failures_count >= 5 or disabled_at:
            status = "[red]Disabled[/red]"
        elif failures_count >= 3:
            status = "[yellow]At Risk[/yellow]"
        else:
            status = "[dim]Active[/dim]"

        # Format error message
        error_msg = error if error else "Unknown"
        if len(error_msg) > 32:
            error_msg = error_msg[:29] + "..."

        # Format last checked
        checked_display = checked[:10] if checked else "Never"

        # Color code the failure count
        if failures_count >= 5:
            failure_display = f"[red]{failures_count}/5[/red]"
        elif failures_count >= 3:
            failure_display = f"[yellow]{failures_count}/5[/yellow]"
        else:
            failure_display = f"[dim]{failures_count}/5[/dim]"

        table.add_row(name, failure_display, status, error_msg, checked_display)

    console.print(table)

    if len(failures) > 30:
        console.print(f"\n[dim]Showing 30 of {len(failures)} companies with failures...[/dim]")

    # Action suggestions
    console.print("\n[bold yellow]💡 Recommended Actions:[/bold yellow]")
    if auto_disabled > 0:
        console.print(
            "  • [red]Auto-disabled companies:[/red] Review career page URLs, re-enable with SQL, or remove from monitoring"
        )
    if at_risk > 0:
        console.print(
            "  • [yellow]At-risk companies:[/yellow] Check logs/scraper_failures.log for patterns"
        )
    console.print("  • [dim]View logs:[/dim] tail -50 logs/scraper_failures.log")
    console.print(
        "  • [dim]Re-enable company:[/dim] UPDATE companies SET active=1, consecutive_failures=0 WHERE name='CompanyName'"
    )

    press_enter_to_continue()


def select_action() -> str | None:
    """Select what action to perform"""
    console.print("\n[bold yellow]Step 2:[/bold yellow] Select Action\n")

    table = Table(box=box.ROUNDED, show_header=True, header_style=STYLE_BOLD_MAGENTA)
    table.add_column("Option", style="cyan", width=8)
    table.add_column("Action", style="green", width=20)
    table.add_column("Description", style="white")

    table.add_row("1", "Scrape Only", "Fetch and score jobs, store in database")
    table.add_row("2", "Send Digest", "Send email digest with stored jobs")
    table.add_row("3", "Scrape + Digest", "Run scraper then send digest email")
    table.add_row("c", "View Criteria", "Show scoring criteria and grading scale")
    table.add_row("f", "LLM Failures", "Review and retry failed LLM extractions")
    table.add_row("h", "System Health", "View system health and error dashboard")
    table.add_row("b", "Back", "Return to profile selection")
    table.add_row("q", "Quit", "Exit application")

    console.print(table)

    choice = Prompt.ask(
        PROMPT_SELECT_ACTION,
        choices=["1", "2", "3", "c", "f", "h", "b", "q"],
        default="3",
    )

    # Map choices to actions
    choice_map = {
        "q": None,
        "b": "back",
        "c": "criteria",
        "f": "failures",
        "h": "health",
        "1": "scrape",
        "2": "digest",
        "3": "both",
    }

    return choice_map.get(choice, "both")


def select_digest_options() -> dict:
    """Select digest options (dry-run, force-resend)"""
    console.print("\n[bold yellow]Step 5:[/bold yellow] Digest Options\n")

    table = Table(box=box.ROUNDED, show_header=True, header_style=STYLE_BOLD_MAGENTA)
    table.add_column("Option", style="cyan", width=8)
    table.add_column("Mode", style="green", width=20)
    table.add_column("Sends Email?", style="white", width=14)
    table.add_column("Marks Sent?", style="white", width=14)
    table.add_column("Use Case", style="yellow")

    table.add_row("1", "Production", "✅ Yes", "✅ Yes", "Real digest")
    table.add_row("2", "Dry Run", "❌ No", "❌ No", "Testing/preview (default)")
    table.add_row("3", "Force Resend", "✅ Yes", "❌ No", "Re-send previous jobs")

    console.print(table)
    console.print(
        "\n[dim]Note: Use 'Dry Run' during testing to avoid marking jobs as sent for this profile.[/dim]"
    )
    console.print(
        "[dim]      Digest tracking is profile-specific - same job can be sent to multiple profiles.[/dim]"
    )

    choice = Prompt.ask("\n[bold]Select digest mode[/bold]", choices=["1", "2", "3"], default="2")

    return {
        "dry_run": choice == "2",
        "force_resend": choice == "3",
    }


def confirm_execution(
    sources: list[str],
    inbox_profile: str | None,
    action: str,
    digest_recipients: list[str] | None,
    digest_options: dict | None = None,
) -> bool:
    """Show summary and confirm execution"""
    console.print("\n[bold yellow]Step 6: Confirm Execution[/bold yellow]\n")

    # Map action codes to display names
    action_display = {
        "scrape": "Scrape Only",
        "digest": "Send Digest",
        "both": "Scrape and Send Digest",
    }
    action_text = action_display.get(action, action.title())

    # Build summary text
    summary_text = f"[bold]Sources:[/bold] {', '.join(sources).title()}"

    # Show inbox if email processing
    if inbox_profile:
        if inbox_profile == "all":
            summary_text += "\n[bold]Email Inbox:[/bold] All Configured Inboxes"
        else:
            pm = get_profile_manager()
            profile_obj = pm.get_profile(inbox_profile)
            inbox_name = profile_obj.name if profile_obj else inbox_profile
            inbox_email = (
                profile_obj.email_username
                if (profile_obj and hasattr(profile_obj, "email_username"))
                else "unknown"
            )
            summary_text += f"\n[bold]Email Inbox:[/bold] {inbox_name} ({inbox_email})"

    summary_text += f"\n[bold]Action:[/bold] {action_text}"

    # Show digest recipients if applicable
    if digest_recipients and action in ["digest", "both"]:
        pm = get_profile_manager()
        if digest_recipients == ["all"]:
            recipient_text = "All Enabled Profiles"
        else:
            names = []
            for pid in digest_recipients:
                profile_obj = pm.get_profile(pid)
                names.append(profile_obj.name if profile_obj else pid)
            recipient_text = ", ".join(names)
        summary_text += f"\n[bold]Digest Recipients:[/bold] {recipient_text}"

        # Add digest mode
        if digest_options:
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


def run_scraper(sources: list[str], inbox_profile: str | None = None) -> bool:
    """Execute the unified scraper

    Args:
        sources: List of source codes to scrape
        inbox_profile: Profile ID for email inbox (None if no email scraping)

    Returns:
        True if successful, False otherwise
    """
    console.print("\n[bold green]Running Job Scraper...[/bold green]\n")

    # Build command
    cmd = [PYTHON_EXECUTABLE, "src/jobs/weekly_unified_scraper.py"]

    # Add profile or all-inboxes flag if email processing selected
    if inbox_profile and "email" in sources:
        if inbox_profile == "all":
            cmd.append("--all-inboxes")
            console.print("[dim]Processing all configured email inboxes[/dim]")
        else:
            cmd.extend(["--profile", inbox_profile])

            # Show which inbox we're using
            pm = get_profile_manager()
            profile_obj = pm.get_profile(inbox_profile)
            if profile_obj and hasattr(profile_obj, "email_username"):
                console.print(f"[dim]Email inbox: {profile_obj.email_username}[/dim]")

    # Add source filters
    all_sources = ["companies", "email"]
    if len(sources) < len(all_sources):  # Not "all" sources
        if "email" in sources and len(sources) == 1:
            cmd.append("--email-only")
        elif "companies" in sources and len(sources) == 1:
            cmd.append("--companies-only")

    console.print(f"[dim]Command: {' '.join(cmd)}[/dim]\n")

    # Execute
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd())

    result = subprocess.run(cmd, env=env)
    return result.returncode == 0


def send_digest(
    recipients: list[str] | None, dry_run: bool = False, force_resend: bool = False
) -> bool:
    """Send email digest to selected recipients

    Args:
        recipients: List of profile IDs, or None to skip
                   Special: ["all"] sends to all enabled profiles
        dry_run: Preview only, don't send or mark as sent
        force_resend: Send email but don't mark as sent

    Returns:
        True if successful, False otherwise
    """
    if not recipients:
        console.print("[yellow]Skipping digest (no recipients selected)[/yellow]")
        return True

    # Determine mode
    if dry_run:
        mode = "DRY RUN"
    elif force_resend:
        mode = "FORCE RESEND"
    else:
        mode = "PRODUCTION"

    console.print(f"\n[bold green]Sending Email Digest ({mode})...[/bold green]\n")

    # Handle "all" recipients
    if recipients == ["all"]:
        cmd = [PYTHON_EXECUTABLE, "src/send_profile_digest.py", "--all"]
        if dry_run:
            cmd.append("--dry-run")
        if force_resend:
            cmd.append("--force-resend")

        console.print(f"[dim]Command: {' '.join(cmd)}[/dim]")
        console.print("[dim]Sending to all enabled profiles...[/dim]\n")

        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path.cwd())

        result = subprocess.run(cmd, env=env)
        return result.returncode == 0

    # Send to individual profiles sequentially
    pm = get_profile_manager()
    success_count = 0
    for profile_id in recipients:
        profile_obj = pm.get_profile(profile_id)
        profile_name = profile_obj.name if profile_obj else profile_id

        console.print(f"[cyan]→ Sending to {profile_name}...[/cyan]")

        cmd = [PYTHON_EXECUTABLE, "src/send_profile_digest.py", "--profile", profile_id]
        if dry_run:
            cmd.append("--dry-run")
        if force_resend:
            cmd.append("--force-resend")

        console.print(f"[dim]  Command: {' '.join(cmd)}[/dim]")

        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path.cwd())

        result = subprocess.run(cmd, env=env)
        if result.returncode == 0:
            success_count += 1
            console.print(f"[green]  ✓ Sent to {profile_name}[/green]\n")
        else:
            console.print(f"[red]  ✗ Failed to send to {profile_name}[/red]\n")

    # Report overall success
    if success_count == len(recipients):
        console.print(
            f"[bold green]✓ Successfully sent to all {success_count} recipients[/bold green]"
        )
        return True
    else:
        console.print(
            f"[bold yellow]⚠ Sent to {success_count}/{len(recipients)} recipients[/bold yellow]"
        )
        return success_count > 0


def manage_companies():
    """Review and manage auto-discovered companies"""
    console.print(SEPARATOR_TOP)
    console.print("[bold cyan]Company Management - Auto-Discovered Companies[/bold cyan]")
    console.print(SEPARATOR_BOTTOM)

    # Get all inactive companies with auto-discovery notes
    company_service = CompanyService()
    all_companies = company_service.get_all_companies(active_only=False)

    auto_discovered = [
        c for c in all_companies if c.get("active") == 0 and "Auto-discovered" in c.get("notes", "")
    ]

    if not auto_discovered:
        console.print("\n[green]✓ No auto-discovered companies pending review![/green]")
        console.print(
            "\n[dim]Companies are auto-discovered when jobs are scraped from emails.[/dim]"
        )
        press_enter_to_continue()
        return

    console.print(
        f"\n[yellow]Found {len(auto_discovered)} auto-discovered companies pending review[/yellow]\n"
    )

    # Display summary table
    table = Table(box=box.ROUNDED, show_header=True, header_style=STYLE_BOLD_MAGENTA)
    table.add_column("#", style="cyan", width=5)
    table.add_column("Company Name", style="green", width=30)
    table.add_column("Discovered", style="blue", width=20)
    table.add_column("Source", style="yellow", width=20)

    for i, company in enumerate(auto_discovered, 1):
        created_at = company.get("created_at", "")[:10]  # Just the date
        source = "Email" if "email" in company.get("notes", "").lower() else "Unknown"
        table.add_row(str(i), company.get("name", "Unknown"), created_at, source)

    console.print(table)
    console.print(
        "\n[dim]These companies were automatically discovered from job postings but need manual review.[/dim]"
    )

    # Review options
    console.print("\n[bold]Actions:[/bold]")
    console.print("  [cyan]r[/cyan] - Review companies one by one")
    console.print("  [cyan]l[/cyan] - List all with details")
    console.print("  [cyan]b[/cyan] - Back to main menu")

    choice = Prompt.ask(PROMPT_SELECT_ACTION, choices=["r", "l", "b"], default="r")

    if choice == "b":
        return
    elif choice == "l":
        _list_companies_detailed(auto_discovered)
        press_enter_to_continue()
    elif choice == "r":
        _review_companies_interactive(auto_discovered, company_service)


def _list_companies_detailed(companies: list[dict]):
    """Display detailed list of companies"""
    console.print(SEPARATOR_FULL)
    console.print("[bold cyan]Detailed Company List[/bold cyan]\n")

    for i, company in enumerate(companies, 1):
        console.print(f"\n[bold cyan]{i}. {company.get('name', 'Unknown')}[/bold cyan]")
        console.print(f"   ID: {company.get('id')}")
        console.print(f"   Created: {company.get('created_at', 'Unknown')}")
        console.print(f"   Placeholder URL: {company.get('careers_url', 'None')}")
        console.print(f"   Notes: {company.get('notes', 'None')}")


def _review_companies_interactive(companies: list[dict], company_service: CompanyService):
    """Review companies one by one interactively"""
    total = len(companies)
    activated = 0
    skipped = 0
    deleted = 0

    for i, company in enumerate(companies, 1):
        console.print(SEPARATOR_FULL)
        console.print(f"[bold cyan]Company {i} of {total}[/bold cyan]\n")

        # Display company details
        panel_content = f"""[bold green]{company.get("name", "Unknown")}[/bold green]

[yellow]Details:[/yellow]
  ID: {company.get("id")}
  Created: {company.get("created_at", "Unknown")}
  Current URL: {company.get("careers_url", "None")}

[yellow]Notes:[/yellow]
  {company.get("notes", "None")}"""

        console.print(Panel(panel_content, title="Company Information", border_style="cyan"))

        # Action options
        console.print("\n[bold]Actions:[/bold]")
        console.print("  [green]a[/green] - Activate (requires careers URL)")
        console.print("  [yellow]s[/yellow] - Skip for now")
        console.print("  [red]d[/red] - Delete (not relevant)")
        console.print("  [cyan]q[/cyan] - Quit review")

        action = Prompt.ask(
            "\n[bold]Choose action[/bold]", choices=["a", "s", "d", "q"], default="s"
        )

        if action == "q":
            break
        elif action == "s":
            skipped += 1
            console.print("[yellow]⊘ Skipped[/yellow]")
        elif action == "d":
            if Confirm.ask(f"\n[red]Delete '{company.get('name')}'?[/red]", default=False):
                # Delete company from database
                import sqlite3

                conn = sqlite3.connect(company_service.db_path)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM companies WHERE id = ?", (company.get("id"),))
                conn.commit()
                conn.close()
                deleted += 1
                console.print("[red]✓ Deleted[/red]")
            else:
                console.print("[yellow]⊘ Skipped deletion[/yellow]")
                skipped += 1
        elif action == "a":
            # Activate company
            console.print("\n[bold yellow]Activating company...[/bold yellow]")
            careers_url = Prompt.ask(
                "\n[bold]Enter careers page URL[/bold]",
                default=company.get("careers_url", ""),
            )

            if careers_url and careers_url != "https://placeholder.com/careers":
                # Update company
                import sqlite3
                from datetime import datetime

                conn = sqlite3.connect(company_service.db_path)
                cursor = conn.cursor()

                now = datetime.now().isoformat()
                cursor.execute(
                    """
                    UPDATE companies
                    SET careers_url = ?, active = 1, notes = ?, updated_at = ?
                    WHERE id = ?
                """,
                    (
                        careers_url,
                        f"Activated from TUI on {now}. Originally: {company.get('notes', '')}",
                        now,
                        company.get("id"),
                    ),
                )
                conn.commit()
                conn.close()

                activated += 1
                console.print(f"[green]✓ Activated: {company.get('name')}[/green]")
                console.print(f"[dim]   URL: {careers_url}[/dim]")
            else:
                console.print("[yellow]⊘ Activation cancelled (invalid URL)[/yellow]")
                skipped += 1

    # Summary
    console.print(SEPARATOR_FULL)
    console.print("[bold green]Review Summary[/bold green]\n")
    console.print(f"  Companies reviewed: {i}/{total}")
    console.print(f"  [green]Activated:[/green] {activated}")
    console.print(f"  [yellow]Skipped:[/yellow] {skipped}")
    console.print(f"  [red]Deleted:[/red] {deleted}")

    press_enter_to_continue()


def main():  # pragma: no cover
    """Main TUI loop"""
    try:
        while True:
            show_header()

            # Step 1: Select Sources
            sources, inbox_profile = select_sources()

            # Handle utility actions
            utility_result = _handle_utility_action(sources)
            if utility_result is False:  # Quit
                sys.exit(0)
            elif utility_result is True:  # Continue loop
                continue
            # else: utility_result is None, proceed to workflow

            # Step 2: Select Action
            action = select_action()

            # Handle secondary actions
            secondary_result = _handle_secondary_action(action)
            if secondary_result is False:  # Quit
                sys.exit(0)
            elif secondary_result is True:  # Continue loop
                continue
            # else: secondary_result is None, proceed to workflow

            # Execute workflow
            _execute_workflow(sources, inbox_profile, action)

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Interrupted by user. Goodbye![/yellow]\n")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]Error: {e}[/bold red]\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
