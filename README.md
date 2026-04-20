# Simple Microservice E-commerce (Django + Docker Compose)

E-commerce microservices dùng Django/DRF + Docker Compose, bán **LAPTOP** và **CLOTHES**.

## 1) Services (hiện tại)

Các Django projects chính:

- `api_gateway` (Django templates)
  - Frontend HTML + routing/proxy gọi sang các services.
- `customer_service` (MySQL)
  - Đăng ký/đăng nhập khách hàng, profile, token auth.
- `staff_service` (MySQL)
  - Đăng nhập staff + dashboard gọi proxy sang product/cart.
- `product_service` (PostgreSQL)
  - Catalog thống nhất cho `LAPTOP` + `CLOTHES`.
  - Search kết hợp **FTS + substring**.
- `cart_service` (PostgreSQL)
  - Cart + checkout + orders.
- `interaction_service` (PostgreSQL + Neo4j)
  - Ghi event hành vi (view/search/cart/purchase/chat).
  - Sync dữ liệu sang Neo4j KG bằng management command.
- `ai_chat_service` (FAISS + Gemini + Neo4j)
  - Chatbot RAG (KB markdown) + cá nhân hoá theo segment/hành vi.
  - Vector store **FAISS local** trong service (không dùng ChromaDB).
  - Embeddings: `paraphrase-multilingual-MiniLM-L12-v2` (Sentence-Transformers).

Hạ tầng đi kèm trong `docker-compose.yml`:
- MySQL: `customer_mysql`, `staff_mysql`
- PostgreSQL: `product_postgres`, `cart_postgres`, `interaction_postgres`
- Neo4j: `neo4j`

## 2) Nguyên tắc kiến trúc

- Mỗi service có Dockerfile/requirements riêng.
- DB **độc lập**; **không có cross-service foreign keys** (chỉ chia sẻ IDs qua REST).
- Inter-service communication: REST qua `requests`.
- SQL init scripts tự chạy khi DB containers start (tạo table + sample data).

## 3) Ports

### Web services

- API Gateway: http://localhost:8000
- Customer service: http://localhost:8001
- Product service: http://localhost:8002
- Cart service: http://localhost:8004
- Staff service: http://localhost:8005
- AI Chat service: http://localhost:8006
- Interaction service: http://localhost:8007

### Neo4j

- Neo4j Browser: http://localhost:7475
- Neo4j Bolt: `bolt://localhost:7688`

### Databases (custom host ports)

MySQL (container `3306`, host map port tuỳ chỉnh):
- Customer MySQL: `localhost:3307`
- Staff MySQL: `localhost:3308`

PostgreSQL (container `5432`, host map port tuỳ chỉnh):
- Cart Postgres: `localhost:5435`
- Product Postgres: `localhost:5436`
- Interaction Postgres: `localhost:5437`

## 4) Run (Docker)

Prerequisites:
- Docker Desktop (Windows)
- Docker Compose v2 (`docker compose`)

Tạo file `.env` ở repo root (để gọi Gemini; không có key vẫn chạy nhưng sẽ fallback rule-based):

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

Chạy từ repo root:

```powershell
docker compose up --build
```

Mở UI:
- http://localhost:8000

Stop:

```powershell
docker compose down
```

Reset dữ liệu (drop volumes):

```powershell
docker compose down -v
```

## 5) Demo accounts

### Staff

- Username: `admin`
- Password: `password123`

(Seed bởi `staff_service/sql/init.sql`.)

### Customer

Đăng ký tại:
- `/customer/register/`

- username: `demo.customer@example.com`
- password: `123456`

## 6) UI routes (API Gateway)

- Home: `/`
- Product listing (search + pagination):
  - Laptops: `/products/laptops/?search=mac&page=1`
  - Clothes: `/products/clothes/?search=polo&page=1`
- Product detail: `/products/<laptops|clothes>/<id>/`
- Customer auth: `/customer/register/`, `/customer/login/`, `/customer/logout/`
- Cart: `/cart/`, `/cart/checkout/`
- Staff: `/staff/login/`, `/staff/dashboard/`

## 7) Main APIs

### ai_chat_service (8006)

- `GET /api/v1/chat/health/`
- `POST /api/v1/chat/message/` JSON: `{ "user_id", "message", "context" }`

Gateway proxy:
- `POST /api/chat/message/`

### interaction_service (8007)

- `GET /api/health/`
- `GET/POST /api/events/` (log hành vi; dùng cho demo + sync Neo4j)

### product_service (8002)

- `GET /api/v1/products/?product_type=LAPTOP|CLOTHES&q=<term>&page=1`
- CRUD: `/api/v1/products/` và `/api/v1/products/<id>/`

### cart_service (8004)

- Cart: `GET /api/cart/`, `POST /api/cart/items/`, `PATCH/DELETE /api/cart/items/<item_id>/`
- Checkout: `POST /api/checkout/`
- Orders: `GET /api/orders/`

### customer_service (8001)

- `POST /api/register/`, `POST /api/login/`, `GET /api/profile/`

### staff_service (8005)

- `POST /api/login/`, `GET /api/profile/`
- Proxy endpoints (require staff token):
  - `/api/proxy/products/...` → `product_service`
  - `/api/proxy/orders/...` → `cart_service`

## 8) AI Chat (RAG) – Vector store

- KB markdown: [ai_chat_service/knowledge_base/](ai_chat_service/knowledge_base/)
- FAISS index lưu local (bind mount):
  - `/app/vector_store/kb.index`
  - `/app/vector_store/kb_meta.json`
  - `/app/vector_store/embedder_meta.json`

Re-index thủ công (trong container `ai_chat_service`):

```bash
python manage.py init_kb --force
```

Lưu ý: lần đầu service chạy sẽ tải model embeddings từ HuggingFace (cần internet).

## 9) DB initialization (SQL)

Init scripts:
- `customer_service/sql/init.sql`
- `staff_service/sql/init.sql`
- `cart_service/sql/init.sql`
- `interaction_service/sql/init.sql`

## 10) Troubleshooting

- Muốn chạy lại SQL init scripts: `docker compose down -v` rồi up lại.
- Nếu port bị trùng: sửa mapping trong [docker-compose.yml](docker-compose.yml).
