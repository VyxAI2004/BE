"""
Service cho Product Analytics - Phân tích LLM dựa trên reviews và trust score.
"""
import json
import logging
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy.orm import Session

from services.core.product import ProductService
from services.core.product_review import ProductReviewService
from services.core.product_trust_score import ProductTrustScoreService
from services.core.review_analysis import ReviewAnalysisService
from services.features.product_intelligence.agents.llm_provider_selector import (
    LLMProviderSelector,
)
from core.llm.base import BaseAgent

logger = logging.getLogger(__name__)


class ProductAnalyticsService:
    """Service để phân tích sản phẩm bằng LLM dựa trên reviews và trust score"""

    def __init__(self, db: Session):
        self.db = db
        self.product_service = ProductService(db)
        self.review_service = ProductReviewService(db)
        self.trust_score_service = ProductTrustScoreService(db)
        self.analysis_service = ReviewAnalysisService(db)
        self.llm_selector = LLMProviderSelector(db)

    def analyze_product(
        self, product_id: UUID, user_id: UUID, project_assigned_model_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Phân tích sản phẩm bằng LLM dựa trên reviews và trust score.
        
        Returns:
            Dict chứa kết quả phân tích từ LLM
        """
        try:
            logger.info(f"Starting analytics for product {product_id}, user {user_id}")
            
            # 1. Lấy thông tin sản phẩm
            product = self.product_service.get(product_id)
            if not product:
                raise ValueError(f"Product {product_id} not found")
            logger.info(f"Product found: {product.name}")

            # 2. Lấy trust score detail
            trust_score_detail = self.trust_score_service.get_trust_score_detail(product_id)
            if not trust_score_detail:
                raise ValueError(
                    f"Trust score not calculated for product {product_id}. Please calculate trust score first."
                )
            logger.info(f"Trust score found: {trust_score_detail.trust_score}")

            # 3. Lấy reviews và analysis (lấy top reviews để phân tích)
            reviews, total_reviews = self.review_service.get_product_reviews(
                product_id=product_id, skip=0, limit=50, include_analysis=True
            )
            logger.info(f"Found {total_reviews} total reviews, fetched {len(reviews)} for analysis")

            if total_reviews == 0:
                raise ValueError(f"Product {product_id} has no reviews")

            # 4. Lấy review statistics
            review_stats = self.review_service.get_review_statistics(product_id)
            analysis_stats = self.analysis_service.get_statistics(product_id)
            logger.info(f"Review stats: {review_stats.get('total_reviews')} reviews, avg rating: {review_stats.get('average_rating')}")
        except ValueError:
            # Re-raise ValueError as-is
            raise
        except Exception as e:
            logger.error(f"Error preparing data for analytics (product {product_id}): {e}", exc_info=True)
            raise ValueError(f"Failed to prepare analytics data: {str(e)}")

        # 5. Chuẩn bị dữ liệu cho LLM
        product_data = {
            "name": product.name,
            "brand": product.brand,
            "category": product.category,
            "platform": product.platform,
            "price": float(product.current_price) if product.current_price else None,
            "currency": product.currency or "VND",
            "average_rating": float(product.average_rating) if product.average_rating else None,
        }

        trust_score_data = {
            "trust_score": trust_score_detail.trust_score,
            "total_reviews": trust_score_detail.total_reviews,
            "analyzed_reviews": trust_score_detail.analyzed_reviews,
            "breakdown": {
                k: {
                    "factor": float(v.factor),
                    "weight": float(v.weight),
                    "contribution": float(v.contribution),
                    "details": v.details,
                }
                for k, v in trust_score_detail.breakdown.items()
            },
        }

        # Lấy sample reviews (top positive, negative, và neutral)
        sample_reviews = self._get_sample_reviews(reviews)

        # 6. Tạo prompt cho LLM
        prompt = self._create_analysis_prompt(
            product_data=product_data,
            trust_score_data=trust_score_data,
            review_stats=review_stats,
            analysis_stats=analysis_stats,
            sample_reviews=sample_reviews,
        )

        # 7. Gọi LLM
        try:
            llm_agent = self.llm_selector.select_agent(
                user_id=user_id, project_assigned_model_id=project_assigned_model_id
            )
            logger.info(f"Using LLM agent: {llm_agent.model_name()} for product {product_id}")
        except Exception as e:
            logger.error(f"Failed to select LLM agent for product {product_id}: {e}")
            raise ValueError(f"Failed to initialize LLM agent: {str(e)}")

        try:
            logger.info(f"Calling LLM for product {product_id}...")
            response = llm_agent.generate(
                prompt=prompt,
                json_mode=True,
                timeout=60.0,
            )

            if not response or not hasattr(response, 'text') or not response.text:
                logger.error(f"LLM returned empty response for product {product_id}")
                raise ValueError("LLM returned empty response")

            logger.info(f"LLM response received for product {product_id}, length: {len(response.text)}")

            # Parse JSON response
            try:
                # Try to extract JSON if wrapped in markdown code blocks
                response_text = response.text.strip()
                if response_text.startswith("```"):
                    # Remove markdown code blocks
                    lines = response_text.split("\n")
                    response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text
                elif response_text.startswith("```json"):
                    lines = response_text.split("\n")
                    response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text
                
                analysis_result = json.loads(response_text)
                
                # Validate required fields
                required_fields = ["summary", "trust_score_analysis", "review_insights", "recommendations", "risk_assessment"]
                missing_fields = [field for field in required_fields if field not in analysis_result]
                if missing_fields:
                    logger.warning(f"LLM response missing fields: {missing_fields} for product {product_id}")
                    # Fill missing fields with defaults
                    if "summary" not in analysis_result:
                        analysis_result["summary"] = "Không thể tạo tóm tắt."
                    if "trust_score_analysis" not in analysis_result:
                        analysis_result["trust_score_analysis"] = {
                            "interpretation": "Không thể phân tích trust score.",
                            "strengths": [],
                            "weaknesses": []
                        }
                    if "review_insights" not in analysis_result:
                        analysis_result["review_insights"] = {
                            "sentiment_overview": "Không thể phân tích sentiment.",
                            "key_positive_themes": [],
                            "key_negative_themes": [],
                            "spam_concerns": "Không thể đánh giá spam."
                        }
                    if "recommendations" not in analysis_result:
                        analysis_result["recommendations"] = []
                    if "risk_assessment" not in analysis_result:
                        analysis_result["risk_assessment"] = {
                            "overall_risk": "medium",
                            "risk_factors": [],
                            "confidence_level": "Thấp"
                        }

                return {
                    "product_id": str(product_id),
                    "analysis": analysis_result,
                    "metadata": {
                        "model_used": llm_agent.model_name(),
                        "total_reviews_analyzed": total_reviews,
                        "sample_reviews_count": len(sample_reviews),
                    },
                }
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON for product {product_id}: {e}")
                logger.error(f"Raw response (first 500 chars): {response.text[:500]}")
                # Fallback: return structured response with raw text
                return {
                    "product_id": str(product_id),
                    "analysis": {
                        "summary": response.text[:500] if len(response.text) > 500 else response.text,
                        "trust_score_analysis": {
                            "interpretation": "Không thể parse JSON từ LLM response.",
                            "strengths": [],
                            "weaknesses": []
                        },
                        "review_insights": {
                            "sentiment_overview": "Không thể phân tích do lỗi parse JSON.",
                            "key_positive_themes": [],
                            "key_negative_themes": [],
                            "spam_concerns": "Không thể đánh giá."
                        },
                        "recommendations": ["Vui lòng thử lại sau."],
                        "risk_assessment": {
                            "overall_risk": "medium",
                            "risk_factors": ["Lỗi parse JSON từ LLM"],
                            "confidence_level": "Thấp - có lỗi xảy ra"
                        }
                    },
                    "metadata": {
                        "model_used": llm_agent.model_name(),
                        "total_reviews_analyzed": total_reviews,
                        "sample_reviews_count": len(sample_reviews),
                        "error": "Failed to parse JSON response",
                    },
                }
        except Exception as e:
            logger.error(f"Error calling LLM for product {product_id}: {e}", exc_info=True)
            raise ValueError(f"LLM analysis failed: {str(e)}")

    def _get_sample_reviews(self, reviews: List) -> List[Dict[str, Any]]:
        """Lấy sample reviews (positive, negative, neutral)"""
        sample_reviews = []
        
        # Phân loại reviews
        positive_reviews = []
        negative_reviews = []
        neutral_reviews = []

        for review in reviews:
            if not hasattr(review, "analysis") or not review.analysis:
                continue

            analysis = review.analysis
            review_data = {
                "rating": review.rating,
                "content": review.content[:500] if review.content else "",  # Limit length
                "sentiment": analysis.sentiment_label,
                "sentiment_score": float(analysis.sentiment_score),
                "is_spam": analysis.is_spam,
                "verified_purchase": review.is_verified_purchase,
            }

            if analysis.sentiment_label == "positive":
                positive_reviews.append(review_data)
            elif analysis.sentiment_label == "negative":
                negative_reviews.append(review_data)
            else:
                neutral_reviews.append(review_data)

        # Lấy top 3 mỗi loại
        sample_reviews.extend(positive_reviews[:3])
        sample_reviews.extend(negative_reviews[:3])
        sample_reviews.extend(neutral_reviews[:2])

        return sample_reviews

    def _create_analysis_prompt(
        self,
        product_data: Dict[str, Any],
        trust_score_data: Dict[str, Any],
        review_stats: Dict[str, Any],
        analysis_stats: Dict[str, Any],
        sample_reviews: List[Dict[str, Any]],
    ) -> str:
        """Tạo prompt cho LLM phân tích"""

        prompt = f"""Bạn là một chuyên gia phân tích sản phẩm và đánh giá khách hàng. 
Hãy phân tích sản phẩm dựa trên dữ liệu trust score và reviews được cung cấp.

## THÔNG TIN SẢN PHẨM:
- Tên: {product_data.get('name', 'N/A')}
- Thương hiệu: {product_data.get('brand', 'N/A')}
- Danh mục: {product_data.get('category', 'N/A')}
- Nền tảng: {product_data.get('platform', 'N/A')}
- Giá: {product_data.get('price', 'N/A')} {product_data.get('currency', 'VND')}
- Đánh giá trung bình: {product_data.get('average_rating', 'N/A')}/5

## TRUST SCORE:
- Trust Score: {trust_score_data.get('trust_score', 0):.2f}/100
- Tổng số reviews: {trust_score_data.get('total_reviews', 0)}
- Reviews đã phân tích: {trust_score_data.get('analyzed_reviews', 0)}

### Phân tích chi tiết Trust Score:
"""

        # Thêm breakdown
        breakdown = trust_score_data.get("breakdown", {})
        for component, data in breakdown.items():
            prompt += f"""
- {component.upper()}:
  + Factor: {data.get('factor', 0):.4f}
  + Weight: {data.get('weight', 0):.4f}
  + Contribution: {data.get('contribution', 0):.2f}%
  + Chi tiết: {json.dumps(data.get('details', {}), ensure_ascii=False, indent=2)}
"""

        prompt += f"""
## THỐNG KÊ REVIEWS:
- Tổng số reviews: {review_stats.get('total_reviews', 0)}
- Reviews đã xác thực mua hàng: {review_stats.get('verified_purchases', 0)}
- Đánh giá trung bình: {review_stats.get('average_rating', 0):.2f}/5
- Phân bố rating: {json.dumps(review_stats.get('rating_distribution', {}), ensure_ascii=False)}

## PHÂN TÍCH SENTIMENT & SPAM:
- Reviews tích cực: {analysis_stats.get('sentiment_counts', {}).get('positive', 0)}
- Reviews tiêu cực: {analysis_stats.get('sentiment_counts', {}).get('negative', 0)}
- Reviews trung lập: {analysis_stats.get('sentiment_counts', {}).get('neutral', 0)}
- Reviews spam: {analysis_stats.get('spam_count', 0)} ({analysis_stats.get('spam_percentage', 0):.2f}%)
- Điểm sentiment trung bình: {analysis_stats.get('average_sentiment_score', 0):.4f}

## SAMPLE REVIEWS:
{json.dumps(sample_reviews, ensure_ascii=False, indent=2)}

---

## YÊU CẦU PHÂN TÍCH:

Hãy phân tích và trả về kết quả dưới dạng JSON với cấu trúc sau:

{{
  "summary": "Tóm tắt tổng quan về sản phẩm dựa trên trust score và reviews (2-3 câu)",
  "trust_score_analysis": {{
    "interpretation": "Giải thích ý nghĩa của trust score này (cao/trung bình/thấp) và các yếu tố ảnh hưởng",
    "strengths": ["Điểm mạnh của sản phẩm dựa trên trust score breakdown"],
    "weaknesses": ["Điểm yếu cần cải thiện"]
  }},
  "review_insights": {{
    "sentiment_overview": "Tổng quan về sentiment của reviews",
    "key_positive_themes": ["Các chủ đề tích cực được đề cập nhiều trong reviews"],
    "key_negative_themes": ["Các vấn đề tiêu cực được đề cập nhiều"],
    "spam_concerns": "Đánh giá về mức độ spam và độ tin cậy của reviews"
  }},
  "recommendations": [
    "Các khuyến nghị cụ thể để cải thiện trust score và chất lượng sản phẩm"
  ],
  "risk_assessment": {{
    "overall_risk": "low|medium|high",
    "risk_factors": ["Các yếu tố rủi ro được xác định"],
    "confidence_level": "Đánh giá độ tin cậy của phân tích này"
  }}
}}

Hãy trả về JSON hợp lệ, không có markdown formatting hay code blocks."""

        return prompt
