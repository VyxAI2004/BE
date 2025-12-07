from typing import Optional
from services.features.product_intelligence.crawler.base_scraper import BaseScraper
from services.features.product_intelligence.crawler.lazada_scraper import LazadaScraper
from services.features.product_intelligence.crawler.tiki_scraper import TikiScraper

class ScraperFactory:
    @staticmethod
    def get_scraper(url_or_platform: str) -> BaseScraper:
        """
        Returns the appropriate scraper instance based on the URL or platform name.
        Defaults to ShopeeScraper if detection fails (or we can raise error).
        """
        if "lazada" in url_or_platform.lower():
            return LazadaScraper()
        elif "tiki" in url_or_platform.lower():
            return TikiScraper()
        else:
            # For testing purposes, default to Lazada if Shopee is removed
            return LazadaScraper()
