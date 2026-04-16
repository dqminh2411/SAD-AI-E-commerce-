# AI Service Design (Neo4j KG + LSTM Behavior + GraphRAG Chat)

Tài liệu này mô tả luồng hoạt động và các bước cần làm để chuyển hệ gợi ý + chatbot AI sang kiến trúc như [ai1.md](ai1.md), trong bối cảnh bạn đã refactor về **1 `product-service` quản lý 2 loại sản phẩm `LAPTOP` và `CLOTHES`** (tham khảo thiết kế entity trong `entity_and_db_design.md`).

Mục tiêu: có **MVP đủ demo** nhưng vẫn “đúng kiến trúc” (có KG Neo4j, có mô hình hành vi LSTM, có chat RAG cá nhân hoá).

---

## 1) Tổng quan kiến trúc

### 1.1 Microservices (đề xuất tối thiểu)

- `product-service` (PostgreSQL)
  - Quản lý product types, products, variants, images, search.
- `interaction-service` (PostgreSQL hoặc Kafka + storage) — có thể tách hoặc nhúng tạm trong gateway khi MVP
  - Ghi log hành vi: view/search/cart/purchase/chat.
- `ai-service` (Django REST hoặc FastAPI)
  - ETL → Neo4j KG
  - Training LSTM / inference user embedding
  - Recommend API
  - Chat API (GraphRAG + LLM)
- `neo4j` (Knowledge Graph + có thể kiêm Vector Index)
- LLM provider (Gemini API)

### 1.2 Online vs Offline

- **Online (real-time / near real-time)**
  - Ghi event hành vi
  - Cập nhật cạnh KG (weights)
  - Trả lời chat / recommendation dựa trên dữ liệu hiện có
- **Offline (batch, định kỳ)**
  - Dọn dữ liệu + tạo sequence
  - Train LSTM
  - Sinh embedding (user/product/query)
  - Ghi embedding vào Neo4j + build vector index

---

## 2) Dữ liệu đầu vào: cần có những bảng/record gì?

### 2.1 Product data (từ product-service)

Tối thiểu cần:
- `product_id`, `product_type` (`LAPTOP`/`CLOTHES`)
- `name`, `description`, `base_price`, `currency`, `is_active`
- `brand`, `category`
- `attributes` (JSONB) theo schema (laptop specs / clothes material-size-color)
- `images[]`

**Mục tiêu AI:**
- Dùng để tạo node `Product`, `Brand`, `Category` trong KG
- Dùng để tạo “document” cho RAG (mô tả sản phẩm, hướng dẫn chọn, policies)

### 2.2 Interaction / behavior data (từ interaction-service)

Schema gợi ý (tương thích với [ai2.md](ai2.md) nhưng tổng quát hơn):
- `event_id`
- `user_id`, `session_id`
- `event_type`: `view` | `search` | `add_to_cart` | `purchase` | `chat`
- `product_id` (nullable)
- `query_text` (nullable)
- `duration_ms` (nullable)
- `created_at`
- `metadata` JSON (page, filters, referrer, device, …)

**Mục tiêu AI:**
- Tạo các cạnh có trọng số trong KG
- Tạo chuỗi hành vi để train LSTM
- Tạo context cá nhân hoá cho chat

### 2.3 Knowledge base (docs)

Có 2 nguồn:
1) **Docs tĩnh**: guides/policies/faq (markdown)
2) **Docs động**: mô tả sản phẩm (từ product-service) → chuyển thành đoạn văn để RAG

**MVP:** chỉ cần (2) + vài file guides/policies.

---

## 3) Knowledge Graph trong Neo4j

### 3.1 Node types

- `(:User {id})`
- `(:Product {id, product_type, name, price, brand_id, category_id, ...})`
- `(:Category {id, slug, name})`
- `(:Brand {id, name})`
- `(:Query {text, normalized_text, lang, ...})` (tuỳ MVP)

### 3.2 Edge types (quan trọng)

- (User)-[:VIEWED {w, cnt, last_ts}]->(Product)
- (User)-[:CARTED {w, cnt, last_ts}]->(Product)
- (User)-[:PURCHASED {w, cnt, last_ts}]->(Product)
- (User)-[:SEARCHED {w, cnt, last_ts}]->(Query)
- (Query)-[:MATCHES {score}]->(Product) (optional)
- (Product)-[:BELONGS_TO]->(Category)
- (Product)-[:BRANDED_BY]->(Brand)
- (Product)-[:SIMILAR_TO {score}]->(Product) (offline job tạo)

### 3.3 Trọng số tương tác (weights)

Tạo weight aggregate để biểu diễn “interest/trust”:

$$ w_{u,p} = \alpha \cdot views + \beta \cdot carts + \gamma \cdot purchases $$

Gợi ý MVP:
- views: α=1
- carts: β=3
- purchases: γ=10

**Online job cần làm:**
- Khi có event mới, `MERGE` node/edge và update `cnt`, `last_ts`, `w`.

### 3.4 Neo4j constraints / indexes tối thiểu

