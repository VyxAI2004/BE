---
description: Kế hoạch triển khai Product Trust Score dựa trên phân tích Review
---

# 🎯 Kế hoạch triển khai Product Trust Score

## Tổng quan
Mở rộng hệ thống Product để tính toán **điểm tin cậy (Trust Score)** dựa trên phân tích cảm xúc và phát hiện spam trong reviews được crawl từ các sàn thương mại điện tử.

### Kiến trúc hệ thống

#### Flow 1: Trust Score Calculation (Phase 1-9)
```
LLM Search → Product filter → Product URLs → BeautifulSoup Crawler → Product + Reviews
                                                                                     ↓
                                                                             Save to Database
                                                                                     ↓
                                                                        AI Models Service (External)
                                                                        ├─ Sentiment Analysis API
                                                                        └─ Spam Detection API
                                                                                     ↓
                                                                        Review Analysis Results
                                                                                     ↓
                                                                        Trust Score Calculation
                                                                                     ↓
                                                                        Update Product Score
```

#### Flow 2: Automated Product Discovery & Import (Phase 10)
```
User Text Input → AI Intent Parser → Filter Criteria (JSON) → AI Validation
                                                                     ↓
                                                              Valid Criteria
                                                                     ↓
AI Discovery (LLM Search) → Search Links → Auto Crawl → Product List (Raw Data)
                                                                     ↓
                                                              AI Filtering Service
                                                                     ↓
                                                              Filtered Products
                                                                     ↓
                                                              Auto Import Service
                                                                     ↓
                                                              Products in Database
                                                                     ↓
                                                              (Optional) Trigger Trust Score Flow
```

---

## 📊 Phase 1: Database Schema Design

### 1.1. Model ProductReview
**File:** `models/product.py`

Lưu trữ reviews được crawl từ Shopee, Lazada, Tiki

```python
class ProductReview(Base):
    __tablename__ = "product_reviews"
    
    # Foreign Keys
    product_id: UUID (FK -> products.id, CASCADE)
    
    # Review Information
    reviewer_name: String(200)          # Tên người review
    reviewer_id: String(100)            # ID trên platform (nếu có)
    rating: Integer                     # Điểm đánh giá (1-5)
    content: Text                       # Nội dung review
    review_date: DateTime               # Ngày đăng review
    
    # Platform Information
    platform: String(50)                # shopee/lazada/tiki
    source_url: String(500)             # Link gốc của review
    
    # Crawl Metadata
    crawled_at: DateTime                # Thời gian crawl
    crawl_session_id: UUID (FK)         # Session crawl này
```

**Indexes:**
- `product_id` (để query nhanh reviews của 1 product)
- `platform` (filter theo platform)
- `review_date` (sắp xếp theo thời gian)

---

### 1.2. Model ReviewAnalysis
**File:** `models/product.py`

Lưu kết quả phân tích từ AI models service

```python
class ReviewAnalysis(Base):
    __tablename__ = "review_analyses"
    
    # Foreign Keys
    review_id: UUID (FK -> product_reviews.id, CASCADE, UNIQUE)
    
    # Sentiment Analysis Results
    sentiment_label: String(20)         # positive/negative/neutral
    sentiment_score: Numeric(5,4)       # 0.0000 - 1.0000
    sentiment_confidence: Numeric(5,4)  # Độ tin cậy dự đoán
    
    # Spam Detection Results
    is_spam: Boolean                    # True nếu là spam
    spam_score: Numeric(5,4)            # 0.0000 - 1.0000
    spam_confidence: Numeric(5,4)       # Độ tin cậy dự đoán
    
    # Model Information
    sentiment_model_version: String(50) # v1.0.0
    spam_model_version: String(50)      # v1.0.0
    
    # Analysis Metadata
    analyzed_at: DateTime               # Thời gian phân tích
    analysis_metadata: JSONB            # Thông tin bổ sung
    # Format: {
    #   "sentiment_raw_output": {...},
    #   "spam_features": {...},
    #   "processing_time_ms": 150
    # }
```

**Indexes:**
- `review_id` (unique, 1-1 relationship)
- `sentiment_label` (filter theo cảm xúc)
- `is_spam` (filter spam)

---

### 1.3. Model ProductTrustScore
**File:** `models/product.py`

Lưu chi tiết tính toán trust score

```python
class ProductTrustScore(Base):
    __tablename__ = "product_trust_scores"
    
    # Foreign Keys
    product_id: UUID (FK -> products.id, CASCADE, UNIQUE)
    
    # Trust Score
    trust_score: Numeric(5,2)           # 0.00 - 100.00
    
    # Review Statistics
    total_reviews: Integer              # Tổng số reviews
    analyzed_reviews: Integer           # Số reviews đã phân tích
    verified_reviews_count: Integer     # Reviews đã xác thực
    
    # Spam Statistics
    spam_reviews_count: Integer         # Số reviews spam
    spam_percentage: Numeric(5,2)       # % spam
    
    # Sentiment Statistics
    positive_reviews_count: Integer     # Reviews tích cực
    negative_reviews_count: Integer     # Reviews tiêu cực
    neutral_reviews_count: Integer      # Reviews trung lập
    average_sentiment_score: Numeric(5,4) # Điểm cảm xúc TB
    
    # Quality Metrics
    review_quality_score: Numeric(5,2)  # Điểm chất lượng (0-100)
    engagement_score: Numeric(5,2)      # Điểm tương tác (0-100)
    
    # Calculation Details
    calculated_at: DateTime             # Thời gian tính
    calculation_metadata: JSONB         # Chi tiết công thức
    # Format: {
    #   "formula_version": "1.0",
    #   "weights": {
    #     "sentiment_factor": 0.4,
    #     "spam_factor": 0.3,
    #     "volume_factor": 0.2,
    #     "verification_factor": 0.1
    #   },
    #   "component_scores": {
    #     "sentiment_factor": 0.85,
    #     "spam_factor": 0.92,
    #     ...
    #   }
    # }
```

**Indexes:**
- `product_id` (unique)
- `trust_score` (sắp xếp theo điểm)

---

### 1.4. Cập nhật Model Product
**File:** `models/product.py`

Thêm relationship và trường tiện ích

```python
class Product(Base):
    # ... existing fields ...
    
    # NEW: Quick access to trust score
    trust_score: Mapped[Optional[Numeric]] = mapped_column(
        Numeric(5,2), nullable=True
    )  # Denormalized for performance
    
    # NEW: Relationships
    reviews: Mapped[list["ProductReview"]] = relationship(
        "ProductReview",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    trust_score_detail: Mapped["ProductTrustScore"] = relationship(
        "ProductTrustScore",
        back_populates="product",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="select"
    )
```

