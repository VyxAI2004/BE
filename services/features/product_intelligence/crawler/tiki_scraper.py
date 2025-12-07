import requests
import urllib.parse
import logging
from typing import List, Dict, Any
from services.features.product_intelligence.crawler.base_scraper import BaseScraper
from schemas.product_crawler import CrawledProductItem, CrawledProductDetail, CrawledReview

logger = logging.getLogger(__name__)

class TikiScraper(BaseScraper):
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://tiki.vn/",
        }

    def crawl_search_results(self, search_url: str, max_products: int = 10) -> List[CrawledProductItem]:
        """
        Tiki Search API: https://tiki.vn/api/v2/products?q={query}&limit={limit}
        """
        # Extract query from URL or use as raw query
        query = search_url
        if "tiki.vn" in search_url:
            try:
                parsed = urllib.parse.urlparse(search_url)
                qs = urllib.parse.parse_qs(parsed.query)
                query = qs.get('q', [''])[0]
                # Fallback if URL is like tiki.vn/search?q=...
            except:
                pass
        
        if not query:
            return []

        q = urllib.parse.quote(query)
        api_url = f"https://tiki.vn/api/v2/products?limit={max_products}&q={q}"

        try:
            res = requests.get(api_url, headers=self.headers, timeout=10)
            data = res.json()
            products = data.get("data", [])
            
            results = []
            for p in products:
                # Tiki API returns standardized data
                link = f"https://tiki.vn/{p.get('url_path')}" if p.get('url_path') else ""
                
                results.append(CrawledProductItem(
                    name=p.get("name"),
                    price=p.get("price"),
                    sold=p.get("quantity_sold", {}).get("value"),
                    rating=p.get("rating_average"),
                    img=p.get("thumbnail_url"),
                    link=link,
                    platform="tiki"
                ))
            
            return results

        except Exception as e:
            logger.error(f"Tiki search error: {e}")
            return []

    def crawl_product_details(self, product_url: str, review_limit: int = 30) -> CrawledProductDetail:
        """
        Crawl detail Tiki. 
        Tiki Product API: https://tiki.vn/api/v2/products/{product_id}
        """
        # Extract ID from URL (e.g., -p123456.html)
        try:
            product_id = ""
            if "-p" in product_url:
                product_id = product_url.split("-p")[-1].split(".")[0]
            
            if not product_id:
                logger.warning("Could not extract Tiki Product ID")
                return CrawledProductDetail(link=product_url)

            api_url = f"https://tiki.vn/api/v2/products/{product_id}"
            res = requests.get(api_url, headers=self.headers, timeout=10)
            data = res.json()

            # Get description
            description = data.get("description", "")
            
            # Tiki reviews API is separate: https://tiki.vn/api/v2/reviews?product_id={id}
            # Implementing basic detail return for now
            
            return CrawledProductDetail(
                link=product_url,
                category=data.get("categories", {}).get("name", ""),
                description=description,
                detailed_rating={}, # Tiki API structure needed here
                total_rating=data.get("review_count", 0),
                comments=[] # Need to call review API separately
            )

        except Exception as e:
            logger.error(f"Tiki detail crawl error: {e}")
            return CrawledProductDetail(link=product_url)
