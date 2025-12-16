# 🤖 AI Task Generation System - Implementation Guide

## 📋 Tổng quan

Hệ thống tự động generate **marketing tasks** từ **product analytics data** (trust score, reviews, sentiment analysis). Tasks được tạo ra để giúp user research đối thủ và đưa ra chiến dịch marketing hợp lý.

## 🎯 Mục đích

- **Research đối thủ**: Tạo tasks để tìm hiểu sản phẩm đối thủ
- **Marketing strategy**: Đề xuất tasks liên quan đến chiến lược marketing
- **Competitive analysis**: Phân tích cạnh tranh dựa trên trust score và reviews
- **Actionable insights**: Chuyển đổi analytics data thành tasks cụ thể

## 🏗️ Kiến trúc

```
Product Analytics Data
    ↓
Task Generation Agent (LLM)
    ↓
Task Generator Service
    ↓
Task Model (Database)
```

## 📁 Cấu trúc Files

```
services/features/product_intelligence/
├── agents/
│   └── task_generation_agent.py      # LLM agent để generate tasks
└── task_generation/
    ├── __init__.py
    └── task_generator_service.py      # Service orchestrate việc generate tasks

services/core/
└── task.py                            # Task service (CRUD operations)

repositories/
└── task.py                            # Task repository

schemas/
└── task.py                            # Task schemas (Create, Update, Response)

controllers/
└── ai_tasks.py                        # API endpoints
```

## 🔌 API Endpoints

### 1. Generate Tasks (và lưu vào database)

**Endpoint:** `POST /api/products/{product_id}/generate-tasks`

**Request:**
```json
{
  "max_tasks": 5  // Optional, default: 5, max: 10
}
```

**Response:**
```json
{
  "product_id": "uuid",
  "tasks_generated": 5,
  "tasks": [
    {
      "id": "uuid",
      "name": "Research 5 sản phẩm đối thủ có trust score > 80",
      "description": "Tìm kiếm và phân tích 5 sản phẩm đối thủ...",
      "task_type": "marketing_research",
      "priority": "high",
      "status": "pending",
      "estimated_hours": 4.0
    }
  ],
  "message": "Đã tạo 5 marketing tasks thành công từ analytics data"
}
```

### 2. Preview Tasks (không lưu)

**Endpoint:** `POST /api/products/{product_id}/generate-tasks-preview`

**Request:** Tương tự endpoint trên

**Response:** Tương tự, nhưng tasks chưa được lưu vào database

## 📊 Loại Tasks được Generate

### 1. **Marketing Research** (`marketing_research`)
- Research đối thủ tương tự
- Tìm hiểu chiến lược pricing
- Research sản phẩm cùng category

### 2. **Competitive Analysis** (`competitive_analysis`)
- So sánh trust score với đối thủ
- Phân tích sentiment trends
- Identify gaps và opportunities

### 3. **Content Strategy** (`content_strategy`)
- Phân tích positive themes để tạo content
- Research messaging strategies
- Identify content gaps

### 4. **Pricing Strategy** (`pricing_strategy`)
- So sánh giá với đối thủ
- Phân tích value proposition
- Research pricing strategies

### 5. **Market Positioning** (`market_positioning`)
- Xác định vị trí trên thị trường
- Research target audience
- Identify positioning opportunities

## 🔄 Flow hoạt động

### Step 1: User request generate tasks
```
User → POST /api/products/{product_id}/generate-tasks
```

### Step 2: Service lấy analytics data
```python
analytics_result = analytics_service.analyze_product(product_id, user_id)
```

### Step 3: LLM Agent generate tasks
```python
task_agent = TaskGenerationAgent(llm_agent)
tasks = task_agent.generate_marketing_tasks(
    product_data, analytics_data, project_info, max_tasks=5
)
```

### Step 4: Lưu tasks vào database
```python
task_service = TaskService(db)
for task_data in tasks:
    task = task_service.create(TaskCreate(**task_data))
```

### Step 5: Return tasks to user
```json
{
  "tasks_generated": 5,
  "tasks": [...]
}
```