---

## 🔧 Phase 2: Crawler Implementation

### 2.1. Review Crawler Service
**File:** `services/sale_smart_ai_app/crawler/review_crawler.py`

```python
class ReviewCrawler:
    """Crawl reviews từ các sàn TMĐT"""
    
    def crawl_shopee_reviews(product_url: str) -> List[ReviewData]
    def crawl_lazada_reviews(product_url: str) -> List[ReviewData]
    def crawl_tiki_reviews(product_url: str) -> List[ReviewData]
    
    def parse_review_html(html: str, platform: str) -> List[ReviewData]
    def extract_reviewer_info(element) -> ReviewerInfo
    def extract_rating(element) -> int
    def extract_images(element) -> List[str]
```

**Workflow:**
1. Nhận product URL từ LLM search
2. Xác định platform (Shopee/Lazada/Tiki)
3. Crawl product info + reviews bằng BeautifulSoup
4. Parse HTML thành structured data
5. Lưu vào database

**Lưu ý:**
- Handle pagination để lấy nhiều reviews
- Respect rate limiting
- Handle anti-bot mechanisms
- Retry logic cho failed requests

---

### 2.2. Product Crawler Integration
**File:** `services/sale_smart_ai_app/crawler/product_crawler.py`

```python
class ProductCrawler:
    """Crawl sản phẩm từ URL"""
    
    def crawl_product(url: str, project_id: UUID) -> Product:
        # 1. Crawl product info
        product_data = self._crawl_product_info(url)
        
        # 2. Crawl reviews
        reviews_data = self.review_crawler.crawl_reviews(url)
        
        # 3. Save to database
        product = self.product_repo.create(product_data)
        
        # 4. Save reviews
        for review_data in reviews_data:
            self.review_repo.create(review_data, product.id)
        
        # 5. Trigger analysis (async)
        self.trigger_review_analysis(product.id)
        
        return product
```

---

## 🤖 Phase 3: AI Models Integration

### 3.1. External AI Service Client
**File:** `services/sale_smart_ai_app/ai/review_analysis_client.py`

```python
class ReviewAnalysisClient:
    """Client để gọi AI models service"""
    
    def __init__(self):
        self.sentiment_api_url = settings.SENTIMENT_API_URL
        self.spam_api_url = settings.SPAM_API_URL
        self.api_key = settings.AI_SERVICE_API_KEY
    
    async def analyze_sentiment(self, text: str) -> SentimentResult:
        """
        Call Sentiment Analysis API
        
        Request:
        POST {sentiment_api_url}/predict
        {
            "text": "Review content here",
            "model_version": "v1.0.0"
        }
        
        Response:
        {
            "label": "positive",
            "score": 0.9234,
            "confidence": 0.95,
            "probabilities": {
                "positive": 0.9234,
                "negative": 0.0512,
                "neutral": 0.0254
            }
        }
        """
        
    async def detect_spam(self, text: str) -> SpamResult:
        """
        Call Spam Detection API
        
        Request:
        POST {spam_api_url}/predict
        {
            "text": "Review content here",
            "model_version": "v1.0.0"
        }
        
        Response:
        {
            "is_spam": false,
            "spam_score": 0.1234,
            "confidence": 0.92,
            "features": {
                "has_promotional_words": false,
                "repetitive_patterns": false,
                ...
            }
        }
        """
    
    async def batch_analyze(self, reviews: List[str]) -> List[AnalysisResult]:
        """Batch analysis cho performance"""
```

**Configuration:**
```python
# .env
SENTIMENT_API_URL=http://sentiment-service:8001
SPAM_API_URL=http://spam-service:8002
AI_SERVICE_API_KEY=your-api-key-here
AI_SERVICE_TIMEOUT=30
AI_SERVICE_MAX_RETRIES=3
```

---

### 3.2. Review Analysis Service
**File:** `services/sale_smart_ai_app/review_analysis.py`

```python
class ReviewAnalysisService:
    """Service phân tích reviews"""
    
    def __init__(self):
        self.ai_client = ReviewAnalysisClient()
        self.analysis_repo = ReviewAnalysisRepository()
    
    async def analyze_review(self, review_id: UUID) -> ReviewAnalysis:
        """Phân tích 1 review"""
        review = await self.review_repo.get(review_id)
        
        # Call AI services
        sentiment = await self.ai_client.analyze_sentiment(review.content)
        spam = await self.ai_client.detect_spam(review.content)
        
        # Save results
        analysis = ReviewAnalysis(
            review_id=review_id,
            sentiment_label=sentiment.label,
            sentiment_score=sentiment.score,
            sentiment_confidence=sentiment.confidence,
            is_spam=spam.is_spam,
            spam_score=spam.spam_score,
            spam_confidence=spam.confidence,
            analysis_metadata={
                "sentiment_probabilities": sentiment.probabilities,
                "spam_features": spam.features
            }
        )
        
        return await self.analysis_repo.create(analysis)
    
    async def analyze_product_reviews(self, product_id: UUID):
        """Phân tích tất cả reviews của 1 product"""
        reviews = await self.review_repo.get_by_product(product_id)
        
        # Batch analysis
        tasks = [self.analyze_review(r.id) for r in reviews]
        await asyncio.gather(*tasks)
        
        # Trigger trust score calculation
        await self.trust_score_service.calculate(product_id)
```

---

## 📊 Phase 4: Trust Score Calculation

### 4.1. Trust Score Formula

```python
def calculate_trust_score(product_id: UUID) -> float:
    """
    Trust Score = (
        sentiment_factor * 0.4 +
        spam_factor * 0.3 +
        volume_factor * 0.2 +
        verification_factor * 0.1
    ) * 100
    
    Range: 0 - 100
    """
    
    # 1. Sentiment Factor (0-1)
    sentiment_factor = calculate_sentiment_factor(product_id)
    # = (positive_count - negative_count) / total_reviews
    # Normalized to 0-1 range
    
    # 2. Spam Factor (0-1)
    spam_factor = 1 - (spam_count / total_reviews)
    # Càng ít spam càng tốt
    
    # 3. Volume Factor (0-1)
    volume_factor = calculate_volume_factor(total_reviews)
    # Logarithmic scale: log(reviews + 1) / log(1000)
    # 1 review = 0.0, 100 reviews = 0.67, 1000 reviews = 1.0
    
    # 4. Verification Factor (0-1)
    verification_factor = verified_count / total_reviews
    # Tỷ lệ verified purchases
    
    # Final Score
    trust_score = (
        sentiment_factor * 0.4 +
        spam_factor * 0.3 +
        volume_factor * 0.2 +
        verification_factor * 0.1
    ) * 100
    
    return round(trust_score, 2)
```

