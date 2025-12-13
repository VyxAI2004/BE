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
                extracted_query = qs.get("q", [""])[0]
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

                    try:
                        html_products = self._parse_html_products(driver.page_source, max_products)
                        if html_products:
                            driver.quit()
                            return html_products
                    except Exception:
                        pass

                    driver.get(api_url)
                    time.sleep(3)

                    content = None
                    try:
                        pre = driver.find_elements(By.TAG_NAME, "pre")
                        if pre:
                            content = pre[0].text
                    except Exception:
                        pass

                    if not content:
                        try:
                            content = driver.find_element(By.TAG_NAME, "body").text
                        except Exception:
                            pass

                    if content:
                        try:
                            data = json.loads(content)
                        except json.JSONDecodeError:
                            html_products = self._parse_html_products(driver.page_source, max_products)
                            if html_products:
                                driver.quit()
                                return html_products
                            data = {}
                except Exception:
                    if driver:
                        try:
                            driver.quit()
                        except Exception:
                            pass
                    driver = None

            if not data:
                try:
                    headers = self.headers.copy()
                    headers.pop("X-Requested-With", None)

                    res = requests.get(api_url, headers=headers, timeout=15)
                    try:
                        data = res.json()
                    except json.JSONDecodeError:
                        html_products = self._parse_html_products(res.text, max_products)
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
                products = data["data"]

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
        except ImportError:
            return []

        soup = BeautifulSoup(html_content, "html.parser")
        products = []

        product_items = soup.find_all("div", {"data-qa-locator": "product-item"})
        if not product_items:
            product_items = soup.find_all("div", class_=lambda x: x and "Bm3ON" in x)

        for item in product_items[:max_products]:
            try:
                link_elem = item.find("a", href=True)
                link = link_elem.get("href") if link_elem else None

                if link:
                    if link.startswith("//"):
                        link = "https:" + link
                    elif link.startswith("/"):
                        link = "https://www.lazada.vn" + link

                title_elem = item.find("a", title=True)
                name = title_elem.get("title").strip() if title_elem else None

                price_elem = item.find("span", class_=lambda x: x and "ooOxS" in x)
                price = price_elem.get_text(strip=True) if price_elem else None

                img_elem = item.find("img", src=True)
                img = img_elem.get("src") if img_elem else None
                if img and img.startswith("//"):
                    img = "https:" + img

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
            except Exception:
                continue

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
