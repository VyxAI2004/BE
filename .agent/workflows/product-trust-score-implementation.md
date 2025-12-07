---
description: Kế hoạch triển khai Product Trust Score dựa trên phân tích Review
---

# 🎯 Kế hoạch triển khai Product Trust Score

## Tổng quan
Mở rộng hệ thống Product để tính toán **điểm tin cậy (Trust Score)** dựa trên phân tích cảm xúc và phát hiện spam trong reviews được crawl từ các sàn thương mại điện tử.

### Kiến trúc hệ thống
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
9. **Deployment & Monitoring** (1-2 days)

**Total Estimated Time:** 2-3 weeks

---

## 📞 Support & Questions

Nếu có thắc mắc trong quá trình implement:
1. Review lại plan này
2. Check documentation của AI services
3. Test với sample data trước
4. Monitor logs và metrics

Good luck! 🚀
