from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from schemas.product_crawler import CrawledProductItem, CrawledProductDetail

class BaseScraper(ABC):
    @abstractmethod
    def crawl_search_results(self, search_url: str, max_products: int = 10) -> List[CrawledProductItem]:
        """
        Crawl list of products from a search page URL or keyword.
        
        Returns:
            List of CrawledProductItem
        """
        pass

    @abstractmethod
    def crawl_product_details(self, product_url: str, review_limit: int = 30) -> CrawledProductDetail:
        """
        Crawl detailed information and reviews for a single product.
        
        Returns:
            CrawledProductDetail
        """
        pass