---

### 4.2. Trust Score Service
**File:** `services/sale_smart_ai_app/trust_score.py`

```python
class TrustScoreService:
    """Service tính toán trust score"""
    
    async def calculate_trust_score(self, product_id: UUID) -> ProductTrustScore:
        """Tính toán trust score cho product"""
        
        # 1. Get all analyzed reviews
        reviews = await self.review_repo.get_analyzed_reviews(product_id)
        
        # 2. Calculate statistics
        stats = self._calculate_statistics(reviews)
        
        # 3. Calculate component scores
        sentiment_factor = self._calculate_sentiment_factor(stats)
        spam_factor = self._calculate_spam_factor(stats)
        volume_factor = self._calculate_volume_factor(stats)
        verification_factor = self._calculate_verification_factor(stats)
        
        # 4. Calculate final trust score
        trust_score = (
            sentiment_factor * 0.4 +
            spam_factor * 0.3 +
            volume_factor * 0.2 +
            verification_factor * 0.1
        ) * 100
        
        # 5. Save to database
        trust_score_data = ProductTrustScore(
            product_id=product_id,
            trust_score=trust_score,
            total_reviews=stats.total,
            analyzed_reviews=stats.analyzed,
            spam_reviews_count=stats.spam_count,
            positive_reviews_count=stats.positive_count,
            negative_reviews_count=stats.negative_count,
            neutral_reviews_count=stats.neutral_count,
            calculation_metadata={
                "formula_version": "1.0",
                "weights": {
                    "sentiment_factor": 0.4,
                    "spam_factor": 0.3,
                    "volume_factor": 0.2,
                    "verification_factor": 0.1
                },
                "component_scores": {
                    "sentiment_factor": sentiment_factor,
                    "spam_factor": spam_factor,
                    "volume_factor": volume_factor,
                    "verification_factor": verification_factor
                }
            }
        )
        
        result = await self.trust_score_repo.upsert(trust_score_data)
        
        # 6. Update denormalized field in Product
        await self.product_repo.update(
            product_id,
            {"trust_score": trust_score}
        )
        
        return result
    
    def _calculate_sentiment_factor(self, stats) -> float:
        """Calculate sentiment component (0-1)"""
        if stats.total == 0:
            return 0.5  # Neutral if no reviews
        
        # Weighted by sentiment scores
        avg_sentiment = stats.average_sentiment_score
        return avg_sentiment  # Already 0-1
    
    def _calculate_spam_factor(self, stats) -> float:
        """Calculate spam component (0-1)"""
        if stats.total == 0:
            return 1.0
        
        spam_ratio = stats.spam_count / stats.total
        return 1 - spam_ratio  # Invert: less spam = higher score
    
    def _calculate_volume_factor(self, stats) -> float:
        """Calculate volume component (0-1)"""
        import math
        
        # Logarithmic scale
        # 0 reviews = 0.0
        # 10 reviews = 0.33
        # 100 reviews = 0.67
        # 1000+ reviews = 1.0
        
        if stats.total == 0:
            return 0.0
        
        score = math.log(stats.total + 1) / math.log(1001)
        return min(score, 1.0)
    
    def _calculate_verification_factor(self, stats) -> float:
        """Calculate verification component (0-1)"""
        if stats.total == 0:
            return 0.0
        
        return stats.verified_count / stats.total
```

---

## 🛣️ Phase 5: API Endpoints

### 5.1. Product Reviews Endpoints
**File:** `controllers/product_review_controller.py`

```python
# GET /api/products/{product_id}/reviews
# Query params: platform, sentiment, is_spam, page, limit
async def get_product_reviews(product_id: UUID, filters: ReviewFilters)

# GET /api/products/{product_id}/reviews/{review_id}
async def get_review_detail(product_id: UUID, review_id: UUID)

# POST /api/products/{product_id}/reviews/analyze
# Trigger analysis for all reviews of a product
async def analyze_product_reviews(product_id: UUID)

# POST /api/products/{product_id}/reviews/{review_id}/analyze
# Analyze a specific review
async def analyze_single_review(product_id: UUID, review_id: UUID)
```

---

### 5.2. Trust Score Endpoints
**File:** `controllers/trust_score_controller.py`

```python
# GET /api/products/{product_id}/trust-score
# Get trust score with detailed breakdown
async def get_trust_score(product_id: UUID)

# POST /api/products/{product_id}/trust-score/calculate
# Recalculate trust score
async def recalculate_trust_score(product_id: UUID)

# GET /api/products/top-trusted
# Get products sorted by trust score
async def get_top_trusted_products(project_id: UUID, limit: int)
```

**Response Example:**
```json
{
  "product_id": "uuid",
  "trust_score": 85.67,
  "breakdown": {
    "sentiment": {
      "factor": 0.85,
      "weight": 0.4,
      "contribution": 34.0,
      "details": {
        "positive": 850,
        "negative": 100,
        "neutral": 50,
        "average_score": 0.85
      }
    },
    "spam": {
      "factor": 0.92,
      "weight": 0.3,
      "contribution": 27.6,
      "details": {
        "total_reviews": 1000,
        "spam_detected": 80,
        "spam_percentage": 8.0
      }
    },
    "volume": {
      "factor": 0.69,
      "weight": 0.2,
      "contribution": 13.8,
      "details": {
        "total_reviews": 1000,
        "analyzed_reviews": 1000
      }
    },
    "verification": {
      "factor": 0.60,
      "weight": 0.1,
      "contribution": 6.0,
      "details": {
        "verified_purchases": 600,
        "total_reviews": 1000,
        "verification_rate": 60.0
      }
    }
  },
  "calculated_at": "2025-11-26T13:00:00Z"
}
```

---

## 📝 Phase 6: Schemas

### 6.1. Review Schemas
**File:** `schemas/product_review.py`

```python
class ProductReviewBase(BaseModel):
    reviewer_name: Optional[str]
    reviewer_id: Optional[str]
    rating: int = Field(ge=1, le=5)
    content: str
    review_date: datetime
    platform: str
    is_verified_purchase: bool = False
    helpful_count: int = 0
    images: Optional[List[str]]

class ProductReviewCreate(ProductReviewBase):
    product_id: UUID

class ProductReviewResponse(ProductReviewBase):
    id: UUID
    product_id: UUID
    source_url: Optional[str]
    crawled_at: datetime
    analysis: Optional["ReviewAnalysisResponse"]
```

---

### 6.2. Analysis Schemas
**File:** `schemas/review_analysis.py`

