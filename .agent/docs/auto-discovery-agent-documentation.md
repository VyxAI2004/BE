# Auto Discovery Agent - Tài liệu tổng hợp

## Tổng quan

Auto Discovery Agent là một hệ thống tự động hóa hoàn toàn quy trình tìm kiếm, lọc và nhập sản phẩm từ ngôn ngữ tự nhiên của người dùng. Hệ thống sử dụng nhiều AI agents để xử lý từng bước trong workflow.

## Workflow tổng quan

```
User Input (Natural Language)
    ↓
[Step 0] Natural Language Parser (AI)
    ↓
[Step 1] Filter Intent Parser (AI)
    ↓
[Step 2] Filter Criteria Validator (AI)
    ↓
[Step 3] Product AI Agent - Discovery (AI)
    ↓
[Step 4] Auto Crawl (BeautifulSoup)
    ↓
[Step 5] Product Filter Service (Logic-based)
    ↓
[Step 5.5] Product Ranking Service (AI) - Nếu cần
    ↓
[Step 6] Auto Import Service
    ↓
Database (Products saved)
```

---

## Ví dụ sử dụng

### Ví dụ 1: Tìm kiếm cơ bản với filter

**Input:**
```json
{
  "project_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "user_query": "tìm kiếm cho tôi 2 sản phẩm mẫu dựa trên project của tôi, yêu cầu là có hơn 100 reviews và trên sàn lazada"
}
```

**Output:**
```json
{
  "status": "success",
  "message": "Đã import 2 sản phẩm thành công",
  "products_found": 20,
  "products_filtered": 6,
  "products_imported": 2,
  "imported_product_ids": ["uuid1", "uuid2"]
}
```

---

### Ví dụ 2: Tìm kiếm với nhiều tiêu chí

**Input:**
```json
{
  "project_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "user_query": "tìm 5 sản phẩm cà phê rang xay, rating 4.5 trở lên, review 100+, mall, max price 500000, trên lazada và tiki"
}
```

**Output:**
```json
{
  "status": "success",
  "message": "Đã import 5 sản phẩm thành công",
  "products_found": 20,
  "products_filtered": 8,
  "products_imported": 5,
  "imported_product_ids": ["uuid1", "uuid2", "uuid3", "uuid4", "uuid5"],
  "extracted_criteria": {
    "min_rating": 4.5,
    "min_review_count": 100,
    "is_mall": true,
    "max_price": 500000,
    "platforms": ["lazada", "tiki"]
  }
}
```

---

### Ví dụ 3: Tìm kiếm dựa trên project (sử dụng thông tin project)

**Input:**
```json
{
  "project_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "user_query": "tìm 3 sản phẩm mẫu dựa trên project của tôi"
}
```

**Project Info:**
- Name: "Cà phê rang xay"
- Target Product: "cà phê rang xay"
- Budget: 120,000 VND
- Category: "Đồ uống"

**Output:**
```json
{
  "status": "success",
  "message": "Đã import 3 sản phẩm thành công",
  "products_found": 20,
  "products_filtered": 12,
  "products_imported": 3,
  "imported_product_ids": ["uuid1", "uuid2", "uuid3"]
}
```

---

## Chi tiết từng Step và AI Service

### Step 0: Natural Language Parser

**Service:** `NaturalLanguageParser`

**Mục đích:** Phân tích input ngôn ngữ tự nhiên của user và trích xuất:
- `user_query`: Từ khóa tìm kiếm
- `filter_criteria`: Tiêu chí lọc (dạng text)
- `max_products`: Số lượng sản phẩm cần

**Input:**
```python
{
    "user_text": "tìm kiếm cho tôi 2 sản phẩm mẫu dựa trên project của tôi, yêu cầu là có hơn 100 reviews và trên sàn lazada",
    "project_info": {
        "name": "cà phê rang xay",
        "description": "cà phê phân khúc tầm trung, khoảng 120k 1 kg",
        "target_product_name": "cà phê rang xay",
        "target_product_category": "Đồ uống",
        "target_budget_range": 120000,
        "currency": "VND"
    }
}
```

