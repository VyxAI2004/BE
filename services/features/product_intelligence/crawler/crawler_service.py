from uuid import UUID
from typing import List
from sqlalchemy.orm import Session

from services.features.product_intelligence.crawler.scraper_factory import ScraperFactory
from repositories.product import ProductRepository
from repositories.product_review import ProductReviewRepository
from schemas.product import ProductUpdate
from schemas.product_review import ProductReviewCreate
from schemas.product_crawler import CrawlProductReviewsResponse
from models.product import Product, ProductReview


class CrawlerService:
    def __init__(self, db: Session):
        self.db = db
        self.product_repo = ProductRepository(Product, db)
        self.review_repo = ProductReviewRepository(ProductReview, db)

    def crawl_search_page(
        self,
        project_id: UUID,
        search_url: str,
        max_products: int = 10
    ) -> List[str]:

        scraper = ScraperFactory.get_scraper(search_url)
        crawled_products = scraper.crawl_search_results(
            search_url,
            max_products
        )

        if not crawled_products:
            return []

        product_urls = []
        for prod in crawled_products:
            if prod.link:
                product_urls.append(prod.link)

        return product_urls

    def crawl_product_reviews(
        self,
        product_id: UUID,
        review_limit: int = 30
    ) -> CrawlProductReviewsResponse:

        product = self.product_repo.get(product_id)
        if not product:
            return CrawlProductReviewsResponse(
                status="failed",
                message="Product not found"
            )

        if not product.url:
            return CrawlProductReviewsResponse(
                status="failed",
                message="Product has no URL"
            )

        scraper = ScraperFactory.get_scraper(
            product.platform or product.url
        )

        details = scraper.crawl_product_details(
            product.url,
            review_limit
        )

        update_data = ProductUpdate(
            specifications={
                "category": details.category,
                "description": details.description,
                "detailed_rating": details.detailed_rating,
            }
        )
        self.product_repo.update(
            db_obj=product,
            obj_in=update_data
        )

        comments = details.comments
        crawl_session_id = product.crawl_session_id

        review_creates = []
        for comment in comments:
            rating = comment.rating
            if not isinstance(rating, int):
                try:
                    rating = int(float(rating))
                except Exception:
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
                raw_data=comment.model_dump(),
            )
            review_creates.append(review_in)

        saved_reviews_count = 0
        if review_creates:
            try:
                self.review_repo.bulk_create(review_creates)
                saved_reviews_count = len(review_creates)
            except Exception:
                pass

        return CrawlProductReviewsResponse(
            product_id=product_id,
            reviews_crawled=saved_reviews_count,
            status="completed",
        )
