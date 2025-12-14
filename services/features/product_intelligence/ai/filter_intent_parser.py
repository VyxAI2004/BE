import json
import logging
from typing import Optional, Tuple
from pydantic import ValidationError

from core.llm.base import BaseAgent
from core.llm.utils import safe_json_parse
from schemas.product_filter import ProductFilterCriteria

logger = logging.getLogger(__name__)


class FilterIntentParser:
    """Parse natural language user input into structured filter criteria"""
    
    def __init__(self, llm_agent: BaseAgent):
        self.llm = llm_agent
    
    def parse_user_intent(self, user_text: str) -> Tuple[Optional[ProductFilterCriteria], Optional[str]]:
        """
        Parse user text input into filter criteria
        
        Returns:
            (filter_criteria, error_message)
            - If parsing successful: (ProductFilterCriteria, None)
            - If parsing failed: (None, error_message)
        """
        
        prompt = f"""
Bạn là một AI chuyên phân tích yêu cầu lọc sản phẩm từ người dùng.

Nhiệm vụ: Phân tích đoạn text sau và trích xuất các tiêu chí lọc sản phẩm thành JSON format.

Input từ người dùng:
"{user_text}"

Hãy trích xuất các thông tin sau (nếu có):
- min_rating: Điểm đánh giá tối thiểu (0-5)
- max_rating: Điểm đánh giá tối đa (0-5)
- min_review_count: Số lượng review tối thiểu
- max_review_count: Số lượng review tối đa
- min_price: Giá tối thiểu (VND)
- max_price: Giá tối đa (VND)
- platforms: Danh sách platform (shopee, lazada, tiki)
- is_mall: Chỉ lấy sản phẩm từ mall (true/false)
- is_verified_seller: Chỉ lấy từ seller đã xác thực (true/false)
- required_keywords: Từ khóa bắt buộc có trong tên sản phẩm
- excluded_keywords: Từ khóa cần loại trừ
- min_sales_count: Số lượng bán tối thiểu
- min_trust_score: Điểm tin cậy tối thiểu (0-100)
- trust_badge_types: Loại trust badge (TikiNOW, Yêu thích, etc.)
- required_brands: Thương hiệu bắt buộc
- excluded_brands: Thương hiệu loại trừ
- seller_locations: Vị trí người bán

Lưu ý:
- Chỉ trả về các trường có trong input, không tự thêm
- Nếu không có thông tin, để null
- Giá tiền: chuyển đổi sang VND (ví dụ: 500k = 500000)
- Rating: chuyển đổi sang số thập phân (ví dụ: "4.5 trở lên" = min_rating: 4.5)

Trả về JSON format:
{{
    "min_rating": null,
    "max_rating": null,
    "min_review_count": null,
    "max_review_count": null,
    "min_price": null,
    "max_price": null,
    "platforms": null,
    "is_mall": null,
    "is_verified_seller": null,
    "required_keywords": null,
    "excluded_keywords": null,
    "min_sales_count": null,
    "min_trust_score": null,
    "trust_badge_types": null,
    "required_brands": null,
    "excluded_brands": null,
    "seller_locations": null
}}
"""
        
        try:
            response = self.llm.generate(
                prompt=prompt,
                json_mode=True,
                timeout=30.0
            )
            
            parsed_data = safe_json_parse(response.text)
            
            if not parsed_data:
                return None, "Không thể parse JSON từ AI response"
            
            # Create ProductFilterCriteria from parsed data
            criteria = ProductFilterCriteria(**parsed_data)
            
            # Validate criteria makes sense
            validation_error = self._validate_criteria(criteria)
            if validation_error:
                return None, validation_error
            
            return criteria, None
            
        except ValidationError as e:
            logger.error(f"Validation error parsing criteria: {str(e)}")
            return None, f"Invalid criteria format: {str(e)}"
        except Exception as e:
            logger.error(f"Failed to parse intent: {str(e)}", exc_info=True)
            return None, f"Failed to parse intent: {str(e)}"
    
    def _validate_criteria(self, criteria: ProductFilterCriteria) -> Optional[str]:
        """Validate that criteria makes logical sense"""
        
        # Check rating range
        if criteria.min_rating is not None and criteria.max_rating is not None:
            if criteria.min_rating > criteria.max_rating:
                return "min_rating cannot be greater than max_rating"
        
        # Check price range
        if criteria.min_price is not None and criteria.max_price is not None:
            if criteria.min_price > criteria.max_price:
                return "min_price cannot be greater than max_price"
        
        # Check review count range
        if criteria.min_review_count is not None and criteria.max_review_count is not None:
            if criteria.min_review_count > criteria.max_review_count:
                return "min_review_count cannot be greater than max_review_count"
        
        return None

