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
PYTHON_EXECUTABLE = "job-agent-venv/bin/python"
TABLE_HEADER_STYLE = "bold magenta"
MAGENTA_SEPARATOR_TOP = (
    "\n[bold magenta]═══════════════════════════════════════════════[/bold magenta]"
)
MAGENTA_SEPARATOR_BOTTOM = (
    "[bold magenta]═══════════════════════════════════════════════[/bold magenta]\n"
)
PRESS_ENTER_PROMPT = "\n[dim]Press Enter to continue...[/dim]"
SELECT_ACTION_PROMPT = "\n[bold]Select action[/bold]"
LAST_RUN_LABEL = "Last Run"

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
[bold cyan]║[/bold cyan]        [bold white]Job Agent Pipeline Controller[/bold white]         [bold cyan]║[/bold cyan]
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
    elif sources == ["utility:onboard"]:
        onboard_new_profile()
        return True
    elif sources == ["utility:credits"]:
        check_api_credits()
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
    elif action == "metrics":
        show_extraction_metrics()
        return True
    elif action == "health":
        show_system_health()
        return True
    elif action == "performance":
        show_company_performance()
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
    console.print("\n[bold yellow]Choose Action[/bold yellow]\n")

    table = Table(box=box.ROUNDED, show_header=True, header_style=TABLE_HEADER_STYLE)
    table.add_column("Key", style="cyan", width=8)
    table.add_column("Action", style="white", width=40)

    table.add_row("[bold]Scrape[/bold]", "")
    table.add_row("1", "Company Monitoring")
    table.add_row("2", "Email Processing")
    table.add_row("a", "All Sources")
    table.add_row("", "")
    table.add_row("[bold]Tools[/bold]", "")
    table.add_row("n", "New Profile (Onboarding Wizard)")
    table.add_row("api", "API Credits (Check LLM/Firecrawl status)")
    table.add_row("h", "System Health")
    table.add_row("q", "Quit")

    console.print(table)
    console.print("\n[dim]Scrape: Enter source number(s), e.g. '1,2' or 'a' for all.[/dim]")

    choice = Prompt.ask("\n[bold]Action[/bold]", default="a").lower().strip()

    # Handle utility actions
    utility_map = {
        "q": ([], None),
        "n": (["utility:onboard"], None),
        "api": (["utility:credits"], None),
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

    table = Table(box=box.ROUNDED, show_header=True, header_style=TABLE_HEADER_STYLE)
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

    table = Table(box=box.ROUNDED, show_header=True, header_style=TABLE_HEADER_STYLE)
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

    scoring_table = Table(box=box.ROUNDED, show_header=True, header_style=TABLE_HEADER_STYLE)
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

    grade_table = Table(box=box.ROUNDED, show_header=True, header_style=TABLE_HEADER_STYLE)
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

    source_table = Table(box=box.ROUNDED, show_header=True, header_style=TABLE_HEADER_STYLE)
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


def _threshold_color(
    value: float, green_above: float, yellow_above: float
) -> str:  # pragma: no cover
    """Return a Rich color name based on threshold ranges."""
    if value >= green_above:
        return "green"
    return "yellow" if value >= yellow_above else "red"


def _format_time_ago(iso_time: str) -> str:  # pragma: no cover
    """Format an ISO timestamp as a human-readable 'X ago' string."""
    from datetime import datetime

    try:
        last_run = datetime.fromisoformat(iso_time)
        time_ago = datetime.now() - last_run
        if time_ago.days > 0:
            return f"{time_ago.days} days ago"
        if time_ago.seconds > 3600:
            return f"{time_ago.seconds // 3600} hours ago"
        return f"{time_ago.seconds // 60} minutes ago"
    except ValueError:
        return iso_time


def _add_company_health_rows(health_table: Table, company_health: dict) -> None:  # pragma: no cover
    """Add company scraper health rows to the health table."""
    if company_health["total_companies"] == 0:
        return

    success_rate = company_health["success_rate"]
    success_color = _threshold_color(success_rate, green_above=90, yellow_above=75)
    active = company_health["active_companies"]

    health_table.add_row(
        "Company Scraper Success",
        f"[{success_color}]{success_rate:.1f}% ({active - company_health['total_failures']}/{active})[/{success_color}]",
    )

    if company_health["at_risk_count"] > 0:
        health_table.add_row(
            "At Risk (3-4 failures)",
            f"[yellow]{company_health['at_risk_count']} companies[/yellow]",
        )

    if company_health["auto_disabled_count"] > 0:
        health_table.add_row(
            "Auto-Disabled (5 failures)",
            f"[red]{company_health['auto_disabled_count']} companies[/red]",
        )

    if company_health.get("pending_review_count", 0) > 0:
        health_table.add_row(
            "Pending Review",
            f"[yellow]{company_health['pending_review_count']} auto-discovered[/yellow]",
        )

    if company_health.get("companies_with_failures", 0) > 0:
        health_table.add_row(
            "Companies with Failures",
            f"[red]{company_health['companies_with_failures']} companies[/red]",
        )

    health_table.add_row(
        "Scraped in Last 24h",
        f"[dim]{company_health['recent_scrape_count']}/{company_health['total_companies']}[/dim]",
    )


def show_system_health():  # pragma: no cover
    """Display system health dashboard with errors, budget, and activity

    Note: TUI functions are excluded from coverage requirements as they will be
    tested through manual testing and integration tests
    """
    from database import JobDatabase

    db = JobDatabase()

    while True:
        clear_screen()
        show_header()

        health_checker = SystemHealthChecker(db)
        health = health_checker.get_health_summary()

        console.print(SEPARATOR_TOP)
        console.print("[bold cyan]            🔍 SYSTEM HEALTH CHECK              [/bold cyan]")
        console.print(SEPARATOR_BOTTOM)

        health_table = Table(box=box.ROUNDED, show_header=False)
        health_table.add_column("Metric", style="bold cyan", width=30)
        health_table.add_column("Status", width=50)

        # LLM Failures
        failures = health["llm_failures"]
        failure_color = _threshold_color(
            -failures["total_pending"], green_above=0, yellow_above=-10
        )
        health_table.add_row(
            "LLM Failures (Pending)",
            f"[{failure_color}]{failures['total_pending']}[/{failure_color}]",
        )
        health_table.add_row("LLM Failures (Last 24h)", f"[dim]{failures['last_24h']}[/dim]")
        if failures["most_common_error"]:
            health_table.add_row(
                "Most Common Error",
                f"[dim]{failures['most_common_error']} ({failures['most_common_count']} times)[/dim]",
            )

        # Budget
        health_table.add_row("", "")
        budget = health["budget"]
        budget_color = _threshold_color(
            100 - budget["percentage_used"], green_above=20, yellow_above=0
        )
        health_table.add_row(
            "Budget Usage",
            f"[{budget_color}]${budget['total_spent']:.2f} / ${budget['monthly_limit']:.2f} ({budget['percentage_used']:.1f}%)[/{budget_color}]",
        )
        health_table.add_row("API Calls This Month", f"[dim]{budget['api_calls']}[/dim]")
        health_table.add_row("Remaining Budget", f"[dim]${budget['remaining']:.2f}[/dim]")

        # Database Stats
        health_table.add_row("", "")
        db_stats = health["database"]
        health_table.add_row("Total Jobs in DB", f"[green]{db_stats['total_jobs']:,}[/green]")
        health_table.add_row("A/B Grade Jobs", f"[green]{db_stats['high_quality_jobs']:,}[/green]")
        by_grade = db_stats.get("by_grade", {})
        if by_grade:
            grade_str = ", ".join(
                [f"{grade}: {count}" for grade, count in sorted(by_grade.items())]
            )
            health_table.add_row("By Grade", f"[dim]{grade_str}[/dim]")

        # Recent Activity
        health_table.add_row("", "")
        activity = health["recent_activity"]
        if activity["last_run_time"]:
            time_str = _format_time_ago(activity["last_run_time"])
            health_table.add_row("Last Scraper Run", f"[green]{time_str}[/green]")
            health_table.add_row("Jobs Found", f"[dim]{activity['jobs_found_last_run']}[/dim]")
            if activity["last_run_source"]:
                health_table.add_row("Source", f"[dim]{activity['last_run_source']}[/dim]")
        else:
            health_table.add_row("Last Scraper Run", "[yellow]No runs found[/yellow]")

        # Company Scraper
        health_table.add_row("", "")
        _add_company_health_rows(health_table, health["company_scraper"])

        console.print(health_table)

        # Critical Issues
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

        console.print(
            "[dim]Actions: \\[f] LLM failures | \\[c] Company failures | \\[t] Company types | \\[b] Back to menu[/dim]"
        )
        choice = Prompt.ask("\n[bold]Action[/bold]", choices=["f", "c", "t", "b"], default="b")

        if choice == "b":
            return
        elif choice == "f":
            review_llm_failures()
        elif choice == "c":
            review_company_failures()
        elif choice == "t":
            review_company_classifications()


def show_extraction_metrics():  # pragma: no cover
    """Display LLM vs Regex extraction comparison dashboard."""
    import json
    from collections import defaultdict
    from datetime import datetime
    from pathlib import Path

    from database import JobDatabase

    clear_screen()
    show_header()

    console.print(SEPARATOR_TOP)
    console.print("[bold cyan]         📊 EXTRACTION METRICS DASHBOARD          [/bold cyan]")
    console.print(SEPARATOR_BOTTOM)

    days = 30

    while True:
        db = JobDatabase()
        metrics = db.get_extraction_metrics(days=days)

        if not metrics:
            console.print(f"[yellow]No extraction metrics found for last {days} days[/yellow]")
            press_enter_to_continue()
            return

        # Aggregate by company (latest scrape per company)
        latest_by_company: dict[str, dict] = {}
        for m in metrics:
            name = m["company_name"]
            if name not in latest_by_company:
                latest_by_company[name] = m

        # Calculate summary stats
        total_regex = sum(m["regex_jobs_found"] for m in latest_by_company.values())
        total_llm = sum(m["llm_jobs_found"] for m in latest_by_company.values())
        total_jobs = sum(m["total_jobs_found"] for m in latest_by_company.values())
        companies_with_llm = sum(1 for m in latest_by_company.values() if m["llm_jobs_found"] > 0)
        companies_total = len(latest_by_company)
        fetch_failures = sum(
            1 for m in latest_by_company.values() if not m.get("fetch_success", True)
        )

        # Cost data from budget file
        current_month = datetime.now().strftime("%Y-%m")
        budget_file = Path(f"logs/llm-budget-{current_month}.json")
        monthly_cost = 0.0
        model_costs: dict[str, float] = defaultdict(float)
        model_calls: dict[str, int] = defaultdict(int)
        if budget_file.exists():
            try:
                with open(budget_file) as f:
                    budget_data = json.load(f)
                monthly_cost = budget_data.get("total_cost", 0)
                for record in budget_data.get("records", []):
                    model = record.get("model", "unknown")
                    model_costs[model] += record.get("cost_usd", 0)
                    model_calls[model] += 1
            except (json.JSONDecodeError, OSError):
                pass

        # Summary stats table
        summary = Table(box=box.ROUNDED, show_header=True, header_style=TABLE_HEADER_STYLE)
        summary.add_column("Metric", style="bold cyan", width=28)
        summary.add_column("Value", style="white", width=20)

        summary.add_row("Period", f"Last {days} days")
        summary.add_row("Companies Scraped", str(companies_total))
        summary.add_row(
            "Fetch Failures", f"[{'red' if fetch_failures > 5 else 'dim'}]{fetch_failures}[/]"
        )
        summary.add_row("", "")
        summary.add_row("Regex Jobs Found", str(total_regex))
        summary.add_row("LLM Jobs Found", str(total_llm))
        summary.add_row("Total Jobs", f"[bold]{total_jobs}[/bold]")
        summary.add_row("LLM Coverage", f"{companies_with_llm}/{companies_total} companies")
        summary.add_row("", "")
        summary.add_row("Monthly LLM Cost", f"[green]${monthly_cost:.2f}[/green]")
        if total_llm > 0 and monthly_cost > 0:
            cost_per_llm_job = monthly_cost / total_llm
            summary.add_row("Cost per LLM Job", f"${cost_per_llm_job:.4f}")

        # Model breakdown
        for model, cost in sorted(model_costs.items()):
            calls = model_calls[model]
            model_short = model.split("/")[-1] if "/" in model else model
            summary.add_row(f"  {model_short}", f"${cost:.4f} ({calls} calls)")

        console.print(summary)

        # Per-company comparison table
        console.print(f"\n[bold]Per-Company Breakdown[/bold] (last {days} days):\n")

        company_table = Table(box=box.ROUNDED, show_header=True, header_style=TABLE_HEADER_STYLE)
        company_table.add_column("Company", style="white", width=30)
        company_table.add_column("Regex", style="cyan", justify="right", width=7)
        company_table.add_column("LLM", style="yellow", justify="right", width=7)
        company_table.add_column("Total", style="bold", justify="right", width=7)
        company_table.add_column("LLM %", justify="right", width=8)
        company_table.add_column("Backend", style="dim", width=12)
        company_table.add_column("Date", style="dim", width=10)

        # Sort by total jobs descending
        sorted_companies = sorted(
            latest_by_company.items(), key=lambda x: x[1]["total_jobs_found"], reverse=True
        )

        for name, m in sorted_companies:
            regex = m["regex_jobs_found"]
            llm = m["llm_jobs_found"]
            total = m["total_jobs_found"]
            backend = m.get("scraper_backend", "")

            if total > 0 and llm > 0:
                llm_pct = f"{llm / total * 100:.0f}%"
                # Color: green if LLM found jobs regex missed
                llm_color = "green" if llm > regex else "yellow" if llm == regex else "dim"
                llm_str = f"[{llm_color}]{llm}[/{llm_color}]"
            elif total == 0:
                llm_pct = "[dim]-[/dim]"
                llm_str = "[dim]0[/dim]"
            else:
                llm_pct = "[dim]0%[/dim]"
                llm_str = "[dim]0[/dim]"

            company_table.add_row(
                name[:30], str(regex), llm_str, str(total), llm_pct, backend, m["scrape_date"]
            )

        console.print(company_table)

        console.print(
            f"\n[dim]Showing {len(sorted_companies)} companies | "
            f"Actions: \\[7] 7 days | \\[30] 30 days | \\[90] 90 days | \\[b] Back[/dim]"
        )
        choice = Prompt.ask("\n[bold]Action[/bold]", choices=["7", "30", "90", "b"], default="b")

        if choice == "b":
            return

        days = int(choice)
        clear_screen()
        show_header()
        console.print(SEPARATOR_TOP)
        console.print("[bold cyan]         📊 EXTRACTION METRICS DASHBOARD          [/bold cyan]")
        console.print(SEPARATOR_BOTTOM)


def _build_performers_table(
    companies: list[dict[str, object]], title: str, limit: int = 10
) -> Table:
    """Build a Rich table of top or bottom performing companies."""
    table = Table(title=title, box=box.ROUNDED, show_header=True, header_style=TABLE_HEADER_STYLE)
    table.add_column("#", style="dim", width=4)
    table.add_column("Company", style="white", width=25)
    table.add_column("Scrapes", justify="right", width=8)
    table.add_column("Total Jobs", justify="right", width=10)
    table.add_column("Avg/Scrape", justify="right", width=10)
    table.add_column("Fail %", justify="right", width=8)
    table.add_column("Last Scraped", width=12)

    for i, c in enumerate(companies[:limit], 1):
        avg_raw = c.get("avg_jobs_per_scrape", 0) or 0
        fail_raw = c.get("failure_rate", 0) or 0
        avg = float(str(avg_raw))
        fail = float(str(fail_raw))

        avg_color = "green" if avg >= 5 else ("yellow" if avg >= 1 else "red")
        fail_color = "red" if fail > 50 else ("yellow" if fail > 25 else "green")

        table.add_row(
            str(i),
            str(c["company_name"]),
            str(c.get("scrape_count", 0)),
            str(c.get("total_jobs", 0)),
            f"[{avg_color}]{avg:.1f}[/{avg_color}]",
            f"[{fail_color}]{fail:.0f}%[/{fail_color}]",
            str(c.get("last_scrape_date", ""))[:10],
        )

    return table


def show_company_performance() -> None:  # pragma: no cover
    """Show company scraping performance dashboard with top/bottom performers."""
    from database import JobDatabase

    db = JobDatabase()
    days = 30

    while True:
        clear_screen()
        show_header()
        console.print(SEPARATOR_TOP)
        console.print("[bold cyan]         🏢 COMPANY PERFORMANCE DASHBOARD          [/bold cyan]")
        console.print(SEPARATOR_BOTTOM)

        performance = db.get_company_performance_summary(days=days)
        if not performance:
            console.print(f"\n[yellow]No extraction metrics found for last {days} days.[/yellow]")
            Prompt.ask("\nPress Enter to return")
            return

        # Summary stats
        total_companies = len(performance)
        total_jobs = sum(int(c.get("total_jobs", 0) or 0) for c in performance)
        total_scrapes = sum(int(c.get("scrape_count", 0) or 0) for c in performance)
        total_failures = sum(int(c.get("failure_count", 0) or 0) for c in performance)
        overall_fail_rate = (total_failures / total_scrapes * 100) if total_scrapes else 0

        summary = Table(box=box.ROUNDED, show_header=False)
        summary.add_column("Metric", style="cyan", width=25)
        summary.add_column("Value", style="white", width=20)
        summary.add_row("Period", f"Last {days} days")
        summary.add_row("Companies scraped", str(total_companies))
        summary.add_row("Total scrapes", str(total_scrapes))
        summary.add_row("Total jobs found", str(total_jobs))
        fail_color = (
            "red" if overall_fail_rate > 10 else "yellow" if overall_fail_rate > 5 else "green"
        )
        summary.add_row(
            "Overall failure rate", f"[{fail_color}]{overall_fail_rate:.1f}%[/{fail_color}]"
        )
        console.print(summary)

        # Top performers (by avg jobs per scrape)
        top = sorted(
            performance, key=lambda c: float(c.get("avg_jobs_per_scrape", 0) or 0), reverse=True
        )
        console.print()
        console.print(_build_performers_table(top, "🏆 Top Performers (by avg jobs/scrape)"))

        # Underperformers
        underperformers = db.get_underperforming_companies(days=days)
        if underperformers:
            console.print()
            console.print(
                _build_performers_table(
                    underperformers, "⚠️  Underperformers (>50% fail OR avg <1 job)", limit=20
                )
            )
        else:
            console.print("\n[green]✓ No underperforming companies found.[/green]")

        # Action bar
        console.print("\n[dim]Time window: [7] [30] [90] days | [b] Back[/dim]")
        choice = Prompt.ask("Select", choices=["7", "30", "90", "b"], default="b")
        if choice == "b":
            return
        days = int(choice)


def _display_llm_budget() -> None:  # pragma: no cover
    """Display LLM budget status section."""
    import json
    from datetime import datetime
    from pathlib import Path

    console.print("[bold yellow]🤖 LLM Extraction (Gemini 2.5 Flash)[/bold yellow]\n")

    current_month = datetime.now().strftime("%Y-%m")
    llm_budget_file = Path(f"logs/llm-budget-{current_month}.json")
    if not llm_budget_file.exists():
        console.print("[dim]No LLM budget data found (not used this month)[/dim]")
        return

    try:
        with open(llm_budget_file) as f:
            data = json.load(f)

        total_cost = data.get("total_cost", 0)
        budget = 5.00
        remaining = budget - total_cost
        usage_pct = (total_cost / budget * 100) if budget > 0 else 0
        usage_color = _threshold_color(100 - usage_pct, green_above=50, yellow_above=20)

        llm_table = Table(box=box.ROUNDED, show_header=True, header_style=TABLE_HEADER_STYLE)
        llm_table.add_column("Metric", style="cyan", width=20)
        llm_table.add_column("Value", style="white", width=25)
        llm_table.add_row("Total Spent", f"${total_cost:.2f}")
        llm_table.add_row("Monthly Budget", f"${budget:.2f}")
        llm_table.add_row("Remaining", f"${remaining:.2f}")
        llm_table.add_row("Usage", f"[{usage_color}]{usage_pct:.1f}%[/{usage_color}]")
        llm_table.add_row("API Calls", str(len(data.get("requests", []))))
        console.print(llm_table)

        if remaining > 0:
            console.print(f"\n[green]✓ {remaining / 0.01:.0f} more company scans available[/green]")
        else:
            console.print("\n[red]⚠ Budget exceeded![/red]")

    except Exception as e:
        console.print(f"[red]Error reading LLM budget: {e}[/red]")


def _grep_log(
    pattern: str,
    log_path: str = "logs/unified_scraper.log",
    last_run_only: bool = False,
) -> list[str]:
    """Grep log file for pattern, return matching lines.

    If last_run_only=True, only search from the second-to-last 'Completed:' line
    onwards (i.e., the most recent complete run).
    """
    import re
    import subprocess

    if last_run_only:
        # Find line numbers of all "Completed:" markers
        result = subprocess.run(
            ["grep", "-n", "^Completed:", log_path],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            completed_lines = result.stdout.strip().split("\n")
            # Start from second-to-last Completed (start of last run)
            start_line = completed_lines[-2].split(":")[0] if len(completed_lines) >= 2 else "1"
            result = subprocess.run(
                ["tail", "-n", f"+{start_line}", log_path],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                return [
                    line
                    for line in result.stdout.split("\n")
                    if re.search(pattern, line, re.IGNORECASE)
                ]
        return []

    result = subprocess.run(
        ["grep", "-i", pattern, log_path],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip().split("\n")
    return []


def _display_firecrawl_status() -> None:  # pragma: no cover
    """Display Firecrawl API status section."""
    from pathlib import Path

    console.print("\n\n[bold yellow]🔥 Firecrawl API[/bold yellow]\n")

    firecrawl_table = Table(box=box.ROUNDED, show_header=True, header_style=TABLE_HEADER_STYLE)
    firecrawl_table.add_column("Metric", style="cyan", width=20)
    firecrawl_table.add_column("Status", style="white", width=25)

    try:
        log_path = Path("logs/unified_scraper.log")

        if log_path.exists():
            log_str = str(log_path)

            # Companies checked
            matches = _grep_log("companies checked:", log_str)
            if matches:
                firecrawl_table.add_row(LAST_RUN_LABEL, f"[green]✓ {matches[-1].strip()}[/green]")
            else:
                firecrawl_table.add_row(LAST_RUN_LABEL, "[dim]No company scrape runs found[/dim]")

            # Last completed timestamp
            completed = _grep_log("^Completed:", log_str)
            if completed:
                timestamp = completed[-1].replace("Completed: ", "").split(" (")[0]
                firecrawl_table.add_row("Last Completed", f"[dim]{timestamp}[/dim]")

            # Scraping errors (last run only)
            errors = _grep_log('"scraping_errors":', log_str, last_run_only=True)
            if errors:
                last_error = errors[-1].strip()
                count = last_error.split(":")[-1].strip().rstrip(",")
                error_color = "green" if count == "0" else "yellow"
                firecrawl_table.add_row(
                    "Scraping Errors", f"[{error_color}]{count}[/{error_color}]"
                )

            # Firecrawl fallbacks (last run only)
            fallbacks = _grep_log("Firecrawl fallback found", log_str, last_run_only=True)
            if fallbacks:
                firecrawl_table.add_row(
                    "Firecrawl Fallbacks",
                    f"[dim]{len(fallbacks)} companies rescued[/dim]",
                )
        else:
            firecrawl_table.add_row(LAST_RUN_LABEL, "[dim]No logs found[/dim]")

        firecrawl_table.add_row(
            "API Key",
            "[green]✓ Configured[/green]" if Path(".env").exists() else "[red]✗ Missing[/red]",
        )

    except Exception as e:
        firecrawl_table.add_row("Status", f"[red]Error: {e}[/red]")

    console.print(firecrawl_table)


def check_api_credits():  # pragma: no cover
    """Display API credit status for LLM and Firecrawl

    Note: TUI functions are excluded from coverage requirements as they will be
    replaced with Textual framework (Issue #119). Manual testing confirms functionality.
    """
    console.clear()
    console.print(MAGENTA_SEPARATOR_TOP)
    console.print("[bold magenta]              API CREDIT STATUS                  [/bold magenta]")
    console.print(MAGENTA_SEPARATOR_BOTTOM)

    _display_llm_budget()
    _display_firecrawl_status()

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
        console.print(MAGENTA_SEPARATOR_TOP)
        console.print(
            "[bold magenta]           LLM EXTRACTION FAILURES REVIEW           [/bold magenta]"
        )
        console.print(MAGENTA_SEPARATOR_BOTTOM)

        # Get pending failures
        failures = db.get_llm_failures(review_action="pending", limit=50)

        if not failures:
            console.print("[green]✅ No pending LLM extraction failures to review![/green]\n")
            press_enter_to_continue()
            return

        # Summary stats
        console.print(f"[bold yellow]📊 Summary:[/bold yellow] {len(failures)} pending failures\n")

        # Display failures table
        table = Table(box=box.ROUNDED, show_header=True, header_style=TABLE_HEADER_STYLE)
        table.add_column("#", style="cyan", width=4)
        table.add_column("Company", style="white", width=20)
        table.add_column("Failure Reason", style="yellow", width=20)
        table.add_column("Careers URL", style="dim", width=35)
        table.add_column("Occurred", style="dim", width=10)

        for idx, failure in enumerate(failures[:20], 1):  # Show first 20
            occurred = failure["occurred_at"][:10] if failure["occurred_at"] else "Unknown"
            reason = _format_llm_failure_reason(
                failure["failure_reason"], failure.get("error_details")
            )
            url = failure.get("careers_url") or ""
            if len(url) > 35:
                url = url[:32] + "..."
            table.add_row(
                str(idx),
                failure["company_name"],
                reason,
                url,
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
        console.print("  \\[b] Back")

        choice = Prompt.ask(SELECT_ACTION_PROMPT, choices=["r", "a", "s", "b"], default="b")

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
            input(PRESS_ENTER_PROMPT)
            return

        failure = failures[failure_idx]
    except ValueError:
        console.print("[red]❌ Invalid input. Enter a number.[/red]")
        input(PRESS_ENTER_PROMPT)
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
    detail_table.add_row("Careers URL", failure.get("careers_url") or "N/A")
    detail_table.add_row("Occurred At", failure["occurred_at"] or "Unknown")
    detail_table.add_row("Failure Reason", failure["failure_reason"])
    if failure.get("error_details"):
        detail_table.add_row("Error Details", failure["error_details"][:200])
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

    action = Prompt.ask(SELECT_ACTION_PROMPT, choices=choices, default="b")

    if action == "b":
        return
    elif action == "v":
        _view_markdown(failure)
        input(PRESS_ENTER_PROMPT)
    elif action == "r":
        if db.update_llm_failure(failure["id"], "retry"):
            console.print(f"\n[green]✅ Marked {failure['company_name']} for retry[/green]")
        else:
            console.print("\n[red]❌ Failed to update failure record[/red]")
        input(PRESS_ENTER_PROMPT)
    elif action == "s":
        if db.update_llm_failure(failure["id"], "skip"):
            console.print(f"\n[yellow]⏭️  Skipped {failure['company_name']} permanently[/yellow]")
        else:
            console.print("\n[red]❌ Failed to update failure record[/red]")
        input(PRESS_ENTER_PROMPT)


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


def _format_llm_failure_reason(failure_reason: str, error_details: str | None) -> str:
    """Format failure reason with HTTP status code from error details if available.

    Extracts 'Error code: 402' from details like:
    "Error code: 402 - {'error': {'message': '...'}}"
    """
    import re

    if error_details and failure_reason == "APIStatusError":
        match = re.search(r"Error code: (\d+)", error_details)
        if match:
            code = match.group(1)
            labels = {
                "402": "402 Payment Required",
                "429": "429 Rate Limited",
                "500": "500 Server Error",
            }
            return labels.get(code, f"{code} API Error")

    if len(failure_reason) > 20:
        return failure_reason[:17] + "..."
    return failure_reason


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
        input(PRESS_ENTER_PROMPT)


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
        input(PRESS_ENTER_PROMPT)


def review_company_failures():  # pragma: no cover
    """Redirect to unified company management flow.

    Previously a separate list-only view; now routes to manage_companies()
    which handles both auto-discovered and failing companies interactively.
    """
    manage_companies()


def review_company_classifications():  # pragma: no cover
    """Review and classify companies that have unknown type."""
    import json
    import sqlite3

    from database import JobDatabase

    db = JobDatabase()

    while True:
        clear_screen()
        show_header()

        console.print(SEPARATOR_TOP)
        console.print("[bold cyan]         🏢 COMPANY TYPE CLASSIFICATIONS          [/bold cyan]")
        console.print(SEPARATOR_BOTTOM)

        # Get companies from recent jobs and cross-ref with manual classifications
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()

        # Load manually reviewed classifications (skip auto/unknown entries)
        cursor.execute(
            """SELECT company_name, classification FROM company_classifications
               WHERE source = 'manual' OR classification != 'unknown'"""
        )
        known_classifications = {row[0]: row[1] for row in cursor.fetchall()}

        cursor.execute(
            """
            SELECT j.company, js.classification_metadata, j.link
            FROM job_scores js
            JOIN jobs j ON j.id = js.job_id
            WHERE j.received_at >= datetime('now', '-30 days')
            AND js.classification_metadata IS NOT NULL
            """
        )

        unknown_with_urls: dict[str, str] = {}  # company -> sample link
        classified_companies: dict[str, str] = {}
        for row in cursor.fetchall():
            company = row[0]
            if company in classified_companies:
                continue

            # Check DB classification first, fall back to job metadata
            if company in known_classifications:
                ct = known_classifications[company]
                # Already in DB (even if "unknown") — don't show for review again
                classified_companies[company] = ct
            else:
                meta = json.loads(row[1] or "{}")
                ct = meta.get("company_type", "unknown")
                classified_companies[company] = ct
                if ct == "unknown":
                    unknown_with_urls[company] = row[2] or ""

        classified = {"software": 0, "hardware": 0, "both": 0, "unknown": 0}
        for ct in classified_companies.values():
            classified[ct] = classified.get(ct, 0) + 1

        conn.close()

        # Show summary
        total = sum(classified.values())
        coverage = (total - len(unknown_with_urls)) / total * 100 if total else 0
        summary = Table(box=box.ROUNDED, show_header=False)
        summary.add_column("Metric", style="bold cyan", width=25)
        summary.add_column("Value", width=40)
        summary.add_row("Total companies (30d)", f"{total}")
        summary.add_row("Software", f"[blue]{classified['software']}[/blue]")
        summary.add_row("Hardware", f"[green]{classified['hardware']}[/green]")
        summary.add_row("Both", f"[yellow]{classified['both']}[/yellow]")
        unknown_color = "red" if len(unknown_with_urls) > 50 else "yellow"
        summary.add_row("Unknown", f"[{unknown_color}]{len(unknown_with_urls)}[/{unknown_color}]")
        coverage_color = "green" if coverage > 80 else "yellow"
        summary.add_row("Coverage", f"[{coverage_color}]{coverage:.0f}%[/{coverage_color}]")
        console.print(summary)

        if not unknown_with_urls:
            console.print("\n[bold green]All companies classified![/bold green]")
            press_enter_to_continue()
            return

        console.print("\n[dim]Actions: \\[enter] Start classifying | \\[b/q] Back[/dim]")
        choice = Prompt.ask("[bold]Action[/bold]", default="")

        if choice.lower() in ("b", "q"):
            return

        _auto_classify_unknown(unknown_with_urls, db)
        return


def _auto_classify_unknown(companies: dict[str, str], db) -> None:  # pragma: no cover
    """Fast keyboard-driven classification: s/h/b per company, enter=skip, q=quit."""

    console.print(
        "\n[bold]s[/bold]=software  [bold]h[/bold]=hardware  "
        "[bold]b[/bold]=both  [bold]enter[/bold]=skip  [bold]q[/bold]=quit\n"
    )
    type_map = {"s": "software", "h": "hardware", "b": "both"}
    classified_count = 0
    skipped_count = 0
    colors = {"software": "blue", "hardware": "green", "both": "yellow"}
    sorted_names = sorted(companies.keys())
    total = len(sorted_names)

    for i, name in enumerate(sorted_names, 1):
        url = companies[name]
        console.print(f"[dim]{i:3d}/{total}[/dim] [bold]{name}[/bold]")
        if url:
            console.print(f"       [link={url}]{url}[/link]")
        choice = Prompt.ask("       ", default="")
        if choice.lower() == "q":
            break
        if choice.lower() in type_map:
            ct = type_map[choice.lower()]
            _store_manual_classification(name, ct, db)
            console.print(f"       [{colors[ct]}]→ {ct}[/{colors[ct]}]")
            classified_count += 1
        else:
            # Mark as reviewed (keeps unknown classification) so it doesn't reappear
            _store_manual_classification(name, "unknown", db)
            skipped_count += 1

    console.print(
        f"\n[bold green]Classified {classified_count}, skipped {skipped_count}[/bold green]"
    )
    press_enter_to_continue()


def _store_manual_classification(company_name: str, classification: str, db) -> None:
    """Store a manual company classification in the database."""
    import json
    import sqlite3
    from datetime import datetime

    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    signals = json.dumps({"manual": {"source": "tui", "classified_at": now}})

    # Upsert: update existing entry (any source) or insert new
    cursor.execute(
        "SELECT id FROM company_classifications WHERE company_name = ?",
        (company_name,),
    )
    existing = cursor.fetchone()

    if existing:
        cursor.execute(
            """UPDATE company_classifications
               SET classification = ?, confidence_score = 1.0, source = 'manual',
                   signals = ?, updated_at = ?
               WHERE id = ?""",
            (classification, signals, now, existing[0]),
        )
    else:
        cursor.execute(
            """INSERT INTO company_classifications
               (company_name, classification, confidence_score, source, signals, created_at, updated_at)
               VALUES (?, ?, 1.0, 'manual', ?, ?, ?)""",
            (company_name, classification, signals, now, now),
        )

    conn.commit()
    conn.close()


def select_action() -> str | None:
    """Select what action to perform"""
    console.print("\n[bold yellow]Step 2:[/bold yellow] Select Action\n")

    table = Table(box=box.ROUNDED, show_header=True, header_style=TABLE_HEADER_STYLE)
    table.add_column("Option", style="cyan", width=8)
    table.add_column("Action", style="green", width=20)
    table.add_column("Description", style="white")

    table.add_row("1", "Scrape Only", "Fetch and score jobs, store in database")
    table.add_row("2", "Send Digest", "Send email digest with stored jobs")
    table.add_row("3", "Scrape + Digest", "Run scraper then send digest email")
    table.add_row("c", "View Criteria", "Show scoring criteria and grading scale")
    table.add_row("f", "LLM Failures", "Review and retry failed LLM extractions")
    table.add_row("m", "LLM Metrics", "View regex vs LLM extraction comparison")
    table.add_row("h", "System Health", "View system health and error dashboard")
    table.add_row("p", "Company Perf", "View company scraping performance and reliability")
    table.add_row("b", "Back", "Return to profile selection")
    table.add_row("q", "Quit", "Exit application")

    console.print(table)

    choice = Prompt.ask(
        SELECT_ACTION_PROMPT,
        choices=["1", "2", "3", "c", "f", "m", "h", "p", "b", "q"],
        default="3",
    )

    # Map choices to actions
    choice_map = {
        "q": None,
        "b": "back",
        "c": "criteria",
        "f": "failures",
        "m": "metrics",
        "h": "health",
        "p": "performance",
        "1": "scrape",
        "2": "digest",
        "3": "both",
    }

    return choice_map.get(choice, "both")


def select_digest_options() -> dict:
    """Select digest options (dry-run, force-resend)"""
    console.print("\n[bold yellow]Step 5:[/bold yellow] Digest Options\n")

    table = Table(box=box.ROUNDED, show_header=True, header_style=TABLE_HEADER_STYLE)
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


def _build_inbox_summary(inbox_profile: str) -> str:  # pragma: no cover
    """Build the inbox description line for the execution summary."""
    if inbox_profile == "all":
        return "\n[bold]Email Inbox:[/bold] All Configured Inboxes"
    pm = get_profile_manager()
    profile_obj = pm.get_profile(inbox_profile)
    inbox_name = profile_obj.name if profile_obj else inbox_profile
    inbox_email = (
        profile_obj.email_username
        if (profile_obj and hasattr(profile_obj, "email_username"))
        else "unknown"
    )
    return f"\n[bold]Email Inbox:[/bold] {inbox_name} ({inbox_email})"


def _build_digest_summary(
    digest_recipients: list[str],
    digest_options: dict | None,
) -> str:  # pragma: no cover
    """Build digest recipients and mode lines for the execution summary."""
    pm = get_profile_manager()
    if digest_recipients == ["all"]:
        recipient_text = "All Enabled Profiles"
    else:
        names = []
        for pid in digest_recipients:
            profile_obj = pm.get_profile(pid)
            names.append(profile_obj.name if profile_obj else pid)
        recipient_text = ", ".join(names)

    result = f"\n[bold]Digest Recipients:[/bold] {recipient_text}"

    if digest_options:
        if digest_options.get("dry_run"):
            digest_mode = "Dry Run (testing)"
        elif digest_options.get("force_resend"):
            digest_mode = "Force Resend (re-send previous jobs)"
        else:
            digest_mode = "Production (real digest)"
        result += f"\n[bold]Digest Mode:[/bold] {digest_mode}"

    return result


def confirm_execution(
    sources: list[str],
    inbox_profile: str | None,
    action: str,
    digest_recipients: list[str] | None,
    digest_options: dict | None = None,
) -> bool:
    """Show summary and confirm execution"""
    console.print("\n[bold yellow]Step 6: Confirm Execution[/bold yellow]\n")

    action_display = {
        "scrape": "Scrape Only",
        "digest": "Send Digest",
        "both": "Scrape and Send Digest",
    }
    action_text = action_display.get(action, action.title())

    summary_text = f"[bold]Sources:[/bold] {', '.join(sources).title()}"

    if inbox_profile:
        summary_text += _build_inbox_summary(inbox_profile)

    summary_text += f"\n[bold]Action:[/bold] {action_text}"

    if digest_recipients and action in ["digest", "both"]:
        summary_text += _build_digest_summary(digest_recipients, digest_options)

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


def manage_companies():  # pragma: no cover
    """Review and manage auto-discovered companies and companies with failures"""
    import sqlite3

    console.print(SEPARATOR_TOP)
    console.print("[bold cyan]Company Management[/bold cyan]")
    console.print(SEPARATOR_BOTTOM)

    company_service = CompanyService()
    all_companies = company_service.get_all_companies(active_only=False)

    # Auto-discovered (inactive, pending review)
    auto_discovered = [
        c for c in all_companies if c.get("active") == 0 and "Auto-discovered" in c.get("notes", "")
    ]

    # Companies with failures (active or auto-disabled)
    conn = sqlite3.connect(company_service.db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, careers_url, consecutive_failures, last_failure_reason,
               last_checked, active, auto_disabled_at, notes, created_at, updated_at
        FROM companies
        WHERE consecutive_failures > 0
        ORDER BY consecutive_failures DESC, name ASC
    """)
    failure_rows = cursor.fetchall()
    conn.close()

    failing_companies = [
        {
            "id": r[0],
            "name": r[1],
            "careers_url": r[2],
            "consecutive_failures": r[3],
            "last_failure_reason": r[4],
            "last_checked": r[5],
            "active": r[6],
            "auto_disabled_at": r[7],
            "notes": r[8],
            "created_at": r[9],
            "updated_at": r[10],
            "_review_type": "failure",
        }
        for r in failure_rows
    ]

    if not auto_discovered and not failing_companies:
        console.print("[green]✓ No companies pending review and no failures![/green]")
        press_enter_to_continue()
        return

    # Show summary
    if auto_discovered:
        console.print(
            f"  [yellow]📋 Auto-discovered (pending review):[/yellow] {len(auto_discovered)}"
        )
    if failing_companies:
        at_risk = sum(
            1 for c in failing_companies if 3 <= c["consecutive_failures"] < 5 and c["active"] == 1
        )
        disabled = sum(
            1 for c in failing_companies if c["consecutive_failures"] >= 5 or c["auto_disabled_at"]
        )
        console.print(f"  [red]⚠ Companies with failures:[/red] {len(failing_companies)}")
        if at_risk:
            console.print(f"    [yellow]At risk (3-4 failures):[/yellow] {at_risk}")
        if disabled:
            console.print(f"    [red]Auto-disabled (5+):[/red] {disabled}")
    console.print()

    # Build summary table
    table = Table(box=box.ROUNDED, show_header=True, header_style=TABLE_HEADER_STYLE)
    table.add_column("#", style="cyan", width=5)
    table.add_column("Company Name", style="white", width=25)
    table.add_column("Status", style="white", width=16)
    table.add_column("Careers URL", style="dim", width=45)

    # Tag auto-discovered companies for unified list
    for c in auto_discovered:
        c["_review_type"] = "discovered"
        c["consecutive_failures"] = 0
        c["last_failure_reason"] = None

    combined = auto_discovered + failing_companies
    for i, company in enumerate(combined, 1):
        review_type = company.get("_review_type", "")
        failures = company.get("consecutive_failures", 0)

        if review_type == "discovered":
            status = "[cyan]Pending Review[/cyan]"
        elif failures >= 5 or company.get("auto_disabled_at"):
            status = f"[red]Disabled ({failures}/5)[/red]"
        elif failures >= 3:
            status = f"[yellow]At Risk ({failures}/5)[/yellow]"
        else:
            status = f"[dim]Active ({failures}/5)[/dim]"

        url = company.get("careers_url") or ""
        if url == "https://placeholder.com/careers":
            url_display = "[dim]needs URL[/dim]"
        elif len(url) > 45:
            url_display = url[:42] + "..."
        else:
            url_display = url

        table.add_row(str(i), company.get("name", "Unknown"), status, url_display)

    console.print(table)

    # Inline action loop
    console.print("\n[bold]Actions:[/bold]")
    console.print("  [green]a#[/green]  - Activate company # (e.g. a5)")
    console.print("  [red]d#[/red]  - Delete/disable company # (e.g. d3)")
    console.print("  [cyan]r#[/cyan]  - Reset failures for company # (e.g. r7)")
    console.print("  [cyan]r[/cyan]   - Review all one by one")
    console.print("  [cyan]b[/cyan]   - Back")

    _inline_company_actions(combined, company_service)


def _inline_company_actions(  # pragma: no cover
    companies: list[dict], company_service: CompanyService
) -> None:
    """Process inline actions like a5 (activate #5), d3 (delete #3), r7 (reset #7)."""
    import re

    while True:
        choice = Prompt.ask("\n[bold]Action[/bold]", default="b")
        choice = choice.strip().lower()

        if choice == "b":
            return
        if choice == "r":
            _review_companies_interactive(companies, company_service)
            return

        # Parse action + number (e.g., "a5", "d12", "r3")
        match = re.match(r"^([adr])(\d+)$", choice)
        if not match:
            console.print("[red]Invalid action. Use a#, d#, r#, r, or b[/red]")
            continue

        action, num = match.group(1), int(match.group(2))
        if num < 1 or num > len(companies):
            console.print(f"[red]Invalid number. Choose 1-{len(companies)}[/red]")
            continue

        company = companies[num - 1]
        name = company.get("name", "Unknown")
        is_failure = company.get("_review_type") == "failure"

        if action == "a":
            if _handle_activate_company(company, company_service):
                console.print(f"[green]#{num} {name} activated[/green]")
            else:
                console.print(f"[yellow]#{num} {name} not activated[/yellow]")
        elif action == "d":
            _handle_delete_company(company, company_service, is_failure)
        elif action == "r":
            if is_failure:
                _handle_reset_failures(company, company_service)
            else:
                console.print(f"[yellow]#{num} {name} has no failures to reset[/yellow]")


def _list_companies_detailed(companies: list[dict]):  # pragma: no cover
    """Display detailed list of companies"""
    console.print(SEPARATOR_FULL)
    console.print("[bold cyan]Detailed Company List[/bold cyan]\n")

    for i, company in enumerate(companies, 1):
        console.print(f"\n[bold cyan]{i}. {company.get('name', 'Unknown')}[/bold cyan]")
        console.print(f"   ID: {company.get('id')}")
        console.print(f"   Created: {company.get('created_at', 'Unknown')}")
        console.print(f"   URL: {company.get('careers_url', 'None')}")
        console.print(f"   Notes: {company.get('notes', 'None')}")
        failures = company.get("consecutive_failures", 0)
        if failures > 0:
            console.print(f"   [yellow]Failures: {failures}/5[/yellow]")
            console.print(f"   Last Error: {company.get('last_failure_reason', 'Unknown')}")
            console.print(f"   Last Checked: {company.get('last_checked', 'Never')}")


def _review_companies_interactive(companies: list[dict], company_service: CompanyService):
    """Review companies one by one interactively (discovered + failing)"""  # pragma: no cover
    import sqlite3

    total = len(companies)
    activated = 0
    skipped = 0
    deleted = 0
    reset = 0
    reviewed = 0

    for i, company in enumerate(companies, 1):
        reviewed = i
        console.print(SEPARATOR_FULL)
        console.print(f"[bold cyan]Company {i} of {total}[/bold cyan]\n")

        company_name = company.get("name", "Unknown")
        is_failure = company.get("_review_type") == "failure"
        failures = company.get("consecutive_failures", 0)

        # Look up source email from jobs table
        source_info = ""
        try:
            conn = sqlite3.connect(company_service.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DISTINCT source, source_email FROM jobs WHERE company = ? LIMIT 3",
                (company_name,),
            )
            sources = cursor.fetchall()
            conn.close()
            if sources:
                source_lines = [f"{s[0]}" + (f" ({s[1]})" if s[1] else "") for s in sources]
                source_info = "\n\n[yellow]Discovered From:[/yellow]\n  " + "\n  ".join(
                    source_lines
                )
        except Exception:
            pass

        # Build panel content based on review type
        failure_info = ""
        if is_failure:
            status_label = (
                "[red]Disabled[/red]"
                if failures >= 5 or company.get("auto_disabled_at")
                else ("[yellow]At Risk[/yellow]" if failures >= 3 else "[dim]Active[/dim]")
            )
            failure_info = f"""

[red]Failure Info:[/red]
  Status: {status_label}
  Consecutive Failures: {failures}/5
  Last Error: {company.get("last_failure_reason", "Unknown")}
  Last Checked: {company.get("last_checked", "Never")}"""
            if company.get("auto_disabled_at"):
                failure_info += f"\n  Auto-Disabled: {company.get('auto_disabled_at')}"

        panel_content = f"""[bold green]{company_name}[/bold green]

[yellow]Details:[/yellow]
  ID: {company.get("id")}
  Created: {company.get("created_at", "Unknown")}
  Current URL: {company.get("careers_url", "None")}{source_info}{failure_info}

[yellow]Notes:[/yellow]
  {company.get("notes", "None")}"""

        border = "red" if is_failure and failures >= 5 else "yellow" if is_failure else "cyan"
        title = "Company with Failures" if is_failure else "Auto-Discovered Company"
        console.print(Panel(panel_content, title=title, border_style=border))

        # Action options - different for discovered vs failing
        console.print("\n[bold]Actions:[/bold]")
        if is_failure:
            console.print("  [green]r[/green] - Reset failures (re-enable scraping)")
            console.print("  [cyan]u[/cyan] - Update careers URL")
            console.print("  [yellow]s[/yellow] - Skip for now")
            console.print("  [red]d[/red] - Disable permanently")
            console.print("  [cyan]q[/cyan] - Quit review")
            choices = ["r", "u", "s", "d", "q"]
        else:
            console.print("  [green]a[/green] - Activate (requires careers URL)")
            console.print("  [yellow]s[/yellow] - Skip for now")
            console.print("  [red]d[/red] - Delete (not relevant)")
            console.print("  [cyan]q[/cyan] - Quit review")
            choices = ["a", "s", "d", "q"]

        action = Prompt.ask("\n[bold]Choose action[/bold]", choices=choices, default="s")

        if action == "q":
            break
        elif action == "s":
            skipped += 1
            console.print("[yellow]⊘ Skipped[/yellow]")
        elif action == "d":
            _handle_delete_company(company, company_service, is_failure)
            deleted += 1
        elif action == "r" and is_failure:
            _handle_reset_failures(company, company_service)
            reset += 1
        elif action == "u" and is_failure:
            result = _handle_update_url(company, company_service)
            if result:
                reset += 1
            else:
                skipped += 1
        elif action == "a" and not is_failure:
            result = _handle_activate_company(company, company_service)
            if result:
                activated += 1
            else:
                skipped += 1

    # Summary
    console.print(SEPARATOR_FULL)
    console.print("[bold green]Review Summary[/bold green]\n")
    console.print(f"  Companies reviewed: {reviewed}/{total}")
    console.print(f"  [green]Activated:[/green] {activated}")
    if reset > 0:
        console.print(f"  [green]Reset/Updated:[/green] {reset}")
    console.print(f"  [yellow]Skipped:[/yellow] {skipped}")
    console.print(f"  [red]Deleted/Disabled:[/red] {deleted}")

    press_enter_to_continue()


def _handle_delete_company(  # pragma: no cover
    company: dict, company_service: CompanyService, is_failure: bool
) -> None:
    """Handle delete/disable action for a company."""
    label = "Disable" if is_failure else "Delete"
    if Confirm.ask(f"\n[red]{label} '{company.get('name')}'?[/red]", default=False):
        if is_failure:
            existing_notes = company.get("notes", "")
            company_service.disable_company(
                company.get("id"),
                reason="manually_disabled",
                notes=f"Manually disabled from TUI. {existing_notes}",
            )
        else:
            company_service.delete_company(company.get("id"))
        console.print(f"[red]✓ {label}d[/red]")
    else:
        console.print(f"[yellow]⊘ {label} cancelled[/yellow]")


def _handle_reset_failures(
    company: dict, company_service: CompanyService
) -> None:  # pragma: no cover
    """Reset consecutive failures and re-enable a company."""
    company_service.reset_company_failures(company.get("id"))
    console.print(f"[green]✓ Reset failures for {company.get('name')} — re-enabled[/green]")


def _handle_update_url(company: dict, company_service: CompanyService) -> bool:  # pragma: no cover
    """Update careers URL and reset failures. Returns True if updated."""
    careers_url = Prompt.ask(
        "\n[bold]Enter new careers page URL[/bold]",
        default=company.get("careers_url", ""),
    )
    if not careers_url or careers_url == company.get("careers_url"):
        console.print("[yellow]⊘ URL unchanged[/yellow]")
        return False

    company_service.update_company_url(company.get("id"), careers_url)
    console.print(f"[green]✓ Updated URL and reset failures for {company.get('name')}[/green]")
    console.print(f"[dim]   New URL: {careers_url}[/dim]")
    return True


def _handle_activate_company(  # pragma: no cover
    company: dict, company_service: CompanyService
) -> bool:
    """Activate an auto-discovered company. Returns True if activated."""
    from datetime import datetime

    careers_url = Prompt.ask(
        "\n[bold]Enter careers page URL[/bold]",
        default=company.get("careers_url", ""),
    )

    if careers_url and careers_url != "https://placeholder.com/careers":
        now = datetime.now().isoformat()
        notes = f"Activated from TUI on {now}. Originally: {company.get('notes', '')}"
        company_service.activate_company(company.get("id"), careers_url, notes=notes)
        console.print(f"[green]✓ Activated: {company.get('name')}[/green]")
        console.print(f"[dim]   URL: {careers_url}[/dim]")
        return True

    console.print("[yellow]⊘ Activation cancelled (invalid URL)[/yellow]")
    return False


def _make_rich_prompt_kit():
    """Create a PromptKit that uses Rich prompts instead of plain input()."""
    scripts_dir = str(Path(__file__).parent.parent / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from onboard_profile import PromptKit

    def rich_prompt(label: str, default: str = "") -> str:
        return Prompt.ask(f"  {label}", default=default or "")

    def rich_prompt_list(label: str, default: str = "") -> list[str]:
        raw = Prompt.ask(f"  {label}", default=default or "")
        if not raw:
            return []
        return [item.strip().lower() for item in raw.split(",") if item.strip()]

    def rich_prompt_yes_no(label: str, default: bool = False) -> bool:
        return Confirm.ask(f"  {label}", default=default)

    return PromptKit(
        prompt=rich_prompt,
        prompt_list=rich_prompt_list,
        prompt_yes_no=rich_prompt_yes_no,
        print_fn=console.print,
    )


def _review_and_save_profile(profile: dict, kit) -> bool:
    """Review profile JSON, confirm, and save. Returns True if saved."""
    import json

    console.print("\n[bold yellow]Review Profile:[/bold yellow]")
    console.print(Panel(json.dumps(profile, indent=2), title="Profile JSON", expand=False))

    if not kit.prompt_yes_no("Looks good? Save profile?", default=True):
        console.print("[yellow]Aborted.[/yellow]")
        return False

    from onboard_profile import save_profile

    result = save_profile(profile, kit)
    return result is not None


def _validate_and_setup_profile(profile_id: str, kit) -> None:
    """Validate profile, optionally backfill scores and run dry-run digest."""
    from onboard_profile import run_backfill, run_dry_digest, validate_profile

    console.print("\n[bold yellow]Validating...[/bold yellow]")
    if not validate_profile(profile_id):
        console.print("[red]Profile validation failed. Check JSON and retry.[/red]")
        return

    console.print("[green]✓ Profile loaded successfully![/green]")

    # Reload so new profile appears in TUI menus immediately
    pm = get_profile_manager()
    pm.reload_profiles()
    console.print(f"[green]✓ Profile '{profile_id}' now available in TUI[/green]")

    if kit.prompt_yes_no("Run backfill (score existing jobs)?", default=True):
        max_jobs = int(kit.prompt("Max jobs to backfill", "500"))
        console.print("\n[bold yellow]Backfilling scores...[/bold yellow]")
        run_backfill(profile_id, max_jobs)

    if kit.prompt_yes_no("Run dry-run digest (preview email)?", default=True):
        console.print("\n[bold yellow]Running dry-run digest...[/bold yellow]")
        run_dry_digest(profile_id)


def onboard_new_profile():  # pragma: no cover
    """Interactive wizard for creating a new profile via TUI."""
    scripts_dir = str(Path(__file__).parent.parent / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    from onboard_profile import gather_profile_info, print_onboarding_message

    clear_screen()
    console.print(MAGENTA_SEPARATOR_TOP)
    console.print("[bold magenta]           NEW PROFILE ONBOARDING              [/bold magenta]")
    console.print(MAGENTA_SEPARATOR_BOTTOM)

    kit = _make_rich_prompt_kit()

    # Step 1: Gather info
    profile = gather_profile_info(kit)

    # Step 2: Review & Save
    if not _review_and_save_profile(profile, kit):
        press_enter_to_continue()
        return

    # Step 3: Validate, backfill, dry-run
    _validate_and_setup_profile(profile["id"], kit)

    # Step 4: Onboarding message
    console.print("\n[bold yellow]Onboarding Message:[/bold yellow]")
    print_onboarding_message(profile)

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