```python
class ReviewAnalysisResponse(BaseModel):
    id: UUID
    review_id: UUID
    sentiment_label: str
    sentiment_score: float
    sentiment_confidence: float
    is_spam: bool
    spam_score: float
    spam_confidence: float
    analyzed_at: datetime
```

---

### 6.3. Trust Score Schemas
**File:** `schemas/trust_score.py`

```python
class TrustScoreBreakdown(BaseModel):
    factor: float
    weight: float
    contribution: float
    details: dict

class TrustScoreResponse(BaseModel):
    product_id: UUID
    trust_score: float
    breakdown: dict[str, TrustScoreBreakdown]
    total_reviews: int
    analyzed_reviews: int
    calculated_at: datetime
```

---

## 🗄️ Phase 7: Repository Layer

### 7.1. ProductReviewRepository
**File:** `repositories/product_review_repository.py`

```python
class ProductReviewRepository(BaseRepository[ProductReview]):
    
    async def get_by_product(
        self,
        product_id: UUID,
        filters: Optional[ReviewFilters] = None
    ) -> List[ProductReview]:
        """Get reviews by product with filters"""
    
    async def get_analyzed_reviews(
        self,
        product_id: UUID
    ) -> List[ProductReview]:
        """Get reviews that have been analyzed"""
    
    async def get_unanalyzed_reviews(
        self,
        product_id: UUID
    ) -> List[ProductReview]:
        """Get reviews pending analysis"""
    
    async def count_by_sentiment(
        self,
        product_id: UUID
    ) -> dict:
        """Count reviews by sentiment label"""
```

---

### 7.2. ReviewAnalysisRepository
**File:** `repositories/review_analysis_repository.py`

```python
class ReviewAnalysisRepository(BaseRepository[ReviewAnalysis]):
    
    async def get_by_review(
        self,
        review_id: UUID
    ) -> Optional[ReviewAnalysis]:
        """Get analysis for a review"""
    
    async def get_statistics(
        self,
        product_id: UUID
    ) -> AnalysisStatistics:
        """Get aggregated statistics for a product"""
```

---

### 7.3. ProductTrustScoreRepository
**File:** `repositories/product_trust_score_repository.py`

```python
class ProductTrustScoreRepository(BaseRepository[ProductTrustScore]):
    
    async def upsert(
        self,
        trust_score: ProductTrustScore
    ) -> ProductTrustScore:
        """Insert or update trust score"""
    
    async def get_by_product(
        self,
        product_id: UUID
    ) -> Optional[ProductTrustScore]:
        """Get trust score for a product"""
    
    async def get_top_products(
        self,
        project_id: UUID,
        limit: int = 10
    ) -> List[ProductTrustScore]:
        """Get top trusted products"""
```

---

## 🔄 Phase 8: Background Jobs

### 8.1. Celery Tasks (Optional)
**File:** `tasks/review_tasks.py`

```python
@celery.task
def analyze_reviews_task(product_id: str):
    """Background task to analyze reviews"""
    service = ReviewAnalysisService()
    asyncio.run(service.analyze_product_reviews(UUID(product_id)))

@celery.task
def calculate_trust_score_task(product_id: str):
    """Background task to calculate trust score"""
    service = TrustScoreService()
    asyncio.run(service.calculate_trust_score(UUID(product_id)))

@celery.task
def recrawl_reviews_task(product_id: str):
    """Background task to recrawl reviews"""
    crawler = ReviewCrawler()
    # Crawl new reviews and trigger analysis
```

---

## 🧪 Phase 9: Testing

### 9.1. Unit Tests
```python
# tests/services/test_trust_score_service.py
def test_calculate_sentiment_factor()
def test_calculate_spam_factor()
def test_calculate_volume_factor()
def test_calculate_trust_score()

# tests/services/test_review_analysis_service.py
def test_analyze_review()
def test_batch_analyze()

# tests/crawler/test_review_crawler.py
def test_crawl_shopee_reviews()
def test_parse_review_html()
```

### 9.2. Integration Tests
```python
# tests/integration/test_trust_score_flow.py
async def test_full_trust_score_calculation_flow():
    # 1. Create product with reviews
    # 2. Analyze reviews
    # 3. Calculate trust score
    # 4. Verify results
```

---

## 📋 Implementation Checklist

### Database & Models
- [ ] Create ProductReview model
- [ ] Create ReviewAnalysis model
- [ ] Create ProductTrustScore model
- [ ] Update Product model with relationships
- [ ] Create migration files
- [ ] Run migrations

### Crawler
- [ ] Implement ReviewCrawler base class
- [ ] Implement Shopee crawler
- [ ] Implement Lazada crawler
- [ ] Implement Tiki crawler
- [ ] Add retry logic and error handling
- [ ] Integrate with ProductCrawler

### AI Integration
- [ ] Create ReviewAnalysisClient
- [ ] Implement sentiment analysis call
- [ ] Implement spam detection call
- [ ] Add batch processing
- [ ] Add error handling and retries
- [ ] Add configuration in .env

### Business Logic
- [ ] Create ReviewAnalysisService
- [ ] Create TrustScoreService
- [ ] Implement trust score formula
- [ ] Add component calculations
- [ ] Add statistics aggregation

### API Layer
- [ ] Create ProductReview schemas
- [ ] Create ReviewAnalysis schemas
- [ ] Create TrustScore schemas
- [ ] Create ProductReviewRepository
- [ ] Create ReviewAnalysisRepository
- [ ] Create TrustScoreRepository
- [ ] Create review endpoints
- [ ] Create trust score endpoints

### Background Jobs (Optional)
- [ ] Setup Celery/RQ
- [ ] Create review analysis task
- [ ] Create trust score calculation task
- [ ] Create recrawl task

### Testing
- [ ] Unit tests for services
- [ ] Unit tests for crawler
- [ ] Integration tests
- [ ] API endpoint tests

### Documentation
- [ ] API documentation
- [ ] Crawler documentation
- [ ] Trust score formula documentation

### Auto Discovery (Phase 10)
- [ ] Create FilterIntentParser service
- [ ] Create FilterCriteriaValidator service
- [ ] Create ProductFilterCriteria schema
- [ ] Create CrawledProductItemExtended schema
- [ ] Create ProductFilterService
- [ ] Create AutoImportService
- [ ] Create AutoDiscoveryService (orchestration)
- [ ] Enhance crawlers to extract extended fields
- [ ] Create API endpoint for auto discovery
- [ ] Add error handling and logging
- [ ] Add unit tests for intent parsing
- [ ] Add unit tests for filtering logic
- [ ] Add integration tests for complete flow

