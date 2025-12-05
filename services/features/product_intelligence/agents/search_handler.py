import json
from typing import Dict, Any, List
from core.llm.base import BaseAgent
from core.llm.utils import safe_json_parse
from prompts.product_ai import ANALYZE_PRODUCTS_PROMPT, GENERATE_LINKS_PROMPT
from schemas.product_ai import (
    ProductAnalysisResponse,
    ProductLinksResponse,
    ProductMultiLinksResponse
)
from .grounding_handler import GroundingHandler


class SearchHandler:
    """
    Two-step product search handler:
    1. Analyze and find prominent products within budget using LLM
    2. Generate Shopee links for those products using LLM with smart link generation
    """
    
    def __init__(self, llm_agent: BaseAgent):
        self.llm = llm_agent
        self.grounding_handler = GroundingHandler()
    
    def search(
        self, 
        search_keyword: str, 
        description: str,
        budget: float,
        limit: int = 10,
        platform: str = "all"
    ) -> Dict[str, Any]:
        """
        Execute 2-step search flow:
        Step 1: LLM analyzes and recommends prominent products
        Step 2: LLM generates Shopee links for those products
        """
        budget_text = f"{budget:,.0f} VND" if budget else "không giới hạn"
        
        # Step 1: Analyze and find prominent products
        analysis_result, grounding_metadata_1 = self._analyze_products(
            search_keyword, description, budget_text, limit
        )
        
        if "error" in analysis_result or not analysis_result.get("products"):
            return {
                "ai_result": analysis_result,
                "shopee_products": [],
                "grounding_metadata": {
                    "step1_analysis": grounding_metadata_1,
                    "step2_links": None
                }
            }
        
        # Step 2: Generate ecommerce links for analyzed products
        products_with_links, grounding_metadata_2 = self._generate_links(
            analysis_result.get("products", []),
            platform=platform
        )
        
        # Combine results
        final_result = {
            "analysis": analysis_result.get("analysis", ""),
            "products": products_with_links
        }
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Search completed: {len(products_with_links)} products with links generated")
        
        return {
            "ai_result": final_result,
            "shopee_products": products_with_links,
            "grounding_metadata": {
                "step1_analysis": grounding_metadata_1,
                "step2_links": grounding_metadata_2
            }
        }
    
    def _analyze_products(
        self, 
        search_keyword: str, 
        description: str, 
        budget_text: str,
        limit: int
    ) -> tuple:
        """
        Step 1: Use LLM with grounding to find and analyze prominent products
        Includes retry logic for reliability
        """
        import logging
        import traceback
        import time
        
        logger = logging.getLogger(__name__)
        provider = self.llm.model_name().split("-")[0]
        search_tools = self.grounding_handler.create_search_tools(provider)
        
        prompt = ANALYZE_PRODUCTS_PROMPT.format(
            search_keyword=search_keyword,
            description=description,
            budget_text=budget_text,
            limit=limit
        )
        
        # Retry configuration
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Step 1 - Attempt {attempt + 1}/{max_retries}: Analyzing products...")
                
                # NOTE: Cannot use response_schema + json_mode with tools (grounding)
                # Gemini API error: "Tool use with a response mime type: 'application/json' is unsupported"
                response = self.llm.generate(
                    prompt=prompt,
                    tools=search_tools,
                    timeout=90.0  # Increased timeout for grounding search
                )
                
                # Debug: Log raw response
                logger.info(f"Step 1 - Attempt {attempt + 1}: Raw LLM response length: {len(response.text)}")
                logger.debug(f"Step 1 - Attempt {attempt + 1}: Raw response preview: {response.text[:500]}...")
                
                result = safe_json_parse(response.text)
                
                # Debug: Log parsed result
                logger.info(f"Step 1 - Attempt {attempt + 1}: Parsed result keys: {list(result.keys())}")
                logger.debug(f"Step 1 - Attempt {attempt + 1}: Full parsed result: {result}")
                
                # Validate result has products
                if not result.get('products'):
                    logger.warning(f"Step 1 - Attempt {attempt + 1}: No products in response. Result keys: {list(result.keys())}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                        continue
                
                grounding_metadata = self.grounding_handler.extract_grounding_metadata(response)
                logger.info(f"Step 1 - Success: Found {len(result.get('products', []))} products")
                
                return result, grounding_metadata
                
            except Exception as e:
                error_details = traceback.format_exc()
                logger.error(f"Step 1 - Attempt {attempt + 1} failed: {str(e)}\n{error_details}")
                
                # Retry on transient errors
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)  # Exponential backoff
                    logger.info(f"Step 1 - Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    # Final failure after all retries
                    logger.error(f"Step 1 - All {max_retries} attempts failed")
                    result = {
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "analysis": f"Lỗi khi phân tích sản phẩm sau {max_retries} lần thử: {str(e)}",
                        "products": []
                    }
                    return result, None
        
        # Should not reach here
        return {"error": "Unknown error", "products": []}, None
    
    def _generate_links(self, products: List[Dict[str, Any]], platform: str = "all") -> tuple:
        """
        Step 2: Use LLM to generate simple ecommerce search links for products
        Supports: shopee, lazada, tiki, or all platforms
        Includes retry logic for reliability
        """
        import logging
        import traceback
        import time
        
        logger = logging.getLogger(__name__)
        
        products_json = json.dumps(products, ensure_ascii=False, indent=2)
        prompt = GENERATE_LINKS_PROMPT.format(
            products_json=products_json,
            platform=platform
        )
        
        # Retry configuration
        max_retries = 3
        retry_delay = 1  # seconds (shorter for step 2)
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Step 2 - Attempt {attempt + 1}/{max_retries}: Generating links for platform={platform}...")
                
                # No grounding tools needed - just URL formatting
                response = self.llm.generate(
                    prompt=prompt,
                    tools=None,
                    timeout=30.0  # Reduced timeout (no grounding needed)
                )
                
                result = safe_json_parse(response.text)
                products_with_links = result.get("products", [])
                
                # Validate products have URLs
                if not products_with_links or not any(p.get('url') for p in products_with_links):
                    logger.warning(f"Step 2 - Attempt {attempt + 1}: No URLs in response")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                
                grounding_metadata = self.grounding_handler.extract_grounding_metadata(response)
                logger.info(f"Step 2 - Success: {len(products_with_links)} products with links")
                
                return products_with_links, grounding_metadata
                
            except Exception as e:
                error_details = traceback.format_exc()
                logger.error(f"Step 2 - Attempt {attempt + 1} failed: {str(e)}\n{error_details}")
                
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    logger.info(f"Step 2 - Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Step 2 - All {max_retries} attempts failed. Returning products without links.")
                    # Fallback: Return original products without links
                    return products, None
        
        # Fallback
        return products, None
