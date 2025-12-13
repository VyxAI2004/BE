import requests
import urllib.parse
from typing import List

from services.features.product_intelligence.crawler.base_scraper import BaseScraper
from schemas.product_crawler import CrawledProductItem, CrawledProductDetail, CrawledReview


class TikiScraper(BaseScraper):
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": "https://tiki.vn/",
        }

    def crawl_search_results(self, search_url: str, max_products: int = 10) -> List[CrawledProductItem]:
        query = search_url
        if "tiki.vn" in search_url:
            try:
                parsed = urllib.parse.urlparse(search_url)
                qs = urllib.parse.parse_qs(parsed.query)
                query = qs.get('q', [''])[0]
            except Exception:
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
                link = f"https://tiki.vn/{p.get('url_path')}" if p.get('url_path') else None
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
        except Exception:
            return []

    def crawl_product_details(self, product_url: str, review_limit: int = 30) -> CrawledProductDetail:
        try:
            product_id = ""
            if "-p" in product_url:
                part = product_url.split("-p")[-1]
                product_id = part.split(".")[0].split("?")[0]

            if not product_id:
                return CrawledProductDetail(link=product_url)

            api_url = f"https://tiki.vn/api/v2/products/{product_id}"
            res = requests.get(api_url, headers=self.headers, timeout=10)
            if res.status_code != 200:
                return CrawledProductDetail(link=product_url)

            data = res.json()
            description = data.get("description", "")

            comments = []
            page = 1
            while len(comments) < review_limit:
                reviews_api = f"https://tiki.vn/api/v2/reviews?product_id={product_id}&limit=20&page={page}"
                rev_res = requests.get(reviews_api, headers=self.headers, timeout=10)
                if rev_res.status_code != 200:
                    break

                rev_data = rev_res.json()
                reviews_list = rev_data.get("data", [])
                if not reviews_list:
                    break

                for r in reviews_list:
                    if len(comments) >= review_limit:
                        break

                    images = []
                    if r.get("images"):
                        images = [img.get("full_path") for img in r.get("images") if img.get("full_path")]

                    comments.append(CrawledReview(
                        author=r.get("created_by", {}).get("full_name", "Anonymous"),
                        rating=r.get("rating", 5),
                        content=r.get("content", ""),
                        time=str(r.get("created_at", "")),
                        images=images,
                        helpful_count=r.get("thank_count", 0),
                        seller_respond=None
                    ))
                page += 1

            detailed_rating = data.get("rating_average", 0)
            if isinstance(detailed_rating, (int, float)):
                detailed_rating = {
                    "avg": detailed_rating,
                    "count": data.get("review_count", 0)
                }

            return CrawledProductDetail(
                link=product_url,
                category=data.get("categories", {}).get("name", ""),
                description=description,
                detailed_rating=detailed_rating,
                total_rating=data.get("review_count", 0),
                comments=comments
            )
        except Exception:
            return CrawledProductDetail(link=product_url)