**AI Prompt (tóm tắt):**
```
Bạn là một AI chuyên phân tích yêu cầu tìm kiếm sản phẩm từ người dùng.

Nhiệm vụ: Phân tích đoạn text sau và trích xuất các thông tin:
1. Từ khóa tìm kiếm (user_query)
2. Tiêu chí lọc (filter_criteria)
3. Số lượng sản phẩm cần (max_products)

Input từ người dùng: "{user_text}"

Thông tin project đầy đủ:
- Tên project: {project_name}
- Mô tả project: {description}
- Sản phẩm mục tiêu: {target_product_name}
- Ngân sách: {budget}

Trả về JSON format:
{
    "user_query": "từ khóa tìm kiếm",
    "filter_criteria": "tiêu chí lọc hoặc null",
    "max_products": số lượng
}
```

**Output:**
```python
(
    "cà phê rang xay",  # user_query
    "{'reviews_min': 100, 'platform': 'lazada'}",  # filter_criteria (text)
    2,  # max_products
    None  # error (None nếu thành công)
)
```

**Lỗi có thể xảy ra:**
- `"Không thể parse JSON từ AI response"`
- `"Không tìm thấy từ khóa tìm kiếm trong input"`

---

### Step 1: Filter Intent Parser

**Service:** `FilterIntentParser`

**Mục đích:** Chuyển đổi filter criteria từ text sang structured `ProductFilterCriteria` object

**Input:**
```python
{
    "user_text": "{'reviews_min': 100, 'platform': 'lazada', 'max_price': 120000}"
}
```

**AI Prompt (tóm tắt):**
```
Bạn là một AI chuyên phân tích yêu cầu lọc sản phẩm từ người dùng.

Nhiệm vụ: Phân tích đoạn text sau và trích xuất các tiêu chí lọc sản phẩm thành JSON format.

Input từ người dùng: "{user_text}"

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

Trả về JSON format:
{
    "min_rating": null,
    "max_rating": null,
    "min_review_count": null,
    "max_review_count": null,
    "min_price": null,
    "max_price": null,
    "platforms": null,
    "is_mall": null,
    ...
}
```

**Output:**
```python
(
    ProductFilterCriteria(
        min_rating=None,
        max_rating=None,
        min_review_count=100,
        max_review_count=None,
        min_price=None,
        max_price=120000.0,
        platforms=["lazada"],
        is_mall=None,
        ...
    ),
    None  # error (None nếu thành công)
)
```

**Lỗi có thể xảy ra:**
- `"Không thể parse JSON từ AI response"`
- `"Invalid criteria format: {validation_error}"`
- `"min_rating cannot be greater than max_rating"` (nếu logic không hợp lý)

---

### Step 2: Filter Criteria Validator

**Service:** `FilterCriteriaValidator`

**Mục đích:** Xác thực xem criteria đã được trích xuất có đúng với ý định của user không

**Input:**
```python
{
    "user_text": "{'reviews_min': 100, 'platform': 'lazada', 'max_price': 120000}",
    "criteria": ProductFilterCriteria(
        min_review_count=100,
        max_price=120000.0,
        platforms=["lazada"]
    )
}
```

**AI Prompt (tóm tắt):**
```
Bạn là một AI validator kiểm tra xem criteria đã được trích xuất có đúng với ý định của người dùng không.

Input từ người dùng: "{user_text}"

Criteria đã trích xuất:
{
  "min_review_count": 100,
  "max_price": 120000.0,
  "platforms": ["lazada"]
}

Nhiệm vụ: Kiểm tra xem criteria có phản ánh đúng yêu cầu của người dùng không.

Trả về JSON:
{
    "is_valid": true/false,
    "reason": "Lý do nếu không hợp lệ"
}

Nếu criteria không đúng hoặc thiếu thông tin quan trọng, trả về is_valid: false và giải thích lý do.
```

**Output:**
```python
(
    True,  # is_valid
    None  # error_message (None nếu valid)
)
```

**Hoặc nếu không valid:**
```python
(
    False,  # is_valid
    "AI không hiểu yêu cầu của bạn"  # error_message
)
```

