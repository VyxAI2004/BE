import logging
from typing import List, Optional

from core.llm.base import BaseAgent
from core.llm.utils import safe_json_parse
from schemas.product_crawler import CrawledProductItemExtended

logger = logging.getLogger(__name__)


class ProductRankingService:
    """AI service to rank and select best products from filtered list"""
    
    def __init__(self, llm_agent: BaseAgent):
        self.llm = llm_agent
    
    def rank_and_select_products(
        self,
        products: List[CrawledProductItemExtended],
        user_query: str,
        filter_criteria: Optional[dict] = None,
        limit: int = 10
    ) -> List[CrawledProductItemExtended]:
        """
        Use AI to rank products and select the best ones
        
        Args:
            products: List of filtered products
            user_query: Original search query
            filter_criteria: Filter criteria that was applied
            limit: Maximum number of products to return
        
        Returns:
            List of top-ranked products
        """
        
        if not products:
            return []
        
        if len(products) <= limit:
            # If already within limit, return as is
            return products
        
        # Create products summary for AI
        products_summary = self._create_products_summary(products)
        
        # Build prompt
        prompt = self._build_ranking_prompt(
            products_summary=products_summary,
            total_count=len(products),
            limit=limit,
            user_query=user_query,
            filter_criteria=filter_criteria
        )
        
        try:
            response = self.llm.generate(
                prompt=prompt,
                json_mode=True,
                timeout=60.0
            )
            
            ranking_result = safe_json_parse(response.text)
            
            if not ranking_result:
                logger.warning("Failed to parse ranking result, using original order")
                return products[:limit]
            
            # Extract selected product URLs/names
            selected_products = ranking_result.get("top_products", [])
            
            if not selected_products:
                logger.warning("No products selected by AI, using original order")
                return products[:limit]
            
            # Map AI selection back to original products
            ranked_products = self._map_ai_selection_to_products(
                selected_products,
                products
            )
            
            logger.info(f"AI ranked and selected {len(ranked_products)} products from {len(products)} candidates")
            return ranked_products[:limit]
            
        except Exception as e:
            logger.error(f"AI ranking failed: {str(e)}", exc_info=True)
            # Fallback: return first N products
            return products[:limit]
    
    def _create_products_summary(self, products: List[CrawledProductItemExtended]) -> str:
        """Create a summary string of products for AI prompt"""
        
        summary_lines = []
        for idx, product in enumerate(products, 1):
            rating_str = f"{product.rating_score:.1f}" if product.rating_score else "N/A"
            review_str = f"{product.review_count}" if product.review_count else "N/A"
            sales_str = f"{product.sales_count:,}" if product.sales_count else "N/A"
            mall_str = "Mall" if product.is_mall else "Thường"
            
            line = (
                f"{idx}. {product.product_name}\n"
                f"   - Giá: {product.price_current:,.0f} VND\n"
                f"   - Rating: {rating_str}/5.0\n"
                f"   - Reviews: {review_str}\n"
                f"   - Đã bán: {sales_str}\n"
                f"   - Platform: {product.platform}\n"
                f"   - Loại: {mall_str}\n"
            )
            
            if product.brand:
                line += f"   - Thương hiệu: {product.brand}\n"
            
            if product.trust_score:
                line += f"   - Trust Score: {product.trust_score:.1f}/100\n"
            
            line += f"   - URL: {product.product_url}\n"
            
            summary_lines.append(line)
        
        return "\n".join(summary_lines)
    
    def _build_ranking_prompt(
        self,
        products_summary: str,
        total_count: int,
        limit: int,
        user_query: str,
        filter_criteria: Optional[dict]
    ) -> str:
        """Build prompt for AI ranking"""
        
        criteria_text = ""
        if filter_criteria:
            criteria_parts = []
            if filter_criteria.get("min_rating"):
                criteria_parts.append(f"Rating tối thiểu: {filter_criteria['min_rating']}")
            if filter_criteria.get("max_price"):
                criteria_parts.append(f"Giá tối đa: {filter_criteria['max_price']:,.0f} VND")
            if filter_criteria.get("is_mall"):
                criteria_parts.append("Chỉ sản phẩm Mall")
            if filter_criteria.get("required_keywords"):
                criteria_parts.append(f"Từ khóa: {', '.join(filter_criteria['required_keywords'])}")
            
            if criteria_parts:
                criteria_text = f"\nTiêu chí lọc đã áp dụng:\n" + "\n".join(f"- {p}" for p in criteria_parts)
        
        prompt = f"""
Bạn là chuyên gia đánh giá và lựa chọn sản phẩm thông minh.

Nhiệm vụ: Từ danh sách {total_count} sản phẩm đã được lọc, hãy chọn ra TOP {limit} sản phẩm TỐT NHẤT.

Thông tin tìm kiếm:
- Từ khóa: "{user_query}"
{criteria_text}

Danh sách {total_count} sản phẩm đã lọc:
{products_summary}

Hãy đánh giá và chọn TOP {limit} sản phẩm dựa trên:
1. **Chất lượng tổng thể**: Rating cao, nhiều reviews tích cực
2. **Độ tin cậy**: Trust score cao, Mall seller, thương hiệu uy tín
3. **Giá trị**: Giá hợp lý so với chất lượng
4. **Độ phổ biến**: Đã bán được nhiều (sales count cao)
5. **Phù hợp với yêu cầu**: Match với từ khóa và tiêu chí

Trả về JSON format:
{{
    "analysis": "Phân tích ngắn gọn về các sản phẩm được chọn và lý do",
    "top_products": [
        {{
            "product_name": "Tên sản phẩm chính xác từ danh sách",
            "product_url": "URL chính xác từ danh sách",
            "reason": "Lý do chọn sản phẩm này"
        }}
    ]
}}

Lưu ý:
- Chỉ chọn sản phẩm từ danh sách trên, không tự thêm
- product_name và product_url phải CHÍNH XÁC khớp với danh sách
- Ưu tiên chất lượng và độ tin cậy hơn giá rẻ
"""
        
        return prompt
    
    def _map_ai_selection_to_products(
        self,
        ai_selected: List[dict],
        original_products: List[CrawledProductItemExtended]
    ) -> List[CrawledProductItemExtended]:
        """Map AI selected products back to original product objects"""
        
        ranked_products = []
        
        # Create lookup by URL (most reliable)
        products_by_url = {p.product_url: p for p in original_products}
        
        # Create lookup by name (fallback)
        products_by_name = {}
        for p in original_products:
            name_lower = p.product_name.lower().strip()
            if name_lower not in products_by_name:
                products_by_name[name_lower] = p
        
        for selected in ai_selected:
            product = None
            
            # Try to match by URL first
            url = selected.get("product_url", "").strip()
            if url and url in products_by_url:
                product = products_by_url[url]
            
            # Fallback: match by name
            if not product:
                name = selected.get("product_name", "").strip().lower()
                if name in products_by_name:
                    product = products_by_name[name]
            
            # Try fuzzy match by name
            if not product:
                name = selected.get("product_name", "").strip().lower()
                for orig_product in original_products:
                    orig_name = orig_product.product_name.lower().strip()
                    # Check if names are similar (contains or similar)
                    if name in orig_name or orig_name in name:
                        product = orig_product
                        break
            
            if product:
                ranked_products.append(product)
            else:
                logger.warning(f"Could not map AI selected product: {selected.get('product_name')}")
        
        return ranked_products

