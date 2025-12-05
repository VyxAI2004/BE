
SEARCH_PRODUCT_PROMPT = """
Bạn là trợ lý mua sắm AI thông minh. Hãy sử dụng Google Search để tìm kiếm các sản phẩm THẬT trên Shopee Việt Nam.

Thông tin yêu cầu:
- Sản phẩm: {search_keyword}
- Mô tả: {description}
- Ngân sách: {budget_text}

Nhiệm vụ:
1. Tìm kiếm thông tin thực tế về các sản phẩm đang bán trên Shopee phù hợp với yêu cầu.
2. Trả về danh sách 5-10 sản phẩm TỐT NHẤT kèm LINK MUA HÀNG THẬT.

QUAN TRỌNG - VỀ LINK SẢN PHẨM (URL):
- TUYỆT ĐỐI KHÔNG tự bịa ra link (ví dụ: không dùng id 123456789).
- Link phải chứa ID thật của shop và sản phẩm (ví dụ: ...-i.12345.67890).
- Nếu không tìm thấy link thật, HÃY BỎ QUA sản phẩm đó.
- Chỉ trả về các sản phẩm có link truy cập được.

Format JSON trả về:
{{
    "analysis": "Phân tích thị trường và lý do chọn các sản phẩm này",
    "products": [
        {{
            "name": "Tên đầy đủ của sản phẩm",
            "price": 120000,
            "url": "https://shopee.vn/ten-san-pham-that-i.shopid.itemid",
            "rating": 4.9,
            "sold": 1000,
            "shop_name": "Tên Shop (nếu có)",
            "reason": "Lý do đề xuất"
        }}
    ]
}}
"""

RANKING_PRODUCT_PROMPT = """
Dựa trên danh sách {count} sản phẩm thật từ Shopee:

{products_summary}

Phân tích và chọn TOP {limit} sản phẩm TỐT NHẤT dựa trên:
- Giá phù hợp với ngân sách {budget_text}
- Rating cao
- Đã bán được nhiều
- Uy tín

Trả về JSON:
{{
    "analysis": "Phân tích ngắn gọn về các sản phẩm",
    "top_products": [
        {{
            "name": "tên sản phẩm",
            "price": giá,
            "url": "url_thật_từ_danh_sách",
            "rating": rating,
            "sold": số_bán,
            "reason": "Lý do chọn"
        }}
    ]
}}
"""

ANALYZE_PRODUCTS_PROMPT = """
Bạn là chuyên gia tư vấn mua sắm. Hãy tìm kiếm và đề xuất các sản phẩm nổi bật phù hợp với yêu cầu sau:

- Từ khóa: {search_keyword}
- Mô tả chi tiết: {description}
- Ngân sách: {budget_text}

Yêu cầu:
1. Tìm {limit} sản phẩm được đánh giá cao, phổ biến trên thị trường.
2. Ưu tiên các thương hiệu uy tín hoặc sản phẩm có review tốt.
3. Phân tích ngắn gọn ưu điểm của từng sản phẩm.

Trả về JSON (chỉ JSON thuần, không markdown, không giải thích thêm):
{{
    "analysis": "Nhận định chung về thị trường và xu hướng cho dòng sản phẩm này",
    "products": [
        {{
            "name": "Tên đầy đủ và chính xác của sản phẩm",
            "estimated_price": 100000,
            "features": ["tính năng 1", "tính năng 2"],
            "reason": "Lý do đề xuất"
        }}
    ]
}}
"""

GENERATE_LINKS_PROMPT = """
Dựa trên danh sách sản phẩm sau, hãy tạo link tìm kiếm cho từng sản phẩm trên các sàn thương mại điện tử.

Danh sách sản phẩm:
{products_json}

Platform được chọn: {platform}

Yêu cầu tạo link:

1. **Nếu platform = "shopee"** hoặc "all" (bao gồm Shopee):
   Format: https://shopee.vn/search?keyword={{tên_sản_phẩm_encoded}}
   Ví dụ: https://shopee.vn/search?keyword=ca%20phe%20robusta%20rang%20xay

2. **Nếu platform = "lazada"** hoặc "all" (bao gồm Lazada):
   Format: https://www.lazada.vn/catalog/?q={{tên_sản_phẩm_encoded}}
   Ví dụ: https://www.lazada.vn/catalog/?q=ca%20phe%20robusta%20rang%20xay

3. **Nếu platform = "tiki"** hoặc "all" (bao gồm Tiki):
   Format: https://tiki.vn/search?q={{tên_sản_phẩm_encoded}}
   Ví dụ: https://tiki.vn/search?q=ca%20phe%20robusta%20rang%20xay

Quy tắc encode tên sản phẩm:
- Space → %20
- Ký tự đặc biệt tiếng Việt → encode URL chuẩn
- Chỉ dùng TÊN SẢN PHẨM chính, ngắn gọn

Trả về JSON (chỉ JSON thuần, không markdown):
- Nếu platform = "shopee", "lazada", hoặc "tiki": Chỉ 1 URL cho platform đó
- Nếu platform = "all": Trả về object với URLs cho cả 3 platforms

**Format khi platform cụ thể (shopee/lazada/tiki):**
{{
    "products": [
        {{
            "name": "Tên sản phẩm",
            "estimated_price": 100000,
            "url": "https://... (URL của platform được chọn)"
        }}
    ]
}}

**Format khi platform = "all":**
{{
    "products": [
        {{
            "name": "Tên sản phẩm",
            "estimated_price": 100000,
            "urls": {{
                "shopee": "https://shopee.vn/search?keyword=...",
                "lazada": "https://www.lazada.vn/catalog/?q=...",
                "tiki": "https://tiki.vn/search?q=..."
            }}
        }}
    ]
}}
"""


