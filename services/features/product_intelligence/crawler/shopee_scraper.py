import re
import requests
import json
import logging
import urllib.parse
from typing import List, Any, Optional

from services.features.product_intelligence.crawler.base_scraper import BaseScraper
from schemas.product_crawler import CrawledProductItem, CrawledProductDetail, CrawledReview

# Configure logging
logger = logging.getLogger(__name__)

class ShopeeScraper(BaseScraper):
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://shopee.vn/",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json",
        }

    def crawl_search_results(self, search_url: str, max_products: int = 10) -> List[CrawledProductItem]:
        """
        Crawl search results from Shopee.
        """
        # Extract query from URL provided or use as is
        query = search_url
        if "shopee.vn/search" in search_url:
             parsed = urllib.parse.urlparse(search_url)
             qs = urllib.parse.parse_qs(parsed.query)
             if 'keyword' in qs:
                 query = qs['keyword'][0]
        
        logger.info(f"Shopee crawling search query: {query}")
        
        products = []
        
        # We will try to use the API directly first
        api_url = "https://shopee.vn/api/v4/search/search_items"
        params = {
            "by": "relevancy",
            "keyword": query,
            "limit": max_products,
            "newest": 0,
            "order": "desc",
            "page_type": "search",
            "scenario": "PAGE_GLOBAL_SEARCH",
            "version": 2
        }
        
        try:
            resp = requests.get(api_url, params=params, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("items", [])
                
                for item_wrapper in items:
                    item = item_wrapper.get("item_basic", {})
                    if not item:
                        continue
                        
                    itemid = item.get("itemid")
                    shopid = item.get("shopid")
                    name = item.get("name")
                    
                    # Construct link
                    # Shopee link format: https://shopee.vn/{name}-i.{shopid}.{itemid}
                    # We need to slugify the name roughly or just use a generic slug
                    safe_name = re.sub(r'[^a-zA-Z0-9]+', '-', name) if name else "product"
                    link = f"https://shopee.vn/{safe_name}-i.{shopid}.{itemid}"
                    
                    # Image URL
                    image = item.get("image")
                    img_url = f"https://down-ws-vn.img.susercontent.com/{image}" if image else None
                    
                    # Price (Shopee price is in micros, divide by 100000)
                    price = item.get("price")
                    if price:
                         price = price / 100000.0
                    
                    products.append(CrawledProductItem(
                        name=name,
                        price=price,
                        link=link,
                        img=img_url,
                        sold=item.get("sold") or item.get("historical_sold"),
                        rating=item.get("item_rating", {}).get("rating_star"),
                        platform="shopee"
                    ))
            else:
                logger.warning(f"Shopee search API returned status {resp.status_code}")
                # Fallback to selenium could be added here similar to LazadaScraper
                
        except Exception as e:
            logger.error(f"Error crawling Shopee search: {e}")
            
        return products

    def _extract_ids(self, url: str) -> tuple[Optional[str], Optional[str]]:
        """Extract itemid and shopid from Shopee URL"""
        # Pattern 1: i.{shopid}.{itemid}
        match = re.search(r"i\.(\d+)\.(\d+)", url)
        if match:
            return match.group(1), match.group(2)
        
        # Pattern 2: API style? Usually URLs are standardized.
        return None, None

    def crawl_product_details(self, product_url: str, review_limit: int = 30) -> CrawledProductDetail:
        """
        Crawl product details and reviews from Shopee
        """
        shopid, itemid = self._extract_ids(product_url)
        if not shopid or not itemid:
             logger.error(f"Could not extract shopid/itemid from url: {product_url}")
             return CrawledProductDetail(link=product_url)

        # 1. Get Product Info (Optional, but good for detailed rating)
        # API: https://shopee.vn/api/v4/item/get?itemid={itemid}&shopid={shopid}
        
        # 2. Get Reviews
        # API: https://shopee.vn/api/v2/item/get_ratings
        # params: itemid, shopid, filter=0 (all), flag=1 (has content?), limit, offset, type=0 (all)
        
        reviews_url = "https://shopee.vn/api/v2/item/get_ratings"
        all_reviews = []
        
        offset = 0
        limit_per_req = 20 # Shopee limit usually 50 or 20
        
        while len(all_reviews) < review_limit:
            params = {
                "itemid": itemid,
                "shopid": shopid,
                "filter": 0,
                "flag": 1, 
                "limit": limit_per_req,
                "offset": offset,
                "type": 0
            }
            
            try:
                resp = requests.get(reviews_url, params=params, headers=self.headers, timeout=10)
                if resp.status_code != 200:
                    logger.warning(f"Shopee review API failed: {resp.status_code}")
                    break
                    
                data = resp.json()
                data_inner = data.get("data", {})
                ratings = data_inner.get("ratings", [])
                
                if not ratings:
                    break
                    
                for r in ratings:
                    # author
                    author_name = r.get("author_username")
                    if not author_name and r.get("anonymous"):
                        author_name = "******"
                    
                    # content
                    content = r.get("comment", "")
                    
                    # rating
                    rating_star = r.get("rating_star", 5)
                    
                    # time
                    timestamp = r.get("ctime")
                    # Convert to convenient string if needed, or keep raw
                    
                    # images
                    images = r.get("images", []) or []
                    image_urls = [f"https://down-ws-vn.img.susercontent.com/{img}" for img in images]
                    
                    review = CrawledReview(
                        author=author_name or "Anonymous",
                        rating=rating_star,
                        content=content,
                        time=str(timestamp),
                        images=image_urls,
                        helpful_count=r.get("like_count", 0)
                    )
                    all_reviews.append(review)
                    if len(all_reviews) >= review_limit:
                        break
                
                offset += len(ratings)
                
            except Exception as e:
                logger.error(f"Error crawling Shopee reviews: {e}")
                break
                
        return CrawledProductDetail(
             link=product_url,
             category="", 
             description="", 
             detailed_rating={},
             total_rating=len(all_reviews),
             comments=all_reviews
        )
