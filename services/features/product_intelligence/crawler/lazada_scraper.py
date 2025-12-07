import re
import requests
import urllib.parse
import json
import logging
from typing import List, Dict, Any, Optional
import selenium
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(ch)

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
        """
        Crawl search results from Lazada.
        Uses Selenium if available to pass WAF and fetch search API; otherwise falls back to requests.
        """
        # Extract query from URL if it's a full URL, otherwise treat as query
        query = None
        if "lazada.vn" in search_url:
            try:
                parsed = urllib.parse.urlparse(search_url)
                
                # Method 1: Extract from query parameter 'q' (priority)
                qs = urllib.parse.parse_qs(parsed.query)
                extracted_query = qs.get('q', [''])[0]
                if extracted_query:
                    # Decode URL encoding
                    query = urllib.parse.unquote(extracted_query)
                    logger.info(f"Extracted query from 'q' parameter: {query}")
                
                # Method 2: Extract from tag path if no query param (e.g., /tag/cà-phê-rang-xay/)
                if not query and "/tag/" in parsed.path:
                    tag_path = parsed.path.split("/tag/")[-1].rstrip("/")
                    if tag_path:
                        # Decode URL encoding and replace hyphens with spaces
                        query = urllib.parse.unquote(tag_path).replace("-", " ")
                        logger.info(f"Extracted query from tag path: {query}")
                
            except Exception as e:
                logger.warning(f"Failed to extract query from URL: {e}")
        
        # If still no query, treat the whole input as query
        if not query:
            query = search_url
            logger.info(f"Using full input as query: {query}")

        if not query or not query.strip():
            logger.warning("Could not extract query from Lazada URL")
            return []

        # Construct the AJAX API URL that returns JSON
        q = urllib.parse.quote(query)
        api_url = f"https://www.lazada.vn/catalog/?_keyori=ss&ajax=true&from=input&q={q}"
        logger.info(f"🔍 Crawling Lazada API: {api_url}")
        logger.info(f"📝 Query: {query}")

        driver = None
        data: Dict[str, Any] = {}

        # Try to import selenium and start driver (best-effort)
        selenium_available = False
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            import time
            selenium_available = True
        except Exception:
            selenium_available = False

        try:
            # Option A: Use Selenium for API call (Best success rate - bypasses WAF)
            if selenium_available:
                try:
                    options = Options()
                    # NOTE: on Windows/desktop avoid headless for best success; caller can adjust
                    options.add_argument("--headless=new")
                    options.add_argument("--disable-blink-features=AutomationControlled")
                    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
                    options.add_argument("--no-sandbox")
                    options.add_argument("--disable-dev-shm-usage")
                    logger.info("Starting Selenium driver for search...")
                    driver = webdriver.Chrome(options=options)

                    # 1. Visit search page first to set cookies/pass challenge
                    search_page_url = f"https://www.lazada.vn/catalog/?q={q}"
                    logger.info(f"Visiting search page to pass WAF: {search_page_url}")
                    driver.get(search_page_url)
                    time.sleep(5)  # Wait for challenge/redirect
                    
                    # Check if we can parse products directly from search page HTML
                    try:
                        page_source = driver.page_source
                        html_products = self._parse_html_products(page_source, max_products)
                        if html_products:
                            logger.info(f"✅ Found {len(html_products)} products directly from search page HTML")
                            driver.quit()
                            return html_products
                    except Exception as html_error:
                        logger.debug(f"Could not parse HTML from search page: {html_error}")

                    # 2. Now fetch the API URL with the same driver (cookies are set)
                    logger.info(f"Fetching API with Selenium: {api_url}")
                    driver.get(api_url)
                    time.sleep(3)  # Wait for content to load
                    
                    # Try to get JSON from body or pre tag
                    content = None
                    try:
                        pre = driver.find_elements(By.TAG_NAME, "pre")
                        if pre:
                            content = pre[0].text
                            logger.info("Found JSON in <pre> tag")
                    except Exception:
                        pass
                    
                    if not content:
                        try:
                            content = driver.find_element(By.TAG_NAME, "body").text
                            logger.info("Found content in body")
                        except Exception:
                            pass
                    
                    # Try to parse as JSON
                    if content:
                        try:
                            data = json.loads(content)
                            logger.info("✅ Successfully parsed JSON from Selenium response")
                        except json.JSONDecodeError:
                            # If not JSON, might be HTML - try to parse HTML
                            logger.warning("Response is not JSON, trying to parse HTML from page source...")
                            try:
                                page_source = driver.page_source
                                html_products = self._parse_html_products(page_source, max_products)
                                if html_products:
                                    logger.info(f"✅ Found {len(html_products)} products from HTML parsing")
                                    try:
                                        driver.quit()
                                    except:
                                        pass
                                    return html_products
                                else:
                                    logger.warning("Could not parse products from HTML")
                            except Exception as html_error:
                                logger.error(f"HTML parsing failed: {html_error}")
                            # Continue to try requests fallback
                            data = {}
                    else:
                        logger.warning("No content found in Selenium response")
                        # Try to parse HTML from page source as fallback
                        try:
                            page_source = driver.page_source
                            html_products = self._parse_html_products(page_source, max_products)
                            if html_products:
                                logger.info(f"✅ Found {len(html_products)} products from HTML parsing (no content fallback)")
                                try:
                                    driver.quit()
                                except:
                                    pass
                                return html_products
                        except Exception as html_error:
                            logger.error(f"HTML parsing fallback failed: {html_error}")
                        data = {}
                except Exception as parse_error:
                    logger.error(f"Selenium parse error: {parse_error}")
                    # If we already tried HTML parsing above, continue to requests fallback
                    if not data:
                        # fallback to requests attempt below
                        if driver:
                            try:
                                driver.quit()
                            except:
                                pass
                        driver = None
                except Exception as e:
                    logger.error(f"Selenium search fetch failed: {e}", exc_info=True)
                    # fallback to requests attempt below
                    if driver:
                        try:
                            driver.quit()
                        except:
                            pass
                    driver = None

            # Option B: Use requests with custom cookies (fallback)
            if not data:
                try:
                    headers = self.headers.copy()
                    headers["Referer"] = "https://www.lazada.vn/"
                    headers.pop("X-Requested-With", None)

                    res = requests.get(api_url, headers=headers, timeout=15)
                    try:
                        data = res.json()
                        logger.info(f"✅ Successfully fetched search results with requests (status: {res.status_code})")
                    except json.JSONDecodeError:
                        # Try to parse as HTML if not JSON
                        logger.warning(f"API response is not JSON (status: {res.status_code}), trying to parse HTML...")
                        html_products = self._parse_html_products(res.text, max_products)
                        if html_products:
                            logger.info(f"✅ Found {len(html_products)} products from API HTML parsing")
                            return html_products
                        
                        # If API HTML parsing failed, try loading search page directly
                        logger.info("🔄 Trying to load search page directly...")
                        search_page_url = f"https://www.lazada.vn/catalog/?q={q}"
                        try:
                            page_res = requests.get(search_page_url, headers=headers, timeout=15)
                            logger.info(f"Search page response status: {page_res.status_code}")
                            html_products = self._parse_html_products(page_res.text, max_products)
                            if html_products:
                                logger.info(f"✅ Found {len(html_products)} products from search page HTML")
                                return html_products
                        except Exception as page_error:
                            logger.error(f"Failed to load search page: {page_error}")
                        
                        logger.error(f"❌ Không parse được JSON hoặc HTML. API Status: {res.status_code}")
                        logger.error(f"Response preview: {res.text[:500] if res.text else 'Empty response'}")
                        return []
                except requests.exceptions.RequestException as e:
                    logger.error(f"Requests search fetch failed: {e}")
                    # Last resort: try to load search page directly even if API failed
                    try:
                        logger.info("🔄 Last resort: Loading search page directly...")
                        search_page_url = f"https://www.lazada.vn/catalog/?q={q}"
                        headers = self.headers.copy()
                        headers["Referer"] = "https://www.lazada.vn/"
                        page_res = requests.get(search_page_url, headers=headers, timeout=15)
                        html_products = self._parse_html_products(page_res.text, max_products)
                        if html_products:
                            logger.info(f"✅ Found {len(html_products)} products from direct search page")
                            return html_products
                    except Exception as last_error:
                        logger.error(f"Last resort also failed: {last_error}")
                    return []
                except Exception as e:
                    logger.error(f"Unexpected error in requests fallback: {e}", exc_info=True)
                    return []

            # Process Data - Support multiple response structures
            products = []
            
            # Try different response structures
            if data.get("mods", {}).get("listItems"):
                products = data.get("mods", {}).get("listItems", [])
                logger.info(f"✅ Found {len(products)} products in mods.listItems")
            elif data.get("listItems"):
                products = data.get("listItems", [])
                logger.info(f"✅ Found {len(products)} products in listItems")
            elif data.get("items"):
                products = data.get("items", [])
                logger.info(f"✅ Found {len(products)} products in items")
            elif isinstance(data.get("data"), list):
                products = data.get("data", [])
                logger.info(f"✅ Found {len(products)} products in data array")
            else:
                logger.warning(f"⚠️ No products found in response. Response keys: {list(data.keys())}")
                logger.debug(f"Response structure: {json.dumps(data, indent=2)[:500]}")
                
                # Fallback 1: Try to load search page directly with requests and parse HTML
                if not products:
                    logger.info("🔄 Fallback: Loading search page directly with requests to parse HTML...")
                    try:
                        search_page_url = f"https://www.lazada.vn/catalog/?q={q}"
                        headers = self.headers.copy()
                        headers["Referer"] = "https://www.lazada.vn/"
                        page_res = requests.get(search_page_url, headers=headers, timeout=15)
                        logger.info(f"Search page response status: {page_res.status_code}")
                        html_products = self._parse_html_products(page_res.text, max_products)
                        if html_products:
                            logger.info(f"✅ Found {len(html_products)} products from search page HTML fallback")
                            return html_products
                    except Exception as fallback_error:
                        logger.warning(f"Search page HTML fallback failed: {fallback_error}")
                
                # Fallback 2: If original URL is a tag URL and we got no results, try loading the tag page directly with Selenium
                if not products and "/tag/" in search_url and selenium_available and not driver:
                    logger.info("🔄 Attempting fallback: Loading tag URL directly with Selenium...")
                    try:
                        options = Options()
                        options.add_argument("--headless=new")
                        options.add_argument("--disable-blink-features=AutomationControlled")
                        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
                        options.add_argument("--no-sandbox")
                        options.add_argument("--disable-dev-shm-usage")
                        driver = webdriver.Chrome(options=options)
                        
                        # Add ajax=true to tag URL to get JSON response
                        tag_api_url = search_url
                        if "ajax=true" not in tag_api_url:
                            separator = "&" if "?" in tag_api_url else "?"
                            tag_api_url = f"{search_url}{separator}ajax=true"
                        
                        logger.info(f"Loading tag URL: {tag_api_url}")
                        driver.get(tag_api_url)
                        time.sleep(5)
                        
                        content = driver.find_element(By.TAG_NAME, "body").text
                        try:
                            pre = driver.find_elements(By.TAG_NAME, "pre")
                            if pre:
                                content = pre[0].text
                        except Exception:
                            pass
                        
                        fallback_data = json.loads(content)
                        
                        # Try to extract products from fallback response
                        if fallback_data.get("mods", {}).get("listItems"):
                            products = fallback_data.get("mods", {}).get("listItems", [])
                            logger.info(f"✅ Found {len(products)} products from tag URL fallback")
                        elif fallback_data.get("listItems"):
                            products = fallback_data.get("listItems", [])
                            logger.info(f"✅ Found {len(products)} products from tag URL fallback")
                    except Exception as e:
                        logger.error(f"Tag URL fallback failed: {e}")
                    finally:
                        if driver:
                            try:
                                driver.quit()
                            except:
                                pass
            
            results: List[CrawledProductItem] = []

            for p in products[:max_products]:
                # Lazada link nằm trong 3 key có thể xuất hiện:
                link = None
                if p.get("productUrl"):
                    link = p["productUrl"]
                elif p.get("itemUrl"):
                    link = p["itemUrl"]
                elif p.get("productUrlAlias"):
                    link = p["productUrlAlias"]

                # Fix relative links (Lazada usually returns //path or /path)
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

        except Exception as e:
            logger.error(f"Lazada search error: {e}")
            return []
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

    def _parse_html_products(self, html_content: str, max_products: int = 10) -> List[CrawledProductItem]:
        """
        Parse products from HTML content when API returns HTML instead of JSON.
        Looks for product items with data-qa-locator="product-item"
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.warning("BeautifulSoup not available, cannot parse HTML")
            return []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            products = []
            
            # Find all product items using data-qa-locator="product-item"
            product_items = soup.find_all('div', {'data-qa-locator': 'product-item'})
            logger.info(f"Found {len(product_items)} product items in HTML")
            
            if not product_items:
                # Try alternative selector - sometimes products are in different structure
                product_items = soup.find_all('div', class_=lambda x: x and 'Bm3ON' in str(x) if x else False)
                logger.info(f"Found {len(product_items)} product items using alternative selector")
            
            for item in product_items[:max_products]:
                try:
                    # Extract product link - look for href containing "pdp-i" or "products"
                    link = None
                    # Try multiple selectors for link
                    link_elem = item.find('a', href=lambda x: x and ('pdp-i' in x or '/products/' in x) if x else False)
                    if not link_elem:
                        link_elem = item.find('a', href=True)
                    
                    if link_elem:
                        link = link_elem.get('href', '').strip()
                        # Fix relative links
                        if link.startswith("//"):
                            link = "https:" + link
                        elif link.startswith("/"):
                            link = "https://www.lazada.vn" + link
                        elif not link.startswith("http"):
                            if link.startswith("www."):
                                link = "https://" + link
                            else:
                                link = "https://www.lazada.vn" + link
                    
                    # Extract product name - priority: title attribute, then text in RfADt div
                    name = None
                    # Try title attribute first
                    title_elem = item.find('a', title=True)
                    if title_elem:
                        name = title_elem.get('title', '').strip()
                    
                    # If no title, try to find text in product title area (class RfADt)
                    if not name:
                        title_div = item.find('div', class_=lambda x: x and 'RfADt' in str(x) if x else False)
                        if title_div:
                            name_link = title_div.find('a')
                            if name_link:
                                name = name_link.get_text(strip=True)
                            if not name:
                                name = title_div.get_text(strip=True)
                    
                    # Extract price - look for span with class containing "ooOxS"
                    price = None
                    price_elem = item.find('span', class_=lambda x: x and 'ooOxS' in str(x) if x else False)
                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        # Remove currency symbols and clean - keep as string for now
                        price = price_text.replace('₫', '').strip()
                    
                    # Extract image - look for main product image
                    img = None
                    # Try to find main image (usually first img with product type)
                    img_elem = item.find('img', {'type': 'product'})
                    if not img_elem:
                        img_elem = item.find('img', src=True)
                    
                    if img_elem:
                        img = img_elem.get('src', '').strip()
                        if img.startswith("//"):
                            img = "https:" + img
                        elif not img.startswith("http"):
                            img = "https:" + img if img.startswith(":") else "https://" + img
                    
                    # Extract rating - count filled stars in mdmmT div
                    rating = None
                    rating_elem = item.find('div', class_=lambda x: x and 'mdmmT' in str(x) if x else False)
                    if rating_elem:
                        # Count filled stars (class containing "Dy1nx")
                        stars = rating_elem.find_all('i', class_=lambda x: x and 'Dy1nx' in str(x) if x else False)
                        if stars:
                            rating = len(stars)
                    
                    # Extract sold count - look for span containing "Đã bán"
                    sold = None
                    # Find span with text containing "Đã bán"
                    for span in item.find_all('span'):
                        text = span.get_text()
                        if 'Đã bán' in text:
                            # Extract the number part (e.g., "1.3K" from "1.3K Đã bán")
                            parts = text.split()
                            if parts:
                                sold = parts[0]  # Keep original format like "1.3K"
                            break
                    
                    # Only add product if we have at least name and link
                    if name and link:
                        products.append(CrawledProductItem(
                            name=name,
                            price=price,
                            sold=sold,
                            rating=float(rating) if rating else None,
                            img=img,
                            link=link,
                            platform="lazada"
                        ))
                        logger.debug(f"✅ Parsed product: {name[:50]}... | {link[:50]}...")
                    else:
                        logger.warning(f"⚠️ Skipped product - missing name or link. name={bool(name)}, link={bool(link)}")
                    
                except Exception as e:
                    logger.warning(f"Error parsing product item: {e}", exc_info=True)
                    continue
            
            logger.info(f"✅ Successfully parsed {len(products)} products from HTML")
            return products
            
        except Exception as e:
            logger.error(f"Error parsing HTML: {e}", exc_info=True)
            return []

    def _extract_item_id(self, url: str) -> Optional[str]:
        patterns = [
            r"-i(\d+)\.html",   # /xxx-i123.html
            r"-i(\d+)-s",       # /xxx-i123-s333.html
            r"itemId=(\d+)",    # query param
            r"pdp-i(\d+)\.html", # sometimes pdp-i123.html
        ]
        for p in patterns:
            m = re.search(p, url)
            if m:
                return m.group(1)
        return None

    def crawl_product_details(self, product_url: str, review_limit: int = 30) -> CrawledProductDetail:
        """
        Crawl details for Lazada.
        Uses Selenium if available to pass WAF and fetch review API; otherwise falls back to requests.
        """
        item_id = self._extract_item_id(product_url)
        all_reviews: List[CrawledReview] = []
        driver = None

        # Try to import selenium and start driver (best-effort)
        selenium_available = False
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            import time
            selenium_available = True
        except Exception:
            selenium_available = False

        try:
            if selenium_available:
                try:
                    options = Options()
                    # NOTE: on Windows/desktop avoid headless for best success; caller can adjust
                    options.add_argument("--headless=new")
                    options.add_argument("--disable-blink-features=AutomationControlled")
                    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
                    options.add_argument("--no-sandbox")
                    options.add_argument("--disable-dev-shm-usage")
                    logger.info("Starting Selenium driver...")
                    driver = webdriver.Chrome(options=options)

                    # 1. Visit Product Page first to set cookies/pass challenge
                    logger.info(f"Visiting product page to pass WAF: {product_url}")
                    driver.get(product_url)
                    time.sleep(5)  # Wait for challenge/redirect

                    # 2. Re-attempt ID extraction from FINAL URL (in case of redirect)
                    current_url = driver.current_url
                    if not item_id:
                        logger.info(f"Trying to extract item_id from redirected URL: {current_url}")
                        item_id = self._extract_item_id(current_url)

                    # 3. If still no ID, try to find in Page Source (advanced)
                    if not item_id:
                        try:
                            page_source = driver.page_source
                            match = re.search(r'"itemId"\s*:\s*"?(?P<id>\d+)"?', page_source)
                            if match:
                                item_id = match.group("id")
                                logger.info(f"Found item_id from page source: {item_id}")
                        except Exception:
                            pass

                except Exception as e:
                    logger.error(f"Failed to start Selenium or load page: {e}")
                    if driver:
                        try:
                            driver.quit()
                        except:
                            pass
                    driver = None

            if not item_id:
                logger.error(f"Could not extract item_id from URL: {product_url}")
                return CrawledProductDetail(link=product_url)

            # Calculate pages
            page_size = 20
            max_pages = max(1, (review_limit // page_size) + (1 if review_limit % page_size > 0 else 0))

            for page in range(1, max_pages + 1):
                if len(all_reviews) >= review_limit:
                    break

                api_url = (
                    f"https://my.lazada.vn/pdp/review/getReviewList?"
                    f"itemId={item_id}&pageSize={page_size}&pageNo={page}"
                )

                data: Dict[str, Any] = {}

                # Option A: Use Selenium for API call (Best success rate)
                if driver:
                    try:
                        driver.get(api_url)
                        # Extract text from body
                        content = driver.find_element(By.TAG_NAME, "body").text
                        # Sometimes response wrapped in <pre>
                        try:
                            pre = driver.find_elements(By.TAG_NAME, "pre")
                            if pre:
                                content = pre[0].text
                        except Exception:
                            pass

                        data = json.loads(content)
                    except Exception as e:
                        logger.error(f"Selenium API fetch failed for page {page}: {e}")
                        # fallback to requests attempt below

                # Option B: Use requests with custom cookies
                if not data:
                    try:
                        headers = self.headers.copy()
                        headers["Referer"] = product_url
                        headers.pop("X-Requested-With", None)

                        res = requests.get(api_url, headers=headers, timeout=10)
                        try:
                            data = res.json()
                        except Exception:
                            logger.error(f"Requests returned non-json for page {page}: {res.text[:200]}")
                            data = {}
                    except Exception as e:
                        logger.error(f"Requests API fetch failed for page {page}: {e}")
                        data = {}

                # Process Data
                model = data.get("model", {})
                items = model.get("items", [])
                if not items:
                    # no more reviews or failed
                    break

                for r in items:
                    if len(all_reviews) >= review_limit:
                        break

                    review = CrawledReview(
                        author=r.get("buyerName", "Anonymous"),
                        rating=int(r.get("rating", 5) or 5),
                        content=r.get("reviewContent", "") or "",
                        time=r.get("reviewTime", "") or "",
                        images=[img.get("url") for img in r.get("images", []) if img.get("url")] if r.get("images") else [],
                        seller_respond=None,
                        helpful_count=int(r.get("likeCount", 0) or 0)
                    )

                    # seller replies handling
                    replies = r.get("replies") or []
                    if replies:
                        for reply in replies:
                            if reply.get("reviewContent"):
                                review.seller_respond = reply.get("reviewContent")
                                break

                    all_reviews.append(review)

        except Exception as e:
            logger.error(f"Crawl failed: {e}")
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

        # Build and return product detail (we populate total_rating from crawled count)
        detail = CrawledProductDetail(
            link=product_url,
            category="Unknown",
            description="",
            detailed_rating={},
            total_rating=len(all_reviews),
            comments=all_reviews
        )

        return detail
