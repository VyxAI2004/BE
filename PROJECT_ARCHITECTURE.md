# Tài liệu Kiến trúc Dự án Sale Smart AI BE

Tài liệu này cung cấp cái nhìn tổng quan về kiến trúc, cấu trúc thư mục và các thành phần cốt lõi của dự án Sale Smart AI Backend. Mục tiêu là giúp lập trình viên mới nhanh chóng hiểu và bắt đầu làm việc với codebase.

## 1. Tổng quan Công nghệ

*   **Framework**: FastAPI (Python)
*   **Database**: PostgreSQL
*   **ORM**: SQLAlchemy (Async/Sync)
*   **Migration**: Alembic
*   **Validation**: Pydantic
*   **Architecture**: Layered Architecture (Controller -> Service -> Repository -> Model)

## 2. Cấu trúc Thư mục

```
Sale_Smart_AI_BE/
├── app.py                  # Entry point của ứng dụng, khởi tạo FastAPI app
├── config/                 # Các file cấu hình
├── controllers/            # API Layer (Routes/Endpoints)
│   └── routers.py          # Tập hợp tất cả các router con
├── core/                   # Các thành phần cốt lõi dùng chung
│   ├── db.py               # Cấu hình Database Engine & Session
│   ├── settings.py         # Quản lý biến môi trường
│   └── llm/                # Tích hợp LLM (Large Language Model)
├── models/                 # Database Models (SQLAlchemy)
│   └── base.py             # Base Model (id, created_at, updated_at)
├── repositories/           # Data Access Layer
│   └── base.py             # Base Repository (CRUD generic)
├── schemas/                # Pydantic Schemas (Request/Response models)
├── services/               # Business Logic Layer
│   ├── core/               # Các service cơ bản (User, Auth, etc.)
│   │   └── base.py         # Base Service
│   └── features/           # Các service nghiệp vụ phức tạp
└── tests/                  # Unit & Integration Tests
```

## 3. Kiến trúc Phân lớp (Layered Architecture)

Dự án tuân theo mô hình phân lớp chặt chẽ để đảm bảo tính tách biệt (Separation of Concerns) và dễ bảo trì.

### Luồng dữ liệu:
`Request` -> **Controller** -> **Service** -> **Repository** -> **Database (Model)**

### Chi tiết các lớp:

#### A. Models (`models/`)
Định nghĩa cấu trúc bảng trong Database.
*   **Base Class**: `models.base.Base`
*   **Đặc điểm**:
    *   Tự động thêm các trường: `id` (UUID), `created_at`, `updated_at`.
    *   Sử dụng cú pháp hiện đại của SQLAlchemy (`Mapped`, `mapped_column`).

#### B. Repositories (`repositories/`)
Chịu trách nhiệm tương tác trực tiếp với Database.
*   **Base Class**: `repositories.base.BaseRepository`
*   **Chức năng có sẵn**:
    *   `get(id)`: Lấy 1 bản ghi theo ID.
    *   `get_multi(skip, limit, filters, order_by)`: Lấy danh sách, hỗ trợ phân trang, lọc và sắp xếp.
    *   `create(obj_in)`: Tạo mới.
    *   `update(db_obj, obj_in)`: Cập nhật.
    *   `delete(id)`: Xóa.
    *   `count(filters)`: Đếm số lượng bản ghi.
    *   `apply_filters(query, filters)`: Hỗ trợ lọc động (ví dụ: `price__gt`, `name__like`).

#### C. Services (`services/`)
Chứa logic nghiệp vụ (Business Logic).
*   **Base Class**: `services.core.base.BaseService`
*   **Đặc điểm**:
    *   Wrapper cho Repository, giúp Controller không gọi trực tiếp Repository.
    *   Xử lý logic phức tạp trước khi lưu/lấy dữ liệu.
    *   Được chia thành `core` (các entity cơ bản) và `features` (tính năng phức tạp).

#### D. Controllers (`controllers/`)
Định nghĩa các API Endpoints.
*   Nhận Request, validate dữ liệu (qua Pydantic Schemas).
*   Gọi Service để xử lý.
*   Trả về Response.
*   Được gom nhóm trong `controllers/routers.py`.

