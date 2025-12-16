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
        """
        Crawl product details và reviews từ Lazada
        Sử dụng Selenium để load dynamic content và parse HTML
        """
        item_id = self._extract_item_id(product_url)
        all_reviews: List[CrawledReview] = []
        driver = None
        category = "Unknown"
        description = ""
        detailed_rating = {}
        total_rating_count = 0

        try:
            from selenium import webdriver
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            selenium_available = True
        except Exception:
            selenium_available = False

        try:
            if selenium_available:
                options = Options()
                options.add_argument("--headless=new")
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                # Enable logging to capture network requests
                options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
                driver = webdriver.Chrome(options=options)
                
                print(f"[LAZADA] 📦 Crawling product details: {product_url}")
                driver.get(product_url)
                time.sleep(5)

                if not item_id:
                    item_id = self._extract_item_id(driver.current_url)
                    print(f"[LAZADA] 🔑 Extracted item ID: {item_id}")

            if not item_id:
                print(f"[LAZADA] ❌ Cannot extract item ID from URL")
                return CrawledProductDetail(link=product_url)

            if driver:
                from bs4 import BeautifulSoup
                
                # Wait for page to load
                print("[LAZADA] ⏳ Waiting for page to load...")
                time.sleep(5)
                
                # Try to find and click on reviews tab/section
                try:
                    # Look for reviews tab or section
                    review_tabs = driver.find_elements(By.XPATH, "//*[contains(text(), 'Đánh giá') or contains(text(), 'Reviews') or contains(text(), 'Review')]")
                    for tab in review_tabs[:3]:  # Try first 3 matches
                        try:
                            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", tab)
                            time.sleep(1)
                            driver.execute_script("arguments[0].click();", tab)
                            time.sleep(3)
                            break
                        except Exception:
                            continue
                except Exception as e:
                    print(f"[LAZADA] ⚠️  Could not click review tab: {str(e)}")
                
                # Scroll to load reviews section - multiple strategies
                print("[LAZADA] 📜 Scrolling to reviews section...")
                
                # Strategy 1: Scroll to bottom
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)
                
                # Strategy 2: Find reviews section and scroll to it
                try:
                    review_section = driver.find_elements(By.XPATH, "//*[contains(@class, 'review') or contains(@id, 'review') or contains(@data-spm, 'review')]")
                    if review_section:
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'start'});", review_section[0])
                        time.sleep(3)
                except Exception:
                    pass
                
                # Strategy 3: Try to click "See all reviews" or "Xem tất cả đánh giá" button
                try:
                    review_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Xem tất cả') or contains(text(), 'Xem thêm') or contains(text(), 'See all') or contains(text(), 'View all')]")
                    for btn in review_buttons[:2]:
                        try:
                            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", btn)
                            time.sleep(1)
                            driver.execute_script("arguments[0].click();", btn)
                            time.sleep(3)
                            break
                        except Exception:
                            continue
                except Exception:
                    pass
                
                # Strategy 3.5: Try to click on "Reviews" or "Đánh giá" tab/button
                try:
                    review_tabs = driver.find_elements(By.XPATH, "//*[contains(text(), 'Đánh giá') or contains(text(), 'Reviews') or contains(text(), 'Feedback')]")
                    for tab in review_tabs[:3]:
                        try:
                            # Check if it's clickable (button, link, or div with click handler)
                            tag_name = tab.tag_name.lower()
                            if tag_name in ['button', 'a', 'div', 'span']:
                                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", tab)
                                time.sleep(1)
                                driver.execute_script("arguments[0].click();", tab)
                                time.sleep(3)
                                print(f"[LAZADA] ✅ Clicked on review tab: {tab.text[:50]}")
                                break
                        except Exception as e:
                            continue
                except Exception as e:
                    print(f"[LAZADA] ⚠️  Error clicking review tab: {e}")
                
                # Strategy 4: Scroll incrementally to trigger lazy loading
                for i in range(5):
                    scroll_position = (i + 1) * 1000
                    driver.execute_script(f"window.scrollTo(0, {scroll_position});")
                    time.sleep(2)
                
                # Strategy 5: Tìm và scroll đến phần reviews cụ thể, wait và parse ngay
                mod_reviews_element = None
                try:
                    # Tìm phần reviews bằng nhiều cách
                    review_selectors = [
                        "div.mod-reviews",
                        "div[class*='mod-reviews']",
                        "div[class*='review']",
                        "*[class*='feedback']"
                    ]
                    for selector in review_selectors:
                        try:
                            review_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                            if review_elements:
                                print(f"[LAZADA] 📍 Found review section with selector: {selector}")
                                mod_reviews_element = review_elements[0]
                                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", mod_reviews_element)
                                time.sleep(2)
                                
                                # Wait for reviews to load - check for items inside
                                for wait_attempt in range(5):
                                    try:
                                        items_inside = mod_reviews_element.find_elements(By.CSS_SELECTOR, "div.item")
                                        if len(items_inside) > 0:
                                            print(f"[LAZADA] ✅ Found {len(items_inside)} review items after waiting")
                                            break
                                    except Exception:
                                        pass
                                    time.sleep(2)
                                
                                # Additional scroll to trigger lazy loading
                                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", mod_reviews_element)
                                time.sleep(3)
                                break
                        except Exception as e:
                            print(f"[LAZADA] ⚠️  Error with selector {selector}: {e}")
                            continue
                except Exception as e:
                    print(f"[LAZADA] ⚠️  Error finding review section: {e}")
                
                # Final scroll to bottom
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)
                
                # Wait for any dynamic content to load
                try:
                    WebDriverWait(driver, 10).until(
                        lambda d: d.execute_script("return document.readyState") == "complete"
                    )
                except Exception:
                    pass
                
                # Get page source after all scrolling
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # Debug: Save HTML for inspection (optional, can be removed later)
                # with open(f"lazada_debug_{item_id}.html", "w", encoding="utf-8") as f:
                #     f.write(driver.page_source)
                
                # Extract product info
                try:
                    # Try to get category
                    category_elem = soup.find('a', class_=lambda x: x and 'breadcrumb' in str(x).lower())
                    if category_elem:
                        category = category_elem.get_text(strip=True)
                    
                    # Try to get description
                    desc_elem = soup.find('div', class_=lambda x: x and ('description' in str(x).lower() or 'product-detail' in str(x).lower()))
                    if desc_elem:
                        description = desc_elem.get_text(strip=True)[:1000]  # Limit length
                except Exception:
                    pass
                
                # Extract reviews - try multiple methods
                print("[LAZADA] 🔍 Looking for reviews...")
                review_items = []
                
                # Method 0: Nếu đã tìm thấy mod_reviews_element bằng Selenium, parse trực tiếp từ đó
                if mod_reviews_element:
                    try:
                        # Get HTML từ Selenium element
                        mod_reviews_html = mod_reviews_element.get_attribute('outerHTML')
                        if mod_reviews_html:
                            mod_reviews_soup = BeautifulSoup(mod_reviews_html, 'html.parser')
                            all_items = mod_reviews_soup.find_all('div', class_='item')
                            print(f"[LAZADA] 📦 Method 0 (Selenium): Found {len(all_items)} items in mod-reviews element")
                            # Filter: chỉ lấy items có cấu trúc review hợp lệ
                            valid_review_items = []
                            for item in all_items:
                                has_item_top = item.find('div', class_='item-top') is not None
                                has_item_content = item.find('div', class_='item-content') is not None
                                if has_item_top and has_item_content:
                                    valid_review_items.append(item)
                            if valid_review_items:
                                review_items = valid_review_items
                                print(f"[LAZADA] ✅ Method 0: Found {len(review_items)} valid review items from Selenium element")
                    except Exception as e:
                        print(f"[LAZADA] ⚠️  Method 0 error: {e}")
                
                # Method 1: Tìm div.mod-reviews trực tiếp (ưu tiên nhất)
                if not review_items:
                    mod_reviews_container = soup.find('div', class_='mod-reviews')
                    if mod_reviews_container:
                        print(f"[LAZADA] ✅ Found mod-reviews container")
                        # Tìm tất cả div.item trong mod-reviews
                        all_items = mod_reviews_container.find_all('div', class_='item')
                        print(f"[LAZADA] 📦 Found {len(all_items)} items in mod-reviews")
                        # Filter: chỉ lấy items có cấu trúc review hợp lệ (item-top + item-content)
                        valid_review_items = []
                        for item in all_items:
                            has_item_top = item.find('div', class_='item-top') is not None
                            has_item_content = item.find('div', class_='item-content') is not None
                            if has_item_top and has_item_content:
                                valid_review_items.append(item)
                        review_items = valid_review_items
                        print(f"[LAZADA] ✅ Method 1: Found {len(review_items)} valid review items from mod-reviews")
                
                # Method 2: Tìm div có class chứa "mod-reviews" (có thể có nhiều class)
                if not review_items:
                    mod_reviews_container = soup.find('div', class_=lambda x: x and 'mod-reviews' in str(x))
                    if mod_reviews_container:
                        print(f"[LAZADA] ✅ Found mod-reviews container (with multiple classes)")
                        all_items = mod_reviews_container.find_all('div', class_='item')
                        # Filter: chỉ lấy items có cấu trúc review hợp lệ
                        valid_review_items = []
                        for item in all_items:
                            has_item_top = item.find('div', class_='item-top') is not None
                            has_item_content = item.find('div', class_='item-content') is not None
                            if has_item_top and has_item_content:
                                valid_review_items.append(item)
                        review_items = valid_review_items
                        print(f"[LAZADA] ✅ Method 2: Found {len(review_items)} valid review items")
                
                # Method 3: Tìm bằng text content - tìm các div chứa text "đánh giá" hoặc "review"
                if not review_items:
                    # Find all divs that might contain reviews by looking for review-related text
                    all_divs = soup.find_all('div')
                    for div in all_divs:
                        div_text = div.get_text(strip=True).lower()
                        # Check if div contains review-like content
                        if any(keyword in div_text for keyword in ['đánh giá', 'review', 'rating', 'sao']):
                            # Check if it has child elements that look like review items
                            child_items = div.find_all('div', class_=lambda x: x and 'item' in str(x))
                            if child_items:
                                # Check if items have review-like structure
                                for child in child_items:
                                    child_text = child.get_text(strip=True)
                                    # Simple heuristic: if it has text and is not too short, might be a review
                                    if len(child_text) > 20 and any(char in child_text for char in ['⭐', '★', 'sao', 'star']):
                                        review_items.append(child)
                                if review_items:
                                    print(f"[LAZADA] ✅ Method 3: Found {len(review_items)} reviews by text content")
                                    break
                
                # Method 3.5: Sử dụng Selenium để tìm trực tiếp review items (nếu BeautifulSoup không tìm thấy)
                if not review_items:
                    try:
                        # Tìm tất cả div.item có cấu trúc review trong toàn bộ page
                        all_selenium_items = driver.find_elements(By.CSS_SELECTOR, "div.item")
                        print(f"[LAZADA] 🔍 Method 3.5 (Selenium): Found {len(all_selenium_items)} items in page, checking structure...")
                        for selenium_item in all_selenium_items:
                            try:
                                # Check structure bằng Selenium - phải có cả item-top và item-content
                                item_top = selenium_item.find_elements(By.CSS_SELECTOR, "div.item-top")
                                item_content = selenium_item.find_elements(By.CSS_SELECTOR, "div.item-content")
                                if item_top and item_content:
                                    # Get HTML và parse
                                    item_html = selenium_item.get_attribute('outerHTML')
                                    if item_html:
                                        item_soup = BeautifulSoup(item_html, 'html.parser')
                                        # Double check structure in parsed HTML
                                        parsed_item_top = item_soup.find('div', class_='item-top')
                                        parsed_item_content = item_soup.find('div', class_='item-content')
                                        if parsed_item_top and parsed_item_content:
                                            review_items.append(item_soup)
                            except Exception as e:
                                continue
                        if review_items:
                            print(f"[LAZADA] ✅ Method 3.5: Found {len(review_items)} valid review items via Selenium")
                    except Exception as e:
                        print(f"[LAZADA] ⚠️  Method 3.5 error: {e}")
                
                # Method 4: Tìm tất cả div.item và filter by structure (ưu tiên cấu trúc Lazada thực tế)
                if not review_items:
                    all_items = soup.find_all('div', class_='item')
                    print(f"[LAZADA] 🔍 Method 4: Found {len(all_items)} items with 'item' class, filtering...")
                    for item in all_items:
                        # Check for Lazada review structure: item-top + item-content
                        has_item_top = item.find('div', class_='item-top') is not None
                        has_item_content = item.find('div', class_='item-content') is not None
                        
                        # Also check for review elements
                        has_reviewer = item.find('span', class_='reviewer') is not None
                        has_star = item.find('div', class_='container-star') is not None
                        has_review_content = item.find('div', class_='item-content-main-content-reviews') is not None
                        
                        # Must have both item-top and item-content (Lazada structure)
                        # OR have reviewer + star + review content
                        if (has_item_top and has_item_content) or (has_reviewer and has_star and has_review_content):
                            review_items.append(item)
                    print(f"[LAZADA] ⚠️  Method 4: Found {len(review_items)} review items from {len(all_items)} total items")
                
                # Method 5: Try finding by data attributes
                if not review_items:
                    review_items = soup.find_all('div', attrs={'data-qa-locator': lambda x: x and 'review' in str(x).lower()})
                    if review_items:
                        print(f"[LAZADA] ✅ Method 5: Found {len(review_items)} reviews by data-qa-locator")
                
                # Method 6: Try finding by common class patterns
                if not review_items:
                    # Look for divs with review-related classes
                    potential_reviews = soup.find_all('div', class_=lambda x: x and any(
                        keyword in str(x).lower() for keyword in ['review', 'comment', 'rating', 'feedback', 'evaluation']
                    ))
                    for potential in potential_reviews:
                        # Check if it has review-like structure (has text, has user info, etc.)
                        potential_text = potential.get_text(strip=True)
                        if len(potential_text) > 20:
                            # Check for user/author indicators
                            has_user_indicator = potential.find('span', class_=lambda x: x and ('user' in str(x).lower() or 'name' in str(x).lower() or 'author' in str(x).lower()))
                            if has_user_indicator:
                                review_items.append(potential)
                    if review_items:
                        print(f"[LAZADA] ✅ Method 6: Found {len(review_items)} reviews by class pattern matching")
                
                # Method 7: Try finding by looking for star ratings
                if not review_items:
                    # Find all elements with star ratings
                    star_elements = soup.find_all(['i', 'span', 'div'], class_=lambda x: x and 'star' in str(x).lower())
                    for star_elem in star_elements:
                        # Find parent container that might be a review
                        parent = star_elem.find_parent('div')
                        if parent:
                            parent_text = parent.get_text(strip=True)
                            if len(parent_text) > 20 and parent not in review_items:
                                review_items.append(parent)
                    if review_items:
                        print(f"[LAZADA] ✅ Method 7: Found {len(review_items)} reviews by star rating")
                
                # Method 8: Last resort - find any div with substantial text that might be a review
                if not review_items:
                    # Blacklist: các class/id không phải review
                    blacklist_classes = [
                        'footer', 'header', 'nav', 'navigation', 'menu', 'breadcrumb',
                        'sidebar', 'advertisement', 'ad', 'banner', 'promotion',
                        'cookie', 'popup', 'modal', 'dialog', 'overlay'
                    ]
                    all_divs = soup.find_all('div')
                    for div in all_divs:
                        # Skip if has blacklist class/id
                        div_class = str(div.get('class', [])).lower()
                        div_id = str(div.get('id', '')).lower()
                        if any(bl in div_class or bl in div_id for bl in blacklist_classes):
                            continue
                        
                        div_text = div.get_text(strip=True)
                        # Heuristic: if div has substantial text (50+ chars) and contains review keywords
                        if len(div_text) > 50 and len(div_text) < 1500:  # Reduced max length
                            div_lower = div_text.lower()
                            # Must have review keywords
                            if any(keyword in div_lower for keyword in ['đánh giá', 'review', 'sao', 'tốt', 'xấu', 'hài lòng', 'sản phẩm', 'mua', 'dùng']):
                                # Must NOT have too many blacklist keywords
                                blacklist_count = sum(1 for keyword in ['góp ý', 'tiết kiệm', 'ứng dụng', 'voucher', 'đăng nhập', 'đăng ký'] if keyword in div_lower)
                                if blacklist_count < 2:  # Allow max 1 blacklist keyword
                                    # Check if it's not already a parent/child of another review
                                    is_child = False
                                    for existing_review in review_items:
                                        try:
                                            if div in existing_review.descendants or existing_review in div.descendants:
                                                is_child = True
                                                break
                                        except Exception:
                                            pass
                                    if not is_child:
                                        review_items.append(div)
                    if review_items:
                        print(f"[LAZADA] ⚠️  Method 8: Found {len(review_items)} potential reviews by text heuristic")
                
                print(f"[LAZADA] 📊 Total review items found: {len(review_items)}")
                
                # Method 9: Try to find reviews via network requests (API calls)
                if not review_items and item_id:
                    try:
                        # Check browser logs for network requests
                        logs = driver.get_log('performance')
                        for log in logs:
                            try:
                                message = json.loads(log['message'])
                                if message.get('message', {}).get('method') == 'Network.responseReceived':
                                    url = message.get('message', {}).get('params', {}).get('response', {}).get('url', '')
                                    if 'review' in url.lower() or 'rating' in url.lower() or 'feedback' in url.lower():
                                        print(f"[LAZADA] 🔍 Found potential review API: {url}")
                                        # Try to fetch the response
                                        try:
                                            response = requests.get(url, headers=self.headers, timeout=10)
                                            if response.status_code == 200:
                                                data = response.json()
                                                # Try to parse reviews from API response
                                                if isinstance(data, dict):
                                                    # Common patterns for review data
                                                    reviews_data = (
                                                        data.get('data', {}).get('reviews') or
                                                        data.get('reviews') or
                                                        data.get('data', {}).get('items') or
                                                        data.get('items') or
                                                        data.get('data', [])
                                                    )
                                                    if reviews_data and isinstance(reviews_data, list):
                                                        print(f"[LAZADA] ✅ Found {len(reviews_data)} reviews via API")
                                                        # Convert API data to CrawledReview objects
                                                        for r in reviews_data[:review_limit]:
                                                            if len(all_reviews) >= review_limit:
                                                                break
                                                            all_reviews.append(CrawledReview(
                                                                author=r.get('author') or r.get('user') or r.get('name') or "Anonymous",
                                                                rating=int(r.get('rating', r.get('score', 5))),
                                                                content=r.get('content') or r.get('comment') or r.get('text') or "",
                                                                time=str(r.get('time') or r.get('date') or r.get('created_at') or ""),
                                                                images=r.get('images') or r.get('photos') or [],
                                                                seller_respond=r.get('seller_response'),
                                                                helpful_count=int(r.get('helpful', r.get('like_count', 0)))
                                                            ))
                                                        if all_reviews:
                                                            print(f"[LAZADA] ✅ Successfully parsed {len(all_reviews)} reviews from API")
                                                            return CrawledProductDetail(
                                                                link=product_url,
                                                                category=category,
                                                                description=description,
                                                                detailed_rating=detailed_rating,
                                                                total_rating=len(all_reviews),
                                                                comments=all_reviews
                                                            )
                                        except Exception as api_error:
                                            print(f"[LAZADA] ⚠️  Could not fetch from API: {str(api_error)}")
                            except Exception:
                                continue
                    except Exception as e:
                        print(f"[LAZADA] ⚠️  Error checking network logs: {str(e)}")
                
                # Method 10: Try to find reviews in iframes
                if not review_items:
                    try:
                        iframes = driver.find_elements(By.TAG_NAME, "iframe")
                        for iframe in iframes:
                            try:
                                driver.switch_to.frame(iframe)
                                iframe_soup = BeautifulSoup(driver.page_source, 'html.parser')
                                iframe_reviews = iframe_soup.find_all('div', class_=lambda x: x and 'item' in str(x))
                                if iframe_reviews:
                                    review_items.extend(iframe_reviews)
                                    print(f"[LAZADA] ✅ Found {len(iframe_reviews)} reviews in iframe")
                                driver.switch_to.default_content()
                            except Exception:
                                driver.switch_to.default_content()
                                continue
                    except Exception:
                        pass
                
                # Parse each review item
                for item in review_items:
                    if len(all_reviews) >= review_limit:
                        break
                    
                    try:
                        # 1. Extract Author - từ cấu trúc Lazada: item-top > user-info > infos > reviewer
                        author = "Anonymous"
                        # Try Lazada structure first: item-top > user-info > infos > p > span.reviewer
                        item_top = item.find('div', class_='item-top')
                        if item_top:
                            user_info = item_top.find('div', class_='user-info')
                            if user_info:
                                infos = user_info.find('div', class_='infos')
                                if infos:
                                    reviewer_elem = infos.find('span', class_='reviewer')
                                    if reviewer_elem:
                                        author = reviewer_elem.get_text(strip=True)
                        
                        # Fallback: try other selectors
                        if author == "Anonymous":
                            reviewer_elem = item.find('span', class_='reviewer')
                            if reviewer_elem:
                                author = reviewer_elem.get_text(strip=True)
                        
                        # Fallback: try alternative selectors
                        if author == "Anonymous":
                            reviewer_selectors = [
                                ('span', lambda x: x and ('user' in str(x).lower() or 'name' in str(x).lower() or 'author' in str(x).lower())),
                                ('div', lambda x: x and ('user' in str(x).lower() or 'name' in str(x).lower() or 'author' in str(x).lower())),
                            ]
                            for tag, selector in reviewer_selectors:
                                reviewer_elem = item.find(tag, class_=selector)
                                if reviewer_elem:
                                    author_text = reviewer_elem.get_text(strip=True)
                                    if author_text and len(author_text) > 0 and len(author_text) < 100:
                                        author = author_text
                                        break
                        
                        # 2. Extract Time - từ cấu trúc Lazada: item-top > user-info > infos > p > span.time
                        review_time = ""
                        if item_top:
                            user_info = item_top.find('div', class_='user-info')
                            if user_info:
                                infos = user_info.find('div', class_='infos')
                                if infos:
                                    time_elem = infos.find('span', class_='time')
                                    if time_elem:
                                        review_time = time_elem.get_text(strip=True)
                        
                        # Fallback: try other selectors
                        if not review_time:
                            time_elem = item.find('span', class_='time')
                            if not time_elem:
                                time_elem = item.find('span', class_=lambda x: x and 'time' in str(x).lower())
                            if time_elem:
                                review_time = time_elem.get_text(strip=True)
                        
                        # 3. Extract Rating - từ cấu trúc Lazada: item-middle > container-star > img.star
                        rating = 5  # default
                        item_middle = item.find('div', class_='item-middle')
                        if item_middle:
                            star_container = item_middle.find('div', class_='container-star')
                            if star_container:
                                stars = star_container.find_all('img', class_='star')
                                if stars:
                                    rating = len(stars)
                        
                        # Fallback: try other selectors
                        if rating == 5:
                            star_container = item.find('div', class_='container-star')
                            if not star_container:
                                star_container = item.find('div', class_=lambda x: x and 'star' in str(x).lower())
                            if star_container:
                                stars = star_container.find_all('img', class_='star')
                                if not stars:
                                    stars = star_container.find_all('i', class_=lambda x: x and 'star' in str(x).lower())
                                if stars:
                                    rating = len(stars)
                        
                        # 4. Extract Content - từ cấu trúc Lazada: item-content > item-content-main > item-content-main-content > item-content-main-content-reviews
                        content = ""
                        item_content = item.find('div', class_='item-content')
                        if item_content:
                            item_content_main = item_content.find('div', class_='item-content-main')
                            if item_content_main:
                                item_content_main_content = item_content_main.find('div', class_='item-content-main-content')
                                if item_content_main_content:
                                    # Skip SKU info
                                    sku_info = item_content_main_content.find('div', class_='item-content-main-content-skuInfo')
                                    if sku_info:
                                        sku_info.decompose()
                                    
                                    # Get reviews content
                                    reviews_container = item_content_main_content.find('div', class_='item-content-main-content-reviews')
                                    if reviews_container:
                                        # Lấy tất cả các review items và join lại
                                        review_items_elems = reviews_container.find_all('div', class_='item-content-main-content-reviews-item')
                                        content_parts = []
                                        for review_item_elem in review_items_elems:
                                            spans = review_item_elem.find_all('span')
                                            item_text_parts = []
                                            for span in spans:
                                                span_classes = span.get('class', [])
                                                # Skip review-attribute labels (như "Chất liệu:")
                                                if isinstance(span_classes, list) and 'review-attribute' in span_classes:
                                                    continue
                                                if isinstance(span_classes, str) and 'review-attribute' in span_classes:
                                                    continue
                                                
                                                span_text = span.get_text(strip=True)
                                                if span_text and len(span_text) > 2:
                                                    # Skip short labels/emojis
                                                    if len(span_text) < 10 and any(char in span_text for char in ['💲', '🍲', '👃', ':', '：']):
                                                        continue
                                                    item_text_parts.append(span_text)
                                            
                                            if item_text_parts:
                                                item_text = ' '.join(item_text_parts)
                                                if len(item_text) > 5:
                                                    content_parts.append(item_text)
                                        
                                        if content_parts:
                                            content = ' '.join(content_parts)
                                    
                                    # Fallback: get all text from item-content-main-content (excluding SKU)
                                    if not content or len(content) < 10:
                                        content = item_content_main_content.get_text(separator=' ', strip=True)
                        
                        # Fallback: try old method
                        if not content or len(content) < 10:
                            reviews_container = item.find('div', class_='item-content-main-content-reviews')
                            if reviews_container:
                                review_items_elems = reviews_container.find_all('div', class_='item-content-main-content-reviews-item')
                                content_parts = []
                                for review_item_elem in review_items_elems:
                                    spans = review_item_elem.find_all('span')
                                    item_text_parts = []
                                    for span in spans:
                                        span_classes = span.get('class', [])
                                        if isinstance(span_classes, list) and 'review-attribute' in span_classes:
                                            continue
                                        if isinstance(span_classes, str) and 'review-attribute' in span_classes:
                                            continue
                                        span_text = span.get_text(strip=True)
                                        if span_text and len(span_text) > 2:
                                            if len(span_text) < 10 and any(char in span_text for char in ['💲', '🍲', '👃', ':', '：']):
                                                continue
                                            item_text_parts.append(span_text)
                                    if item_text_parts:
                                        item_text = ' '.join(item_text_parts)
                                        if len(item_text) > 5:
                                            content_parts.append(item_text)
                                if content_parts:
                                    content = ' '.join(content_parts)
                        
                        # Fallback: Extract content from item text if not found
                        if not content or len(content) < 10:
                            # Get all text from item, but exclude known non-content elements
                            item_text = item.get_text(separator=' ', strip=True)
                            # Remove common non-content patterns
                            lines = item_text.split('\n')
                            content_lines = []
                            for line in lines:
                                line = line.strip()
                                # Skip very short lines, dates, ratings only, etc.
                                if len(line) > 10 and not re.match(r'^\d+[\./]\d+[\./]\d+', line):  # Skip dates
                                    if not re.match(r'^[⭐★☆\s]+$', line):  # Skip rating-only lines
                                        content_lines.append(line)
                            if content_lines:
                                content = ' '.join(content_lines[:5])  # Take first 5 meaningful lines
                        
                        # Validate content - chỉ lấy nếu có content hợp lệ
                        if not content or len(content) < 10:
                            # Last resort: use item text if it's substantial
                            item_text = item.get_text(separator=' ', strip=True)
                            if len(item_text) > 20 and len(item_text) < 2000:
                                # Check if it looks like a review (has some keywords)
                                if any(keyword in item_text.lower() for keyword in ['tốt', 'xấu', 'hài lòng', 'không', 'sản phẩm', 'mua', 'dùng']):
                                    content = item_text[:2000]
                                else:
                                    continue
                            else:
                                continue
                        
                        # Validate content - loại bỏ nội dung không phải review
                        content_lower = content.lower()
                        
                        # Blacklist: các từ khóa cho thấy đây KHÔNG phải review
                        blacklist_keywords = [
                            'góp ý', 'tiết kiệm', 'ứng dụng', 'tải ứng dụng', 'mua sắm',
                            'voucher', 'deal', 'khuyến mãi', 'bán hàng', 'chăm sóc khách hàng',
                            'trung tâm hỗ trợ', 'đơn hàng', 'thanh toán', 'giao hàng',
                            'đổi trả', 'hoàn tiền', 'liên hệ', 'kiểm tra đơn hàng',
                            'đăng nhập', 'đăng ký', 'quản lý tài khoản', 'danh sách yêu thích',
                            'nhận xét của tôi', 'đăng xuất', 'change language', 'tìm kiếm',
                            'danh mục', 'lazmall', 'mã giảm giá', 'nạp thẻ', 'lazglobal',
                            'success!', 'please check', 'download link', 'inner feedback',
                            'footer', 'header', 'navigation', 'menu', 'breadcrumb',
                            'copyright', 'lazada', 'southeast asia', 'follow us',
                            'payment methods', 'delivery services', 'verified by'
                        ]
                        
                        # Nếu content chứa quá nhiều blacklist keywords, loại bỏ
                        blacklist_count = sum(1 for keyword in blacklist_keywords if keyword in content_lower)
                        if blacklist_count >= 3:
                            print(f"[LAZADA] ⚠️  Skipping item - too many blacklist keywords ({blacklist_count})")
                            continue
                        
                        # Nếu content chứa các pattern không phải review
                        non_review_patterns = [
                            r'vui lòng nhập',
                            r'địa chỉ email',
                            r'mã đơn hàng',
                            r'nhấn vào đây',
                            r'check your phone',
                            r'download link',
                            r'voucher độc quyền',
                            r'deal tốt hơn',
                            r'cập nhật đầu tiên'
                        ]
                        pattern_matches = sum(1 for pattern in non_review_patterns if re.search(pattern, content_lower))
                        if pattern_matches >= 2:
                            print(f"[LAZADA] ⚠️  Skipping item - matches non-review patterns ({pattern_matches})")
                            continue
                        
                        # Validate: review phải có ít nhất một từ khóa review-related
                        review_keywords = [
                            'sản phẩm', 'hàng', 'mua', 'dùng', 'sử dụng', 'tốt', 'xấu',
                            'hài lòng', 'không hài lòng', 'đánh giá', 'review', 'rating',
                            'chất lượng', 'giá', 'giao hàng', 'đóng gói', 'nhận hàng',
                            'khuyến nghị', 'nên mua', 'không nên', 'tốt', 'tệ', 'ok',
                            'thích', 'không thích', 'phù hợp', 'đáng tiền', 'rẻ', 'đắt'
                        ]
                        has_review_keyword = any(keyword in content_lower for keyword in review_keywords)
                        if not has_review_keyword:
                            print(f"[LAZADA] ⚠️  Skipping item - no review keywords found")
                            continue
                        
                        # Validate: content không được quá dài (có thể là toàn bộ page)
                        if len(content) > 1500:
                            print(f"[LAZADA] ⚠️  Skipping item - content too long ({len(content)} chars), might be page content")
                            continue
                        
                        # Validate: content không được chứa quá nhiều links/URLs (có thể là navigation)
                        url_count = len(re.findall(r'http[s]?://|www\.', content))
                        if url_count > 5:
                            print(f"[LAZADA] ⚠️  Skipping item - too many URLs ({url_count}), might be navigation")
                            continue
                        
                        # 5. Extract Images - từ cấu trúc Lazada: item-content > item-content-main > item-content-main-imgs
                        images = []
                        if item_content:
                            item_content_main = item_content.find('div', class_='item-content-main')
                            if item_content_main:
                                imgs_container = item_content_main.find('div', class_='item-content-main-imgs')
                                if imgs_container:
                                    img_wrappers = imgs_container.find_all('div', class_='img-wrapper')
                                    for wrapper in img_wrappers:
                                        img_item = wrapper.find('div', class_='img-item')
                                        if img_item:
                                            style = img_item.get('style', '')
                                            if style:
                                                bg_match = re.search(r'background-image:\s*url\(["\']?([^"\']+)["\']?\)', style)
                                                if bg_match:
                                                    img_url = bg_match.group(1)
                                                    if img_url:
                                                        # Decode HTML entities
                                                        img_url = img_url.replace('&quot;', '"').replace('&amp;', '&')
                                                        if img_url.startswith('//'):
                                                            img_url = 'https:' + img_url
                                                        elif not img_url.startswith('http'):
                                                            img_url = 'https:' + img_url
                                                        images.append(img_url)
                        
                        # Fallback: try old method
                        if not images:
                            imgs_container = item.find('div', class_='item-content-main-imgs')
                            if imgs_container:
                                img_wrappers = imgs_container.find_all('div', class_='img-wrapper')
                                for wrapper in img_wrappers:
                                    img_item = wrapper.find('div', class_='img-item')
                                    if img_item:
                                        style = img_item.get('style', '')
                                        if style:
                                            bg_match = re.search(r'background-image:\s*url\(["\']?([^"\']+)["\']?\)', style)
                                            if bg_match:
                                                img_url = bg_match.group(1)
                                                if img_url:
                                                    img_url = img_url.replace('&quot;', '"').replace('&amp;', '&')
                                                    if img_url.startswith('//'):
                                                        img_url = 'https:' + img_url
                                                    elif not img_url.startswith('http'):
                                                        img_url = 'https:' + img_url
                                                    images.append(img_url)
                        
                        # 6. Extract Helpful Count - từ cấu trúc Lazada: item-content > item-content-like > item-content-like-content-text
                        helpful_count = 0
                        if item_content:
                            item_content_like = item_content.find('div', class_='item-content-like')
                            if item_content_like:
                                helpful_elem = item_content_like.find('span', class_='item-content-like-content-text')
                                if helpful_elem:
                                    helpful_text = helpful_elem.get_text(strip=True)
                                    # Pattern: "Helpful(2)" or "Hữu ích(2)"
                                    helpful_match = re.search(r'\((\d+)\)', helpful_text)
                                    if helpful_match:
                                        try:
                                            helpful_count = int(helpful_match.group(1))
                                        except:
                                            pass
                        
                        # Fallback: try old method
                        if helpful_count == 0:
                            helpful_elem = item.find('span', class_='item-content-like-content-text')
                            if helpful_elem:
                                helpful_text = helpful_elem.get_text(strip=True)
                                helpful_match = re.search(r'\((\d+)\)', helpful_text)
                                if helpful_match:
                                    try:
                                        helpful_count = int(helpful_match.group(1))
                                    except:
                                        pass
                        
                        # 7. Extract Seller Response (optional) - từ seller-reply-wrapper-v2
                        seller_respond = None
                        seller_reply_wrapper = item.find('div', class_='seller-reply-wrapper-v2')
                        if seller_reply_wrapper:
                            seller_reply_content = seller_reply_wrapper.find('div', class_='item-content-main-content-reviews')
                            if seller_reply_content:
                                seller_reply_items = seller_reply_content.find_all('div', class_='item-content-main-content-reviews-item')
                                seller_text_parts = []
                                for reply_item in seller_reply_items:
                                    spans = reply_item.find_all('span')
                                    for span in spans:
                                        span_text = span.get_text(strip=True)
                                        if span_text and len(span_text) > 2:
                                            seller_text_parts.append(span_text)
                                if seller_text_parts:
                                    seller_respond = ' '.join(seller_text_parts)
                        
                        all_reviews.append(CrawledReview(
                            author=author[:200] if author else "Anonymous",
                            rating=rating,
                            content=content[:2000],
                            time=review_time,
                            images=images[:5],
                            seller_respond=seller_respond,
                            helpful_count=helpful_count
                        ))
                    except Exception as e:
                        # Nếu có lỗi parse, skip item này
                        print(f"[LAZADA] ⚠️  Error parsing review item: {str(e)}")
                        continue
                
                # Try to get total review count
                try:
                    total_review_elem = soup.find('span', class_=lambda x: x and ('review' in str(x).lower() and 'count' in str(x).lower()))
                    if total_review_elem:
                        total_text = total_review_elem.get_text(strip=True)
                        match = re.search(r'(\d+)', total_text)
                        if match:
                            total_rating_count = int(match.group(1))
                except Exception:
                    total_rating_count = len(all_reviews)
                
                print(f"[LAZADA] ✅ Successfully crawled {len(all_reviews)} reviews")
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

        return CrawledProductDetail(
            link=product_url,
            category=category,
            description=description,
            detailed_rating=detailed_rating,
            total_rating=total_rating_count if total_rating_count > 0 else len(all_reviews),
            comments=all_reviews
        )