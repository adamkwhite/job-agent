"""
Generate HTML page with jobs table
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from database import JobDatabase


def generate_html():
    """Generate HTML page with all jobs (sorted by score)"""
    db = JobDatabase()
    jobs = db.get_recent_jobs(limit=100)

    # Sort by fit_score descending (None scores go to bottom)
    jobs = sorted(jobs, key=lambda x: x.get("fit_score") or 0, reverse=True)

    html = (
        """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Job Opportunities - PM & Engineering Leadership</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
        }
        .stats {
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }
        .stats span {
            margin-right: 20px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th {
            background-color: #4CAF50;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            position: sticky;
            top: 0;
        }
        td {
            padding: 12px;
            border-bottom: 1px solid #ddd;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .source-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
        }
        .source-linkedin {
            background-color: #0077b5;
            color: white;
        }
        .source-supra {
            background-color: #ff6b6b;
            color: white;
        }
        .source-f6s {
            background-color: #95e1d3;
            color: #333;
        }
        .keywords {
            font-size: 12px;
            color: #666;
            margin-top: 4px;
        }
        .keyword-tag {
            background-color: #e8f5e9;
            padding: 2px 6px;
            border-radius: 3px;
            margin-right: 4px;
            display: inline-block;
        }
        a {
            color: #4CAF50;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        .title-cell {
            font-weight: 500;
            color: #333;
        }
        .company-cell {
            color: #666;
        }
        .location-cell {
            color: #999;
            font-size: 14px;
        }
        .score-cell {
            font-weight: 600;
            font-size: 16px;
            text-align: center;
        }
        .grade-A {
            color: #1e7e34;
            background-color: #d4edda;
        }
        .grade-B {
            color: #004085;
            background-color: #cce5ff;
        }
        .grade-C {
            color: #856404;
            background-color: #fff3cd;
        }
        .grade-D {
            color: #721c24;
            background-color: #f8d7da;
        }
        .grade-F {
            color: #666;
            background-color: #e2e3e5;
        }
        .filters {
            margin: 20px 0;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 4px;
        }
        .filter-btn {
            padding: 8px 16px;
            margin-right: 10px;
            border: 2px solid #ddd;
            background-color: white;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.2s;
        }
        .filter-btn:hover {
            background-color: #e9ecef;
        }
        .filter-btn.active {
            background-color: #4CAF50;
            color: white;
            border-color: #4CAF50;
        }
    </style>
    <script>
        function filterJobs(filterType) {
            const rows = document.querySelectorAll('tbody tr');
            const buttons = document.querySelectorAll('.filter-btn');

            // Update button states
            buttons.forEach(btn => {
                if (btn.dataset.filter === filterType) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            });

            // Filter rows
            rows.forEach(row => {
                const locationCell = row.cells[3].textContent.toLowerCase();
                let show = false;

                if (filterType === 'all') {
                    show = true;
                } else if (filterType === 'remote') {
                    show = locationCell.includes('remote') || locationCell.includes('wfh') || locationCell.includes('anywhere');
                } else if (filterType === 'hybrid') {
                    show = locationCell.includes('hybrid');
                } else if (filterType === 'ontario') {
                    show = locationCell.includes('toronto') || locationCell.includes('waterloo') ||
                           locationCell.includes('burlington') || locationCell.includes('ontario') ||
                           locationCell.includes('canada') || locationCell.includes('oakville') ||
                           locationCell.includes('hamilton') || locationCell.includes('mississauga');
                } else if (filterType === 'acceptable') {
                    // Remote OR Hybrid OR Ontario
                    show = locationCell.includes('remote') || locationCell.includes('hybrid') ||
                           locationCell.includes('toronto') || locationCell.includes('waterloo') ||
                           locationCell.includes('burlington') || locationCell.includes('ontario') ||
                           locationCell.includes('canada') || locationCell.includes('wfh');
                }

                row.style.display = show ? '' : 'none';
            });

            // Update count
            const visibleRows = Array.from(rows).filter(row => row.style.display !== 'none').length;
            document.getElementById('job-count').textContent = visibleRows;
        }

        // Initialize with all jobs visible
        window.onload = () => {
            document.querySelector('[data-filter="all"]').classList.add('active');
        };
    </script>
</head>
<body>
    <div class="container">
        <h1>🎯 Job Opportunities - PM & Engineering Leadership</h1>
        <div class="stats">
            <span><strong>Showing:</strong> <span id="job-count">"""
        + str(len(jobs))
        + """</span> of """
        + str(len(jobs))
        + """ jobs</span>
            <span><strong>LinkedIn:</strong> """
        + str(sum(1 for j in jobs if j["source"] == "linkedin"))
        + """</span>
            <span><strong>Supra:</strong> """
        + str(sum(1 for j in jobs if j["source"] == "supra_newsletter"))
        + """</span>
            <span><strong>Robotics:</strong> """
        + str(sum(1 for j in jobs if j["source"] == "robotics_deeptech_sheet"))
        + """</span>
            <span><strong>Date:</strong> """
        + (jobs[0]["received_at"][:10] if jobs else "N/A")
        + """</span>
        </div>

        <div class="filters">
            <strong>Location Filter:</strong>
            <button class="filter-btn" data-filter="all" onclick="filterJobs('all')">All Jobs</button>
            <button class="filter-btn" data-filter="acceptable" onclick="filterJobs('acceptable')">✅ Acceptable (Remote/Hybrid/Ontario)</button>
            <button class="filter-btn" data-filter="remote" onclick="filterJobs('remote')">🏠 Remote Only</button>
            <button class="filter-btn" data-filter="hybrid" onclick="filterJobs('hybrid')">🏢 Hybrid</button>
            <button class="filter-btn" data-filter="ontario" onclick="filterJobs('ontario')">📍 Ontario/Canada</button>
        </div>

        <table>
            <thead>
                <tr>
                    <th style="width: 8%">Fit</th>
                    <th style="width: 27%">Title</th>
                    <th style="width: 18%">Company</th>
                    <th style="width: 13%">Location</th>
                    <th style="width: 22%">Keywords</th>
                    <th style="width: 12%">Source</th>
                </tr>
            </thead>
            <tbody>
"""
    )

    for job in jobs:
        # Parse keywords
        try:
            keywords = json.loads(job["keywords_matched"])
        except (json.JSONDecodeError, TypeError):
            keywords = []

        # Format source badge
        source_class = "source-" + job["source"].replace("_newsletter", "").replace("_", "-")
        source_label = job["source"].replace("_", " ").title().replace("Newsletter", "")

        # Format location
        location = job["location"] or "Not specified"
        if len(location) > 30:
            location = location[:27] + "..."

        # Format keywords
        keywords_html = "".join([f'<span class="keyword-tag">{k}</span>' for k in keywords[:4]])

        # Format fit score
        fit_score = job.get("fit_score")
        fit_grade = job.get("fit_grade") or "N/A"
        if fit_score:
            score_display = f"{fit_grade}<br><small>{fit_score}/115</small>"
            grade_class = f"grade-{fit_grade}"
        else:
            score_display = "Not Scored"
            grade_class = "grade-F"

        html += f"""
                <tr>
                    <td class="score-cell {grade_class}">{score_display}</td>
                    <td class="title-cell">
                        <a href="{job["link"]}" target="_blank">{job["title"]}</a>
                    </td>
                    <td class="company-cell">{job["company"]}</td>
                    <td class="location-cell">{location}</td>
                    <td class="keywords">{keywords_html}</td>
                    <td>
                        <span class="source-badge {source_class}">{source_label}</span>
                    </td>
                </tr>
"""

    html += """
            </tbody>
        </table>
    </div>
</body>
</html>
"""

    # Write to file
    output_file = Path("jobs.html")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✓ HTML page generated: {output_file.absolute()}")
    print(f"  Total jobs: {len(jobs)}")
    print(f"\nOpen in browser: file://{output_file.absolute()}")


if __name__ == "__main__":
    generate_html()