---

## 🚀 Deployment Considerations

### Environment Variables
```bash
# AI Services
SENTIMENT_API_URL=http://sentiment-service:8001
SPAM_API_URL=http://spam-service:8002
AI_SERVICE_API_KEY=your-api-key
AI_SERVICE_TIMEOUT=30
AI_SERVICE_MAX_RETRIES=3

# Crawler
CRAWLER_USER_AGENT=Mozilla/5.0...
CRAWLER_RATE_LIMIT=1  # requests per second
CRAWLER_MAX_RETRIES=3
CRAWLER_TIMEOUT=30

# Background Jobs
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Performance Optimization
- Use connection pooling for AI service calls
- Implement caching for trust scores
- Batch process reviews for analysis
- Use database indexes effectively
- Consider read replicas for heavy queries

### Monitoring
- Track AI service response times
- Monitor crawler success/failure rates
- Alert on trust score calculation failures
- Track review analysis queue length

---

## 📊 Expected Outcomes

### Metrics to Track
- **Coverage:** % products with trust scores
- **Freshness:** Average age of trust scores
- **Quality:** Correlation between trust score and actual product quality
- **Performance:** Time to calculate trust score
- **AI Accuracy:** Sentiment/spam detection accuracy

### Success Criteria
- ✅ 95%+ products have trust scores
- ✅ Trust scores updated within 24h of new reviews
- ✅ <5s API response time for trust score endpoint
- ✅ >90% AI model accuracy
- ✅ Successfully crawl reviews from all 3 platforms

---

## 🤖 Phase 10: Automated Product Discovery & Import Flow

### 10.1. Tổng quan Flow

Flow tự động hóa hoàn toàn từ tìm kiếm ý tưởng đến nhập liệu sản phẩm:

```
User Text Input → AI Intent Parser → Filter Criteria (JSON) → AI Validation
                                                                     ↓
                                                              Valid Criteria
                                                                     ↓
AI Discovery (LLM Search) → Search Links → Auto Crawl → Product List (Raw Data)
                                                                     ↓
                                                              AI Filtering Service
                                                                     ↓
                                                              Filtered Products
                                                                     ↓
                                                              Auto Import Service
                                                                     ↓
                                                              Products in Database
```

**Các bước:**
1. **AI Discovery**: Tìm kiếm từ khóa và ý tưởng sản phẩm (sử dụng `ProductAIAgent`)
2. **Auto Crawl**: Tự động crawl danh sách sản phẩm từ các kết quả tìm kiếm
3. **AI Filtering**: Lọc sản phẩm tốt nhất dựa trên tiêu chí người dùng
4. **Auto Import**: Tự động tạo sản phẩm trong Database

---

### 10.2. AI Intent Parser & Filter Criteria Extraction

**File:** `services/features/product_intelligence/ai/filter_intent_parser.py`

```python
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ValidationError
from core.llm.base import BaseAgent

class ProductFilterCriteria(BaseModel):
    """Structured filter criteria extracted from user input"""
    
    # Rating filters
    min_rating: Optional[float] = Field(None, ge=0, le=5, description="Minimum rating score")
    max_rating: Optional[float] = Field(None, ge=0, le=5, description="Maximum rating score")
    
    # Review count filters
    min_review_count: Optional[int] = Field(None, ge=0, description="Minimum number of reviews")
    max_review_count: Optional[int] = Field(None, ge=0, description="Maximum number of reviews")
    
    # Price filters
    min_price: Optional[float] = Field(None, ge=0, description="Minimum price in VND")
    max_price: Optional[float] = Field(None, ge=0, description="Maximum price in VND")
    
    # Platform & Seller filters
    platforms: Optional[list[str]] = Field(None, description="Filter by platforms: shopee, lazada, tiki")
    is_mall: Optional[bool] = Field(None, description="Only mall sellers")
    is_verified_seller: Optional[bool] = Field(None, description="Only verified sellers")
    
    # Keyword filters
    required_keywords: Optional[list[str]] = Field(None, description="Keywords that must appear in product name")
    excluded_keywords: Optional[list[str]] = Field(None, description="Keywords to exclude")
    
    # Sales & Trust filters
    min_sales_count: Optional[int] = Field(None, ge=0, description="Minimum sales count")
    min_trust_score: Optional[float] = Field(None, ge=0, le=100, description="Minimum trust score")
    
    # Trust badge filters
    trust_badge_types: Optional[list[str]] = Field(None, description="Trust badge types: TikiNOW, Yêu thích, etc.")
    
    # Brand filters
    required_brands: Optional[list[str]] = Field(None, description="Required brands")
    excluded_brands: Optional[list[str]] = Field(None, description="Excluded brands")
    
    # Location filters
    seller_locations: Optional[list[str]] = Field(None, description="Seller locations")

class FilterIntentParser:
    """Parse natural language user input into structured filter criteria"""
    
    def __init__(self, llm_agent: BaseAgent):
        self.llm = llm_agent
    
    async def parse_user_intent(self, user_text: str) -> tuple[Optional[ProductFilterCriteria], Optional[str]]:
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
            response = self.llm.generate(prompt, response_schema=ProductFilterCriteria)
            criteria = ProductFilterCriteria(**response.parsed)
            
            # Validate criteria makes sense
            validation_error = self._validate_criteria(criteria)
            if validation_error:
                return None, validation_error
            
            return criteria, None
            
        except ValidationError as e:
            return None, f"Invalid criteria format: {str(e)}"
        except Exception as e:
            return None, f"Failed to parse intent: {str(e)}"
    
    def _validate_criteria(self, criteria: ProductFilterCriteria) -> Optional[str]:
        """Validate that criteria makes logical sense"""
        
        # Check rating range
        if criteria.min_rating and criteria.max_rating:
            if criteria.min_rating > criteria.max_rating:
                return "min_rating cannot be greater than max_rating"
        
        # Check price range
        if criteria.min_price and criteria.max_price:
            if criteria.min_price > criteria.max_price:
                return "min_price cannot be greater than max_price"
        
        # Check review count range
        if criteria.min_review_count and criteria.max_review_count:
            if criteria.min_review_count > criteria.max_review_count:
                return "min_review_count cannot be greater than max_review_count"
        
        return None
```

**Example Usage:**
```python
# Input: "tôi muốn sản phẩm có rating 4.5 trở lên, review 100 trở lên, mall, keyword chính hãng, premium, max price 500000"

