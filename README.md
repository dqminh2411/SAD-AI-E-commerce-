# Simple Microservice E-commerce (Django + Docker Compose)

This workspace contains a small microservice e-commerce website split into 6 Django projects:

- `customer_service`: customer registration/auth/profile (MySQL)
- `product_service`: unified product catalog (LAPTOP + CLOTHES) + full-text + substring search (PostgreSQL)
- `cart_service`: cart + checkout + orders (PostgreSQL)
- `staff_service`: staff login + proxy endpoints for product management & order viewing (MySQL)
- `api_gateway`: HTML frontend + request routing (Django templates)
- `ai_chat_service`: RAG chatbot with behavior personalization (ChromaDB + Gemini)

## Architecture

- Each service has its own codebase, dependencies, and Dockerfile.
- Databases are **independent** (no cross-service foreign keys; only IDs are shared across services).
- Inter-service calls use REST via the `requests` library.
- Sample data is loaded via SQL init scripts when the DB containers start.

## Ports

### Web services

- API Gateway: http://localhost:8000
- Customer service: http://localhost:8001
- Product service: http://localhost:8002
- Cart service: http://localhost:8004
- Staff service: http://localhost:8005
- AI Chat service: http://localhost:8006
- ChromaDB: http://localhost:8007

### Databases (custom host ports)

MySQL (containers expose `3306`, host maps custom ports):
- Customer MySQL: `localhost:3307`
- Staff MySQL: `localhost:3308`

PostgreSQL (containers expose `5432`, host maps custom ports):
- Cart Postgres: `localhost:5435`
- Product Postgres: `localhost:5436`

## Run (Docker)

Prerequisites:
- Docker Desktop (Windows)
- Docker Compose v2 (`docker compose`)

From the repo root:

```powershell
docker compose up --build
```

Create `.env` in repo root (already added in this MVP):

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

Then open:
- http://localhost:8000

To stop:

```powershell
docker compose down
```

If you want a clean DB re-init (drops volumes):

```powershell
docker compose down -v
```

## Demo accounts

### Staff

- Username: `admin`
- Password: `password123`

(Inserted by `staff_service/sql/init.sql`.)

### Customer

You can register from the UI at:
- `/customer/register/`

A demo customer row also exists in the customer DB init script.

## UI pages (API Gateway)

- Home (banner): `/`
- Product listing (with search + pagination):
  - Laptops: `/products/laptops/?search=mac&page=1`
  - Clothes: `/products/clothes/?search=polo&page=1`
- Product detail: `/products/<laptops|clothes>/<id>/`
- Customer auth:
  - Register: `/customer/register/`
  - Login: `/customer/login/`
  - Logout: `/customer/logout/`
- Cart:
  - View cart: `/cart/`
  - Checkout: `/cart/checkout/`
- Staff:
  - Login: `/staff/login/`
  - Dashboard (manage products + view orders): `/staff/dashboard/`

## Service APIs (main routes)

### ai_chat_service (port 8006)

- `GET /api/v1/chat/health/`
- `POST /api/v1/chat/message/` JSON: `{ "user_id", "message", "context" }`

Example:

```json
{
  "user_id": "US_001",
  "message": "Tu van laptop gaming tam 25 trieu",
  "context": {"page": "home"}
}
```

The API gateway proxies this as:
- `POST /api/chat/message/`

You can also test via the floating chat widget in the UI.

### customer_service (port 8001)

- `POST /api/register/`  JSON: `{ "email", "full_name", "password" }`
- `POST /api/login/`     JSON: `{ "email", "password" }`
- `GET  /api/profile/`   Header: `Authorization: Token <token>`

### product_service (port 8002)

- `GET  /api/v1/products/?product_type=LAPTOP|CLOTHES&q=<term>&page=1` (full-text + substring search)
- `POST /api/v1/products/`
- `GET  /api/v1/products/<id>/`
- `PUT/PATCH/DELETE /api/v1/products/<id>/`

### cart_service (port 8004)

Customer token required for cart actions:
- `GET  /api/cart/` header `Authorization: Token <customer_token>`
- `POST /api/cart/items/` JSON: `{ "product_type": "laptop"|"clothes", "product_id", "quantity" }`
- `PATCH /api/cart/items/<item_id>/` JSON: `{ "quantity" }`
- `DELETE /api/cart/items/<item_id>/`
- `POST /api/checkout/` (creates an order)

Orders listing (used by staff dashboard):
- `GET /api/orders/` (optionally `?customer_id=<id>`)

### staff_service (port 8005)

- `POST /api/login/` JSON: `{ "username", "password" }`
- `GET  /api/profile/` header `Authorization: Token <staff_token>`

Proxy endpoints (require staff token):
- `/api/proxy/products/...` (proxies to product_service)
- `/api/proxy/orders/...` (proxies to cart_service)

## DB initialization (SQL)

These scripts run automatically when DB containers start:
- `customer_service/sql/init.sql`
- `staff_service/sql/init.sql`
- `cart_service/sql/init.sql`

`product_service` uses PostgreSQL for full-text + substring search.

## Troubleshooting

- If you change SQL init scripts and want them to re-run, use `docker compose down -v` and start again.
- If ports are already in use, edit `docker-compose.yml` to use different host ports.

## Behavior Model (Google Colab)

- Notebook: `behavior_model/train_model_behavior.ipynb`
- Purpose:
  - Generate fake user behavior events
  - Train a small Transformer-based next-event model
  - Cluster users into behavior segments
  - Export `fake_user_behavior.json` for `ai_chat_service`

## Run ChromaDB by Docker (standalone)

If you want to run ChromaDB outside compose:

```powershell
docker run -d --name chromadb -p 8007:8000 chromadb/chroma:0.5.5
```

Then configure `ai_chat_service` env accordingly:
- `CHROMA_HOST=host.docker.internal`
- `CHROMA_PORT=8007`
