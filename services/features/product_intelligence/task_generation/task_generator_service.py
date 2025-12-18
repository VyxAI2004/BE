"""
Service để generate marketing tasks từ product analytics.
"""
import logging
from typing import List, Dict, Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.core.product import ProductService
from services.core.product_analytics import ProductAnalyticsService
from services.core.product_trust_score import ProductTrustScoreService
from services.core.project import ProjectService
from services.features.product_intelligence.agents.task_generation_agent import (
    TaskGenerationAgent,
)
from services.features.product_intelligence.agents.llm_provider_selector import (
    LLMProviderSelector,
)

logger = logging.getLogger(__name__)


class TaskGeneratorService:
    """Service để generate marketing tasks từ product analytics"""

    def __init__(self, db: Session):
        self.db = db
        self.product_service = ProductService(db)
        self.analytics_service = ProductAnalyticsService(db)
        self.trust_score_service = ProductTrustScoreService(db)
        self.project_service = ProjectService(db)
        self.llm_selector = LLMProviderSelector(db)

    def _get_spam_percentage(self, trust_score_detail) -> str:
        """Helper method để lấy spam_percentage từ trust_score_detail breakdown"""
        try:
            if "spam" in trust_score_detail.breakdown:
                spam_breakdown = trust_score_detail.breakdown["spam"]
                spam_percentage = spam_breakdown.details.get("spam_percentage", 0.0)
                return f"Tỷ lệ spam: {float(spam_percentage):.2f}%"
            return "Tỷ lệ spam: Không có dữ liệu"
        except (AttributeError, KeyError, TypeError):
            return "Tỷ lệ spam: Không có dữ liệu"

    def generate_tasks_from_product_analytics(
        self,
        product_id: UUID,
        user_id: UUID,
        max_tasks: int = 5,
        project_assigned_model_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate marketing tasks từ product analytics.
        
        Args:
            product_id: ID của sản phẩm
            user_id: ID của user
            max_tasks: Số lượng tasks tối đa (default: 5)
            project_assigned_model_id: Optional model ID từ project
        
        Returns:
            List of tasks với đầy đủ thông tin để tạo Task objects
        """
        try:
            logger.info(f"Generating tasks for product {product_id}, user {user_id}")

            # 1. Lấy thông tin sản phẩm
            product = self.product_service.get(product_id)
            if not product:
                raise ValueError(f"Product {product_id} not found")

            # 2. Kiểm tra trust score trước
            trust_score_detail = self.trust_score_service.get_trust_score_detail(product_id)
            if not trust_score_detail:
                raise ValueError(
                    "Trust score chưa được tính cho sản phẩm này. "
                    "Vui lòng tính trust score trước (POST /products/{product_id}/trust-score/calculate)."
                )

            # 3. Lấy analytics data (có thể từ cache hoặc generate mới)
            try:
                analytics_result = self.analytics_service.analyze_product(
                    product_id=product_id,
                    user_id=user_id,
                    project_assigned_model_id=project_assigned_model_id,
                )
            except ValueError as e:
                # Nếu analytics service fail, vẫn có thể generate tasks từ trust score
                logger.warning(f"Analytics service failed for product {product_id}: {e}")
                # Tạo analytics result từ trust score data
                analytics_result = {
                    "analysis": {
                        "summary": f"Sản phẩm có trust score {float(trust_score_detail.trust_score):.2f}/100",
                        "trust_score_analysis": {
                            "interpretation": f"Trust score {float(trust_score_detail.trust_score):.2f}/100",
                            "strengths": [],
                            "weaknesses": [],
                        },
                        "review_insights": {
                            "sentiment_overview": f"Có {trust_score_detail.total_reviews} reviews",
                            "key_positive_themes": [],
                            "key_negative_themes": [],
                            "spam_concerns": self._get_spam_percentage(trust_score_detail),
                        },
                        "recommendations": [],
                        "risk_assessment": {
                            "overall_risk": "medium",
                            "risk_factors": [],
                            "confidence_level": "Trung bình",
                        },
                    },
                    "metadata": {
                        "model_used": "fallback",
                        "total_reviews_analyzed": trust_score_detail.total_reviews,
                        "sample_reviews_count": 0,
                    },
                }

            # 4. Kiểm tra product có thuộc project không
            if not product.project_id:
                raise ValueError("Sản phẩm phải thuộc một project để tạo tasks. Vui lòng gán sản phẩm vào project trước.")

            # 5. Lấy project info
            project_info = None
            if product.project_id:
                project = self.project_service.get(product.project_id)
                if project:
                    project_info = {
                        "name": project.name,
                        "target_product_name": project.target_product_name,
                        "budget": float(project.target_budget_range) if project.target_budget_range else None,
                        "category": project.target_product_category,
                    }

            # 6. Chuẩn bị product data
            product_data = {
                "name": product.name,
                "brand": product.brand,
                "category": product.category,
                "platform": product.platform,
                "price": float(product.current_price) if product.current_price else None,
                "currency": product.currency or "VND",
                "average_rating": float(product.average_rating) if product.average_rating else None,
            }

            # 7. Lấy trust score (đã có từ bước 2)
            trust_score = float(trust_score_detail.trust_score)

            # 8. Chuẩn bị analytics data
            analytics_data = {
                "analysis": analytics_result.get("analysis", {}),
                "trust_score": trust_score,
                "metadata": analytics_result.get("metadata", {}),
            }

            # 9. Get LLM agent
            llm_agent = self.llm_selector.select_agent(
                user_id=user_id, project_assigned_model_id=project_assigned_model_id
            )

            # 10. Generate tasks
            task_agent = TaskGenerationAgent(llm_agent)
            generated_tasks = task_agent.generate_marketing_tasks(
                product_data=product_data,
                analytics_data=analytics_data,
                project_info=project_info,
                max_tasks=max_tasks,
            )

            # 11. Enrich tasks với thông tin bổ sung
            enriched_tasks = []
            for task in generated_tasks:
                enriched_task = {
                    **task,
                    "product_id": str(product_id),
                    "project_id": str(product.project_id) if product.project_id else None,
                    "source": "ai_generated",
                    "source_analytics": {
                        "trust_score": trust_score,
                        "model_used": analytics_result.get("metadata", {}).get("model_used"),
                    },
                }
                enriched_tasks.append(enriched_task)

            logger.info(
                f"Generated {len(enriched_tasks)} marketing tasks for product {product_id}"
            )
            return enriched_tasks

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error generating tasks for product {product_id}: {e}", exc_info=True)
            raise ValueError(f"Failed to generate tasks: {str(e)}")

    def generate_and_save_tasks(
        self,
        product_id: UUID,
        user_id: UUID,
        max_tasks: int = 5,
        project_assigned_model_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate tasks và lưu vào database.
        
        Returns:
            List of created Task objects (as dicts)
        """
        from services.core.task import TaskService
        from schemas.task import TaskCreate
        from decimal import Decimal

        # Generate tasks
        generated_tasks = self.generate_tasks_from_product_analytics(
            product_id=product_id,
            user_id=user_id,
            max_tasks=max_tasks,
            project_assigned_model_id=project_assigned_model_id,
        )

        # Get product để lấy project_id
        product = self.product_service.get(product_id)
        if not product or not product.project_id:
            raise ValueError("Product must belong to a project to create tasks")

        # Xóa tasks cũ của product này trước khi tạo mới
        task_service = TaskService(self.db)
        try:
            deleted_count = task_service.delete_by_product_id(product_id)
            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} old tasks for product {product_id} before generating new ones")
        except Exception as e:
            logger.warning(f"Failed to delete old tasks for product {product_id}: {e}. Continuing with task creation.")
        
        # Create tasks in database
        created_tasks = []

        # Assign task_order từ 1 đến số lượng tasks
        for index, task_data in enumerate(generated_tasks, start=1):
            try:
                task_create = TaskCreate(
                    project_id=product.project_id,
                    name=task_data["name"],
                    description=task_data.get("description", ""),
                    pipeline_stage="research",
                    stage_order=1,
                    task_order=index,  # Thứ tự ưu tiên từ 1-5
                    task_type=task_data.get("task_type", "marketing_research"),
                    status="pending",
                    priority=task_data.get("priority", "medium"),
                    assigned_to=user_id,
                    estimated_hours=Decimal(str(task_data.get("estimated_hours", 0))) if task_data.get("estimated_hours") else None,
                    stage_metadata={
                        "source": "ai_generated",
                        "product_id": str(product_id),
                        "marketing_focus": task_data.get("marketing_focus"),
                        "related_insights": task_data.get("related_insights", []),
                        "source_analytics": task_data.get("source_analytics", {}),
                    },
                )

                created_task = task_service.create(payload=task_create)
                created_tasks.append({
                    "id": str(created_task.id),
                    "name": created_task.name,
                    "description": created_task.description,
                    "task_type": created_task.task_type,
                    "priority": created_task.priority,
                    "status": created_task.status,
                    "task_order": created_task.task_order,
                    "estimated_hours": float(created_task.estimated_hours) if created_task.estimated_hours else None,
                })

            except Exception as e:
                logger.error(f"Failed to create task '{task_data.get('name')}': {e}")
                continue

        logger.info(f"Created {len(created_tasks)} tasks in database for product {product_id}")
        return created_tasks
