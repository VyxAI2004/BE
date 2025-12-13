"""
Cookie Manager for Shopee Scraper
Manages cookies to avoid re-login on every request
"""

import json
import os
import time
from typing import List, Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class CookieManager:
    """Quản lý cookies cho Shopee scraper để tránh login mỗi lần"""
    
    def __init__(self, account_name: str = "default"):
        """
        Initialize cookie manager
        
        Args:
            account_name: Tên account để lưu cookies riêng biệt (cho rotation)
        """
        self.account_name = account_name
        
        # Tạo thư mục lưu cookies
        self.cookies_dir = Path("data/cookies")
        self.cookies_dir.mkdir(parents=True, exist_ok=True)
        
        self.cookie_file = self.cookies_dir / f"shopee_{account_name}.json"
        logger.info(f"Cookie file: {self.cookie_file}")
    
    def save_cookies(self, cookies: List[Dict]) -> None:
        """
        Lưu cookies vào file
        
        Args:
            cookies: List cookies từ Selenium driver.get_cookies()
        """
        cookie_data = {
            "cookies": cookies,
            "timestamp": time.time(),
            "account": self.account_name
        }
        
        try:
            with open(self.cookie_file, "w", encoding="utf-8") as f:
                json.dump(cookie_data, f, indent=2)
            logger.info(f"✅ Saved {len(cookies)} cookies for account '{self.account_name}'")
            print(f"[COOKIE MANAGER] ✅ Saved {len(cookies)} cookies")
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")
            print(f"[COOKIE MANAGER] ❌ Failed to save cookies: {e}")
    
    def load_cookies(self) -> Optional[List[Dict]]:
        """
        Load cookies từ file
        
        Returns:
            List cookies hoặc None nếu không có/hết hạn
        """
        if not self.cookie_file.exists():
            logger.info("No cookie file found")
            print("[COOKIE MANAGER] 📂 No saved cookies found")
            return None
        
        try:
            with open(self.cookie_file, "r", encoding="utf-8") as f:
                cookie_data = json.load(f)
            
            cookies = cookie_data.get("cookies", [])
            timestamp = cookie_data.get("timestamp", 0)
            
            # Kiểm tra tuổi của cookies (Shopee cookies thường sống 7-30 ngày)
            age_hours = (time.time() - timestamp) / 3600
            
            if age_hours > 24 * 7:  # 7 ngày
                logger.warning(f"Cookies are {age_hours:.1f} hours old, might be expired")
                print(f"[COOKIE MANAGER] ⚠️  Cookies are {age_hours:.1f} hours old")
                return None
            
            logger.info(f"✅ Loaded {len(cookies)} cookies (age: {age_hours:.1f} hours)")
            print(f"[COOKIE MANAGER] ✅ Loaded {len(cookies)} cookies ({age_hours:.1f}h old)")
            return cookies
            
        except Exception as e:
            logger.error(f"Failed to load cookies: {e}")
            print(f"[COOKIE MANAGER] ❌ Failed to load cookies: {e}")
            return None
    
    def is_valid(self) -> bool:
        """
        Kiểm tra xem có cookies valid không
        
        Returns:
            True nếu có cookies và chưa quá cũ
        """
        cookies = self.load_cookies()
        return cookies is not None and len(cookies) > 0
    
    def clear_cookies(self) -> None:
        """Xóa cookies đã lưu"""
        if self.cookie_file.exists():
            self.cookie_file.unlink()
            logger.info("Cookies cleared")
            print("[COOKIE MANAGER] 🗑️  Cookies cleared")


class CookieRotator:
    """Rotate giữa nhiều accounts để tránh rate limiting"""
    
    def __init__(self, accounts: List[str] = None):
        """
        Initialize cookie rotator
        
        Args:
            accounts: List tên accounts (default: ["default"])
        """
        if accounts is None:
            accounts = ["default"]
        
        self.accounts = accounts
        self.current_index = 0
        self.managers = {
            account: CookieManager(account) 
            for account in accounts
        }
        logger.info(f"Initialized cookie rotator with {len(accounts)} accounts")
    
    def get_next_manager(self) -> CookieManager:
        """
        Lấy cookie manager tiếp theo (round-robin)
        
        Returns:
            CookieManager instance
        """
        manager = self.managers[self.accounts[self.current_index]]
        
        # Rotate to next account
        self.current_index = (self.current_index + 1) % len(self.accounts)
        
        logger.debug(f"Using account: {manager.account_name}")
        return manager
    
    def get_valid_manager(self) -> Optional[CookieManager]:
        """
        Tìm manager có cookies valid
        
        Returns:
            CookieManager có cookies valid, hoặc None
        """
        for account in self.accounts:
            manager = self.managers[account]
            if manager.is_valid():
                logger.info(f"Found valid cookies for account: {account}")
                return manager
        
        logger.warning("No valid cookies found in any account")
        return None
