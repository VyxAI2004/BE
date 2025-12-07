from uuid import UUID, uuid4
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from services.features.product_intelligence.crawler.scraper_factory import ScraperFactory
from repositories.product import ProductRepository
from repositories.product_review import ProductReviewRepository
from schemas.product import ProductCreate, ProductUpdate
from schemas.product_review import ProductReviewCreate
from models.product import Product, ProductReview

logger = logging.getLogger(__name__)

class CrawlerService:
    def __init__(self, db: Session):
        self.db = db
        self.product_repo = ProductRepository(Product, db)
        self.review_repo = ProductReviewRepository(ProductReview, db)
        pass

    def crawl_search_page(self, project_id: UUID, search_url: str, max_products: int = 10) -> List[str]:
        """
        Step 1: Crawl product list from search page.
        Returns list of product URLs found (no DB operations).
        Note: Products are not saved to DB. Use POST /products to save products.
        """
        logger.info(f"Starting search crawl for project {project_id} with URL {search_url}")
        
        # Determine platform and scraper
        scraper = ScraperFactory.get_scraper(search_url)

        # 1. Crawl data (no DB operations)
        logger.info(f"Calling scraper.crawl_search_results with URL: {search_url}, max_products: {max_products}")
        crawled_products = scraper.crawl_search_results(search_url, max_products)
        
        logger.info(f"Scraper returned {len(crawled_products) if crawled_products else 0} products")
        
        if not crawled_products:
            logger.warning("No products found in search. Scraper returned empty list.")
            return []

        # Collect URLs only (no DB save)
        product_urls = []
        for idx, prod_data in enumerate(crawled_products, 1):
            if prod_data.link:
                product_urls.append(prod_data.link)
                logger.debug(f"  Product {idx}: {prod_data.name[:50] if prod_data.name else 'Unknown'} -> {prod_data.link}")
            else:
                logger.warning(f"  Product {idx} has no link, skipping")

        logger.info(f"Search crawl completed. Crawled: {len(crawled_products)}, URLs: {len(product_urls)}")
        
        if not product_urls:
            logger.warning(f"⚠️ No product URLs collected! Crawled products: {len(crawled_products)}")
            if crawled_products:
                logger.warning("Products were crawled but no URLs were collected. Checking product links...")
                for idx, prod in enumerate(crawled_products[:5], 1):  # Log first 5
                    logger.warning(f"  Product {idx}: name={prod.name[:50] if prod.name else 'None'}, link={prod.link if prod.link else 'MISSING'}")
        
        return product_urls

    def crawl_product_reviews(self, product_id: UUID, review_limit: int = 30):
        """
        Step 2: Crawl details and reviews for a specific product.
        """
        logger.info(f"Starting review crawl for product {product_id}")
        
        # 1. Get product from DB
        product = self.product_repo.get(product_id)
        if not product:
            return {"status": "failed", "message": "Product not found"}
            
        if not product.url:
            return {"status": "failed", "message": "Product has no URL"}

        # 2. Crawl details
        scraper = ScraperFactory.get_scraper(product.platform or product.url)
            
        details = scraper.crawl_product_details(product.url, review_limit)
        
        # 3. Update Product details
        update_data = ProductUpdate(
            specifications={
                "category": details.category,
                "description": details.description,
                "detailed_rating": details.detailed_rating
            }
        )
        self.product_repo.update(db_obj=product, obj_in=update_data)

        # 4. Save Reviews
        comments = details.comments
        # Use existing session ID if available, otherwise None. Do NOT generate fake UUID.
        crawl_session_id = product.crawl_session_id
        
        review_creates = []
        for comment in comments:
            # Parse rating
            rating = comment.rating
            if not isinstance(rating, int):
                try:
                    rating = int(float(rating))
                except:
                    rating = 5
            rating = max(1, min(5, rating))
            
            review_in = ProductReviewCreate(
                product_id=product.id,
                reviewer_name=comment.author[:200],
                rating=rating,
                content=comment.content,
                review_date=None, 
                platform=product.platform or "shopee",
                crawl_session_id=crawl_session_id,
                helpful_count=comment.helpful_count,
                raw_data=comment.model_dump()
            )
            review_creates.append(review_in)
        
        saved_reviews_count = 0
        if review_creates:
            try:
                self.review_repo.bulk_create(review_creates)
                saved_reviews_count = len(review_creates)
            except Exception as e:
                logger.error(f"Failed to save reviews for product {product.id}: {e}")

        return {
            "product_id": product_id,
            "reviews_crawled": saved_reviews_count,
            "status": "completed"
        }