- Unique:
  - `User(id)`
  - `Product(id)`
  - `Category(id)`
  - `Brand(id)`
  - `Query(normalized_text)`
- Index:
  - `Product(product_type)`
  - `Product(category_id)`
  - `Product(brand_id)`

---

## 4) Mô hình hành vi LSTM (Behavior Model)

### 4.1 LSTM dùng để làm gì trong hệ này?

Trong kiến trúc ai1.md, LSTM là baseline rất hợp lý để:
- Học **sequence** hành vi: `search → view → cart → purchase`
- Sinh **user embedding** (vector) hoặc dự đoán **next item / next intent**
- Làm feature cho:
  - Recommendation cá nhân hoá
  - “User segment” (k-means trên embedding)
  - Chat personalization (tone, budget, brand bias)

### 4.2 Dữ liệu train cần gì?

Từ interaction logs, tạo dataset theo user:
- Sắp xếp theo thời gian
- Chuyển event thành token sequence:
  - item token: `product_id` (hoặc bucket theo category/brand)
  - event token: view/cart/purchase/search/chat
  - query token: optional (dùng embedding text hoặc mapping từ vựng)

MVP đơn giản:
- Input: sequence of `product_id` + `event_type`
- Label: `next_product_id` (next-item prediction) hoặc `next_event_type`

### 4.3 Offline pipeline cần làm

1) Extract logs (ví dụ last 30 ngày)
2) Transform thành sequences (fixed length `T`, padding)
3) Train LSTM
4) Export artifacts:
   - `behavior_lstm.pt`
   - `id_mappings.json` (product_id→index, event_type→index)
5) Batch inference:
   - sinh `user_embedding` cho mỗi user
   - (optional) sinh `product_embedding`
6) Cluster:
   - `segment = kmeans(user_embedding)` (k=6 như ai2.md)
7) Upsert sang Neo4j:
   - set properties `u.embedding = [..]`, `u.segment = ...`

### 4.4 Online inference cần làm

- Khi user chat/recommend:
  - lấy `user_embedding` + `segment` mới nhất từ Neo4j
  - nếu thiếu: fallback = `new_user` + heuristic theo session

---

## 5) Recommendation: luồng hoạt động và cần làm gì?

### 5.1 Recommendation API (đề xuất)

- `GET /api/v1/recommendations?user_id=...&product_type=LAPTOP&k=10`

**Output**: list product_ids + score + reason.

### 5.2 Chiến lược recommend MVP (không cần FAISS ngay)

MVP nên đi theo “Graph-first”, vì bạn đã dùng Neo4j:

1) **Graph neighbor expansion**
- Lấy top products user tương tác mạnh nhất
- Mở rộng sang:
  - sản phẩm cùng brand/category
  - hoặc `SIMILAR_TO` (offline tạo)

2) **User-user similarity** (nếu đã có embedding)
- KNN search theo `user_embedding` để lấy “similar users”
- Aggregation sản phẩm họ mua/cart nhiều

3) **Re-rank**
- lọc theo `product_type` / price range / in_stock
- ưu tiên theo segment (bargain hunter → price thấp; tech enthusiast → specs)

### 5.3 Dữ liệu cần ở bước recommend

- Từ Neo4j:
  - edges User→Product (weights)
  - user embedding + segment
  - product metadata (type, price, brand, category)
  - optional similarity edges
- Từ product-service (khi cần detail để hiển thị):
  - detail + images + stock

---

## 6) Chatbot GraphRAG: luồng hoạt động và cần làm gì?

### 6.1 Endpoint chat

- `POST /api/v1/chat/message`

Request:
- `user_id`
- `message`
- `context` (page, current_product_type tab, filters, cart state)

Response:
- `answer`
- `rag_sources` (references)
- `suggested_actions`
- `user_segment`

### 6.2 Retrieval sources (GraphRAG)

Khi user hỏi, cần dựng context từ 3 lớp:

**(A) Behavior context (từ KG)**
- segment
- brand preference
- viewed categories
- recently viewed products

**(B) Graph traversal context (từ KG)**
- products liên quan qua:
  - category/brand
  - similar_to
  - “users similar” (nếu có vector search)

**(C) Text knowledge context (docs)**
- mô tả sản phẩm
- guides/policies/faq

### 6.3 Prompt assembly (đầu ra cho LLM)

Gợi ý prompt structure:
- System: “Bạn là trợ lý tư vấn laptop/clothes…”
- User profile: segment + preferences
- Retrieved facts: list bullet (product candidates + key specs + price)
- Policies/guides snippets
- User question
- Output constraints: 2-3 options + hỏi ngược 1 câu

### 6.4 Cần dữ liệu gì ở bước chat?

- User graph subgraph:
  - top edges, last interactions
- Candidate products:
  - ids + short specs + price
- Docs chunks:
  - 3-6 đoạn có liên quan

---

## 7) FAISS hay Neo4j Vector Index? (quyết định kiến trúc)

Bạn đang phân vân giữa:
- **FAISS** (vector DB/ANN riêng, thường dùng trong ML)
- **Neo4j Vector Index** (Neo4j 5.x có hỗ trợ vector index + KNN)

