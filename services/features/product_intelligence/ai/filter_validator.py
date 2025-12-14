import json
import logging
from typing import Optional, Tuple

from core.llm.base import BaseAgent
from core.llm.utils import safe_json_parse
from schemas.product_filter import ProductFilterCriteria

logger = logging.getLogger(__name__)


class FilterCriteriaValidator:
    """Validate extracted criteria using AI to ensure it matches user intent"""
    
    def __init__(self, llm_agent: BaseAgent):
        self.llm = llm_agent
    
    def validate_criteria(
        self, 
        user_text: str, 
        criteria: ProductFilterCriteria
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that extracted criteria matches user intent
        
        Returns:
            (is_valid, error_message)
        """
        
        prompt = f"""
Bạn là một AI validator kiểm tra xem criteria đã được trích xuất có đúng với ý định của người dùng không.

Input từ người dùng:
"{user_text}"

Criteria đã trích xuất:
{json.dumps(criteria.model_dump(exclude_none=True), indent=2, ensure_ascii=False)}

Nhiệm vụ: Kiểm tra xem criteria có phản ánh đúng yêu cầu của người dùng không.

Trả về JSON:
{{
    "is_valid": true/false,
    "reason": "Lý do nếu không hợp lệ"
}}

Nếu criteria không đúng hoặc thiếu thông tin quan trọng, trả về is_valid: false và giải thích lý do.
"""
        
        try:
            response = self.llm.generate(
                prompt=prompt,
                json_mode=True,
                timeout=30.0
            )
            
            result = safe_json_parse(response.text)
            
            if not result:
                return False, "Không thể parse validation response"
            
            is_valid = result.get("is_valid", False)
            reason = result.get("reason")
            
            if not is_valid:
                return False, reason or "AI không hiểu yêu cầu của bạn"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Validation failed: {str(e)}", exc_info=True)
            # If validation fails, assume invalid
            return False, f"Không thể xác thực yêu cầu: {str(e)}"