**Lỗi có thể xảy ra:**
- `"Không thể parse validation response"`
- `"AI không hiểu yêu cầu của bạn"` (nếu AI phát hiện criteria không đúng)

---

### Step 3: Product AI Agent - Discovery

**Service:** `ProductAIAgent.search_products()`

**Mục đích:** Sử dụng AI để tìm kiếm và phân tích sản phẩm, sau đó tạo search URLs cho các platform

**Input:**
```python
{
    "project_info": {
        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "name": "cà phê rang xay",
        "target_product_name": "cà phê rang xay",
        "target_budget_range": 120000,
        "description": "cà phê phân khúc tầm trung",
        "assigned_model_id": "model-uuid"
    },
    "user_id": "user-uuid",
    "limit": 4,  # max_products * 2
    "platform": "lazada"
}
```

**AI Process (2-step):**

#### Step 3.1: Product Analysis (AI)
**Prompt:** Phân tích và tìm các sản phẩm nổi bật trong ngân sách

**Output:**
```json
{
    "analysis": "Thị trường cà phê rang xay tại Việt Nam rất sôi động...",
    "products": [
        {
            "name": "Cà phê rang xay Eatu Café",
            "price": 120000,
            "rating": 4.8,
            "description": "..."
        },
        ...
    ]
}
```

#### Step 3.2: Link Generation (AI)
**Prompt:** Tạo search URLs cho các sản phẩm đã phân tích

**Output:**
```json
{
    "products": [
        {
            "name": "Cà phê rang xay Eatu Café",
            "urls": {
                "lazada": "https://www.lazada.vn/catalog/?q=Cà+phê+rang+xay+Eatu+Café..."
            }
        },
        ...
    ]
}
```

**Final Output:**
```python
ProductSearchResponse(
    ai_analysis="Thị trường cà phê rang xay tại Việt Nam...",
    recommended_products=[
        ProductWithLink(
            name="Cà phê rang xay Eatu Café",
            url="https://www.lazada.vn/catalog/?q=..."
        ),
        ...
    ],
    total_found=4
)
```

**Lỗi có thể xảy ra:**
- `"Không tìm thấy sản phẩm nào từ AI search"` (nếu `recommended_products` rỗng)

---

### Step 4: Auto Crawl

**Service:** `ScraperFactory.get_scraper()` + `scraper.crawl_search_results()`

**Mục đích:** Crawl danh sách sản phẩm từ các search URLs đã được tạo

**Input:**
```python
{
    "search_urls": [
        "https://www.lazada.vn/catalog/?q=Cà+phê+rang+xay+Eatu+Café...",
        "https://www.lazada.vn/catalog/?q=Cà+phê+rang+xay+The+Organic...",
        ...
    ],
    "max_products_per_url": 5,
    "total_limit": 20  # MAX_CRAWL_PRODUCTS
}
```

**Process:**
- Sử dụng BeautifulSoup để parse HTML
- Extract: name, price, rating, review_count, sales_count, link, image
- Convert sang `CrawledProductItemExtended`

**Output:**
```python
[
    CrawledProductItemExtended(
        platform="lazada",
        product_name="500GR cà phê hạt rang BƠ ROBUSTA & CULI 80/20 Rang...",
        product_url="https://www.lazada.vn/products/...",
        price_current=129690,
        rating_score=5.0,
        review_count=6,
        sales_count=18936,
        is_mall=False,
        brand=None,
        keywords_in_title=["ROBUSTA", "rang", "CULI"],
        image_urls=["https://..."]
    ),
    ...  # Tối đa 20 products
]
```

**Lỗi có thể xảy ra:**
- `"Không thể crawl được sản phẩm nào từ các search links"` (nếu tất cả URLs fail)

---

### Step 5: Product Filtering

**Service:** `ProductFilterService`

**Mục đích:** Lọc sản phẩm dựa trên criteria (logic-based, không dùng AI)

**Input:**
```python
{
    "products": [CrawledProductItemExtended(...), ...],  # 20 products
    "criteria": ProductFilterCriteria(
        min_review_count=100,
        max_price=120000.0,
        platforms=["lazada"]
    )
}
```

