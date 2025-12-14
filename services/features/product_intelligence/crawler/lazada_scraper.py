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

                # Extract review count separately if available
                review_count = p.get("reviewCount") or p.get("review")
                if review_count:
                    try:
                        review_count = int(review_count)
                    except (ValueError, TypeError):
                        review_count = None
                sold_volume = p.get("sellVolume")
                
                results.append(CrawledProductItem(
                    name=p.get("name"),
                    price=p.get("price"),
                    sold=sold_volume,  # Use sellVolume for sold count
                    rating=float(p.get("ratingScore")) if p.get("ratingScore") else None,
                    img=p.get("thumb"),
                    link=link,
                    platform="lazada",
                    review_count=review_count  # Store review_count separately
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
        # Try multiple selectors for product items
        items = soup.find_all('div', {'data-qa-locator': 'product-item'})
        if not items:
            # Fallback: find by class containing product-related classes
            items = soup.find_all('div', class_=lambda x: x and ('qmXQo' in str(x) or 'product' in str(x).lower()))

        for item in items[:max_products]:
            link = None
            a = item.find('a', href=True)
            if a:
                link = a.get('href')
                if link:
                    if link.startswith("//"):
                        link = "https:" + link
                    elif link.startswith("/"):
                        link = "https://www.lazada.vn" + link

            name = a.get('title') if a else None
            if not name:
                # Try to get name from alt attribute of img
                img_elem = item.find('img', alt=True)
                if img_elem:
                    name = img_elem.get('alt')
            
            price_elem = item.find('span', class_=lambda x: x and 'ooOxS' in x)
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                # Remove currency symbols and spaces
                price_text = price_text.replace('₫', '').replace('đ', '').replace('VND', '').replace('vnd', '').strip()
                # Remove dots used as thousand separators (e.g., "129.690" -> "129690")
                # But keep decimal point if it's a decimal number (e.g., "129.5" -> "129.5")
                # Lazada prices are usually integers, so dots are likely thousand separators
                if '.' in price_text:
                    parts = price_text.split('.')
                    # If last part has 3 digits, it's likely thousand separator
                    if len(parts) > 1 and len(parts[-1]) == 3:
                        price_text = ''.join(parts)  # Remove dots (thousand separator)
                    # Otherwise, treat as decimal
                # Remove commas (thousand separator)
                price_text = price_text.replace(',', '').strip()
                price = price_text
            else:
                price = None
            
            img_elem = item.find('img', src=True)
            img = img_elem['src'] if img_elem else None
            
            # Extract review count from <span class="qzqFw">(3)</span>
            review_count = None
            review_elem = item.find('span', class_=lambda x: x and 'qzqFw' in x)
            if review_elem:
                review_text = review_elem.get_text(strip=True)
                # Extract number from text like "(3)" or "3"
                import re
                match = re.search(r'\(?(\d+)\)?', review_text)
                if match:
                    try:
                        review_count = int(match.group(1))
                    except (ValueError, TypeError):
                        pass
            
            # Extract sold count from <span>6 Đã bán</span>
            sold = None
            sold_elem = item.find('span', string=lambda x: x and 'Đã bán' in str(x))
            if sold_elem:
                sold_text = sold_elem.get_text(strip=True)
                # Extract number from text like "6 Đã bán"
                match = re.search(r'(\d+)', sold_text)
                if match:
                    try:
                        sold = int(match.group(1))
                    except (ValueError, TypeError):
                        pass
            
            # Extract rating from stars (if available)
            rating = None
            rating_container = item.find('div', class_=lambda x: x and ('mdmmT' in str(x) or 'rating' in str(x).lower()))
            if rating_container:
                # Count filled stars
                stars = rating_container.find_all('i', class_=lambda x: x and 'Dy1nx' in str(x))
                if stars:
                    rating = len(stars)  # Simple: count stars, could be improved

            if name and link:
                products.append(CrawledProductItem(
                    name=name,
                    price=price,
                    sold=sold,
                    rating=float(rating) if rating else None,
                    img=img,
                    link=link,
                    platform="lazada",
                    review_count=review_count
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
