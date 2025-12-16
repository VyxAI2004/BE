"""
AI Agent để generate marketing tasks từ product analytics data.
Focus vào research đối thủ và chiến dịch marketing.
"""
import json
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID

from core.llm.base import BaseAgent

logger = logging.getLogger(__name__)


class TaskGenerationAgent:
    """Agent để generate marketing tasks từ analytics data"""

    def __init__(self, llm_agent: BaseAgent):
        self.llm_agent = llm_agent

    def generate_marketing_tasks(
        self,
        product_data: Dict[str, Any],
        analytics_data: Dict[str, Any],
        project_info: Optional[Dict[str, Any]] = None,
        max_tasks: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Generate marketing tasks từ analytics data.
        
        Args:
            product_data: Thông tin sản phẩm (name, brand, category, price, platform, etc.)
            analytics_data: Kết quả phân tích từ ProductAnalyticsService
            project_info: Thông tin project (target_product_name, budget, etc.)
            max_tasks: Số lượng tasks tối đa (default: 5)
        
        Returns:
            List of tasks với format:
            {
                "name": "Task name",
                "description": "Detailed description",
                "task_type": "marketing_research|competitive_analysis|content_strategy|pricing_strategy|market_positioning",
                "priority": "low|medium|high",
                "estimated_hours": float,
                "marketing_focus": "research|strategy|execution|analysis"
            }
        """
        try:
            prompt = self._create_task_generation_prompt(
                product_data=product_data,
                analytics_data=analytics_data,
                project_info=project_info,
                max_tasks=max_tasks,
            )

            logger.info(f"Generating marketing tasks for product: {product_data.get('name')}")
            response = self.llm_agent.generate(
                prompt=prompt,
                json_mode=True,
                timeout=60.0,
            )

            if not response or not hasattr(response, "text") or not response.text:
                logger.error("LLM returned empty response for task generation")
                return self._get_fallback_tasks(product_data, analytics_data)

            # Parse JSON response
            response_text = response.text.strip()
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text
            elif response_text.startswith("```json"):
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text

            try:
                result = json.loads(response_text)
                tasks = result.get("tasks", [])

                # Validate và limit số lượng tasks
                if not isinstance(tasks, list):
                    logger.warning("Tasks is not a list, using fallback")
                    return self._get_fallback_tasks(product_data, analytics_data)

                # Limit to max_tasks
                tasks = tasks[:max_tasks]

                # Validate task structure
                validated_tasks = []
                for task in tasks:
                    if self._validate_task(task):
                        validated_tasks.append(task)
                    else:
                        logger.warning(f"Invalid task structure: {task}")

                if not validated_tasks:
                    logger.warning("No valid tasks generated, using fallback")
                    return self._get_fallback_tasks(product_data, analytics_data)

                logger.info(f"Generated {len(validated_tasks)} marketing tasks")
                return validated_tasks

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                logger.error(f"Raw response (first 500 chars): {response_text[:500]}")
                return self._get_fallback_tasks(product_data, analytics_data)

        except Exception as e:
            logger.error(f"Error generating marketing tasks: {e}", exc_info=True)
            return self._get_fallback_tasks(product_data, analytics_data)

    def _create_task_generation_prompt(
        self,
        product_data: Dict[str, Any],
        analytics_data: Dict[str, Any],
        project_info: Optional[Dict[str, Any]],
        max_tasks: int,
    ) -> str:
        """Tạo prompt cho LLM để generate marketing tasks"""

        analysis = analytics_data.get("analysis", {})
        trust_score_analysis = analysis.get("trust_score_analysis", {})
        review_insights = analysis.get("review_insights", {})
        risk_assessment = analysis.get("risk_assessment", {})

        project_context = ""
        if project_info:
            project_context = f"""
## THÔNG TIN PROJECT:
- Tên project: {project_info.get('name', 'N/A')}
- Sản phẩm mục tiêu: {project_info.get('target_product_name', 'N/A')}
- Ngân sách: {project_info.get('budget', 'N/A')}
- Danh mục: {project_info.get('category', 'N/A')}
"""

        prompt = f"""Bạn là một chuyên gia marketing và nghiên cứu thị trường. 
Nhiệm vụ của bạn là tạo ra các TASK (nhiệm vụ) cụ thể để user có thể research sản phẩm đối thủ và đưa ra chiến dịch marketing hợp lý.

## THÔNG TIN SẢN PHẨM ĐỐI THỦ:
- Tên: {product_data.get('name', 'N/A')}
- Thương hiệu: {product_data.get('brand', 'N/A')}
- Danh mục: {product_data.get('category', 'N/A')}
- Nền tảng: {product_data.get('platform', 'N/A')}
- Giá: {product_data.get('price', 'N/A')} {product_data.get('currency', 'VND')}
- Đánh giá trung bình: {product_data.get('average_rating', 'N/A')}/5
- Trust Score: {analytics_data.get('trust_score', 0):.2f}/100
{project_context}
## PHÂN TÍCH SẢN PHẨM ĐỐI THỦ:

### Trust Score Analysis:
- Interpretation: {trust_score_analysis.get('interpretation', 'N/A')}
- Strengths: {', '.join(trust_score_analysis.get('strengths', []))}
- Weaknesses: {', '.join(trust_score_analysis.get('weaknesses', []))}

### Review Insights:
- Sentiment Overview: {review_insights.get('sentiment_overview', 'N/A')}
- Key Positive Themes: {', '.join(review_insights.get('key_positive_themes', []))}
- Key Negative Themes: {', '.join(review_insights.get('key_negative_themes', []))}
- Spam Concerns: {review_insights.get('spam_concerns', 'N/A')}

### Risk Assessment:
- Overall Risk: {risk_assessment.get('overall_risk', 'N/A')}
- Risk Factors: {', '.join(risk_assessment.get('risk_factors', []))}

### Recommendations từ Analytics:
{chr(10).join('- ' + rec for rec in analysis.get('recommendations', []))}

---

## YÊU CẦU:

Hãy tạo ra TỐI ĐA {max_tasks} TASK (nhiệm vụ) cụ thể, có thể thực hiện được, liên quan đến MARKETING và RESEARCH đối thủ.

Mỗi task phải:
1. **Cụ thể và actionable** - User có thể thực hiện ngay
2. **Liên quan đến marketing** - Research đối thủ, phân tích chiến lược, đề xuất chiến dịch
3. **Dựa trên analytics data** - Sử dụng insights từ trust score, reviews, sentiment
4. **Hướng đến mục tiêu** - Giúp user hiểu đối thủ để đưa ra chiến dịch marketing tốt hơn

### Các loại Task Marketing có thể tạo:

1. **Marketing Research Tasks:**
   - Research đối thủ tương tự với trust score cao hơn/thấp hơn
   - Phân tích điểm mạnh/yếu của đối thủ từ reviews
   - Tìm hiểu chiến lược pricing của đối thủ
   - Research các sản phẩm cùng category có performance tốt

2. **Competitive Analysis Tasks:**
   - So sánh trust score với top 3 đối thủ
   - Phân tích sentiment trends của đối thủ
   - Identify gaps và opportunities so với đối thủ
   - Research marketing messages của đối thủ từ reviews

3. **Content Strategy Tasks:**
   - Phân tích các positive themes để tạo content tương tự
   - Research cách đối thủ xử lý negative feedback
   - Tìm hiểu messaging strategies từ reviews
   - Identify content gaps từ negative themes

4. **Pricing Strategy Tasks:**
   - So sánh giá với đối thủ có trust score tương đương
   - Phân tích value proposition từ reviews
   - Research pricing strategies của đối thủ
   - Đánh giá price-to-trust-score ratio

5. **Market Positioning Tasks:**
   - Xác định vị trí của đối thủ trên thị trường
   - Research target audience từ reviews
   - Phân tích unique selling points của đối thủ
   - Identify positioning opportunities

### Format JSON Response:

{{
  "tasks": [
    {{
      "name": "Tên task ngắn gọn, cụ thể (ví dụ: 'Research 5 sản phẩm đối thủ có trust score > 80')",
      "description": "Mô tả chi tiết task, bao gồm:\n- Mục đích của task\n- Các bước thực hiện cụ thể\n- Dữ liệu cần thu thập\n- Kết quả mong đợi",
      "task_type": "marketing_research|competitive_analysis|content_strategy|pricing_strategy|market_positioning",
      "priority": "low|medium|high",
      "estimated_hours": 2.5,
      "marketing_focus": "research|strategy|execution|analysis",
      "related_insights": ["Các insights từ analytics liên quan đến task này"]
    }}
  ]
}}

### Lưu ý quan trọng:
- Tạo tasks DỰA TRÊN analytics data đã có (trust score, reviews, sentiment)
- Focus vào MARKETING và RESEARCH đối thủ
- Tasks phải actionable và cụ thể
- Ưu tiên tasks có giá trị cao cho chiến dịch marketing
- Sử dụng insights từ weaknesses/strengths để tạo tasks
- Consider risk factors và recommendations

Hãy trả về JSON hợp lệ, không có markdown formatting hay code blocks."""

        return prompt

    def _validate_task(self, task: Dict[str, Any]) -> bool:
        """Validate task structure"""
        required_fields = ["name", "description", "task_type", "priority"]
        for field in required_fields:
            if field not in task:
                return False

        # Validate task_type
        valid_task_types = [
            "marketing_research",
            "competitive_analysis",
            "content_strategy",
            "pricing_strategy",
            "market_positioning",
        ]
        if task.get("task_type") not in valid_task_types:
            return False

        # Validate priority
        valid_priorities = ["low", "medium", "high"]
        if task.get("priority") not in valid_priorities:
            return False

        return True

    def _get_fallback_tasks(
        self, product_data: Dict[str, Any], analytics_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Fallback tasks nếu LLM không generate được"""
        product_name = product_data.get("name", "sản phẩm này")
        trust_score = analytics_data.get("trust_score", 0)

        return [
            {
                "name": f"Research 5 sản phẩm đối thủ tương tự {product_name}",
                "description": f"Tìm kiếm và phân tích 5 sản phẩm đối thủ trong cùng category để so sánh trust score, pricing, và reviews. Trust score hiện tại: {trust_score:.2f}/100",
                "task_type": "marketing_research",
                "priority": "high",
                "estimated_hours": 4.0,
                "marketing_focus": "research",
                "related_insights": ["Trust score analysis"],
            },
            {
                "name": f"Phân tích competitive positioning của {product_name}",
                "description": f"So sánh trust score, sentiment, và reviews của {product_name} với top 3 đối thủ để xác định vị trí trên thị trường",
                "task_type": "competitive_analysis",
                "priority": "high",
                "estimated_hours": 3.0,
                "marketing_focus": "analysis",
                "related_insights": ["Trust score", "Review insights"],
            },
        ]