**Process:**
- Iterate qua từng product
- Check từng điều kiện:
  - `min_review_count`: `product.review_count >= 100`
  - `max_price`: `product.price_current <= 120000`
  - `platforms`: `product.platform in ["lazada"]`
  - `min_rating`: `product.rating_score >= min_rating`
  - `is_mall`: `product.is_mall == True`
  - `required_keywords`: Tất cả keywords phải có trong `product.product_name`
  - ...

**Output:**
```python
[
    CrawledProductItemExtended(...),  # Product 1 (passed)
    CrawledProductItemExtended(...),  # Product 2 (passed)
    ...  # 6 products total (passed filter)
]
```

**Lỗi có thể xảy ra:**
- Không có lỗi, nhưng có thể trả về empty list nếu không có product nào pass

---

### Step 5.5: AI Ranking (Nếu cần)

**Service:** `ProductRankingService`

**Mục đích:** Nếu số lượng products sau filtering > `max_products`, dùng AI để chọn top N sản phẩm tốt nhất

**Input:**
```python
{
    "products": [CrawledProductItemExtended(...), ...],  # 6 products
    "user_query": "cà phê rang xay",
    "filter_criteria": {
        "min_review_count": 100,
        "max_price": 120000.0,
        "platforms": ["lazada"]
    },
    "limit": 2  # max_products
}
```

**AI Prompt (tóm tắt):**
```
Bạn là chuyên gia đánh giá và lựa chọn sản phẩm thông minh.

Nhiệm vụ: Từ danh sách 6 sản phẩm đã được lọc, hãy chọn ra TOP 2 sản phẩm TỐT NHẤT.

Thông tin tìm kiếm:
- Từ khóa: "cà phê rang xay"
- Tiêu chí lọc đã áp dụng:
  - min_review_count: 100
  - max_price: 120000 VND

Danh sách 6 sản phẩm đã lọc:
1. 500GR cà phê hạt rang BƠ ROBUSTA & CULI 80/20 Rang...
   - Giá: 129,690 VND
   - Rating: 5.0/5.0
   - Reviews: 18936
   - Đã bán: 18936
   - Platform: lazada
   - Loại: Thường
   - URL: https://...

2. ...

Hãy đánh giá và chọn TOP 2 sản phẩm dựa trên:
1. **Chất lượng tổng thể**: Rating cao, nhiều reviews tích cực
2. **Độ tin cậy**: Trust score cao, Mall seller, thương hiệu uy tín
3. **Giá trị**: Giá hợp lý so với chất lượng
4. **Độ phổ biến**: Đã bán được nhiều (sales count cao)
5. **Phù hợp với yêu cầu**: Match với từ khóa và tiêu chí

Trả về JSON format:
{
    "analysis": "Phân tích ngắn gọn về các sản phẩm được chọn và lý do",
    "top_products": [
        {
            "product_name": "Tên sản phẩm chính xác từ danh sách",
            "product_url": "URL chính xác từ danh sách",
            "reason": "Lý do chọn sản phẩm này"
        }
    ]
}
```

**Output:**
```python
[
    CrawledProductItemExtended(...),  # Top 1
    CrawledProductItemExtended(...)   # Top 2
]
```

**Lỗi có thể xảy ra:**
- Nếu AI không parse được → fallback về `products[:limit]`
- Nếu không match được product → bỏ qua và dùng fallback

---

### Step 6: Auto Import

**Service:** `AutoImportService`

**Mục đích:** Import các sản phẩm đã được lọc và ranked vào database

**Input:**
```python
{
    "products": [CrawledProductItemExtended(...), ...],  # 2 products
    "project_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "user_id": "user-uuid"
}
```

**Process:**
- Convert `CrawledProductItemExtended` → `ProductCreate` schema
- Check duplicate bằng `product_url`
- Gọi `ProductService.create_product()` để lưu vào DB
- Collect `product_id` của các sản phẩm đã import thành công

**Output:**
```python
[
    "uuid1",  # product_id của product 1
    "uuid2"  # product_id của product 2
]
```

