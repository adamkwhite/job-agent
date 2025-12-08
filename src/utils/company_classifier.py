"""
Company Classification System for Software Engineering Role Filtering

This module implements multi-signal company classification to distinguish between
software companies, hardware companies, and dual-domain companies. The classification
is used to filter software engineering leadership roles for hardware-focused profiles.

Algorithm:
    - Signal 1 (weight 0.3): Company name keyword matching
    - Signal 2 (weight 0.4): Curated company list membership
    - Signal 3 (weight 0.2): Domain keyword matching in job context
    - Signal 4 (weight 0.1): Job title/description analysis

Classification Types:
    - software: Primarily software/SaaS companies
    - hardware: Primarily hardware/robotics/physical product companies
    - both: Dual-domain companies (e.g., Tesla, Apple, Google)
    - unknown: Insufficient signals to classify

Related:
    - Issue #122: Software Engineering Role Filtering
    - PRD: docs/features/software-engineering-role-filter-PLANNED/prd.md
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)

CompanyType = Literal["software", "hardware", "both", "unknown"]
ConfidenceSource = Literal["auto", "manual"]


@dataclass
class CompanyClassification:
    """
    Result of company classification with confidence and signal breakdown

    Attributes:
        type: Classification type (software/hardware/both/unknown)
        confidence: Confidence score from 0.0 to 1.0
        signals: Dictionary of individual signal contributions (nested dicts with mixed types)
        source: Whether classification was automated or manual override
    """

    type: CompanyType
    confidence: float  # 0.0 to 1.0
    signals: dict[str, Any]  # Nested dicts with mixed types (score, type, keywords, etc.)
    source: ConfidenceSource = "auto"

    def __post_init__(self):
        """Validate confidence score is in valid range"""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be 0.0-1.0, got {self.confidence}")


class CompanyClassifier:
    """
    Multi-signal company classification system

    Classifies companies as software, hardware, both, or unknown based on:
    1. Company name keywords (weight: 0.3)
    2. Curated company lists (weight: 0.4)
    3. Domain keywords from job context (weight: 0.2)
    4. Job title/description analysis (weight: 0.1)

    Manual overrides stored in database take precedence over automated classification.
    Results are cached to avoid re-computation.

    Performance target: <100ms per classification
    """

    # Signal weights (must sum to 1.0)
    WEIGHT_NAME = 0.3
    WEIGHT_CURATED = 0.4
    WEIGHT_DOMAIN = 0.2
    WEIGHT_JOB_CONTENT = 0.1

    def __init__(self, db_path: str | Path | None = None, config_path: str | Path | None = None):
        """
        Initialize company classifier

        Args:
            db_path: Path to SQLite database (defaults to data/jobs.db)
            config_path: Path to company classifications config (defaults to config/company_classifications.json)
        """
        self.db_path = db_path or Path(__file__).parent.parent.parent / "data" / "jobs.db"
        self.config_path = (
            config_path
            or Path(__file__).parent.parent.parent / "config" / "company_classifications.json"
        )

        # Load curated company lists and keywords
        self.config = self._load_config()

        # In-memory cache for classification results
        self._classification_cache: dict[str, CompanyClassification] = {}

        logger.debug(
            f"Initialized CompanyClassifier with {len(self.config.get('hardware_companies', []))} "
            f"hardware companies, {len(self.config.get('software_companies', []))} software companies, "
            f"{len(self.config.get('both_domains', []))} dual-domain companies"
        )

    def _load_config(self) -> dict:
        """Load company classifications configuration from JSON file"""
        try:
            with open(self.config_path) as f:
                config = json.load(f)
            logger.debug(f"Loaded company classifications config from {self.config_path}")
            return config
        except FileNotFoundError:
            logger.warning(
                f"Company classifications config not found at {self.config_path}, using empty config"
            )
            return {
                "hardware_companies": [],
                "software_companies": [],
                "both_domains": [],
                "_keywords": {"hardware_indicators": [], "software_indicators": []},
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse company classifications config: {e}")
            raise

    def get_manual_override(self, company_name: str) -> CompanyClassification | None:
        """
        Check database for manual company classification override

        Manual overrides take precedence over automated classification and
        are marked with source='manual'.

        Args:
            company_name: Company name to check

        Returns:
            CompanyClassification if manual override exists, None otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT classification, confidence_score, signals
                FROM company_classifications
                WHERE company_name = ? AND source = 'manual'
                ORDER BY updated_at DESC
                LIMIT 1
            """,
                (company_name,),
            )

            row = cursor.fetchone()
            conn.close()

            if row:
                classification, confidence, signals_json = row
                signals = json.loads(signals_json) if signals_json else {}

                logger.info(
                    f"Using manual override for '{company_name}': {classification} "
                    f"(confidence: {confidence:.2f})"
                )

                return CompanyClassification(
                    type=classification, confidence=confidence, signals=signals, source="manual"
                )

            return None

        except sqlite3.Error as e:
            logger.error(f"Database error checking manual override for '{company_name}': {e}")
            return None

    def _check_company_name_keywords(self, company_name: str) -> dict[str, Any]:
        """
        Signal 1: Check company name for hardware/software indicators

        Args:
            company_name: Company name to analyze

        Returns:
            Dict with 'score' (0.0-1.0), 'type' (software/hardware/unknown), 'matched_keywords'
        """
        company_lower = company_name.lower()

        hardware_keywords = self.config.get("_keywords", {}).get("hardware_indicators", [])
        software_keywords = self.config.get("_keywords", {}).get("software_indicators", [])

        hardware_matches = [kw for kw in hardware_keywords if kw.lower() in company_lower]
        software_matches = [kw for kw in software_keywords if kw.lower() in company_lower]

        # Determine classification based on matches
        if hardware_matches and not software_matches:
            return {
                "score": 1.0,
                "type": "hardware",
                "matched_keywords": hardware_matches,
            }
        elif software_matches and not hardware_matches:
            return {
                "score": 1.0,
                "type": "software",
                "matched_keywords": software_matches,
            }
        elif hardware_matches and software_matches:
            # Both types of keywords present - likely dual-domain
            return {
                "score": 0.8,
                "type": "both",
                "matched_keywords": hardware_matches + software_matches,
            }
        else:
            return {"score": 0.0, "type": "unknown", "matched_keywords": []}

    def _check_curated_lists(self, company_name: str) -> dict[str, Any]:
        """
        Signal 2: Check if company is in curated lists (highest weight signal)

        Args:
            company_name: Company name to check

        Returns:
            Dict with 'score' (0.0-1.0), 'type' (software/hardware/both/unknown), 'list_match'
        """
        # Normalize company name for matching (case-insensitive, strip whitespace)
        company_normalized = company_name.strip().lower()

        hardware_companies = [c.lower() for c in self.config.get("hardware_companies", [])]
        software_companies = [c.lower() for c in self.config.get("software_companies", [])]
        both_domains = [c.lower() for c in self.config.get("both_domains", [])]

        # Check for exact match in curated lists
        if company_normalized in hardware_companies:
            return {"score": 1.0, "type": "hardware", "list_match": "hardware_companies"}
        elif company_normalized in software_companies:
            return {"score": 1.0, "type": "software", "list_match": "software_companies"}
        elif company_normalized in both_domains:
            return {"score": 1.0, "type": "both", "list_match": "both_domains"}

        # Check for partial match (company name contains list entry or vice versa)
        for hw_company in hardware_companies:
            if hw_company in company_normalized or company_normalized in hw_company:
                return {
                    "score": 0.9,
                    "type": "hardware",
                    "list_match": f"partial: {hw_company}",
                }

        for sw_company in software_companies:
            if sw_company in company_normalized or company_normalized in sw_company:
                return {
                    "score": 0.9,
                    "type": "software",
                    "list_match": f"partial: {sw_company}",
                }

        for both_company in both_domains:
            if both_company in company_normalized or company_normalized in both_company:
                return {"score": 0.9, "type": "both", "list_match": f"partial: {both_company}"}

        return {"score": 0.0, "type": "unknown", "list_match": None}

    def _check_domain_keywords(self, domain_keywords: list[str]) -> dict[str, Any]:
        """
        Signal 3: Analyze job domain keywords

        Args:
            domain_keywords: List of domain keywords from job (e.g., from profile scoring)

        Returns:
            Dict with 'score' (0.0-1.0), 'type' (software/hardware/unknown), 'matched_count'
        """
        if not domain_keywords:
            return {"score": 0.0, "type": "unknown", "matched_count": 0}

        # Convert to lowercase for matching
        domain_lower = [kw.lower() for kw in domain_keywords]

        # Hardware domain keywords
        hardware_domains = [
            "robotics",
            "automation",
            "hardware",
            "iot",
            "mechatronics",
            "embedded",
            "firmware",
            "mechanical",
            "manufacturing",
            "industrial",
            "medtech",
            "medical device",
        ]

        # Software domain keywords
        software_domains = [
            "saas",
            "software",
            "cloud",
            "web",
            "mobile",
            "frontend",
            "backend",
            "fullstack",
            "devops",
            "fintech",
            "analytics",
        ]

        hardware_matches = sum(1 for kw in domain_lower if any(hw in kw for hw in hardware_domains))
        software_matches = sum(1 for kw in domain_lower if any(sw in kw for sw in software_domains))

        total_keywords = len(domain_keywords)

        # Calculate match percentage
        if hardware_matches > software_matches and hardware_matches > 0:
            score = min(hardware_matches / total_keywords, 1.0)
            return {"score": score, "type": "hardware", "matched_count": hardware_matches}
        elif software_matches > hardware_matches and software_matches > 0:
            score = min(software_matches / total_keywords, 1.0)
            return {"score": score, "type": "software", "matched_count": software_matches}
        elif hardware_matches == software_matches and hardware_matches > 0:
            score = min(hardware_matches / total_keywords, 0.8)
            return {"score": score, "type": "both", "matched_count": hardware_matches}
        else:
            return {"score": 0.0, "type": "unknown", "matched_count": 0}

    def _analyze_job_content(
        self, job_title: str = "", job_description: str = ""
    ) -> dict[str, Any]:
        """
        Signal 4: Analyze job title and description for hardware/software focus

        Args:
            job_title: Job title text
            job_description: Job description text (optional)

        Returns:
            Dict with 'score' (0.0-1.0), 'type' (software/hardware/unknown), 'indicators_found'
        """
        content = f"{job_title} {job_description}".lower()

        if not content.strip():
            return {"score": 0.0, "type": "unknown", "indicators_found": []}

        # Hardware job indicators
        hardware_indicators = [
            "hardware engineering",
            "robotics",
            "embedded systems",
            "firmware",
            "mechanical",
            "electrical",
            "pcb",
            "manufacturing",
            "physical product",
            "iot devices",
        ]

        # Software job indicators
        software_indicators = [
            "software engineering",
            "web development",
            "mobile app",
            "cloud infrastructure",
            "backend",
            "frontend",
            "full stack",
            "saas",
            "devops",
            "data engineering",
        ]

        hardware_found = [ind for ind in hardware_indicators if ind in content]
        software_found = [ind for ind in software_indicators if ind in content]

        # Determine classification based on indicators
        if hardware_found and not software_found:
            score = min(len(hardware_found) / 3, 1.0)  # Normalize to 1.0 at 3+ indicators
            return {"score": score, "type": "hardware", "indicators_found": hardware_found}
        elif software_found and not hardware_found:
            score = min(len(software_found) / 3, 1.0)
            return {"score": score, "type": "software", "indicators_found": software_found}
        elif hardware_found and software_found:
            score = min((len(hardware_found) + len(software_found)) / 6, 0.8)
            return {
                "score": score,
                "type": "both",
                "indicators_found": hardware_found + software_found,
            }
        else:
            return {"score": 0.0, "type": "unknown", "indicators_found": []}

    def _combine_signals(self, signals: dict[str, Any]) -> CompanyClassification:
        """
        Combine multiple classification signals using weighted scoring

        Args:
            signals: Dictionary containing results from each signal method

        Returns:
            CompanyClassification with final type and confidence
        """
        # Extract individual signal results
        name_signal = signals.get("name", {"score": 0.0, "type": "unknown"})
        curated_signal = signals.get("curated", {"score": 0.0, "type": "unknown"})
        domain_signal = signals.get("domain", {"score": 0.0, "type": "unknown"})
        job_content_signal = signals.get("job_content", {"score": 0.0, "type": "unknown"})

        # Calculate weighted votes for each type
        type_scores = {
            "software": 0.0,
            "hardware": 0.0,
            "both": 0.0,
            "unknown": 0.0,
        }

        # Add weighted contributions from each signal
        type_scores[name_signal["type"]] += name_signal["score"] * self.WEIGHT_NAME
        type_scores[curated_signal["type"]] += curated_signal["score"] * self.WEIGHT_CURATED
        type_scores[domain_signal["type"]] += domain_signal["score"] * self.WEIGHT_DOMAIN
        type_scores[job_content_signal["type"]] += (
            job_content_signal["score"] * self.WEIGHT_JOB_CONTENT
        )

        # Determine final classification (highest weighted score wins)
        final_type = max(type_scores.items(), key=lambda x: x[1])
        classification_type: CompanyType = final_type[0]  # type: ignore[assignment]
        confidence = final_type[1]

        # If no strong signals, mark as unknown with low confidence
        if confidence < 0.3:
            classification_type = "unknown"

        logger.debug(
            f"Combined signals: {classification_type} (confidence: {confidence:.2f}) - "
            f"scores: {type_scores}"
        )

        return CompanyClassification(
            type=classification_type, confidence=confidence, signals=signals, source="auto"
        )

    def classify_company(
        self,
        company_name: str,
        job_title: str = "",
        job_description: str = "",
        domain_keywords: list[str] | None = None,
    ) -> CompanyClassification:
        """
        Classify company using multiple signals

        Process:
        1. Check for manual override in database (highest priority)
        2. Check in-memory cache
        3. Run multi-signal classification:
           - Company name keywords (weight: 0.3)
           - Curated company lists (weight: 0.4)
           - Domain keywords (weight: 0.2)
           - Job content analysis (weight: 0.1)
        4. Cache result
        5. Store in database (if automated classification)

        Args:
            company_name: Company name to classify
            job_title: Job title for context (optional)
            job_description: Job description for context (optional)
            domain_keywords: Domain keywords from job (optional)

        Returns:
            CompanyClassification with type, confidence, and signal breakdown
        """
        # Check manual overrides first (highest priority)
        manual_override = self.get_manual_override(company_name)
        if manual_override:
            return manual_override

        # Check in-memory cache
        cache_key = company_name.lower().strip()
        if cache_key in self._classification_cache:
            logger.debug(f"Using cached classification for '{company_name}'")
            return self._classification_cache[cache_key]

        # Run multi-signal classification
        signals = {}

        # Signal 1: Company name keywords (weight: 0.3)
        signals["name"] = self._check_company_name_keywords(company_name)

        # Signal 2: Curated company lists (weight: 0.4)
        signals["curated"] = self._check_curated_lists(company_name)

        # Signal 3: Domain keywords (weight: 0.2)
        signals["domain"] = self._check_domain_keywords(domain_keywords or [])

        # Signal 4: Job content analysis (weight: 0.1)
        signals["job_content"] = self._analyze_job_content(job_title, job_description)

        # Combine signals with weighted scoring
        classification = self._combine_signals(signals)

        # Log classification decision
        logger.info(
            f"Classified '{company_name}' as '{classification.type}' "
            f"(confidence: {classification.confidence:.2f}, source: {classification.source})"
        )
        logger.debug(f"Signal breakdown: {classification.signals}")

        # Cache result
        self._classification_cache[cache_key] = classification

        # Store in database for future reference
        self._store_classification(company_name, classification)

        return classification

    def _store_classification(self, company_name: str, classification: CompanyClassification):
        """
        Store automated classification in database

        Only stores if classification is automated (not manual override).
        Updates existing record if present, otherwise inserts new record.

        Args:
            company_name: Company name
            classification: Classification result to store
        """
        if classification.source != "auto":
            return  # Don't store manual overrides (they're already in DB)

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            now = datetime.now().isoformat()
            signals_json = json.dumps(classification.signals)

            # Check if record exists
            cursor.execute(
                """
                SELECT id FROM company_classifications
                WHERE company_name = ? AND source = 'auto'
            """,
                (company_name,),
            )

            existing = cursor.fetchone()

            if existing:
                # Update existing record
                cursor.execute(
                    """
                    UPDATE company_classifications
                    SET classification = ?, confidence_score = ?, signals = ?, updated_at = ?
                    WHERE id = ?
                """,
                    (
                        classification.type,
                        classification.confidence,
                        signals_json,
                        now,
                        existing[0],
                    ),
                )
                logger.debug(f"Updated existing classification for '{company_name}'")
            else:
                # Insert new record
                cursor.execute(
                    """
                    INSERT INTO company_classifications
                    (company_name, classification, confidence_score, source, signals, created_at, updated_at)
                    VALUES (?, ?, ?, 'auto', ?, ?, ?)
                """,
                    (
                        company_name,
                        classification.type,
                        classification.confidence,
                        signals_json,
                        now,
                        now,
                    ),
                )
                logger.debug(f"Stored new classification for '{company_name}'")

            conn.commit()
            conn.close()

        except sqlite3.Error as e:
            logger.error(f"Database error storing classification for '{company_name}': {e}")
