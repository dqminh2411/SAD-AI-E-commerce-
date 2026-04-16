# AI Chat Service (RAG + Behavior)

MVP chatbot theo mo ta trong ai2.md:
- RAG voi FAISS (vector store local trong service)
- Knowledge base markdown fake
- Ca nhan hoa theo model_behavior (fake profiles)
- Goi Gemini neu co GEMINI_API_KEY, fallback rule-based neu chua co key

## Endpoints

- GET /api/v1/chat/health/
- POST /api/v1/chat/message/

Body mau:

{
  "user_id": "US_001",
  "message": "Tu van laptop gaming tam 25 trieu",
  "context": {
    "page": "home",
    "category": "gaming"
  }
}

## Re-index knowledge base

Trong container ai_chat_service (se rebuild FAISS index):

python manage.py init_kb --force

## Vector store

FAISS index duoc luu o:
- /app/vector_store/kb.index
- /app/vector_store/kb_meta.json
- /app/vector_store/tfidf_svd.joblib

Neu ban sua/bo sung markdown trong knowledge_base, service se tu rebuild index khi can, hoac ban co the chay lai:

python manage.py init_kb --force