**Lỗi có thể xảy ra:**
- `"Không thể import sản phẩm nào vào database"` (nếu tất cả đều duplicate hoặc lỗi)

---

## Tổng kết Input/Output của từng AI Service

| Step | Service | Input | Output | AI Model |
|------|---------|-------|--------|----------|
| 0 | NaturalLanguageParser | `user_text` + `project_info` | `(user_query, filter_criteria_text, max_products, error)` | LLM (Gemini/OpenAI) |
| 1 | FilterIntentParser | `filter_criteria_text` | `(ProductFilterCriteria, error)` | LLM (Gemini/OpenAI) |
| 2 | FilterCriteriaValidator | `user_text` + `criteria` | `(is_valid, error_message)` | LLM (Gemini/OpenAI) |
| 3 | ProductAIAgent | `project_info` + `user_query` + `platform` | `ProductSearchResponse` (với search URLs) | LLM (Gemini/OpenAI) với Grounding |
| 5.5 | ProductRankingService | `products` + `user_query` + `filter_criteria` | `List[CrawledProductItemExtended]` (top N) | LLM (Gemini/OpenAI) |

---

## Error Handling

### Các loại lỗi có thể xảy ra:

1. **Parsing Errors:**
   - `"parsing_failed"`: Không thể parse user input
   - `"intent_parsing_failed"`: Không thể parse filter criteria
   - `"criteria_validation_failed"`: Criteria không hợp lệ

2. **Platform Errors:**
   - `"platform_not_supported"`: User yêu cầu Shopee (chưa hỗ trợ)

3. **Search Errors:**
   - `"no_products_found"`: AI không tìm thấy sản phẩm

4. **Crawl Errors:**
   - `"crawl_failed"`: Không thể crawl được sản phẩm nào

5. **Filter Errors:**
   - Không có lỗi, nhưng có thể trả về 0 products nếu filter quá strict

6. **Import Errors:**
   - `"import_failed"`: Không thể import sản phẩm nào (có thể do duplicate)

7. **Execution Errors:**
   - `"execution_error"`: Lỗi không xác định trong quá trình thực thi

---

## Best Practices

1. **Input Validation:**
   - Luôn validate `user_input` không rỗng và không quá dài (max 2000 chars)
   - Kiểm tra project có `target_product_name` trước khi thực thi

2. **Error Messages:**
   - Tất cả error messages đều bằng tiếng Việt để user dễ hiểu
   - Cung cấp `error_type` để frontend có thể xử lý phù hợp

3. **Performance:**
   - Giới hạn crawl tối đa 20 products (`MAX_CRAWL_PRODUCTS = 20`)
   - Sử dụng ranking AI chỉ khi cần (khi `len(filtered) > max_products`)

4. **Data Quality:**
   - Check duplicate bằng `product_url` trước khi import
   - Validate price parsing để tránh lỗi format

---

## API Endpoint

**POST** `/api/v1/products/auto-discovery/execute`

**Request Body:**
```json
{
  "project_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "user_query": "tìm kiếm cho tôi 2 sản phẩm mẫu dựa trên project của tôi, yêu cầu là có hơn 100 reviews và trên sàn lazada",
  "filter_criteria": null,  // Optional
  "max_products": 20  // Optional, default 20
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Đã import 2 sản phẩm thành công",
  "products_found": 20,
  "products_filtered": 6,
  "products_imported": 2,
  "imported_product_ids": ["uuid1", "uuid2"],
  "extracted_criteria": {
    "min_review_count": 100,
    "max_price": 120000.0,
    "platforms": ["lazada"]
  }
}
```

---

## Notes

- Tất cả AI services sử dụng cùng một LLM agent được select từ `LLMProviderSelector` dựa trên `user_id` và `project_assigned_model_id`
- Shopee platform hiện chưa được hỗ trợ đầy đủ, hệ thống sẽ tự động exclude và suggest Lazada/Tiki
- Price parsing có logic xử lý thousand separator (ví dụ: "129.690" → 129690)
- Review count được extract từ HTML của search results (Lazada, Tiki)

