from typing import List
import logging

from schemas.product_crawler import CrawledProductItemExtended
from schemas.product_filter import ProductFilterCriteria

logger = logging.getLogger(__name__)


class ProductFilterService:
    """Filter products based on criteria"""
    
    def filter_products(
        self,
        products: List[CrawledProductItemExtended],
        criteria: ProductFilterCriteria
    ) -> List[CrawledProductItemExtended]:
        """Filter products based on criteria"""
        
        filtered = []
        
        for product in products:
            if self._matches_criteria(product, criteria):
                filtered.append(product)
        
        return filtered
    
    def _matches_criteria(
        self,
        product: CrawledProductItemExtended,
        criteria: ProductFilterCriteria
    ) -> bool:
        """Check if product matches all criteria"""
        
        # Rating filter
        if criteria.min_rating is not None:
            if product.rating_score is None or product.rating_score < criteria.min_rating:
                return False
        if criteria.max_rating is not None:
            if product.rating_score is not None and product.rating_score > criteria.max_rating:
                return False
        
        if criteria.min_review_count is not None:
            if product.review_count is None or product.review_count < criteria.min_review_count:
                return False
        if criteria.max_review_count is not None:
            if product.review_count is not None and product.review_count > criteria.max_review_count:
                return False
        
        # Price filter
        if criteria.min_price is not None:
            if product.price_current < criteria.min_price:
                return False
        if criteria.max_price is not None:
            if product.price_current > criteria.max_price:
                return False
        
        # Platform filter
        if criteria.platforms is not None:
            if product.platform not in criteria.platforms:
                return False
        
        # Mall filter
        if criteria.is_mall is not None:
            if product.is_mall != criteria.is_mall:
                return False
        
        # Verified seller filter
        if criteria.is_verified_seller is not None:
            if product.is_verified_seller != criteria.is_verified_seller:
                return False
        
        # Required keywords filter
        if criteria.required_keywords is not None:
            product_name_lower = product.product_name.lower()
            if not all(keyword.lower() in product_name_lower for keyword in criteria.required_keywords):
                return False
        
        # Excluded keywords filter
        if criteria.excluded_keywords is not None:
            product_name_lower = product.product_name.lower()
            if any(keyword.lower() in product_name_lower for keyword in criteria.excluded_keywords):
                return False
        
        # Sales count filter
        if criteria.min_sales_count is not None:
            if product.sales_count is None or product.sales_count < criteria.min_sales_count:
                return False
        
        # Trust score filter
        if criteria.min_trust_score is not None:
            if product.trust_score is None or product.trust_score < criteria.min_trust_score:
                return False
        
        # Trust badge filter
        if criteria.trust_badge_types is not None:
            if product.trust_badge_type is None or product.trust_badge_type not in criteria.trust_badge_types:
                return False
        
        # Required brands filter
        if criteria.required_brands is not None:
            if product.brand is None or product.brand not in criteria.required_brands:
                return False
        
        # Excluded brands filter
        if criteria.excluded_brands is not None:
            if product.brand is not None and product.brand in criteria.excluded_brands:
                return False
        
        # Seller location filter
        if criteria.seller_locations is not None:
            if product.seller_location is None or product.seller_location not in criteria.seller_locations:
                return False
        
        return True

