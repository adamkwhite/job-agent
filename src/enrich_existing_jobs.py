#!/usr/bin/env python3
"""
Enrich existing jobs in the database with additional company information
"""

import sqlite3
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from enrichment.enrichment_pipeline import EnrichmentPipeline
from models import OpportunityData


def main():
    """Enrich all jobs in database that haven't been enriched yet"""

    # Initialize enrichment pipeline
    enrichment = EnrichmentPipeline()

    # Connect to database
    db_path = Path(__file__).parent.parent / "data" / "jobs.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get jobs that need enrichment (no research_notes)
    cursor.execute("""
        SELECT id, company, title, location, link, fit_score, fit_grade, source
        FROM jobs
        WHERE (research_notes IS NULL OR research_notes = '')
        AND fit_score >= 70
        ORDER BY fit_score DESC
        LIMIT 10
    """)

    jobs_to_enrich = cursor.fetchall()
    print(f"Found {len(jobs_to_enrich)} jobs to enrich\n")

    enriched_count = 0

    for job_id, company, title, location, link, score, grade, source in jobs_to_enrich:
        print(f"Enriching: {title} at {company} (Score: {score}, Grade: {grade})")

        # Create opportunity data for enrichment
        opportunity = OpportunityData(
            title=title,
            company=company,
            location=location or "",
            link=link or "",
            keywords_matched=[],
            source=source or "unknown",
            type="direct_job",
        )

        # Enrich the opportunity
        try:
            enriched_result = enrichment.enrich_opportunity(opportunity)
            enriched = enriched_result.opportunity

            if (
                enriched.research_notes
                and enriched.research_notes != "No additional research available"
            ):
                # Update database with research notes
                cursor.execute(
                    """
                    UPDATE jobs
                    SET research_notes = ?
                    WHERE id = ?
                """,
                    (enriched.research_notes, job_id),
                )

                conn.commit()
                enriched_count += 1
                print(f"  ✓ Enriched with: {enriched.research_notes[:100]}...")
            else:
                print("  - No enrichment data available")

        except Exception as e:
            print(f"  ✗ Error enriching: {e}")

        # Rate limiting
        time.sleep(1)

    print(f"\n{'='*60}")
    print("Enrichment Complete")
    print(f"{'='*60}")
    print(f"Jobs enriched: {enriched_count}/{len(jobs_to_enrich)}")

    # Show some enriched jobs
    cursor.execute("""
        SELECT company, title, research_notes, fit_score
        FROM jobs
        WHERE research_notes IS NOT NULL AND research_notes != ''
        ORDER BY fit_score DESC
        LIMIT 5
    """)

    print("\nTop enriched jobs:")
    for company, title, notes, score in cursor.fetchall():
        print(f"\n{score} pts - {title} at {company}")
        print(f"  Research: {notes[:150]}...")

    conn.close()


if __name__ == "__main__":
    main()
