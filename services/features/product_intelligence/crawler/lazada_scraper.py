import re
import requests
import urllib.parse
import json
from typing import List, Dict, Any, Optional
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

from services.features.product_intelligence.crawler.base_scraper import BaseScraper
from schemas.product_crawler import CrawledProductItem, CrawledProductDetail, CrawledReview


class LazadaScraper(BaseScraper):
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": "https://www.lazada.vn/",
            "X-Requested-With": "XMLHttpRequest",
        }

    def crawl_search_results(self, search_url: str, max_products: int = 10) -> List[CrawledProductItem]:
        query = None
        if "lazada.vn" in search_url:
            try:
                parsed = urllib.parse.urlparse(search_url)
                qs = urllib.parse.parse_qs(parsed.query)
                extracted_query = qs.get('q', [''])[0]
                if extracted_query:
                    query = urllib.parse.unquote(extracted_query)
                if not query and "/tag/" in parsed.path:
                    tag_path = parsed.path.split("/tag/")[-1].rstrip("/")
                    if tag_path:
                        query = urllib.parse.unquote(tag_path).replace("-", " ")
            except Exception:
                pass

        if not query:
            query = search_url

        if not query or not query.strip():
            return []

        q = urllib.parse.quote(query)
        api_url = f"https://www.lazada.vn/catalog/?_keyori=ss&ajax=true&from=input&q={q}"

        driver = None
        data: Dict[str, Any] = {}

        try:
            from selenium import webdriver
            selenium_available = True
        except Exception:
            selenium_available = False

        try:
            if selenium_available:
                try:
                    options = Options()
                    options.add_argument("--headless=new")
                    options.add_argument("--disable-blink-features=AutomationControlled")
                    options.add_argument("user-agent=Mozilla/5.0")
                    options.add_argument("--no-sandbox")
                    options.add_argument("--disable-dev-shm-usage")
                    driver = webdriver.Chrome(options=options)

                    driver.get(f"https://www.lazada.vn/catalog/?q={q}")
                    time.sleep(5)

                    html_products = self._parse_html_products(driver.page_source, max_products)
                    if html_products:
                        driver.quit()
                        return html_products

                    driver.get(api_url)
                    time.sleep(3)

                    content = None
                    pre = driver.find_elements(By.TAG_NAME, "pre")
                    if pre:
                        content = pre[0].text
                    else:
                        content = driver.find_element(By.TAG_NAME, "body").text

                    try:
                        data = json.loads(content)
                    except Exception:
                        html_products = self._parse_html_products(driver.page_source, max_products)
                        if html_products:
                            driver.quit()
                            return html_products
                        data = {}
                except Exception:
                    if driver:
                        driver.quit()
                    driver = None

            if not data:
                try:
                    headers = self.headers.copy()
                    headers.pop("X-Requested-With", None)
                    res = requests.get(api_url, headers=headers, timeout=15)
                    try:
                        data = res.json()
                    except Exception:
                        html_products = self._parse_html_products(res.text, max_products)
                        if html_products:
                            return html_products
                        page_res = requests.get(f"https://www.lazada.vn/catalog/?q={q}", headers=headers, timeout=15)
                        html_products = self._parse_html_products(page_res.text, max_products)
                        if html_products:
                            return html_products
                        return []
                except Exception:
                    return []

            products = []
            if data.get("mods", {}).get("listItems"):
                products = data["mods"]["listItems"]
            elif data.get("listItems"):
                products = data["listItems"]
            elif data.get("items"):
                products = data["items"]
            elif isinstance(data.get("data"), list):
                products = data.get("data")

            results: List[CrawledProductItem] = []
            for p in products[:max_products]:
                link = p.get("productUrl") or p.get("itemUrl") or p.get("productUrlAlias")
                if link:
                    if link.startswith("//"):
                        link = "https:" + link
                    elif link.startswith("/"):
                        link = "https://www.lazada.vn" + link
                    elif not link.startswith("http"):
                        link = "https:" + link

                results.append(CrawledProductItem(
                    name=p.get("name"),
                    price=p.get("price"),
                    sold=p.get("sellVolume") or p.get("review") or p.get("reviewCount"),
                    rating=float(p.get("ratingScore")) if p.get("ratingScore") else None,
                    img=p.get("thumb"),
                    link=link,
                    platform="lazada"
                ))

            return results

        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

    def _parse_html_products(self, html_content: str, max_products: int = 10) -> List[CrawledProductItem]:
        try:
            from bs4 import BeautifulSoup
        except Exception:
            return []

        soup = BeautifulSoup(html_content, 'html.parser')
        products = []
        items = soup.find_all('div', {'data-qa-locator': 'product-item'})

        for item in items[:max_products]:
            link = None
            a = item.find('a', href=True)
            if a:
                link = a['href']
                if link.startswith("//"):
                    link = "https:" + link
                elif link.startswith("/"):
                    link = "https://www.lazada.vn" + link

            name = a.get('title') if a else None
            price_elem = item.find('span', class_=lambda x: x and 'ooOxS' in x)
            price = price_elem.get_text(strip=True).replace('₫', '') if price_elem else None
            img_elem = item.find('img', src=True)
            img = img_elem['src'] if img_elem else None

            if name and link:
                products.append(CrawledProductItem(
                    name=name,
                    price=price,
                    sold=None,
                    rating=None,
                    img=img,
                    link=link,
                    platform="lazada"
                ))
        return products

    def _extract_item_id(self, url: str) -> Optional[str]:
        patterns = [
            r"-i(\d+)\.html",
            r"-i(\d+)-s",
            r"itemId=(\d+)",
            r"pdp-i(\d+)\.html",
        ]
        for p in patterns:
            m = re.search(p, url)
            if m:
                return m.group(1)
        return None

    def crawl_product_details(self, product_url: str, review_limit: int = 30) -> CrawledProductDetail:
        item_id = self._extract_item_id(product_url)
        all_reviews: List[CrawledReview] = []
        driver = None

        try:
            from selenium import webdriver
            selenium_available = True
        except Exception:
            selenium_available = False

        try:
            if selenium_available:
                options = Options()
                options.add_argument("--headless=new")
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_argument("user-agent=Mozilla/5.0")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                driver = webdriver.Chrome(options=options)
                driver.get(product_url)
                time.sleep(5)

                if not item_id:
                    item_id = self._extract_item_id(driver.current_url)

            if not item_id:
                return CrawledProductDetail(link=product_url)

            if driver:
                from bs4 import BeautifulSoup
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(4)
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                review_items = soup.find_all('div', class_=lambda x: x and 'item' in x)

                for item in review_items:
                    if len(all_reviews) >= review_limit:
                        break
                    content = item.get_text(strip=True)
                    all_reviews.append(CrawledReview(
                        author="Anonymous",
                        rating=5,
                        content=content,
                        time="",
                        images=[],
                        seller_respond=None,
                        helpful_count=0
                    ))
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

        return CrawledProductDetail(
            link=product_url,
            category="Unknown",
            description="",
            detailed_rating={},
            total_rating=len(all_reviews),
            comments=all_reviews
        )
