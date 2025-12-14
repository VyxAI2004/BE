import logging
from uuid import UUID
from typing import List, Optional

from sqlalchemy.orm import Session

from schemas.product_crawler import CrawledProductItemExtended
from schemas.product import ProductCreate
from services.core.product import ProductService
from repositories.product import ProductRepository
from models.product import Product

logger = logging.getLogger(__name__)


class AutoImportService:
    """Automatically import filtered products to database"""
    
    def __init__(self, db: Session):
        self.db = db
        self.product_service = ProductService(db)
        self.product_repo = ProductRepository(Product, db)
    
    def import_products(
        self,
        products: List[CrawledProductItemExtended],
        project_id: UUID,
        user_id: UUID,
        crawl_session_id: Optional[UUID] = None
    ) -> List[UUID]:
        """Import products to database"""
        
        imported_ids = []
        skipped_duplicates = 0
        failed_imports = 0
        
        for product_data in products:
            try:
                # Check for duplicate by URL (within same project)
                cleaned_url = self._clean_url(product_data.product_url)
                existing_products = self.product_repo.get_multi(
                    filters={"project_id": project_id, "url": cleaned_url},
                    limit=1
                )
                
                if existing_products:
                    skipped_duplicates += 1
                    logger.debug(f"Skipping duplicate product: {product_data.product_url}")
                    continue
                
                # Convert crawled data to ProductCreate schema
                product_create = ProductCreate(
                    project_id=project_id,
                    crawl_session_id=crawl_session_id,
                    name=product_data.product_name,
                    brand=product_data.brand,
                    category=product_data.category,
                    subcategory=product_data.subcategory,
                    platform=product_data.platform,
                    url=product_data.product_url,
                    current_price=product_data.price_current,
                    original_price=product_data.price_original,
                    discount_rate=product_data.discount_rate,
                    currency="VND",
                    data_source="auto_crawl"
                )
                
                # Create product
                product = self.product_service.create_product(
                    payload=product_create,
                    user_id=user_id
                )
                
                imported_ids.append(product.id)
                logger.debug(f"Imported product: {product.id} - {product.name}")
                
            except ValueError as e:
                # Permission or validation errors
                failed_imports += 1
                logger.warning(f"Failed to import product {product_data.product_url}: {str(e)}")
                continue
            except Exception as e:
                # Other errors
                failed_imports += 1
                logger.error(f"Failed to import product {product_data.product_url}: {str(e)}", exc_info=True)
                continue
        
        logger.info(
            f"Import completed: {len(imported_ids)} imported, "
            f"{skipped_duplicates} duplicates skipped, "
            f"{failed_imports} failed"
        )
        
        return imported_ids
    
    def _clean_url(self, url: str) -> str:
        """Clean URL for duplicate checking (same as ProductService)"""
        if not url:
            return url
        try:
            if "shopee.vn" in url or "lazada.vn" in url or "tiki.vn" in url:
                if "?" in url:
                    return url.split("?")[0]
        except:
            pass
        return url