### 7.1 Khi nào dùng Neo4j Vector Index (khuyến nghị cho MVP)

Chọn Neo4j Vector Index nếu:
- Bạn đã dùng Neo4j làm KG chính
- Muốn giảm số service/độ phức tạp triển khai
- Nhu cầu vector search ở mức vừa (k vài chục / vài trăm) + dataset không quá lớn
- Muốn **Graph + Vector** trong 1 chỗ để GraphRAG tiện hơn

Ưu điểm:
- 1 hệ thống dữ liệu: vừa traversal vừa vector KNN
- Triển khai đơn giản (một DB)
- Dễ viết Cypher: “lọc theo product_type rồi KNN”

Nhược điểm:
- Hiệu năng/chi phí có thể kém hơn FAISS khi scale lớn
- Ít tuỳ biến ANN hơn một số vector DB chuyên dụng

### 7.2 Khi nào dùng FAISS

Chọn FAISS nếu:
- Dataset vector rất lớn (nhiều triệu chunks/products/users)
- Cần latency rất thấp cho KNN
- Muốn pipeline ML độc lập và tối ưu mạnh cho embedding retrieval

Ưu điểm:
- Rất nhanh, nhiều thuật toán index (IVF, HNSW, PQ)
- Rất hợp cho retrieval docs/chunks

Nhược điểm:
- Thêm 1 thành phần phải vận hành
- Kết hợp Graph traversal + FAISS cần glue code

### 7.3 Khuyến nghị “đúng bài” cho bạn

- **MVP demo môn học:** dùng **Neo4j Vector Index** (gọn, đúng GraphRAG)
- **Nếu cần retrieval docs chunk kiểu RAG chuẩn:** vẫn có thể thêm FAISS (hoặc vector DB khác) cho “documents”, còn Neo4j giữ “graph + entity vectors”.

Nói cách khác:
- Neo4j: entity graph + entity embeddings (User/Product)
- FAISS: text chunks embeddings (Guides/Policies/Product descriptions)

---

## 8) Các job/worker cần có (tối thiểu)

### 8.1 Online event ingestor

Input: event từ gateway/cart/product service
- Lưu vào interaction DB
- Update Neo4j edges

### 8.2 Batch training job (LSTM)

- Pull logs
- Build sequences
- Train
- Export embeddings

### 8.3 Batch graph enrichment job

- Tạo `SIMILAR_TO` giữa products (dựa category/brand + embedding similarity)
- Xây vector index trong Neo4j

### 8.4 Chat retrieval job (runtime)

- Nhận message
- Kéo context từ Neo4j
- Lấy docs (Neo4j vector index hoặc FAISS)
- Build prompt → gọi Gemini

---

## 9) Luồng end-to-end (demo)

### 9.1 Luồng 1: User browse → recommend

1) User view product P1
2) Gateway gửi event → interaction-service
3) Ingestor update Neo4j: (U)-[:VIEWED{w+=1}]->(P1)
4) Khi user mở trang home/list:
   - gọi recommend API
   - recommend lấy top products từ graph + rerank theo segment
5) Gateway gọi product-service để render cards

### 9.2 Luồng 2: User chat → GraphRAG

1) User hỏi: “Laptop gaming 25tr stream ổn?”
2) ai-service:
   - lấy segment + recent interactions từ Neo4j
   - traverse graph lấy candidate products
   - retrieve docs snippets
   - prompt → Gemini
3) Trả answer + sources + suggested_actions

---

## 10) Checklist triển khai (bạn cần làm gì theo từng giai đoạn)

### Phase A — MVP đúng kiến trúc (1–2 tuần)

- [ ] Tạo `interaction-service` và chuẩn hoá event schema
- [ ] Dựng Neo4j schema + constraints + indexes
- [ ] Ingestor: logs → Neo4j edges (weights)
- [ ] Recommend baseline bằng Cypher traversal
- [ ] Chat baseline: Graph traversal + policies/guides + Gemini

### Phase B — Thêm LSTM (1 tuần)

- [ ] Offline dataset builder (sequences)
- [ ] Train LSTM + export embeddings
- [ ] Segment users (kmeans)
- [ ] Upsert `user_embedding`/`segment` vào Neo4j
- [ ] Re-rank recommend/chat theo segment

### Phase C — Vector search (tuỳ)

- [ ] Neo4j vector index cho User/Product
- [ ] (Optional) FAISS cho docs chunks

---

## 11) Gợi ý deliverables để viết báo cáo môn học

- ERD product-service (đã có)
- KG schema (nodes/edges + weight formula)
- Mô tả pipeline ETL + training LSTM
- Mermaid sequence diagram (online recommend/chat)
- Phân tích trade-off FAISS vs Neo4j vector index (phần 7)

---

Nếu bạn confirm là sẽ dùng **Neo4j Vector Index cho MVP**, mình có thể viết tiếp 2 thứ ngay trong repo:
- `neo4j_setup.md` + `docker-compose` mẫu cho Neo4j (password, volumes, browser port)
- `cypher/` gồm script tạo constraints + ví dụ query recommend + query GraphRAG retrieval
