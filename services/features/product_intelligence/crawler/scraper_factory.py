from typing import Optional
from services.features.product_intelligence.crawler.base_scraper import BaseScraper
from services.features.product_intelligence.crawler.lazada_scraper import LazadaScraper
from services.features.product_intelligence.crawler.tiki_scraper import TikiScraper
from services.features.product_intelligence.crawler.shopee_scraper import ShopeeScraper

class ScraperFactory:
    @staticmethod
    def get_scraper(url_or_platform: str) -> BaseScraper:
        if "lazada" in url_or_platform.lower():
            return LazadaScraper()
        elif "tiki" in url_or_platform.lower():
            return TikiScraper()
        elif "shopee" in url_or_platform.lower():
            return ShopeeScraper()
        else:
            return ShopeeScraper()
