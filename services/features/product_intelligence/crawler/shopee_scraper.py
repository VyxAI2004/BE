"""
Shopee Scraper - Hybrid Approach
Sử dụng Selenium + Saved Cookies để crawl

Flow:
1. Chạy scripts/shopee_login.py để login và save cookies (1 lần)
2. Scraper load cookies vào Selenium (skip login)
3. Parse HTML từ rendered page
"""

import re
import time
import urllib.parse
import json
import logging
import requests
from typing import List, Optional
from pathlib import Path

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from services.features.product_intelligence.crawler.base_scraper import BaseScraper
from services.features.product_intelligence.crawler.cookie_manager import CookieManager
from schemas.product_crawler import CrawledProductItem, CrawledProductDetail, CrawledReview

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ShopeeScraper(BaseScraper):
    """
    Shopee Scraper sử dụng Selenium + Saved Cookies
    Yêu cầu: Chạy scripts/shopee_login.py trước để lấy cookies
    """
    
    def __init__(self, account_name: str = "default"):
        self.base_url = "https://shopee.vn"
        self.cookie_manager = CookieManager(account_name)
        self.account_name = account_name
        logger.info(f"ShopeeScraper initialized with account: {account_name}")
    
    def _auto_login_internal(self, timeout_seconds: int = 120) -> bool:
        """
        Auto login nội bộ - mở browser, chờ user login, lưu cookies
        
        Returns:
            True nếu login thành công, False nếu thất bại
        """
        driver = None
        
        try:
            print(f"\n{'='*60}")
            print(f"[SHOPEE AUTO LOGIN] 🔐 Starting auto login")
            print(f"[SHOPEE AUTO LOGIN] ⏰ Timeout: {timeout_seconds}s")
            print(f"{'='*60}")
            
            options = uc.ChromeOptions()
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--lang=vi-VN")
            options.add_argument("--start-maximized")
            
            driver = uc.Chrome(options=options, version_main=None)
            print("[SHOPEE AUTO LOGIN] ✅ Browser opened")
            
            # Navigate to login page
            print("[SHOPEE AUTO LOGIN] 🌐 Loading login page...")
            driver.get("https://shopee.vn/buyer/login")
            time.sleep(3)
            
            print("[SHOPEE AUTO LOGIN] ⏳ Waiting for you to login...")
            print("[SHOPEE AUTO LOGIN] 💡 Login bằng OTP, SMS hoặc Password")
            print("-" * 60)
            
            # Poll for login completion
            start_time = time.time()
            check_interval = 2
            
            while True:
                elapsed = time.time() - start_time
                
                if elapsed > timeout_seconds:
                    print(f"\n[SHOPEE AUTO LOGIN] ⏰ Timeout sau {timeout_seconds}s")
                    return False
                
                try:
                    current_url = driver.current_url
                    
                    # Log progress mỗi 10 giây
                    if int(elapsed) % 10 == 0 and int(elapsed) > 0:
                        remaining = timeout_seconds - int(elapsed)
                        print(f"[SHOPEE AUTO LOGIN] ⏳ Đang chờ... ({remaining}s còn lại)")
                    
                    # Check if login successful
                    if "/login" not in current_url and "/buyer/login" not in current_url:
                        print(f"\n[SHOPEE AUTO LOGIN] ✅ Login detected!")
                        
                        time.sleep(3)
                        
                        # Check for traffic verification
                        current_url = driver.current_url
                        if "/verify/traffic" in current_url:
                            print("[SHOPEE AUTO LOGIN] ⚠️  Traffic verification detected")
                            time.sleep(10)
                            if "/verify/traffic" in driver.current_url:
                                return False
                        
                        # Get and save cookies
                        cookies = driver.get_cookies()
                        if not cookies:
                            return False
                        
                        self.cookie_manager.save_cookies(cookies)
                        print(f"[SHOPEE AUTO LOGIN] 💾 Saved {len(cookies)} cookies")
                        print("[SHOPEE AUTO LOGIN] ✅ SUCCESS!")
                        print("=" * 60)
                        
                        return True
                    
                except Exception as e:
                    logger.debug(f"Check error: {e}")
                
                time.sleep(check_interval)
            
        except Exception as e:
            print(f"[SHOPEE AUTO LOGIN] ❌ Error: {str(e)}")
            return False
        finally:
            if driver:
                try:
                    driver.quit()
                    print("[SHOPEE AUTO LOGIN] 🔒 Browser closed")
                except:
                    pass

    def crawl_search_results(self, search_url: str, max_products: int = 10) -> List[CrawledProductItem]:
        """
        Crawl search results sử dụng Selenium + Saved Cookies
        """
        print(f"\n{'='*60}")
        print(f"[SHOPEE] 🔍 Crawling search results")
        print(f"[SHOPEE] URL: {search_url}")
        print(f"{'='*60}")
        
        # Extract query từ URL
        query = search_url
        if "shopee.vn/search" in search_url:
            try:
                parsed = urllib.parse.urlparse(search_url)
                qs = urllib.parse.parse_qs(parsed.query)
                query = qs.get("keyword", [search_url])[0]
            except Exception:
                pass
        
        if not query or not query.strip():
            print("[SHOPEE] ❌ Empty query")
            return []
        
        print(f"[SHOPEE] 🔎 Query: {query}")
        
        # Load cookies
        saved_cookies = self.cookie_manager.load_cookies()
        has_cookies = saved_cookies and len(saved_cookies) > 0
        
        if has_cookies:
            print(f"[SHOPEE] 🍪 Found {len(saved_cookies)} saved cookies")
        else:
            print("[SHOPEE] ⚠️  No saved cookies found")
            print("[SHOPEE] � Auto-login sẽ được thực hiện...")
            
            # Auto login
            login_result = self._auto_login_internal()
            
            if login_result:
                saved_cookies = self.cookie_manager.load_cookies()
                has_cookies = saved_cookies and len(saved_cookies) > 0
                print(f"[SHOPEE] ✅ Auto-login thành công! {len(saved_cookies)} cookies")
            else:
                print("[SHOPEE] ❌ Auto-login thất bại!")
                return []
        
        # Build search URL
        encoded_query = urllib.parse.quote(query)
        search_page_url = f"{self.base_url}/search?keyword={encoded_query}"
        
        driver = None
        try:
            # Initialize undetected-chromedriver
            print("[SHOPEE] 🚀 Starting browser...")
            
            options = uc.ChromeOptions()
            # KHÔNG dùng headless - Shopee detect và block
            # options.add_argument("--headless=new")  # DISABLED
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--lang=vi-VN")
            options.add_argument("--start-maximized")
            
            driver = uc.Chrome(options=options, version_main=None)
            print("[SHOPEE] ✅ Browser started (NON-HEADLESS)")
            
            # Load homepage first để set cookies
            print("[SHOPEE] 🏠 Loading homepage...")
            driver.get(self.base_url)
            time.sleep(3)
            
            # Apply saved cookies
            if has_cookies:
                print("[SHOPEE] 🍪 Applying saved cookies...")
                for cookie in saved_cookies:
                    try:
                        cookie_dict = {
                            'name': cookie.get('name'),
                            'value': cookie.get('value'),
                            'domain': cookie.get('domain', '.shopee.vn'),
                            'path': cookie.get('path', '/'),
                        }
                        # Only add if name and value exist
                        if cookie_dict['name'] and cookie_dict['value']:
                            driver.add_cookie(cookie_dict)
                    except Exception as e:
                        logger.debug(f"Failed to add cookie: {e}")
                
                print(f"[SHOPEE] ✅ Applied cookies")
                
                # Refresh để apply cookies
                driver.refresh()
                time.sleep(3)
            
            # Now load search page
            print(f"[SHOPEE] 🔍 Loading search page...")
            driver.get(search_page_url)
            time.sleep(5)
            
            # Check current URL
            current_url = driver.current_url
            page_title = driver.title
            print(f"[SHOPEE] 📄 Page loaded")
            print(f"[SHOPEE]    URL: {current_url[:80]}...")
            print(f"[SHOPEE]    Title: {page_title}")
            
            # Check for login/verification redirect
            if "/login" in current_url:
                print("[SHOPEE] ⚠️  Login required - cookies expired!")
                print("[SHOPEE] 💡 Run: POST /api/v1/shopee/session/auto-login")
                self.cookie_manager.clear_cookies()
                return []
            
            # Handle captcha verification
            if "/verify/captcha" in current_url:
                print("[SHOPEE] ⚠️  Captcha verification detected!")
                print("[SHOPEE] 👆 Vui lòng giải captcha trong browser...")
                print("[SHOPEE] ⏳ Đang chờ bạn hoàn thành captcha (tối đa 120s)...")
                
                # Wait for user to solve captcha - TĂNG LÊN 120s
                captcha_timeout = 120
                start_time = time.time()
                captcha_solved = False
                
                while time.time() - start_time < captcha_timeout:
                    time.sleep(2)
                    
                    try:
                        current_url = driver.current_url
                    except Exception as e:
                        print(f"[SHOPEE] ⚠️  Browser error: {e}")
                        print("[SHOPEE] 💡 Browser có thể đã bị đóng, thử lại...")
                        return []
                    
                    remaining = int(captcha_timeout - (time.time() - start_time))
                    if remaining % 20 == 0 and remaining > 0:
                        print(f"[SHOPEE] ⏳ Còn {remaining}s để giải captcha...")
                    
                    if "/verify/captcha" not in current_url:
                        print("[SHOPEE] ✅ Captcha solved!")
                        captcha_solved = True
                        # Update cookies after captcha
                        try:
                            new_cookies = driver.get_cookies()
                            self.cookie_manager.save_cookies(new_cookies)
                            print(f"[SHOPEE] 💾 Updated cookies after captcha")
                        except:
                            pass
                        break
                
                if not captcha_solved:
                    print("[SHOPEE] ⏰ Captcha timeout sau 120s!")
                    print("[SHOPEE] 💡 Thử lại - bạn có 2 phút để giải captcha")
                    return []
                
                # Check if now on search page
                try:
                    current_url = driver.current_url
                    if "/search" not in current_url:
                        print(f"[SHOPEE] 🔄 Reloading search page...")
                        driver.get(search_page_url)
                        time.sleep(5)
                except Exception as e:
                    print(f"[SHOPEE] ⚠️  Error after captcha: {e}")
                    return []
            
            # Handle traffic verification  
            if "/verify/traffic" in current_url:
                print("[SHOPEE] ⚠️  Traffic verification detected!")
                print("[SHOPEE] 🔄 Waiting for manual verification...")
                print("[SHOPEE] 💡 Bạn có thể cần verify trong browser popup")
                
                # Chờ user verify (nếu có captcha)
                time.sleep(10)
                
                # Thử lại
                driver.get(search_page_url)
                time.sleep(5)
                
                current_url = driver.current_url
                if "/verify/traffic" in current_url:
                    print("[SHOPEE] ❌ Still blocked!")
                    print("[SHOPEE] 💡 Solutions:")
                    print("[SHOPEE]    1. Wait 5-10 minutes and try again")
                    print("[SHOPEE]    2. Use a VPN to change IP")
                    print("[SHOPEE]    3. Login again: POST /api/v1/shopee/session/auto-login")
                    return []
                else:
                    print("[SHOPEE] ✅ Traffic verification passed!")
            
            # Check for error page
            page_source = driver.page_source
            if "sự cố tải" in page_source or "thử lại" in page_source or "error" in current_url.lower():
                print("[SHOPEE] ⚠️  Shopee đang gặp sự cố hoặc rate limiting!")
                print("[SHOPEE] 🔄 Retrying in 5 seconds...")
                
                time.sleep(5)
                driver.refresh()
                time.sleep(5)
                
                # Check again
                page_source = driver.page_source
                if "sự cố tải" in page_source or "thử lại" in page_source:
                    print("[SHOPEE] ❌ Vẫn bị lỗi sau khi retry!")
                    print("[SHOPEE] 💡 Giải pháp:")
                    print("[SHOPEE]    1. Đợi 5-10 phút rồi thử lại")
                    print("[SHOPEE]    2. Dùng VPN để đổi IP")
                    print("[SHOPEE]    3. IP của bạn có thể đang bị rate limit")
                    return []
                else:
                    print("[SHOPEE] ✅ Retry thành công!")
            
            # Scroll to load products
            print("[SHOPEE] 📜 Scrolling to load products...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Update cookies
            new_cookies = driver.get_cookies()
            if len(new_cookies) > 0:
                self.cookie_manager.save_cookies(new_cookies)
                print(f"[SHOPEE] 💾 Updated {len(new_cookies)} cookies")
            
            # Parse products from HTML
            print("[SHOPEE] 🔎 Parsing products from HTML...")
            products = self._parse_search_results(driver.page_source, max_products)
            
            print(f"[SHOPEE] ✅ Found {len(products)} products")
            for i, p in enumerate(products[:3], 1):
                print(f"[SHOPEE]    {i}. {p.name[:50]}...")
            
            return products
            
        except Exception as e:
            print(f"[SHOPEE] ❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

    def _parse_search_results(self, html: str, max_products: int = 10) -> List[CrawledProductItem]:
        """Parse products từ HTML search results"""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            print("[SHOPEE] ❌ BeautifulSoup not installed")
            return []
        
        soup = BeautifulSoup(html, "html.parser")
        results = []
        
        # Shopee product selectors (may change)
        selectors = [
            # Selector 1: Product links with -i. pattern
            ("a", {"href": lambda x: x and "-i." in x}),
            # Selector 2: data-sqe attribute
            ("div", {"data-sqe": "link"}),
        ]
        
        product_links = []
        for tag, attrs in selectors:
            found = soup.find_all(tag, attrs)
            if found:
                product_links = found
                print(f"[SHOPEE] Found {len(found)} items with selector: {tag}, {attrs}")
                break
        
        if not product_links:
            print("[SHOPEE] ⚠️  No products found in HTML")
            # Debug: print first 1000 chars
            print(f"[SHOPEE] HTML preview: {html[:1000]}")
            return []
        
        seen_links = set()
        
        for elem in product_links:
            if len(results) >= max_products:
                break
            
            try:
                # Get link
                if elem.name == "a":
                    link = elem.get("href", "")
                else:
                    link_elem = elem.find("a", href=lambda x: x and "-i." in x)
                    link = link_elem.get("href", "") if link_elem else ""
                
                if not link or "-i." not in link:
                    continue
                
                # Normalize link
                if link.startswith("/"):
                    link = self.base_url + link
                elif not link.startswith("http"):
                    link = self.base_url + "/" + link
                
                # Skip duplicates
                if link in seen_links:
                    continue
                seen_links.add(link)
                
                # Get parent container for more info
                parent = elem.find_parent("div") or elem
                
                # Get name
                name = ""
                name_elem = parent.find("div", class_=lambda x: x and "line-clamp" in str(x))
                if name_elem:
                    name = name_elem.get_text(strip=True)
                if not name:
                    name = elem.get("title") or elem.get_text(strip=True)
                
                if not name or len(name) < 5:
                    continue
                
                # Get price
                price = None
                price_elem = parent.find("span", string=re.compile(r'₫|đ|\d'))
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    # Extract numbers
                    numbers = re.findall(r'[\d.,]+', price_text)
                    if numbers:
                        try:
                            price = float(numbers[0].replace('.', '').replace(',', ''))
                        except:
                            pass
                
                # Get image
                img = None
                img_elem = parent.find("img")
                if img_elem:
                    img = img_elem.get("src") or img_elem.get("data-src")
                    if img and not img.startswith("http"):
                        img = "https:" + img if img.startswith("//") else None
                
                results.append(CrawledProductItem(
                    name=name,
                    price=price,
                    sold=None,
                    rating=None,
                    img=img,
                    link=link,
                    platform="shopee"
                ))
                
            except Exception as e:
                logger.debug(f"Error parsing product: {e}")
                continue
        
        return results

    def _extract_ids(self, url: str) -> tuple[Optional[str], Optional[str]]:
        """Extract shopid và itemid từ URL"""
        m = re.search(r"i\.(\d+)\.(\d+)", url)
        if m:
            return m.group(1), m.group(2)
        return None, None

    def crawl_product_details(self, product_url: str, review_limit: int = 30) -> CrawledProductDetail:
        """
        Crawl product details và reviews
        Ưu tiên API (nhanh) → Fallback Selenium nếu cần
        """
        print(f"\n{'='*60}")
        print(f"[SHOPEE] 📦 Crawling product details")
        print(f"[SHOPEE] URL: {product_url}")
        print(f"{'='*60}")
        
        shopid, itemid = self._extract_ids(product_url)
        if not shopid or not itemid:
            print(f"[SHOPEE] ❌ Cannot extract IDs from URL")
            return CrawledProductDetail(link=product_url)
        
        print(f"[SHOPEE] 🔑 Shop ID: {shopid}, Item ID: {itemid}")
        
        # Load cookies
        saved_cookies = self.cookie_manager.load_cookies()
        
        if not saved_cookies:
            print("[SHOPEE] ❌ No cookies found!")
            print("[SHOPEE] 💡 Run: POST /api/v1/shopee/session/auto-login")
            return CrawledProductDetail(link=product_url)
        
        print(f"[SHOPEE] 🍪 Found {len(saved_cookies)} cookies")
        
        # ========================================
        # PHƯƠNG PHÁP 1: API TRỰC TIẾP (NHANH!)
        # ========================================
        print("[SHOPEE] 🚀 Trying API method (faster)...")
        
        all_reviews = self._fetch_reviews_via_api(saved_cookies, shopid, itemid, review_limit)
        
        if all_reviews:
            print(f"[SHOPEE] ✅ API method success! Got {len(all_reviews)} reviews")
            return CrawledProductDetail(
                link=product_url,
                category="",
                description="",
                detailed_rating={},
                total_rating=len(all_reviews),
                comments=all_reviews
            )
        
        # ========================================
        # PHƯƠNG PHÁP 2: SELENIUM (FALLBACK)
        # ========================================
        print("[SHOPEE] ⚠️  API failed, trying Selenium fallback...")
        all_reviews = self._fetch_reviews_via_selenium(product_url, saved_cookies, shopid, itemid, review_limit)
        
        return CrawledProductDetail(
            link=product_url,
            category="",
            description="",
            detailed_rating={},
            total_rating=len(all_reviews),
            comments=all_reviews
        )
    
    def _fetch_reviews_via_api(
        self, 
        cookies: List[dict], 
        shopid: str, 
        itemid: str, 
        review_limit: int
    ) -> List[CrawledReview]:
        """
        Fetch reviews trực tiếp qua API (NHANH!)
        Chỉ cần cookies, không cần Selenium
        """
        import requests
        
        all_reviews: List[CrawledReview] = []
        
        try:
            # Create session with cookies
            session = requests.Session()
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
                "Accept-Language": "vi-VN,vi;q=0.9",
                "Referer": f"https://shopee.vn/product-i.{shopid}.{itemid}",
            })
            
            # Apply cookies
            for c in cookies:
                if c.get('name') and c.get('value'):
                    session.cookies.set(
                        c['name'], 
                        c['value'], 
                        domain=c.get('domain', '.shopee.vn')
                    )
            
            # Fetch reviews
            reviews_api = "https://shopee.vn/api/v2/item/get_ratings"
            offset = 0
            limit = 20
            
            while len(all_reviews) < review_limit:
                params = {
                    "itemid": itemid,
                    "shopid": shopid,
                    "filter": 0,
                    "flag": 1,
                    "limit": limit,
                    "offset": offset,
                    "type": 0
                }
                
                print(f"[SHOPEE API] � Fetching reviews (offset={offset})...")
                resp = session.get(reviews_api, params=params, timeout=15)
                
                if resp.status_code != 200:
                    print(f"[SHOPEE API] ❌ Status {resp.status_code}")
                    return []  # Return empty to trigger fallback
                
                data = resp.json()
                
                # Check for API errors
                if data.get("error"):
                    print(f"[SHOPEE API] ❌ API error: {data.get('error')}")
                    return []
                
                ratings_data = data.get("data") or {}
                ratings = ratings_data.get("ratings") or []
                
                if not ratings:
                    print(f"[SHOPEE API] 📭 No more reviews")
                    break
                
                for r in ratings:
                    if len(all_reviews) >= review_limit:
                        break
                    
                    images = r.get("images") or []
                    image_urls = [
                        f"https://down-vn.img.susercontent.com/{img}" for img in images
                    ]
                    
                    all_reviews.append(CrawledReview(
                        author=r.get("author_username") or "Anonymous",
                        rating=r.get("rating_star", 5),
                        content=r.get("comment") or "",
                        time=str(r.get("ctime", "")),
                        images=image_urls,
                        helpful_count=r.get("like_count", 0)
                    ))
                
                offset += len(ratings)
                print(f"[SHOPEE API] 📝 Got {len(ratings)} reviews, total: {len(all_reviews)}")
                
                time.sleep(0.3)  # Small delay
            
            return all_reviews
            
        except Exception as e:
            print(f"[SHOPEE API] ❌ Error: {str(e)}")
            return []
    
    def _fetch_reviews_via_selenium(
        self,
        product_url: str,
        cookies: List[dict],
        shopid: str,
        itemid: str,
        review_limit: int
    ) -> List[CrawledReview]:
        """
        Fetch reviews via Selenium (FALLBACK)
        Dùng khi API bị block
        """
        import requests
        
        driver = None
        all_reviews: List[CrawledReview] = []
        
        try:
            print("[SHOPEE SELENIUM] 🚀 Starting browser...")
            
            options = uc.ChromeOptions()
            # Non-headless để bypass detection
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--lang=vi-VN")
            
            driver = uc.Chrome(options=options, version_main=None)
            
            # Load homepage and apply cookies
            driver.get(self.base_url)
            time.sleep(2)
            
            for cookie in cookies:
                try:
                    cookie_dict = {
                        'name': cookie.get('name'),
                        'value': cookie.get('value'),
                        'domain': cookie.get('domain', '.shopee.vn'),
                        'path': cookie.get('path', '/'),
                    }
                    if cookie_dict['name'] and cookie_dict['value']:
                        driver.add_cookie(cookie_dict)
                except:
                    pass
            
            # Load product page
            print("[SHOPEE SELENIUM] 📄 Loading product page...")
            driver.get(product_url)
            time.sleep(5)
            
            # Scroll to reviews
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Get fresh cookies from browser
            browser_cookies = driver.get_cookies()
            
            # Try API with browser cookies
            session = requests.Session()
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": product_url,
                "Accept": "application/json"
            })
            
            for c in browser_cookies:
                session.cookies.set(c['name'], c['value'])
            
            reviews_api = "https://shopee.vn/api/v2/item/get_ratings"
            offset = 0
            limit = 20
            
            while len(all_reviews) < review_limit:
                params = {
                    "itemid": itemid,
                    "shopid": shopid,
                    "filter": 0,
                    "flag": 1,
                    "limit": limit,
                    "offset": offset,
                    "type": 0
                }
                
                try:
                    resp = session.get(reviews_api, params=params, timeout=15)
                    if resp.status_code != 200:
                        break
                    
                    data = resp.json().get("data") or {}
                    ratings = data.get("ratings") or []
                    
                    if not ratings:
                        break
                    
                    for r in ratings:
                        if len(all_reviews) >= review_limit:
                            break
                        
                        images = r.get("images") or []
                        image_urls = [
                            f"https://down-vn.img.susercontent.com/{img}" for img in images
                        ]
                        
                        all_reviews.append(CrawledReview(
                            author=r.get("author_username") or "Anonymous",
                            rating=r.get("rating_star", 5),
                            content=r.get("comment") or "",
                            time=str(r.get("ctime", "")),
                            images=image_urls,
                            helpful_count=r.get("like_count", 0)
                        ))
                    
                    offset += len(ratings)
                    print(f"[SHOPEE SELENIUM] 📝 Got {len(ratings)} reviews, total: {len(all_reviews)}")
                    time.sleep(0.5)
                    
                except Exception as e:
                    print(f"[SHOPEE SELENIUM] ⚠️  API error: {e}")
                    break
            
            # Update cookies
            self.cookie_manager.save_cookies(browser_cookies)
            print(f"[SHOPEE SELENIUM] ✅ Total reviews: {len(all_reviews)}")
            
            return all_reviews
            
        except Exception as e:
            print(f"[SHOPEE SELENIUM] ❌ Error: {str(e)}")
            return []
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
