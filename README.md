# Sale Smart AI Backend

This project uses FastAPI, PostgreSQL 16 (with pgvector), Poetry, and Alembic.

## Project Structure
- models/
- schemas/
- repositories/
- services/
- controllers/
- core/
- migration/
- shared/
- app.py
- env.py

## Prerequisites
- Python 3.10+
- Poetry
- PostgreSQL 16 (hoặc Docker để chạy PostgreSQL qua Docker Compose)
- pgvector extension (được bao gồm trong Docker image)

## Setup

### Cách 1: Dùng Docker Compose (Khuyến nghị - Dễ nhất)

1. **Tạo file `.env` trong thư mục `Sale_Smart_AI_BE/`:**

```env
# Application Environment (dev, prod, test)
APP_ENV=dev

# Database Configuration
DB_NAME=sale_smart_ai
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# Application Settings
APP_DEBUG=true
FRONTEND_URL=http://localhost:5173
DOMAIN_URL=http://localhost:8000

# AI API Keys
OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# CORS Configuration
ALLOWED_ORIGIN_REGEX=.*localhost.*

# JWT Configuration
JWT_SECRET_KEY=your_jwt_secret_key_here_change_in_production
JWT_REFRESH_SECRET_KEY=your_jwt_refresh_secret_key_here_change_in_production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_WEEKS=4
JWT_REFRESH_TOKEN_EXPIRE_WEEKS=8

# Clerk Authentication
CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key_here
```

2. **Khởi động PostgreSQL bằng Docker Compose:**
```bash
cd Sale_Smart_AI_BE
docker-compose up -d
```

3. **Cài đặt dependencies với Poetry:**
```bash
poetry install
```

4. **Chạy migrations để tạo database schema:**
```bash
poetry run alembic upgrade head
```

5. **Khởi động ứng dụng:**
```bash
poetry run uvicorn app:app --reload
```

Ứng dụng sẽ chạy tại `http://localhost:8000`

---

### Cách 2: Cài PostgreSQL Local

1. **Cài đặt PostgreSQL 16:**
   - Download từ: https://www.postgresql.org/download/
   - Hoặc dùng package manager:
     - Windows: `choco install postgresql16` hoặc download installer
     - macOS: `brew install postgresql@16`
     - Linux: `sudo apt-get install postgresql-16` (Ubuntu/Debian)

2. **Cài đặt pgvector extension:**
   ```bash
   # Sau khi cài PostgreSQL, cài pgvector
   # Windows: Download từ https://github.com/pgvector/pgvector/releases
   # macOS: brew install pgvector
   # Linux: sudo apt-get install postgresql-16-pgvector
   ```

3. **Tạo database và user:**
   ```sql
   -- Kết nối PostgreSQL
   psql -U postgres
   
   -- Tạo database
   CREATE DATABASE sale_smart_ai;
   
   -- Tạo user (nếu chưa có)
   CREATE USER postgres WITH PASSWORD 'postgres';
   
   -- Cấp quyền
   GRANT ALL PRIVILEGES ON DATABASE sale_smart_ai TO postgres;
   
   -- Kết nối vào database và cài pgvector
   \c sale_smart_ai
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

4. **Tạo file `.env`** (giống như Cách 1, nhưng đảm bảo `DB_HOST=localhost` và `DB_PORT=5432`)

5. **Cài đặt dependencies với Poetry:**
   ```bash
   poetry install
   ```

6. **Chạy migrations:**
   ```bash
   poetry run alembic upgrade head
   ```

7. **Khởi động ứng dụng:**
   ```bash
   poetry run uvicorn app:app --reload
   ```

## Lưu ý quan trọng

- **PostgreSQL version:** Dự án yêu cầu PostgreSQL 16 (vì sử dụng pgvector 0.7.2-pg16)
- **pgvector extension:** Cần thiết cho tính năng vector similarity search
- **Environment variables:** Tất cả các biến trong file `.env` đều bắt buộc, đặc biệt là các API keys cho AI services

## Troubleshooting

- Nếu gặp lỗi kết nối database, kiểm tra:
  - PostgreSQL đã chạy chưa?
  - Thông tin trong file `.env` có đúng không?
  - Port 5432 có bị chiếm bởi ứng dụng khác không?

- Nếu gặp lỗi pgvector:
  - Đảm bảo extension đã được cài đặt: `CREATE EXTENSION vector;`
  - Kiểm tra version PostgreSQL: `SELECT version();`
