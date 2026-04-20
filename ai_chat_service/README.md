# AI Chat Service (RAG + Behavior)

Service chatbot MVP:
- RAG với **FAISS** (vector store local trong service).
- Knowledge base: markdown trong `knowledge_base/`.
- Cá nhân hoá theo segment/hành vi (fake profiles) + có thể lấy thêm context từ Neo4j.
- Gọi Gemini nếu có `GEMINI_API_KEY`, nếu không sẽ fallback rule-based.

## Endpoints

- `GET /api/v1/chat/health/`
- `POST /api/v1/chat/message/`

Body mẫu:

```json
{
  "user_id": "US_001",
  "message": "Tu van laptop gaming tam 25 trieu",
  "context": {
    "page": "home",
    "category": "gaming"
  }
}
```

## Embeddings

- Model mặc định: `paraphrase-multilingual-MiniLM-L12-v2` (Sentence-Transformers)
- Có thể override qua env: `EMBEDDING_MODEL_NAME`

Lưu ý: lần đầu chạy sẽ tải model từ HuggingFace (cần internet).

## Re-index knowledge base

Trong container `ai_chat_service` (rebuild FAISS index):

```bash
python manage.py init_kb --force
```

## Vector store

FAISS index được lưu tại:
- `/app/vector_store/kb.index`
- `/app/vector_store/kb_meta.json`
- `/app/vector_store/embedder_meta.json`

Nếu bạn sửa/ thêm markdown trong `knowledge_base/`, service sẽ tự rebuild index khi cần, hoặc chạy lại lệnh `init_kb --force`.