# Output:
{
    "min_rating": 4.5,
    "min_review_count": 100,
    "is_mall": true,
    "required_keywords": ["chính hãng", "premium"],
    "max_price": 500000
}
```

---

### 10.3. AI Criteria Validator

**File:** `services/features/product_intelligence/ai/filter_validator.py`

```python
from typing import Optional
from core.llm.base import BaseAgent
from .filter_intent_parser import ProductFilterCriteria

class FilterCriteriaValidator:
    """Validate extracted criteria using AI to ensure it matches user intent"""
    
    def __init__(self, llm_agent: BaseAgent):
        self.llm = llm_agent
    
    async def validate_criteria(
        self, 
        user_text: str, 
        criteria: ProductFilterCriteria
    ) -> tuple[bool, Optional[str]]:
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
{criteria.model_dump_json(indent=2)}

Nhiệm vụ: Kiểm tra xem criteria có phản ánh đúng yêu cầu của người dùng không.

Trả về JSON:
{{
    "is_valid": true/false,
    "reason": "Lý do nếu không hợp lệ"
}}

Nếu criteria không đúng hoặc thiếu thông tin quan trọng, trả về is_valid: false và giải thích lý do.
"""
        
        try:
            response = self.llm.generate(prompt)
            result = json.loads(response.text)
            
            if not result.get("is_valid", False):
                return False, result.get("reason", "AI không hiểu yêu cầu của bạn")
            
            return True, None
            
        except Exception as e:
            # If validation fails, assume invalid
            return False, f"Không thể xác thực yêu cầu: {str(e)}"
```

---

### 10.4. Product Data Schema (Extended)

**File:** `schemas/product_crawler.py` (Update)

```python
class CrawledProductItemExtended(BaseModel):
    """Extended product data from crawler with all fields"""
    
    # Basic Info
    platform: str  # tiki, lazada, shopee
    product_name: str
    product_url: str
    
    # Pricing
    price_current: float
    price_original: Optional[float] = None
    discount_rate: Optional[float] = None
    
    # Ratings & Reviews
    rating_score: Optional[float] = None  # 0-5
    review_count: Optional[int] = None
    sales_count: Optional[int] = None
    
    # Seller Info
    is_mall: bool = False
    is_verified_seller: bool = False
    seller_location: Optional[str] = None
    brand: Optional[str] = None
    
    # Trust & Quality
    trust_badge_type: Optional[str] = None  # TikiNOW, Yêu thích, etc.
    trust_score: Optional[float] = None  # 0-100
    
    # Keywords & Metadata
    keywords_in_title: list[str] = []
    category: Optional[str] = None
    subcategory: Optional[str] = None
    
    # Images
    image_urls: list[str] = []
    
    # Additional metadata
    metadata: dict[str, Any] = {}
```

---

### 10.5. AI Product Filtering Service

**File:** `services/features/product_intelligence/filtering/product_filter_service.py`

```python
from typing import List
from schemas.product_crawler import CrawledProductItemExtended
from .filter_intent_parser import ProductFilterCriteria

class ProductFilterService:
    """Filter products based on criteria"""
    
    def filter_products(
        self,
        products: List[CrawledProductItemExtended],
        criteria: ProductFilterCriteria
    ) -> List[CrawledProductItemExtended]:
        """Filter products based on criteria"""
        
        filtered = []
        
        for product in products:
            if self._matches_criteria(product, criteria):
                filtered.append(product)
        
        return filtered
    
    def _matches_criteria(
        self,
        product: CrawledProductItemExtended,
        criteria: ProductFilterCriteria
    ) -> bool:
        """Check if product matches all criteria"""
        
        # Rating filter
        if criteria.min_rating and (not product.rating_score or product.rating_score < criteria.min_rating):
            return False
        if criteria.max_rating and (product.rating_score and product.rating_score > criteria.max_rating):
            return False
        
        # Review count filter
        if criteria.min_review_count and (not product.review_count or product.review_count < criteria.min_review_count):
            return False
        if criteria.max_review_count and (product.review_count and product.review_count > criteria.max_review_count):
            return False
        
        # Price filter
        if criteria.min_price and product.price_current < criteria.min_price:
            return False
        if criteria.max_price and product.price_current > criteria.max_price:
            return False
        
        # Platform filter
        if criteria.platforms and product.platform not in criteria.platforms:
            return False
        
        # Mall filter
        if criteria.is_mall is not None and product.is_mall != criteria.is_mall:
            return False
        
        # Verified seller filter
        if criteria.is_verified_seller is not None and product.is_verified_seller != criteria.is_verified_seller:
            return False
        
        # Required keywords filter
        if criteria.required_keywords:
            product_name_lower = product.product_name.lower()
            if not all(keyword.lower() in product_name_lower for keyword in criteria.required_keywords):
                return False
        
        # Excluded keywords filter
        if criteria.excluded_keywords:
            product_name_lower = product.product_name.lower()
            if any(keyword.lower() in product_name_lower for keyword in criteria.excluded_keywords):
                return False
        
        # Sales count filter
        if criteria.min_sales_count and (not product.sales_count or product.sales_count < criteria.min_sales_count):
            return False
        
        # Trust score filter
        if criteria.min_trust_score and (not product.trust_score or product.trust_score < criteria.min_trust_score):
            return False
        
        # Trust badge filter
        if criteria.trust_badge_types and product.trust_badge_type not in criteria.trust_badge_types:
            return False
        
        # Required brands filter
        if criteria.required_brands and (not product.brand or product.brand not in criteria.required_brands):
            return False
        
        # Excluded brands filter
        if criteria.excluded_brands and product.brand in criteria.excluded_brands:
            return False
        
        # Seller location filter
        if criteria.seller_locations and (not product.seller_location or product.seller_location not in criteria.seller_locations):
            return False
        
        return True
```

---

### 10.6. Auto Import Service

**File:** `services/features/product_intelligence/import/auto_import_service.py`

```python
from uuid import UUID
from typing import List
from sqlalchemy.orm import Session

from schemas.product_crawler import CrawledProductItemExtended
from schemas.product import ProductCreate
from services.core.product import ProductService
from repositories.product import ProductRepository

class AutoImportService:
    """Automatically import filtered products to database"""
    
    def __init__(self, db: Session):
        self.db = db
        self.product_service = ProductService(db)
    
    def import_products(
        self,
        products: List[CrawledProductItemExtended],
        project_id: UUID,
        user_id: UUID,
        crawl_session_id: Optional[UUID] = None
    ) -> List[UUID]:
        """Import products to database"""
        
        imported_ids = []
        
        for product_data in products:
            try:
                # Convert crawled data to ProductCreate schema
                product_create = ProductCreate(
                    project_id=project_id,
                    crawl_session_id=crawl_session_id,
                    name=product_data.product_name,
                    brand=product_data.brand,
                    category=product_data.category,
                    subcategory=product_data.subcategory,
                    platform=product_data.platform,
                    url=product_data.product_url,
                    current_price=product_data.price_current,
                    original_price=product_data.price_original,
                    discount_rate=product_data.discount_rate,
                    currency="VND",
                    data_source="auto_crawl"
                )
                
                # Create product
                product = self.product_service.create_product(
                    payload=product_create,
                    user_id=user_id
                )
                
                imported_ids.append(product.id)
                
            except Exception as e:
                # Log error but continue with other products
                logger.error(f"Failed to import product {product_data.product_url}: {str(e)}")
                continue
        
        return imported_ids
```

---

### 10.7. Orchestration Service - Complete Flow

**File:** `services/features/product_intelligence/orchestration/auto_discovery_service.py`

```python
from uuid import UUID
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from services.features.product_intelligence.agents.product_agent import ProductAIAgent
from services.features.product_intelligence.crawler.crawler_service import CrawlerService
from services.features.product_intelligence.ai.filter_intent_parser import FilterIntentParser, ProductFilterCriteria
from services.features.product_intelligence.ai.filter_validator import FilterCriteriaValidator
from services.features.product_intelligence.filtering.product_filter_service import ProductFilterService
from services.features.product_intelligence.import.auto_import_service import AutoImportService
from core.llm.factory import AgentFactory

class AutoDiscoveryService:
    """Orchestrate complete automated product discovery and import flow"""
    
    def __init__(self, db: Session):
        self.db = db
        self.product_agent = ProductAIAgent(db)
        self.crawler_service = CrawlerService(db)
        self.filter_service = ProductFilterService()
        self.import_service = AutoImportService(db)
        
        # Initialize LLM for intent parsing
        llm_agent = AgentFactory.create("google")  # or use project's assigned model
        self.intent_parser = FilterIntentParser(llm_agent)
        self.criteria_validator = FilterCriteriaValidator(llm_agent)
    
    async def execute_auto_discovery(
        self,
        project_id: UUID,
        user_id: UUID,
        user_query: str,
        filter_criteria_text: Optional[str] = None,
        max_products: int = 20
    ) -> Dict[str, Any]:
        """
        Execute complete automated discovery flow
        
        Args:
            project_id: Project to import products to
            user_query: Product search query (e.g., "cà phê hòa tan")
            filter_criteria_text: Natural language filter criteria (e.g., "rating 4.5+, review 100+, mall")
            max_products: Maximum products to import
        
        Returns:
            {
                "status": "success" | "error",
                "message": "...",
                "filter_criteria": {...},
                "products_found": 100,
                "products_filtered": 15,
                "products_imported": 15,
                "imported_product_ids": [...]
            }
        """
        
        try:
            # Step 1: Parse filter criteria from user text
            filter_criteria = None
            if filter_criteria_text:
                criteria, error = await self.intent_parser.parse_user_intent(filter_criteria_text)
                
                if error:
                    return {
                        "status": "error",
                        "message": f"Không thể phân tích tiêu chí lọc: {error}",
                        "error_type": "intent_parsing_failed"
                    }
                
                # Step 2: Validate criteria with AI
                is_valid, validation_error = await self.criteria_validator.validate_criteria(
                    filter_criteria_text,
                    criteria
                )
                
                if not is_valid:
                    return {
                        "status": "error",
                        "message": validation_error or "AI không hiểu yêu cầu của bạn",
                        "error_type": "criteria_validation_failed",
                        "extracted_criteria": criteria.model_dump()
                    }
                
                filter_criteria = criteria
            
            # Step 3: AI Discovery - Find product ideas and search links
            project_info = {
                "id": project_id,
                "target_product_name": user_query,
                "target_budget_range": filter_criteria.max_price if filter_criteria else None,
                "description": user_query
            }
            
            search_result = self.product_agent.search_products(
                project_info=project_info,
                user_id=user_id,
                limit=max_products * 2,  # Get more to filter
                platform="all"
            )
            
            if not search_result.get("products") or not search_result["products"]:
                return {
                    "status": "error",
                    "message": "Không tìm thấy sản phẩm nào từ AI search",
                    "error_type": "no_products_found"
                }
            
            # Step 4: Auto Crawl - Crawl products from search links
            all_crawled_products = []
            
            for product_link in search_result.get("shopee_products", []):
                try:
                    # Determine platform from URL
                    scraper = ScraperFactory.get_scraper(product_link)
                    crawled_items = scraper.crawl_search_results(product_link, max_products=1)
                    
                    if crawled_items:
                        # Convert to extended format
                        for item in crawled_items:
                            extended = self._convert_to_extended(item, product_link)
                            all_crawled_products.append(extended)
                
                except Exception as e:
                    logger.warning(f"Failed to crawl {product_link}: {str(e)}")
                    continue
            
            # Step 5: AI Filtering - Filter products based on criteria
            filtered_products = all_crawled_products
            if filter_criteria:
                filtered_products = self.filter_service.filter_products(
                    all_crawled_products,
                    filter_criteria
                )
            
            # Limit to max_products
            filtered_products = filtered_products[:max_products]
            
            # Step 6: Auto Import - Import filtered products to database
            imported_ids = self.import_service.import_products(
                products=filtered_products,
                project_id=project_id,
                user_id=user_id
            )
            
            return {
                "status": "success",
                "message": f"Đã import {len(imported_ids)} sản phẩm thành công",
                "filter_criteria": filter_criteria.model_dump() if filter_criteria else None,
                "products_found": len(all_crawled_products),
                "products_filtered": len(filtered_products),
                "products_imported": len(imported_ids),
                "imported_product_ids": imported_ids
            }
            
        except Exception as e:
            logger.error(f"Auto discovery failed: {str(e)}")
            return {
                "status": "error",
                "message": f"Lỗi trong quá trình tự động hóa: {str(e)}",
                "error_type": "execution_error"
            }
    
    def _convert_to_extended(
        self,
        item: CrawledProductItem,
        source_url: str
    ) -> CrawledProductItemExtended:
        """Convert basic crawled item to extended format"""
        
        # Extract additional info from URL or item metadata
        platform = item.platform or self._detect_platform(source_url)
        
        return CrawledProductItemExtended(
            platform=platform,
            product_name=item.name,
            product_url=item.link or source_url,
            price_current=float(item.price) if item.price else 0.0,
            rating_score=item.rating,
            review_count=None,  # May need to crawl detail page
            sales_count=self._parse_sales_count(item.sold),
            is_mall=False,  # Need to detect from detail page
            brand=None,
            keywords_in_title=self._extract_keywords(item.name),
            image_urls=[item.img] if item.img else []
        )
    
    def _detect_platform(self, url: str) -> str:
        """Detect platform from URL"""
        if "shopee" in url.lower():
            return "shopee"
        elif "lazada" in url.lower():
            return "lazada"
        elif "tiki" in url.lower():
            return "tiki"
        return "unknown"
    
    def _parse_sales_count(self, sold: Any) -> Optional[int]:
        """Parse sales count from various formats"""
        if sold is None:
            return None
        if isinstance(sold, int):
            return sold
        if isinstance(sold, str):
            # Handle "1.2k" format
            sold = sold.lower().replace(",", "")
            if "k" in sold:
                return int(float(sold.replace("k", "")) * 1000)
            try:
                return int(sold)
            except:
                return None
        return None
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from product name"""
        # Simple keyword extraction (can be enhanced with NLP)
        words = text.lower().split()
        # Filter out common words
        stop_words = {"và", "của", "cho", "với", "từ", "đến", "có", "là", "một", "các"}
        keywords = [w for w in words if len(w) > 2 and w not in stop_words]
        return keywords[:10]  # Limit to 10 keywords
