import logging
from typing import Optional, Tuple, Dict, Any
import re

from core.llm.base import BaseAgent
from core.llm.utils import safe_json_parse

logger = logging.getLogger(__name__)


class NaturalLanguageParser:
    """Parse natural language user input into structured components"""
    
    def __init__(self, llm_agent: BaseAgent):
        self.llm = llm_agent
    
    def parse_user_input(
        self,
        user_text: str,
        project_info: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[str]]:
        """
        Parse user natural language input into components
        
        Args:
            user_text: Natural language input from user
            project_info: Optional project information for context
        
        Returns:
            (user_query, filter_criteria, max_products, error_message)
            - If successful: (user_query, filter_criteria, max_products, None)
            - If failed: (None, None, None, error_message)
        """
        
        # Extract comprehensive project context
        project_context = ""
        if project_info:
            project_name = project_info.get('name', 'N/A')
            description = project_info.get('description', 'N/A')
            target_product = project_info.get('target_product_name', 'N/A')
            category = project_info.get('target_product_category', 'N/A')
            budget = project_info.get('target_budget_range')
            currency = project_info.get('currency', 'VND')
            status = project_info.get('status', 'N/A')
            
            budget_text = f"{budget:,.0f} {currency}" if budget else "Không giới hạn"
            
            project_context = f"""
Thông tin project đầy đủ:
- Tên project: {project_name}
- Mô tả project: {description}
- Sản phẩm mục tiêu: {target_product}
- Danh mục sản phẩm: {category if category != 'N/A' else 'Chưa xác định'}
- Ngân sách: {budget_text}
- Trạng thái: {status}

Lưu ý khi parse:
- Nếu user nói "dựa trên project" hoặc "sản phẩm mẫu" → dùng "Sản phẩm mục tiêu" làm user_query
- Nếu user không chỉ định ngân sách → có thể dùng "Ngân sách" từ project làm gợi ý
- Nếu user không chỉ định danh mục → có thể dùng "Danh mục sản phẩm" từ project
- Hiểu context từ "Mô tả project" để parse chính xác hơn
"""
        
        prompt = f"""
Bạn là một AI chuyên phân tích yêu cầu tìm kiếm sản phẩm từ người dùng.

Nhiệm vụ: Phân tích đoạn text sau và trích xuất các thông tin:
1. Từ khóa tìm kiếm (user_query)
2. Tiêu chí lọc (filter_criteria)
3. Số lượng sản phẩm cần (max_products)

{project_context}

Input từ người dùng:
"{user_text}"

Hãy trích xuất:
1. **user_query**: Từ khóa tìm kiếm sản phẩm
   - Ưu tiên: Nếu user nói "dựa trên project", "sản phẩm mẫu", "sản phẩm của project" 
     → dùng "Sản phẩm mục tiêu" từ project (target_product_name)
   - Nếu user chỉ định cụ thể → dùng từ khóa đó
   - Có thể kết hợp với "Danh mục sản phẩm" nếu cần để làm rõ hơn
   - Ví dụ: "cà phê hòa tan", "điện thoại", "laptop"

2. **filter_criteria**: Tiêu chí lọc sản phẩm (nếu có)
   - Rating: "rating 4.5+", "đánh giá trên 4.5"
   - Reviews (ĐÁNH GIÁ): "hơn 100 reviews", "review 100+", "có nhiều đánh giá"
   - Lượt mua (SALES): "hơn 100 lượt mua", "100+ lượt mua", "đã bán 100+"
     * **QUAN TRỌNG**: Phân biệt rõ "lượt mua" (sales) và "review" (đánh giá) - đây là 2 khái niệm KHÁC NHAU
   - Platform: "lazada", "tiki", "shopee" (lưu ý: shopee chưa hỗ trợ)
   - Mall: "mall", "cửa hàng chính hãng"
   - Price: "max price 500000", "giá dưới 500k"
     * Nếu user không chỉ định giá → có thể dùng "Ngân sách" từ project làm max_price
   - Keywords: "chính hãng", "premium", "cao cấp"
   - Category: Nếu user không chỉ định → có thể dùng "Danh mục sản phẩm" từ project
   - Nếu không có tiêu chí → để null

3. **max_products**: Số lượng sản phẩm cần tìm
   - Tìm số trong text: "2 sản phẩm", "5 cái", "10 items"
   - Nếu không có → mặc định 20

Lưu ý quan trọng:
- Ưu tiên thông tin từ user input, nhưng có thể bổ sung từ project nếu hợp lý
- Nếu user nói "dựa trên project" hoặc "sản phẩm mẫu" → BẮT BUỘC dùng thông tin từ project
- Nếu user không chỉ định giá → CÓ THỂ dùng "Ngân sách" từ project làm max_price trong filter_criteria
- Nếu user không chỉ định danh mục → CÓ THỂ dùng "Danh mục sản phẩm" từ project để làm rõ user_query
- Platform shopee chưa hỗ trợ → không thêm vào filter_criteria, suggest lazada/tiki
- Hiểu context từ "Mô tả project" để parse chính xác hơn về mục đích tìm kiếm

Trả về JSON format:
{{
    "user_query": "từ khóa tìm kiếm",
    "filter_criteria": "tiêu chí lọc hoặc null",
    "max_products": số lượng
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
                return None, None, None, "Không thể parse JSON từ AI response"
            
            # Extract components
            user_query = parsed_data.get("user_query")
            filter_criteria = parsed_data.get("filter_criteria")
            max_products = parsed_data.get("max_products", 20)
            
            # Validate
            if not user_query:
                return None, None, None, "Không tìm thấy từ khóa tìm kiếm trong input"
            
            # Ensure max_products is valid
            try:
                max_products = int(max_products)
                if max_products < 1:
                    max_products = 20
                if max_products > 100:
                    max_products = 100
            except (ValueError, TypeError):
                max_products = 20
            
            return user_query, filter_criteria, max_products, None
            
        except Exception as e:
            error_str = str(e)
            logger.error(f"Failed to parse natural language input: {error_str}", exc_info=True)
            
            # Provide user-friendly error messages
            if "503" in error_str or "unavailable" in error_str.lower() or "overloaded" in error_str.lower():
                return None, None, None, "Model đang quá tải. Vui lòng thử lại sau vài giây."
            elif "429" in error_str or "rate limit" in error_str.lower():
                return None, None, None, "Đã vượt quá giới hạn yêu cầu. Vui lòng thử lại sau."
            elif "timeout" in error_str.lower():
                return None, None, None, "Yêu cầu quá thời gian chờ. Vui lòng thử lại."
            else:
                return None, None, None, f"Không thể phân tích yêu cầu: {error_str}"

