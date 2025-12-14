import logging
from uuid import UUID
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from services.features.product_intelligence.agents.product_agent import ProductAIAgent
from services.features.product_intelligence.agents.llm_provider_selector import LLMProviderSelector
from services.features.product_intelligence.crawler.crawler_service import CrawlerService
from services.core.project import ProjectService
from services.features.product_intelligence.crawler.scraper_factory import ScraperFactory
from services.features.product_intelligence.ai.filter_intent_parser import FilterIntentParser
from services.features.product_intelligence.ai.filter_validator import FilterCriteriaValidator
from services.features.product_intelligence.ai.natural_language_parser import NaturalLanguageParser
from services.features.product_intelligence.filtering.product_filter_service import ProductFilterService
from services.features.product_intelligence.ranking.product_ranking_service import ProductRankingService
from services.features.product_intelligence.auto_import.auto_import_service import AutoImportService
from schemas.product_crawler import CrawledProductItem, CrawledProductItemExtended
from schemas.product_filter import ProductFilterCriteria

logger = logging.getLogger(__name__)

MAX_CRAWL_PRODUCTS = 20


class AutoDiscoveryService:
    def __init__(self, db: Session):
        self.db = db
        self.product_agent = ProductAIAgent(db)
        self.crawler_service = CrawlerService(db)
        self.filter_service = ProductFilterService()
        self.import_service = AutoImportService(db)
        self.llm_selector = LLMProviderSelector(db)
        self.project_service = ProjectService(db)
    
    def _get_llm_agent(self, user_id: UUID, project_assigned_model_id: Optional[UUID] = None):
        return self.llm_selector.select_agent(
            user_id=user_id,
            project_assigned_model_id=project_assigned_model_id
        )
    
    def execute_auto_discovery_from_natural_language(
        self,
        project_id: UUID,
        user_id: UUID,
        user_input: str
    ) -> Dict[str, Any]:
        if not user_input or not user_input.strip():
            return {
                "status": "error",
                "message": "Input không được để trống",
                "error_type": "invalid_input"
            }
        
        if len(user_input) > 2000:
            return {
                "status": "error",
                "message": "Input quá dài (tối đa 2000 ký tự)",
                "error_type": "input_too_long"
            }
        
        project = self.project_service.get(project_id)
        if not project:
            return {
                "status": "error",
                "message": "Project not found",
                "error_type": "project_not_found"
            }
        
        if not project.target_product_name or not project.target_product_name.strip():
            return {
                "status": "error",
                "message": "Project chưa có sản phẩm mục tiêu. Vui lòng cập nhật target_product_name cho project.",
                "error_type": "project_incomplete"
            }
        
        project_info = {
            "name": project.name,
            "description": project.description or "",
            "target_product_name": project.target_product_name,
            "target_product_category": project.target_product_category or "",
            "target_budget_range": float(project.target_budget_range) if project.target_budget_range else None,
            "currency": project.currency or "VND",
            "status": project.status or "",
            "pipeline_type": project.pipeline_type or ""
        }
        
        llm_agent = self._get_llm_agent(
            user_id=user_id,
            project_assigned_model_id=project.assigned_model_id
        )
        
        natural_language_parser = NaturalLanguageParser(llm_agent)
        
        user_query, filter_criteria_text, max_products, error = natural_language_parser.parse_user_input(
            user_input,
            project_info=project_info
        )
        
        if error:
            return {
                "status": "error",
                "message": f"Không thể phân tích yêu cầu: {error}",
                "error_type": "parsing_failed"
            }
        
        return self.execute_auto_discovery(
            project_id=project_id,
            user_id=user_id,
            user_query=user_query,
            filter_criteria_text=filter_criteria_text,
            max_products=max_products,
            project_assigned_model_id=project.assigned_model_id
        )
    
    def execute_auto_discovery(
        self,
        project_id: UUID,
        user_id: UUID,
        user_query: str,
        filter_criteria_text: Optional[str] = None,
        max_products: int = 20,
        project_assigned_model_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        
        try:
            llm_agent = self._get_llm_agent(
                user_id=user_id,
                project_assigned_model_id=project_assigned_model_id
            )
            
            intent_parser = FilterIntentParser(llm_agent)
            criteria_validator = FilterCriteriaValidator(llm_agent)
            ranking_service = ProductRankingService(llm_agent)
            
            filter_criteria = None
            if filter_criteria_text:
                criteria, error = intent_parser.parse_user_intent(filter_criteria_text)
                
                if error:
                    return {
                        "status": "error",
                        "message": f"Không thể phân tích tiêu chí lọc: {error}",
                        "error_type": "intent_parsing_failed"
                    }
                
                if criteria.platforms:
                    platforms_lower = [p.lower() for p in criteria.platforms]
                    if "shopee" in platforms_lower:
                        available_platforms = [p for p in platforms_lower if p != "shopee"]
                        if not available_platforms:
                            available_platforms = ["lazada", "tiki"]
                        
                        return {
                            "status": "error",
                            "message": "Hiện tại công cụ scraper cho Shopee chưa hoàn thiện. Vui lòng tìm kiếm trên Lazada hoặc Tiki thay thế.",
                            "error_type": "platform_not_supported",
                            "suggested_platforms": available_platforms,
                            "extracted_criteria": criteria.model_dump(exclude_none=True)
                        }
                
                is_valid, validation_error = criteria_validator.validate_criteria(
                    filter_criteria_text,
                    criteria
                )
                
                if not is_valid:
                    return {
                        "status": "error",
                        "message": validation_error or "AI không hiểu yêu cầu của bạn",
                        "error_type": "criteria_validation_failed",
                        "extracted_criteria": criteria.model_dump(exclude_none=True)
                    }
                
                filter_criteria = criteria
            
            project = self.project_service.get(project_id)
            project_name = project.name if project else f"Project {project_id}"
            
            project_info = {
                "id": project_id,
                "name": project_name,
                "target_product_name": user_query,
                "target_budget_range": filter_criteria.max_price if filter_criteria else None,
                "description": user_query or "",
                "assigned_model_id": project_assigned_model_id
            }
            
            search_platform = "all"
            if filter_criteria and filter_criteria.platforms:
                if len(filter_criteria.platforms) == 1:
                    search_platform = filter_criteria.platforms[0].lower()
                else:
                    search_platform = "all"
            
            if search_platform == "shopee":
                search_platform = "all"
            
            search_result = self.product_agent.search_products(
                project_info=project_info,
                user_id=user_id,
                limit=max_products * 2,
                platform=search_platform
            )
            
            if not search_result.recommended_products:
                return {
                    "status": "error",
                    "message": "Không tìm thấy sản phẩm nào từ AI search",
                    "error_type": "no_products_found"
                }
            
            all_crawled_products = []
            
            search_urls = self._extract_search_urls(
                search_result.recommended_products,
                exclude_platforms=["shopee"]
            )
            
            max_per_url = max(1, MAX_CRAWL_PRODUCTS // max(len(search_urls), 1))
            
            for search_url in search_urls:
                if len(all_crawled_products) >= MAX_CRAWL_PRODUCTS:
                    break
                
                try:
                    remaining = MAX_CRAWL_PRODUCTS - len(all_crawled_products)
                    crawl_limit = min(max_per_url, remaining)
                    
                    scraper = ScraperFactory.get_scraper(search_url)
                    crawled_items = scraper.crawl_search_results(search_url, max_products=crawl_limit)
                    
                    if crawled_items:
                        for item in crawled_items:
                            if len(all_crawled_products) >= MAX_CRAWL_PRODUCTS:
                                break
                            
                            extended = self._convert_to_extended(item, search_url)
                            all_crawled_products.append(extended)
                
                except Exception as e:
                    logger.warning(f"Failed to crawl {search_url}: {str(e)}", exc_info=True)
                    continue
            
            if not all_crawled_products:
                return {
                    "status": "error",
                    "message": "Không thể crawl được sản phẩm nào từ các search links. Có thể do: (1) Links không hợp lệ, (2) Platform chặn requests, (3) Network issues. Vui lòng thử lại sau.",
                    "error_type": "crawl_failed",
                    "products_found": 0
                }
            
            filtered_products = all_crawled_products
            if filter_criteria:
                filtered_products = self.filter_service.filter_products(
                    all_crawled_products,
                    filter_criteria
                )
                
                if len(filtered_products) == 0 and len(all_crawled_products) > 0:
                    logger.warning(
                        f"Filter criteria too strict: {len(all_crawled_products)} products found, "
                        f"but 0 products match criteria"
                    )
            
            if len(filtered_products) > max_products:
                filtered_products = ranking_service.rank_and_select_products(
                    products=filtered_products,
                    user_query=user_query,
                    filter_criteria=filter_criteria.model_dump(exclude_none=True) if filter_criteria else None,
                    limit=max_products
                )
            else:
                filtered_products = filtered_products[:max_products]
            
            if not filtered_products:
                return {
                    "status": "error",
                    "message": "Không có sản phẩm nào đạt yêu cầu sau khi lọc. Vui lòng thử lại với tiêu chí lọc ít nghiêm ngặt hơn.",
                    "error_type": "no_products_after_filter",
                    "products_found": len(all_crawled_products),
                    "products_filtered": 0
                }
            
            imported_ids = self.import_service.import_products(
                products=filtered_products,
                project_id=project_id,
                user_id=user_id
            )
            
            if len(imported_ids) == 0:
                return {
                    "status": "error",
                    "message": "Không thể import sản phẩm nào vào database. Có thể do lỗi permission hoặc duplicate.",
                    "error_type": "import_failed",
                    "products_found": len(all_crawled_products),
                    "products_filtered": len(filtered_products),
                    "products_imported": 0
                }
            
            message = f"Đã import {len(imported_ids)} sản phẩm thành công"
            if len(imported_ids) < len(filtered_products):
                message += f" ({len(filtered_products) - len(imported_ids)} sản phẩm bị bỏ qua do duplicate hoặc lỗi)"
            
            return {
                "status": "success",
                "message": message,
                "filter_criteria": filter_criteria.model_dump(exclude_none=True) if filter_criteria else None,
                "products_found": len(all_crawled_products),
                "products_filtered": len(filtered_products),
                "products_imported": len(imported_ids),
                "imported_product_ids": imported_ids
            }
            
        except Exception as e:
            logger.error(f"Auto discovery failed: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Lỗi trong quá trình tự động hóa: {str(e)}",
                "error_type": "execution_error"
            }
    
    def _extract_search_urls(self, products: List[Any], exclude_platforms: List[str] = None) -> List[str]:
        if exclude_platforms is None:
            exclude_platforms = ["shopee"]
        
        exclude_platforms_lower = [p.lower() for p in exclude_platforms]
        urls = []
        
        for product in products:
            if hasattr(product, 'url') and product.url:
                url_lower = product.url.lower()
                if not any(platform in url_lower for platform in exclude_platforms_lower):
                    urls.append(product.url)
            elif hasattr(product, 'urls'):
                if hasattr(product.urls, 'lazada') and product.urls.lazada:
                    urls.append(product.urls.lazada)
                if hasattr(product.urls, 'tiki') and product.urls.tiki:
                    urls.append(product.urls.tiki)
                if "shopee" not in exclude_platforms_lower:
                    if hasattr(product.urls, 'shopee') and product.urls.shopee:
                        urls.append(product.urls.shopee)
            elif isinstance(product, dict):
                if 'url' in product:
                    url = product['url']
                    url_lower = url.lower()
                    if not any(platform in url_lower for platform in exclude_platforms_lower):
                        urls.append(url)
                elif 'urls' in product:
                    urls_dict = product['urls']
                    if isinstance(urls_dict, dict):
                        for platform, url in urls_dict.items():
                            if url and platform.lower() not in exclude_platforms_lower:
                                urls.append(url)
        
        return list(set(urls))
    
    def _convert_to_extended(
        self,
        item: CrawledProductItem,
        source_url: str
    ) -> CrawledProductItemExtended:
        platform = item.platform or self._detect_platform(source_url)
        price = 0.0
        if item.price:
            try:
                if isinstance(item.price, (int, float)):
                    price = float(item.price)
                elif isinstance(item.price, str):
                    price_str = item.price.replace(',', '').replace('₫', '').replace('đ', '').replace('VND', '').replace('vnd', '').strip()
                    if '.' in price_str:
                        parts = price_str.split('.')
                        if len(parts) > 1 and len(parts[-1]) == 3 and len(parts) == 2:
                            if len(parts[0]) >= 1:
                                price_str = ''.join(parts)
                        elif len(parts) > 2:
                            price_str = ''.join(parts)
                    price = float(price_str)
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse price '{item.price}': {str(e)}")
                price = 0.0
        
        review_count = None
        if hasattr(item, 'review_count') and item.review_count is not None:
            review_count = int(item.review_count) if isinstance(item.review_count, (int, str)) else None
        
        return CrawledProductItemExtended(
            platform=platform,
            product_name=item.name,
            product_url=item.link or source_url,
            price_current=price,
            rating_score=item.rating,
            review_count=review_count,
            sales_count=self._parse_sales_count(item.sold),
            is_mall=False,
            brand=None,
            keywords_in_title=self._extract_keywords(item.name),
            image_urls=[item.img] if item.img else []
        )
    
    def _detect_platform(self, url: str) -> str:
        url_lower = url.lower()
        if "shopee" in url_lower:
            return "shopee"
        elif "lazada" in url_lower:
            return "lazada"
        elif "tiki" in url_lower:
            return "tiki"
        return "unknown"
    
    def _parse_sales_count(self, sold: Any) -> Optional[int]:
        if sold is None:
            return None
        if isinstance(sold, int):
            return sold
        if isinstance(sold, str):
            sold_lower = sold.lower().replace(",", "").replace(" ", "")
            if "k" in sold_lower:
                try:
                    return int(float(sold_lower.replace("k", "")) * 1000)
                except (ValueError, TypeError):
                    pass
            try:
                return int(sold_lower)
            except (ValueError, TypeError):
                return None
        return None
    
    def _extract_keywords(self, text: str) -> List[str]:
        words = text.lower().split()
        stop_words = {"và", "của", "cho", "với", "từ", "đến", "có", "là", "một", "các", "the", "a", "an"}
        keywords = [w for w in words if len(w) > 2 and w not in stop_words]
        return keywords[:10]