## 💡 Ví dụ Tasks được Generate

### Ví dụ 1: Low Trust Score (< 50)
```json
{
  "name": "Research 5 sản phẩm đối thủ có trust score > 70",
  "description": "Tìm kiếm và phân tích 5 sản phẩm đối thủ trong cùng category có trust score cao hơn để học hỏi chiến lược marketing và positioning",
  "task_type": "marketing_research",
  "priority": "high",
  "estimated_hours": 4.0
}
```

### Ví dụ 2: High Spam Percentage
```json
{
  "name": "Phân tích cách đối thủ xử lý spam reviews",
  "description": "Research các sản phẩm đối thủ có tỷ lệ spam thấp để hiểu cách họ maintain trust score và reputation",
  "task_type": "competitive_analysis",
  "priority": "medium",
  "estimated_hours": 3.0
}
```

### Ví dụ 3: Negative Sentiment Trend
```json
{
  "name": "Research messaging strategies từ positive reviews của đối thủ",
  "description": "Phân tích các positive themes từ reviews của đối thủ để tạo content marketing tương tự",
  "task_type": "content_strategy",
  "priority": "high",
  "estimated_hours": 5.0
}
```

## 🎨 Prompt Engineering

LLM Agent sử dụng prompt được thiết kế để:
1. **Hiểu context**: Product data, analytics, project info
2. **Generate actionable tasks**: Tasks cụ thể, có thể thực hiện
3. **Focus marketing**: Tất cả tasks liên quan đến marketing
4. **Dựa trên insights**: Sử dụng trust score, reviews, sentiment

## 🔧 Configuration

### Max Tasks
- Default: 5 tasks
- Min: 1 task
- Max: 10 tasks

### Task Types
- `marketing_research`
- `competitive_analysis`
- `content_strategy`
- `pricing_strategy`
- `market_positioning`

### Priorities
- `low`
- `medium`
- `high`

## 📝 Database Schema

Tasks được lưu trong bảng `tasks` với các fields:
- `project_id`: Project chứa task
- `name`: Tên task
- `description`: Mô tả chi tiết
- `task_type`: Loại task (marketing_research, etc.)
- `status`: pending, in_progress, completed
- `priority`: low, medium, high
- `estimated_hours`: Số giờ ước tính
- `stage_metadata`: Metadata (source, product_id, marketing_focus, etc.)

## 🚀 Usage Example

### Python
```python
from services.features.product_intelligence.task_generation import TaskGeneratorService

service = TaskGeneratorService(db)
tasks = service.generate_and_save_tasks(
    product_id=product_id,
    user_id=user_id,
    max_tasks=5
)
```

### API Call
```bash
curl -X POST "http://localhost:8000/api/products/{product_id}/generate-tasks" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"max_tasks": 5}'
```

## ✅ Requirements

1. **Product phải có analytics data**
   - Trust score đã được tính
   - Reviews đã được phân tích
   - Analytics đã được generate

2. **Product phải thuộc một project**
   - Tasks được tạo trong context của project

3. **User authentication**
   - Cần token để access API

## 🐛 Error Handling

### Product không có analytics
```json
{
  "detail": "Trust score not calculated for product. Please calculate trust score first."
}
```

### Product không thuộc project
```json
{
  "detail": "Product must belong to a project to create tasks"
}
```

### LLM generation failed
- Fallback tasks được tạo
- Log error để debug

## 📈 Future Enhancements

1. **Task Templates**: Pre-defined task templates
2. **Task Dependencies**: Link tasks với nhau
3. **Auto-assignment**: Tự động assign tasks dựa trên user skills
4. **Task Prioritization**: AI-based priority scoring
5. **Task Completion Tracking**: Track progress và completion rate

## 🔗 Related Features

- **Product Analytics**: Source data cho task generation
- **Trust Score**: Key metric để generate tasks
- **Review Analysis**: Insights từ reviews
- **Auto Discovery**: Có thể dùng để research đối thủ

---

**Created:** 2024
**Last Updated:** 2024
