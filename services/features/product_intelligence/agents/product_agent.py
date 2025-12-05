from typing import Dict, Any
from uuid import UUID
import logging
import re
from sqlalchemy.orm import Session

from .llm_provider_selector import LLMProviderSelector
from .search_handler import SearchHandler
from .fallback_handler import FallbackHandler
from schemas.product_ai import (
    ProductSearchResponse,
    ProjectInfo,
    GroundingMetadataFull
)

logger = logging.getLogger(__name__)


class ProductAIAgent:
    def __init__(self, db: Session):
        self.db = db
        self.llm_selector = LLMProviderSelector(db)
    
    def search_products(
        self, 
        project_info: Dict[str, Any], 
        user_id: UUID, 
        limit: int = 10,
        platform: str = "all"
    ) -> ProductSearchResponse:
        search_keyword, budget, description = self._extract_project_data(project_info)
        
        logger.info(f"Starting product search for user {user_id}. Keyword: '{search_keyword}', Budget: {budget}, Platform: {platform}")
        
        llm_agent = self.llm_selector.select_agent(
            user_id=user_id,
            project_assigned_model_id=project_info.get("assigned_model_id")
        )
        
        # Execute 2-step search (analysis + link generation)
        search_handler = SearchHandler(llm_agent)
        search_result = search_handler.search(
            search_keyword=search_keyword,
            description=description,
            budget=budget,
            limit=limit,
            platform=platform
        )
        
        # Handle failures
        if not search_result["shopee_products"]:
            logger.warning(f"No products found for '{search_keyword}'. Triggering fallback.")
            return FallbackHandler.create_failure_response(
                search_keyword=search_keyword,
                budget=budget,
                ai_result=search_result["ai_result"],
                project_info=project_info
            )
        
        # Build final response (no ranking needed - SearchHandler already filtered)
        logger.info(f"Search completed: {len(search_result['shopee_products'])} products returned")
        return self._build_response(
            project_info=project_info,
            search_keyword=search_keyword,
            budget=budget,
            ai_result=search_result["ai_result"],
            shopee_products=search_result["shopee_products"],
            grounding_metadata=search_result["grounding_metadata"],
            platform=platform,
            limit=limit
        )
    
    @staticmethod
    def _extract_project_data(project_info: Dict[str, Any]) -> tuple:
        """Extract relevant data from project info with safe parsing"""
        search_keyword = project_info.get("target_product_name") or project_info.get("name")
        
        # Safe budget parsing
        budget = None
        raw_budget = project_info.get("target_budget_range")
        if raw_budget:
            try:
                # Remove non-numeric chars except dot (simple cleanup)
                clean_budget = re.sub(r'[^\d.]', '', str(raw_budget))
                if clean_budget:
                    budget = float(clean_budget)
            except (ValueError, TypeError):
                logger.warning(f"Failed to parse budget: {raw_budget}. Using None.")
                budget = None
                
        description = project_info.get("description") or ""
        return search_keyword, budget, description
    
    @staticmethod
    def _build_response(
        project_info: Dict[str, Any],
        search_keyword: str,
        budget: float,
        ai_result: Dict[str, Any],
        shopee_products: list,
        grounding_metadata: Dict[str, Any],
        platform: str = "all",
        limit: int = 10
    ) -> ProductSearchResponse:
        """Build final response object as Pydantic model"""
        
        # Platform-specific naming
        platform_names = {
            "shopee": "Shopee",
            "lazada": "Lazada",
            "tiki": "Tiki",
            "all": "các sàn TMĐT"
        }
        platform_display = platform_names.get(platform, "Shopee")
        
        # Build GroundingMetadataFull from dict
        grounding_meta_full = GroundingMetadataFull(
            step1_analysis=grounding_metadata.get("step1_analysis"),
            step2_links=grounding_metadata.get("step2_links")
        )
        
        return ProductSearchResponse(
            project_info=ProjectInfo(
                id=str(project_info.get("id")),
                name=project_info.get("name"),
                description=project_info.get("description"),
                target_product=search_keyword,
                budget=budget,
                platform=platform
            ),
            ai_analysis=ai_result.get("analysis", "Products analyzed successfully"),
            recommended_products=shopee_products[:limit],
            all_products=shopee_products,
            total_found=len(shopee_products),
            grounding_metadata=grounding_meta_full,
            note=f"Sản phẩm được tìm kiếm trên {platform_display} qua 2 bước: (1) LLM phân tích sản phẩm nổi bật, (2) LLM tạo link."
        )