## 4. Hướng dẫn Phát triển (How-to)

Để thêm một tính năng mới (ví dụ: quản lý `Product`), bạn cần thực hiện các bước sau:

1.  **Tạo Model**:
    *   Tạo file `models/product.py`.
    *   Class `Product` kế thừa từ `models.base.Base`.

2.  **Tạo Schema**:
    *   Tạo file `schemas/product.py`.
    *   Định nghĩa `ProductBase`, `ProductCreate`, `ProductUpdate`, `ProductResponse`.

3.  **Tạo Repository**:
    *   Tạo file `repositories/product.py`.
    *   Class `ProductRepository` kế thừa `BaseRepository[Product, ProductCreate, ProductUpdate]`.

4.  **Tạo Service**:
    *   Tạo file `services/core/product.py` (hoặc `features/`).
    *   Class `ProductService` kế thừa `BaseService[Product, ProductCreate, ProductUpdate, ProductRepository]`.

5.  **Tạo Controller**:
    *   Tạo file `controllers/product.py`.
    *   Sử dụng `APIRouter`.
    *   Inject `ProductService` (thông qua `Depends`) để xử lý logic.

6.  **Đăng ký Router**:
    *   Thêm router mới vào `controllers/routers.py`.

## 5. Các Base Class Quan trọng

Khi đọc code, hãy chú ý đến các file này đầu tiên để hiểu các phương thức có sẵn:

*   `models/base.py`: Xem các trường mặc định của mọi bảng.
*   `repositories/base.py`: Xem các hàm CRUD và logic lọc (`apply_filters`) mặc định.
*   `services/core/base.py`: Xem cách Service wrap Repository.

## 6. Database & Migration

*   Dự án sử dụng **Alembic** để quản lý migration.
*   File cấu hình DB: `core/db.py`.
*   Khi thay đổi Model, cần chạy lệnh tạo migration (ví dụ: `alembic revision --autogenerate -m "message"`) và upgrade DB (`alembic upgrade head`).

## 7. Quy tắc Coding & Best Practices (LƯU Ý QUAN TRỌNG)

Để duy trì chất lượng code và kiến trúc, **bắt buộc** tuân thủ các quy tắc sau:

### A. Quy tắc Kiến trúc
1.  **Chỉ Repository mới được truy cập Database**:
    *   Tuyệt đối **KHÔNG** viết câu lệnh query (`db.query(...)`) trong Service hoặc Controller.
    *   Mọi thao tác DB phải được gói gọn trong method của Repository.
2.  **Service chứa Business Logic**:
    *   Controller không được chứa logic nghiệp vụ phức tạp. Controller chỉ nhận input, gọi Service và trả về output.
    *   Service gọi Repository để lấy dữ liệu, xử lý, và trả về kết quả cho Controller.
3.  **Dependency Injection**:
    *   Sử dụng `Depends` của FastAPI để inject Service vào Controller.
    *   Inject `Session` vào Service/Repository thay vì khởi tạo global session.

### B. Clean Code & Style
1.  **Type Hinting**:
    *   Tất cả các function/method **phải** có Type Hint cho arguments và return value.
    *   Ví dụ: `def get_user(self, user_id: UUID) -> Optional[User]:`
2.  **Naming Convention**:
    *   Biến/Function: `snake_case` (ví dụ: `get_user_by_id`).
    *   Class: `PascalCase` (ví dụ: `UserRepository`).
    *   Constant: `UPPER_CASE` (ví dụ: `MAX_RETRY_COUNT`).