```

---

### 10.8. API Endpoint

**File:** `controllers/product_auto_discovery.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.dependencies.db import get_db
from core.dependencies.auth import verify_token
from schemas.auth import TokenData
from services.features.product_intelligence.orchestration.auto_discovery_service import AutoDiscoveryService

router = APIRouter(prefix="/products/auto-discovery", tags=["Auto Discovery"])

class AutoDiscoveryRequest(BaseModel):
    project_id: UUID
    user_query: str = Field(..., description="Product search query")
    filter_criteria: Optional[str] = Field(None, description="Natural language filter criteria")
    max_products: int = Field(default=20, ge=1, le=100)

@router.post("/execute")
async def execute_auto_discovery(
    request: AutoDiscoveryRequest,
    db: Session = Depends(get_db),
    token: TokenData = Depends(verify_token),
):
    """Execute automated product discovery and import flow"""
    
    service = AutoDiscoveryService(db)
    result = await service.execute_auto_discovery(
        project_id=request.project_id,
        user_id=token.user_id,
        user_query=request.user_query,
        filter_criteria_text=request.filter_criteria,
        max_products=request.max_products
    )
    
    if result["status"] == "error":
        raise HTTPException(
            status_code=400,
            detail=result["message"]
        )
    
    return result
```

**Example Request:**
```json
{
  "project_id": "uuid-here",
  "user_query": "cà phê hòa tan",
  "filter_criteria": "tôi muốn sản phẩm có rating 4.5 trở lên, review 100 trở lên, mall, keyword chính hãng, premium, max price 500000",
  "max_products": 20
}
```

**Example Response:**
```json
{
  "status": "success",
  "message": "Đã import 15 sản phẩm thành công",
  "filter_criteria": {
    "min_rating": 4.5,
    "min_review_count": 100,
    "is_mall": true,
    "required_keywords": ["chính hãng", "premium"],
    "max_price": 500000
  },
  "products_found": 100,
  "products_filtered": 15,
  "products_imported": 15,
  "imported_product_ids": ["uuid1", "uuid2", ...]
}
```

---

### 10.9. Enhanced Crawler for Extended Data

**File:** `services/features/product_intelligence/crawler/enhanced_product_crawler.py`

```python
from typing import List
from schemas.product_crawler import CrawledProductItemExtended
from .scraper_factory import ScraperFactory

