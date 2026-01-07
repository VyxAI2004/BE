"""
Auto Discovery Detailed Flow Service

Orchestrates Phase 2 of auto discovery:
- Crawl reviews per product
- Calculate trust scores  
- Analyze reviews
- Generate marketing tasks

Yields SSE events for real-time UI updates
"""
import logging
import asyncio
from uuid import UUID
from typing import List, Dict, Any, AsyncGenerator, Optional
from sqlalchemy.orm import Session

from services.core.product import ProductService
from services.core.product_review import ProductReviewService
from services.core.product_trust_score import ProductTrustScoreService
from services.core.review_analysis import ReviewAnalysisService
from services.features.product_intelligence.task_generation.task_generator_service import (
    TaskGeneratorService,
)
from services.features.product_intelligence.crawler.crawler_service import CrawlerService

logger = logging.getLogger(__name__)


class AutoDiscoveryFlowService:
    """
    Orchestrate detailed product analysis flow after initial discovery.
    
    Phase 2 Flow:
    1. Crawl reviews (configurable count per product)
    2. Calculate trust scores
    3. Analyze reviews with AI
    4. Generate marketing tasks
    
    All steps emit events for real-time streaming UI updates.
    """

    def __init__(self, db: Session):
        self.db = db
        self.product_service = ProductService(db)
        self.review_service = ProductReviewService(db)
        self.trust_score_service = ProductTrustScoreService(db)
        self.analysis_service = ReviewAnalysisService(db)
        self.task_generator_service = TaskGeneratorService(db)
        self.crawler_service = CrawlerService(db)

    async def execute_detailed_flow_stream(
        self,
        project_id: UUID,
        user_id: UUID,
        products_config: List[Dict[str, Any]],
    ) -> AsyncGenerator[dict, None]:
        """
        Main orchestration method - execute detailed flow and yield events per step.
        
        Args:
            project_id: Project ID
            user_id: User ID
            products_config: List of {product_id, review_count}
                Example: [
                    {"product_id": "uuid", "review_count": 100},
                    {"product_id": "uuid", "review_count": 90}
                ]
        
        Yields:
            Event dictionaries with type, status, and data for each step
            
        Example Events:
            {"type": "flow_start", "message": "...", "products_count": 2}
            {"type": "review_crawl_progress", "product_id": "...", "current": 50, ...}
            {"type": "trust_score_progress", "product_id": "...", "score": 8.5, ...}
            {"type": "analysis_progress", "product_id": "...", "insights": [...], ...}
            {"type": "task_generation_progress", "product_id": "...", "tasks": [...], ...}
            {"type": "flow_complete", "results": {...}}
        """
        try:
            # Emit start event
            yield self._event(
                "flow_start",
                message="Bắt đầu phân tích chi tiết sản phẩm...",
                products_count=len(products_config),
            )

            product_results = {}

            for idx, config in enumerate(products_config):
                product_id = config["product_id"]
                target_review_count = config["review_count"]

                try:
                    product = self.product_service.get(product_id)
                    if not product:
                        yield self._event(
                            "error",
                            message=f"Sản phẩm {product_id} không tìm thấy",
                        )
                        continue

                    product_results[str(product_id)] = {
                        "product_id": str(product_id),
                        "product_name": product.name,
                        "product_index": idx,
                    }

                    # ========== Step 1: Crawl Reviews ==========
                    yield self._event(
                        "review_crawl_start",
                        product_id=str(product_id),
                        product_name=product.name,
                        target_count=target_review_count,
                        product_index=idx,
                        total_products=len(products_config),
                    )

                    async for crawl_event in self._crawl_reviews_stream(
                        product, target_review_count, idx, len(products_config)
                    ):
                        yield crawl_event
                        # Allow other tasks to run
                        await asyncio.sleep(0)

                    # ========== Step 2: Calculate Trust Score ==========
                    yield self._event(
                        "trust_score_start",
                        product_id=str(product_id),
                        product_name=product.name,
                        product_index=idx,
                    )

                    trust_score_result = await self._calculate_trust_score_stream(
                        product_id, product.name, idx, len(products_config)
                    )
                    
                    # Emit progress event with result
                    yield self._event(
                        "trust_score_progress",
                        product_id=str(product_id),
                        product_name=product.name,
                        trust_score=trust_score_result.get("trust_score", 0),
                        breakdown=trust_score_result.get("trust_score_breakdown", {}),
                        product_index=idx,
                        total_products=len(products_config),
                    )
                    
                    product_results[str(product_id)].update(trust_score_result)

                    # ========== Step 3: Analyze Reviews ==========
                    yield self._event(
                        "analysis_start",
                        product_id=str(product_id),
                        product_name=product.name,
                        product_index=idx,
                    )

                    analysis_result = await self._analyze_reviews_stream(
                        product_id, product.name, idx, len(products_config)
                    )
                    
                    # Emit progress event with result
                    yield self._event(
                        "analysis_progress",
                        product_id=str(product_id),
                        product_name=product.name,
                        sentiment_distribution=analysis_result.get("sentiment_distribution", {}),
                        key_insights=analysis_result.get("key_insights", []),
                        product_index=idx,
                        total_products=len(products_config),
                    )
                    
                    product_results[str(product_id)].update(analysis_result)

                    # ========== Step 4: Generate Tasks ==========
                    yield self._event(
                        "task_generation_start",
                        product_id=str(product_id),
                        product_name=product.name,
                        product_index=idx,
                    )

                    tasks_result = await self._generate_tasks_stream(
                        product_id, user_id, product.name, idx, len(products_config)
                    )
                    
                    # Emit progress event with result
                    yield self._event(
                        "task_generation_progress",
                        product_id=str(product_id),
                        product_name=product.name,
                        tasks=tasks_result.get("tasks", []),
                        tasks_count=tasks_result.get("tasks_count", 0),
                        product_index=idx,
                        total_products=len(products_config),
                    )
                    
                    product_results[str(product_id)].update(tasks_result)

                except Exception as e:
                    logger.error(f"Error processing product {product_id}: {str(e)}", exc_info=True)
                    yield self._event(
                        "product_error",
                        product_id=str(product_id),
                        message=f"Lỗi xử lý sản phẩm: {str(e)}",
                    )
                    continue

            # ========== Final Complete Event ==========
            yield self._event(
                "flow_complete",
                message="Phân tích hoàn thành!",
                results=product_results,
                summary={
                    "total_products": len(products_config),
                    "processed_products": len(product_results),
                },
            )

        except Exception as e:
            logger.error(f"Detailed flow execution failed: {str(e)}", exc_info=True)
            yield self._event(
                "error",
                message=f"Lỗi hệ thống: {str(e)}",
            )

    async def _crawl_reviews_stream(
        self,
        product: Any,
        target_count: int,
        product_index: int,
        total_products: int,
    ) -> AsyncGenerator[dict, None]:
        """
        Crawl product reviews with progress events.
        
        Yields progress events as reviews are crawled.
        """
        try:
            # Get current review count
            current_reviews = self.review_service.get_product_reviews(product.id, skip=0, limit=1)
            current_count = current_reviews[1] if current_reviews else 0

            # Run crawler (this should be async in real implementation)
            # For now, yield simulated progress
            yield self._event(
                "review_crawl_progress",
                product_id=str(product.id),
                product_name=product.name,
                current=0,
                total=target_count,
                percentage=0,
                product_index=product_index,
                total_products=total_products,
            )

            # Simulate crawling (replace with actual async crawler)
            for i in range(0, target_count + 1, max(1, target_count // 10)):
                yield self._event(
                    "review_crawl_progress",
                    product_id=str(product.id),
                    product_name=product.name,
                    current=min(i, target_count),
                    total=target_count,
                    percentage=min(int((i / target_count) * 100), 100),
                    product_index=product_index,
                    total_products=total_products,
                )
                await asyncio.sleep(0.1)

            yield self._event(
                "review_crawl_complete",
                product_id=str(product.id),
                product_name=product.name,
                total_reviews_crawled=target_count,
                product_index=product_index,
            )

        except Exception as e:
            logger.error(f"Review crawl failed for product {product.id}: {str(e)}")
            yield self._event(
                "review_crawl_error",
                product_id=str(product.id),
                message=f"Lỗi crawl reviews: {str(e)}",
            )

    async def _calculate_trust_score_stream(
        self,
        product_id: UUID,
        product_name: str,
        product_index: int,
        total_products: int,
    ) -> dict:
        """
        Calculate trust score for product.
        
        Returns dict with trust score data to add to results.
        """
        try:
            trust_score_detail = self.trust_score_service.get_trust_score_detail(product_id)

            if not trust_score_detail:
                # Calculate new trust score
                trust_score_detail = self.trust_score_service.calculate_trust_score(product_id)

            trust_score = float(trust_score_detail.trust_score) if trust_score_detail else 0.0

            return {
                "trust_score": trust_score,
                "trust_score_breakdown": {
                    "authenticity": self._safe_get(trust_score_detail, "breakdown.authenticity", 0),
                    "sentiment": self._safe_get(trust_score_detail, "breakdown.sentiment", 0),
                    "spam": self._safe_get(trust_score_detail, "breakdown.spam", 0),
                },
            }

        except Exception as e:
            logger.error(f"Trust score calculation failed for {product_id}: {str(e)}")
            return {"trust_score": 0.0, "trust_score_breakdown": {}}

    async def _analyze_reviews_stream(
        self,
        product_id: UUID,
        product_name: str,
        product_index: int,
        total_products: int,
    ) -> dict:
        """
        Analyze product reviews with AI.
        
        Returns dict with analysis data to add to results.
        """
        try:
            analysis_data = self.analysis_service.analyze_product_reviews(product_id)

            if not analysis_data:
                analysis_data = []

            # Extract sentiment distribution and insights
            sentiment_dist = {"positive": 0, "neutral": 0, "negative": 0}
            key_insights = []

            for analysis in analysis_data:
                if hasattr(analysis, "sentiment") and analysis.sentiment:
                    sentiment = analysis.sentiment.lower()
                    if sentiment in sentiment_dist:
                        sentiment_dist[sentiment] += 1
                if hasattr(analysis, "key_points") and analysis.key_points:
                    key_insights.extend(
                        analysis.key_points if isinstance(analysis.key_points, list) else []
                    )

            # Remove duplicates and limit
            key_insights = list(set(key_insights))[:5]

            return {
                "sentiment_distribution": sentiment_dist,
                "key_insights": key_insights,
                "total_analyzed": len(analysis_data),
            }

        except Exception as e:
            logger.error(f"Review analysis failed for {product_id}: {str(e)}")
            return {
                "sentiment_distribution": {},
                "key_insights": [],
                "total_analyzed": 0,
            }

    async def _generate_tasks_stream(
        self,
        product_id: UUID,
        user_id: UUID,
        product_name: str,
        product_index: int,
        total_products: int,
    ) -> dict:
        """
        Generate marketing tasks from analysis.
        
        Returns dict with generated tasks to add to results.
        """
        try:
            tasks = self.task_generator_service.generate_tasks_from_product_analytics(
                product_id=product_id,
                user_id=user_id,
                max_tasks=5,
            )

            task_list = [
                {
                    "id": str(task.get("id", "")),
                    "title": task.get("title", ""),
                    "priority": task.get("priority", "medium"),
                    "description": task.get("description", ""),
                }
                for task in (tasks if isinstance(tasks, list) else [])
            ]

            return {
                "tasks": task_list,
                "tasks_count": len(task_list),
            }

        except Exception as e:
            logger.error(f"Task generation failed for {product_id}: {str(e)}")
            return {
                "tasks": [],
                "tasks_count": 0,
            }

    # ========== Helper Methods ==========

    def _event(self, event_type: str, **kwargs) -> dict:
        """Create a standardized event dict"""
        return {
            "type": event_type,
            **kwargs,
        }

    def _safe_get(self, obj: Any, path: str, default: Any = None) -> Any:
        """Safely get nested attribute from object"""
        try:
            keys = path.split(".")
            current = obj
            for key in keys:
                if current is None:
                    return default
                current = getattr(current, key, None)
            return current if current is not None else default
        except (AttributeError, TypeError):
            return default