3.  **DRY (Don't Repeat Yourself)**:
    *   Nếu thấy code lặp lại, hãy tách thành hàm chung hoặc đưa vào Base Class.
    *   Tận dụng tối đa các method có sẵn trong `BaseRepository` và `BaseService`.

### C. Xử lý Dữ liệu & Error Handling
1.  **Validation**:
    *   Luôn validate dữ liệu đầu vào bằng Pydantic Schemas trong Controller.
2.  **Exceptions**:
    *   Không để lọt `Internal Server Error (500)` ra ngoài nếu có thể xử lý được.
    *   Service nên raise các Exception cụ thể (ví dụ: `UserNotFoundException`) để Controller bắt và trả về mã lỗi HTTP tương ứng (404, 400).
3.  **Filtering**:
    *   Khi viết hàm lấy danh sách trong Repository, hãy sử dụng cơ chế `apply_filters` có sẵn trong `BaseRepository` thay vì viết chuỗi `if` dài dòng để check từng trường.

### D. AI Agent Note
*   Luôn kiểm tra xem method cần dùng đã có trong Base Class chưa trước khi viết mới.

## 8. Phân chia Service (Core vs Features)

Dự án chia Service thành 2 nhóm chính để dễ quản lý:

*   **`services/core/`**: Chứa các logic nền tảng, ít thay đổi, dùng chung cho toàn hệ thống.
    *   Ví dụ: `User`, `Auth`, `Project`, `Role`, `ActivityLog`.
    *   Đây là "xương sống" của ứng dụng.
*   **`services/features/`**: Chứa các logic nghiệp vụ đặc thù, phức tạp hoặc các tính năng mở rộng.
    *   Ví dụ: `product_intelligence` (AI phân tích sản phẩm), `crawling` (thu thập dữ liệu).
    *   Code ở đây thường thay đổi nhiều và phụ thuộc vào yêu cầu business cụ thể.

## 9. Authentication & Security

*   **Cơ chế**: JWT (JSON Web Token).
*   **Dependency**: `core.dependencies.auth.verify_token`.
*   **Cách dùng**:
    *   Để bảo vệ một route, thêm `Depends(verify_token)` vào hàm controller.
    *   Hàm này sẽ trả về `TokenData` (chứa `user_id`, `email`, `roles`).
    *   Đồng thời, `user.id` cũng được gán vào `db.info["current_user_id"]` để tiện truy xuất trong Repository nếu cần (ví dụ: để ghi log người sửa).

## 10. Cheat Sheet (Các mẫu code thường dùng)

### A. Inject Service vào Controller
```python
from fastapi import APIRouter, Depends
from services.core.user import UserService
from core.dependencies.services import get_user_service

router = APIRouter()

@router.get("/me")
def get_me(
    current_user: TokenData = Depends(verify_token),
    user_service: UserService = Depends(get_user_service)
):
    return user_service.get(current_user.user_id)
```

### B. Transaction Management
Mặc định `BaseRepository` đã handle commit/rollback cho các hàm `create`, `update`, `delete` đơn lẻ.
Nếu cần thực hiện **nhiều** thao tác trong một transaction (ví dụ: tạo Project và add User vào Project cùng lúc):

```python
# Trong Service
def create_project_with_user(self, project_data, user_id):
    try:
        # Bắt đầu transaction thủ công nếu cần logic phức tạp
        # Hoặc đơn giản là gọi các method của repo, vì chúng dùng chung session 'self.db'
        # SQLAlchemy Session mặc định sẽ flush các thay đổi và chỉ commit khi gọi db.commit()
        # Tuy nhiên, BaseRepository thường commit ngay sau mỗi lệnh.
        # ĐỂ AN TOÀN CHO TRANSACTION PHỨC TẠP:
        
        project = self.project_repo.create(obj_in=project_data) # Sẽ commit
        
        # Nếu muốn atomic tuyệt đối, cần viết method riêng trong Service/Repo 
        # và quản lý session.begin() hoặc dùng context manager.
        pass 
    except Exception as e:
        self.db.rollback()
        raise e
```
*Lưu ý*: Hiện tại `BaseRepository` commit ngay lập tức. Nếu cần transaction phức tạp, hãy cân nhắc viết method riêng trong Service và kiểm soát `db.commit()` ở cuối cùng.

### C. Lấy User hiện tại trong Service
Thường thì `user_id` nên được truyền từ Controller xuống Service.
Tuy nhiên, nếu cần thiết, có thể truy cập `self.db.info.get("current_user_id")` (được set bởi middleware/dependency `verify_token`).


