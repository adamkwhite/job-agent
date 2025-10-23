"""Web scrapers for various job boards"""

from scrapers.builtin_scraper import BuiltInScraper
from scrapers.robotics_deeptech_scraper import RoboticsDeeptechScraper
from scrapers.venturelab_scraper import VentureLabScraper

__all__ = ["BuiltInScraper", "VentureLabScraper", "RoboticsDeeptechScraper"]