class EnhancedProductCrawler:
    """Enhanced crawler that extracts all extended fields"""
    
    def crawl_product_extended(self, product_url: str) -> CrawledProductItemExtended:
        """Crawl product with all extended fields"""
        
        scraper = ScraperFactory.get_scraper(product_url)
        
        # Crawl product detail page
        detail = scraper.crawl_product_details(product_url, review_limit=0)
        
        # Extract platform
        platform = self._detect_platform(product_url)
        
        # Build extended product data
        # This requires parsing HTML/API responses to extract:
        # - is_mall
        # - brand
        # - seller_location
        # - trust_badge_type
        # - review_count (if not in search results)
        # etc.
        
        return CrawledProductItemExtended(
            platform=platform,
            product_name=detail.link,  # Need to extract from detail
            product_url=product_url,
            # ... extract all fields from detail page
        )
    
    def _detect_platform(self, url: str) -> str:
        """Detect platform from URL"""
        if "shopee" in url.lower():
            return "shopee"
        elif "lazada" in url.lower():
            return "lazada"
        elif "tiki" in url.lower():
            return "tiki"
        return "unknown"
```

---

### 10.10. Implementation Checklist

- [ ] Create `FilterIntentParser` service
- [ ] Create `FilterCriteriaValidator` service
- [ ] Create `ProductFilterCriteria` schema
- [ ] Create `CrawledProductItemExtended` schema
- [ ] Create `ProductFilterService`
- [ ] Create `AutoImportService`
- [ ] Create `AutoDiscoveryService` (orchestration)
- [ ] Enhance crawlers to extract extended fields (is_mall, brand, seller_location, etc.)
- [ ] Create API endpoint `/products/auto-discovery/execute`
- [ ] Add error handling and logging
- [ ] Add unit tests for intent parsing
- [ ] Add unit tests for filtering logic
- [ ] Add integration tests for complete flow
- [ ] Update documentation

---

## 🎓 Next Steps

1. **Review & Approve Plan** ✓
2. **Setup Development Environment**
   - Configure AI service endpoints
   - Setup test data
3. **Phase 1: Database** (1-2 days)
   - Create models
   - Create migrations
4. **Phase 2: Crawler** (2-3 days)
   - Implement crawlers
   - Test with real platforms
5. **Phase 3: AI Integration** (1-2 days)
   - Setup client
   - Test API calls
6. **Phase 4: Trust Score** (2-3 days)
   - Implement calculation
   - Fine-tune formula
7. **Phase 5-7: API Layer** (2-3 days)
   - Schemas, repos, endpoints
8. **Phase 8-9: Jobs & Testing** (2-3 days)
   - Background jobs
   - Comprehensive testing
9. **Phase 10: Auto Discovery** (3-4 days)
   - Implement intent parser
   - Implement filtering service
   - Implement auto import
   - Test complete flow
10. **Deployment & Monitoring** (1-2 days)

**Total Estimated Time:** 3-4 weeks

---

## 📞 Support & Questions

Nếu có thắc mắc trong quá trình implement:
1. Review lại plan này
2. Check documentation của AI services
3. Test với sample data trước
4. Monitor logs và metrics

Good luck! 🚀
