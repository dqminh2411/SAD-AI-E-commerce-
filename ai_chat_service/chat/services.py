import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import faiss
import joblib
import numpy as np
import requests
from google.generativeai import GenerativeModel, configure
from neo4j import GraphDatabase
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer


BASE_DIR = Path(__file__).resolve().parent.parent
BEHAVIOR_DATA_PATH = Path(os.environ.get('BEHAVIOR_DATA_PATH', BASE_DIR / 'data' / 'fake_user_behavior.json'))
KNOWLEDGE_BASE_PATH = Path(os.environ.get('KNOWLEDGE_BASE_PATH', BASE_DIR / 'knowledge_base'))
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

PRODUCT_SERVICE_URL = os.environ.get('PRODUCT_SERVICE_URL', '')

NEO4J_URI = os.environ.get('NEO4J_URI', '')
NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', '')

VECTOR_STORE_DIR = Path(os.environ.get('VECTOR_STORE_DIR', BASE_DIR / 'vector_store'))
FAISS_INDEX_PATH = Path(os.environ.get('FAISS_INDEX_PATH', VECTOR_STORE_DIR / 'kb.index'))
FAISS_META_PATH = Path(os.environ.get('FAISS_META_PATH', VECTOR_STORE_DIR / 'kb_meta.json'))
VECTORIZER_PATH = Path(os.environ.get('VECTORIZER_PATH', VECTOR_STORE_DIR / 'tfidf_svd.joblib'))


@dataclass
class RetrievedChunk:
    title: str
    file_path: str
    relevance: float
    chunk_excerpt: str


def _get_embedder():
    """Returns (vectorizer, svd) used to embed text into dense vectors.

    Note: We intentionally use a lightweight TF-IDF + SVD pipeline to keep the MVP
    container small and avoid pulling in PyTorch/CUDA dependencies.
    """

    if hasattr(_get_embedder, '_embedder'):
        return _get_embedder._embedder

    if VECTORIZER_PATH.exists():
        _get_embedder._embedder = joblib.load(VECTORIZER_PATH)
        return _get_embedder._embedder

    # Not fitted yet; build_kb_index() will fit and persist.
    _get_embedder._embedder = None
    return None


def _chunk_text(text: str, chunk_size: int = 700, overlap: int = 100):
    chunks = []
    start = 0
    text = text.strip()
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks


def _load_kb_documents():
    docs: list[dict[str, Any]] = []
    for path in KNOWLEDGE_BASE_PATH.rglob('*.md'):
        try:
            content = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            content = path.read_text(encoding='utf-8', errors='ignore')

        chunks = _chunk_text(content)
        rel_path = str(path.relative_to(BASE_DIR)).replace('\\\\', '/').replace('\\', '/')
        title = path.stem.replace('_', ' ').strip()

        for idx, chunk in enumerate(chunks):
            chunk_id = f"{rel_path}#{idx}"
            docs.append(
                {
                    'id': chunk_id,
                    'document': chunk,
                    'metadata': {
                        'title': title,
                        'file_path': rel_path,
                        'chunk_index': idx,
                    },
                }
            )
    return docs


def _ensure_vector_store_dir():
    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)


def _latest_kb_mtime() -> float:
    latest = 0.0
    for path in KNOWLEDGE_BASE_PATH.rglob('*.md'):
        try:
            latest = max(latest, path.stat().st_mtime)
        except OSError:
            continue
    return latest


def _index_mtime() -> float:
    mtimes = []
    for p in (FAISS_INDEX_PATH, FAISS_META_PATH, VECTORIZER_PATH):
        if not p.exists():
            return 0.0
        try:
            mtimes.append(p.stat().st_mtime)
        except OSError:
            return 0.0
    return min(mtimes) if mtimes else 0.0


def _kb_is_stale() -> bool:
    kb_time = _latest_kb_mtime()
    idx_time = _index_mtime()
    if kb_time == 0.0:
        return False
    if idx_time == 0.0:
        return True
    return kb_time > idx_time


def _load_faiss_store():
    if not FAISS_INDEX_PATH.exists() or not FAISS_META_PATH.exists() or not VECTORIZER_PATH.exists():
        return None
    index = faiss.read_index(str(FAISS_INDEX_PATH))
    meta = json.loads(FAISS_META_PATH.read_text(encoding='utf-8'))
    if not isinstance(meta, list):
        return None
    embedder = joblib.load(VECTORIZER_PATH)
    return {'index': index, 'meta': meta, 'embedder': embedder}


def _save_faiss_store(index: faiss.Index, meta: list[dict[str, Any]]):
    _ensure_vector_store_dir()
    faiss.write_index(index, str(FAISS_INDEX_PATH))
    FAISS_META_PATH.write_text(json.dumps(meta, ensure_ascii=False), encoding='utf-8')


def _fit_embedder(corpus: list[str], max_features: int = 50000, target_dim: int = 256):
    vectorizer = TfidfVectorizer(
        lowercase=True,
        strip_accents=None,
        analyzer='word',
        ngram_range=(1, 2),
        max_features=max_features,
    )

    tfidf = vectorizer.fit_transform(corpus)
    # TruncatedSVD requires n_components < n_features
    n_features = int(getattr(tfidf, 'shape', [0, 0])[1])
    if n_features <= 2:
        dim = max(2, n_features)
    else:
        dim = min(target_dim, n_features - 1)
        dim = max(32, dim)

    svd = TruncatedSVD(n_components=dim, random_state=42)
    svd.fit(tfidf)
    return vectorizer, svd


def _embed_texts(embedder, texts: list[str]) -> np.ndarray:
    vectorizer, svd = embedder
    tfidf = vectorizer.transform(texts)
    dense = svd.transform(tfidf)
    vectors = np.asarray(dense, dtype=np.float32)
    faiss.normalize_L2(vectors)
    return vectors


def build_kb_index(force: bool = False):
    docs = _load_kb_documents()
    if not docs:
        return {'indexed': 0, 'reason': 'knowledge base is empty'}

    if not force:
        existing = _load_faiss_store()
        if existing is not None and not _kb_is_stale():
            return {
                'indexed': 0,
                'reason': 'faiss index already exists',
                'index_path': str(FAISS_INDEX_PATH),
            }

    texts = [item['document'] for item in docs]
    embedder = _fit_embedder(texts)
    vectors = _embed_texts(embedder, texts)
    if vectors.ndim != 2 or vectors.shape[0] != len(docs):
        return {'indexed': 0, 'reason': 'vector shape is invalid'}

    dim = int(vectors.shape[1])
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)

    meta = [
        {
            'id': item['id'],
            'document': item['document'],
            'metadata': item['metadata'],
        }
        for item in docs
    ]
    _save_faiss_store(index, meta)
    joblib.dump(embedder, VECTORIZER_PATH)
    return {
        'indexed': len(docs),
        'index_path': str(FAISS_INDEX_PATH),
        'meta_path': str(FAISS_META_PATH),
        'vectorizer_path': str(VECTORIZER_PATH),
        'dim': dim,
    }


def ensure_kb_index():
    if getattr(ensure_kb_index, '_done', False):
        return
    try:
        if _load_faiss_store() is None or _kb_is_stale():
            build_kb_index(force=_kb_is_stale())
        ensure_kb_index._done = True
    except Exception:
        # Do not fail the chat endpoint just because indexing is not available.
        ensure_kb_index._done = False


def _load_behavior_profiles():
    if not BEHAVIOR_DATA_PATH.exists():
        return {}
    with BEHAVIOR_DATA_PATH.open('r', encoding='utf-8') as f:
        payload = json.load(f)
    return {item['user_id']: item for item in payload.get('users', [])}


def _retrieve_chunks(query: str, user_segment: str, top_k: int = 4):
    try:
        store = _load_faiss_store()
        if store is None:
            return []

        q = f"{query}\nsegment:{user_segment}"
        q_vec = _embed_texts(store['embedder'], [q])

        top_k = max(1, min(int(top_k), 20))
        scores, indices = store['index'].search(q_vec, top_k)
        scores = scores[0].tolist()
        indices = indices[0].tolist()

        items: list[RetrievedChunk] = []
        for score, idx in zip(scores, indices):
            if idx < 0:
                continue
            entry = store['meta'][idx]
            meta = entry.get('metadata', {}) or {}
            doc = entry.get('document', '') or ''
            # score is inner product of L2-normalized vectors => [-1, 1], map to [0, 1]
            relevance = max(0.0, min(1.0, (float(score) + 1.0) / 2.0))
            items.append(
                RetrievedChunk(
                    title=str(meta.get('title', 'Knowledge Snippet')),
                    file_path=str(meta.get('file_path', '')),
                    relevance=relevance,
                    chunk_excerpt=(doc[:260] + '...') if len(doc) > 260 else doc,
                )
            )
        return items
    except Exception:
        return []


def _get_neo4j_driver():
    if not NEO4J_URI or not NEO4J_PASSWORD:
        return None

    if hasattr(_get_neo4j_driver, '_driver'):
        return _get_neo4j_driver._driver

    try:
        _get_neo4j_driver._driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD),
        )
    except Exception:
        _get_neo4j_driver._driver = None

    return _get_neo4j_driver._driver


def _fetch_graph_context(user_id: str, product_type: str | None, limit: int = 5) -> dict[str, Any]:
    driver = _get_neo4j_driver()
    if driver is None:
        return {}

    limit = max(1, min(int(limit), 20))
    product_type = product_type.strip().upper() if product_type else None

    top_products_cypher = """
MATCH (u:User {id: $user_id})-[r:VIEWED|CARTED|PURCHASED]->(p:Product)
WHERE $product_type IS NULL OR p.product_type = $product_type
WITH p, sum(coalesce(r.w, 1)) AS score, max(coalesce(r.last_ts, datetime('1970-01-01T00:00:00Z'))) AS last_ts
OPTIONAL MATCH (p)-[:BRANDED_BY]->(b:Brand)
RETURN p.id AS product_id, p.name AS name, p.base_price AS base_price, p.currency AS currency,
       b.name AS brand, score AS score
ORDER BY score DESC, last_ts DESC
LIMIT $limit
""".strip()

    brand_affinity_cypher = """
MATCH (u:User {id: $user_id})-[r:VIEWED|CARTED|PURCHASED]->(p:Product)-[:BRANDED_BY]->(b:Brand)
WHERE $product_type IS NULL OR p.product_type = $product_type
RETURN b.name AS brand, sum(coalesce(r.w, 1)) AS score
ORDER BY score DESC
LIMIT $limit
""".strip()

    try:
        with driver.session() as session:
            top_products = [
                dict(record)
                for record in session.run(
                    top_products_cypher,
                    user_id=user_id,
                    product_type=product_type,
                    limit=limit,
                )
            ]
            brand_affinity = [
                dict(record)
                for record in session.run(
                    brand_affinity_cypher,
                    user_id=user_id,
                    product_type=product_type,
                    limit=limit,
                )
            ]

        return {
            'top_products': top_products,
            'brand_affinity': brand_affinity,
        }
    except Exception:
        return {}


_VI_STOPWORDS = {
    'mình', 'minh', 'cần', 'can', 'muốn', 'muon', 'nhờ', 'nho', 'tư', 'tu', 'vấn', 'van', 'tầm', 'tam',
    'khoảng', 'khoang', 'tư vấn', 'tu van', 'nên', 'nen', 'chọn', 'chon', 'gì', 'gi', 'giúp', 'giup',
    'laptop', 'máy', 'may', 'cho', 'với', 'voi', 'và', 'va', 'có', 'co', 'một', 'mot', 'cái', 'cai',
    'triệu', 'trieu',
}


def _extract_budget_vnd(message: str) -> int | None:
    m = re.search(r"(\d+(?:[\.,]\d+)?)\s*(triệu|trieu)", message.lower())
    if not m:
        return None
    raw = m.group(1).replace(',', '.').strip()
    try:
        value = float(raw)
    except Exception:
        return None
    if value <= 0:
        return None
    return int(round(value * 1_000_000))


def _detect_intent(message: str) -> str | None:
    m = (message or '').lower()
    if ('mỏng' in m and 'nhẹ' in m) or 'ultrabook' in m:
        return 'THIN_LIGHT'
    if ('đồ hoạ' in m) or ('do hoa' in m) or ('kỹ thuật' in m) or ('ky thuat' in m) or ('workstation' in m):
        return 'GRAPHICS_TECH'
    return None


def _intent_query(intent: str | None) -> str:
    if intent == 'THIN_LIGHT':
        return 'mỏng nhẹ'
    if intent == 'GRAPHICS_TECH':
        return 'đồ hoạ kỹ thuật'
    return ''


def _build_product_search_term(message: str) -> str:
    # Keep only a few meaningful tokens to avoid overly-strict FTS queries.
    tokens = re.findall(r"[\w]+", (message or "").lower())
    tokens = [t for t in tokens if t and t not in _VI_STOPWORDS and len(t) >= 3]
    return " ".join(tokens[:6])


def _fetch_catalog_products(
    product_type: str,
    message: str,
    preferred_brands: list[str] | None = None,
    limit: int = 8,
) -> list[dict[str, Any]]:
    if not PRODUCT_SERVICE_URL:
        return []

    base = PRODUCT_SERVICE_URL.rstrip('/') + '/api/v1/products/'

    budget = _extract_budget_vnd(message)
    intent = _detect_intent(message)

    q = _intent_query(intent).strip() or _build_product_search_term(message)

    def _request(p: dict[str, Any]) -> list[dict[str, Any]] | None:
        try:
            r = requests.get(base, params=p, timeout=5)
            if r.status_code != 200:
                return None
            data = r.json() if r.content else {}
        except Exception:
            return None

        items = data.get('results', data) if isinstance(data, dict) else data
        return items if isinstance(items, list) else None

    base_params: dict[str, Any] = {
        'product_type': product_type,
        'page_size': max(1, min(int(limit), 12)),
    }

    candidates: list[dict[str, Any]] = []

    # Try: intent/search + budget (tight), then widen, then remove budget, then remove search.
    if q and budget is not None:
        tight = dict(base_params)
        tight['q'] = q
        tight['min_price'] = int(budget * 0.85)
        tight['max_price'] = int(budget * 1.15)
        candidates = _request(tight) or []

        if not candidates:
            wide = dict(base_params)
            wide['q'] = q
            wide['min_price'] = int(budget * 0.70)
            wide['max_price'] = int(budget * 1.30)
            candidates = _request(wide) or []

    if not candidates and q:
        by_intent = dict(base_params)
        by_intent['q'] = q
        candidates = _request(by_intent) or []

    if not candidates and budget is not None:
        by_budget = dict(base_params)
        by_budget['min_price'] = int(budget * 0.70)
        by_budget['max_price'] = int(budget * 1.30)
        candidates = _request(by_budget) or []

    if not candidates:
        candidates = _request(base_params) or []

    preferred_brands = preferred_brands or []
    preferred_lc = [b.lower() for b in preferred_brands if b]

    def _is_preferred(p: dict[str, Any]) -> bool:
        brand = (p.get('brand') or {}).get('name') if isinstance(p.get('brand'), dict) else p.get('brand')
        return bool(brand) and brand.lower() in preferred_lc

    def _intent_score(p: dict[str, Any]) -> int:
        name = (p.get('name') or '').lower()
        if intent == 'THIN_LIGHT':
            keys = ['slim', 'air', 'zenbook', 'vivobook', 'thinkpad x1', 'carbon']
        elif intent == 'GRAPHICS_TECH':
            keys = ['gaming', 'nitro', 'katana', 'rtx', 'rog', 'tuf', 'aspire 7']
        else:
            keys = []
        return sum(1 for k in keys if k in name)

    candidates = sorted(
        candidates,
        key=lambda p: (
            0 if _is_preferred(p) else 1,
            -_intent_score(p),
        ),
    )

    normalized: list[dict[str, Any]] = []
    for p in candidates[: max(1, min(int(limit), 12))]:
        brand = p.get('brand')
        normalized.append(
            {
                'id': p.get('id'),
                'name': p.get('name'),
                'brand': brand.get('name') if isinstance(brand, dict) else brand,
                'base_price': p.get('base_price'),
                'currency': p.get('currency'),
                'in_stock': p.get('in_stock'),
                'thumbnail_url': p.get('thumbnail_url'),
                'created_at': p.get('created_at'),
            }
        )
    return normalized


def _fallback_answer(
    message: str,
    profile: dict[str, Any],
    chunks: list[RetrievedChunk],
    catalog_products: list[dict[str, Any]],
):
    segment = profile.get('segment', 'new_user')

    if catalog_products:
        lines = [
            f"Mình đang tư vấn dựa trên dữ liệu sản phẩm hiện có trong hệ thống (segment: {segment}).",
            "Nếu chưa có mẫu đúng *chính xác* ngân sách bạn nêu, mình sẽ gợi ý vài mẫu gần/nhỉnh hơn hoặc thấp hơn trong catalog:",
        ]
        for p in catalog_products[:3]:
            price = p.get('base_price')
            cur = p.get('currency') or 'VND'
            brand = p.get('brand') or 'N/A'
            lines.append(f"- {p.get('name')} ({brand}) — {price} {cur}")

        lines.append("Bạn ưu tiên phần mềm nào (AutoCAD, SolidWorks, Revit, Blender...) và có cần mỏng nhẹ hay ưu tiên hiệu năng/tản nhiệt?")
        return "\n".join(lines)

    prefix = 'MVP chatbot (fallback mode): '
    if not chunks:
        return (
            prefix
            + 'Mình chưa truy vấn được kho tri thức và cũng chưa lấy được danh sách sản phẩm lúc này. '
            + f"Dựa trên segment '{segment}', bạn nên ưu tiên RAM 16GB, SSD 512GB, GPU rời nếu làm đồ hoạ/kỹ thuật."
        )

    top_titles = ', '.join(chunk.title for chunk in chunks[:2])
    return (
        prefix
        + f"Câu hỏi: '{message}'. "
        + f"Người dùng thuộc nhóm '{segment}'. "
        + f"Tài liệu liên quan: {top_titles}. "
        + 'Gợi ý nhanh: ưu tiên cấu hình cân bằng CPU/GPU, kiểm tra chính sách bảo hành 12-24 tháng, và so sánh theo mức ngân sách.'
    )


def _generate_with_gemini(
    message: str,
    profile: dict[str, Any],
    context: dict[str, Any],
    chunks: list[RetrievedChunk],
    catalog_products: list[dict[str, Any]],
    graph_context: dict[str, Any],
):
    if not GEMINI_API_KEY:
        return None

    snippets = '\n\n'.join(
        [f"[{idx + 1}] {chunk.title} ({chunk.file_path})\n{chunk.chunk_excerpt}" for idx, chunk in enumerate(chunks)]
    )

    prompt = f"""
Bạn là chatbot tư vấn sản phẩm cho website e-commerce (laptop & clothes).
Trả lời tiếng Việt, ngắn gọn, rõ ràng, bám sát dữ liệu hệ thống.

Thông tin hành vi khách hàng:
- user_id: {profile.get('user_id', 'unknown')}
- segment: {profile.get('segment', 'new_user')}
- brand_preference: {', '.join(profile.get('brand_preference', []))}
- price_sensitivity: {profile.get('price_sensitivity', 'medium')}
- viewed_categories: {', '.join(profile.get('viewed_categories', []))}

Context từ frontend:
{json.dumps(context, ensure_ascii=False)}

Danh sách sản phẩm hiện có trong hệ thống (catalog):
{json.dumps(catalog_products, ensure_ascii=False)}

Context graph từ Neo4j (hành vi & affinity, dùng để cá nhân hoá):
{json.dumps(graph_context, ensure_ascii=False)}

Tài liệu truy xuất từ knowledge base:
{snippets if snippets else 'Không có tài liệu truy xuất được'}

Câu hỏi người dùng: {message}

Ràng buộc quan trọng:
1) Chỉ được đề xuất sản phẩm có trong catalog ở trên. Không được tự chế tên dòng/mẫu (ví dụ "Dell G-series") nếu catalog không có.
2) Nếu ít sản phẩm thuộc hãng yêu thích, hãy nói rõ và gợi ý thêm hãng khác nhưng vẫn phải nằm trong catalog.

Yêu cầu đầu ra:
- Đề xuất 2-3 lựa chọn cụ thể (tên sản phẩm + giá) nếu catalog có.
- Nếu catalog trống/không phù hợp, nêu rõ và hỏi thêm 1-2 câu để lọc nhu cầu.
""".strip()

    configure(api_key=GEMINI_API_KEY)
    model = GenerativeModel(model_name=GEMINI_MODEL)
    response = model.generate_content(prompt)
    text = getattr(response, 'text', None)
    return text.strip() if text else None


def _suggest_actions(profile: dict[str, Any]):
    preferred = profile.get('brand_preference', [])
    top_brand = preferred[0] if preferred else 'laptop'
    return [
        {'type': 'open_category', 'value': 'laptops'},
        {'type': 'apply_filter', 'value': 'ram>=16'},
        {'type': 'search', 'value': top_brand},
    ]


class ChatbotService:
    def __init__(self):
        self.behavior_profiles = _load_behavior_profiles()

    def answer(self, user_id: str, message: str, context: dict[str, Any] | None = None):
        started = time.time()
        context = context or {}
        profile = self.behavior_profiles.get(user_id)

        tab = str(context.get('current_tab') or 'LAPTOP').strip().upper()
        product_type = 'CLOTHES' if tab == 'CLOTHES' else 'LAPTOP'

        if not profile:
            profile = {
                'user_id': user_id,
                'segment': 'new_user',
                'viewed_categories': ['clothes'] if product_type == 'CLOTHES' else ['laptops'],
                'price_sensitivity': 'medium',
                'brand_preference': [],
                'session_duration': 420,
            }

        preferred_brands = profile.get('brand_preference', []) or []

        # Guests can chat, but without personalization (no Neo4j graph queries).
        graph_context: dict[str, Any] = {}
        graph_brands: list[str] = []
        if user_id and user_id != 'guest_user':
            graph_context = _fetch_graph_context(user_id=user_id, product_type=product_type, limit=5)
            graph_brands = [
                item.get('brand')
                for item in (graph_context.get('brand_affinity', []) or [])
                if isinstance(item, dict) and item.get('brand')
            ]

        effective_preferred_brands = preferred_brands or graph_brands
        catalog_products = _fetch_catalog_products(
            product_type=product_type,
            message=message,
            preferred_brands=effective_preferred_brands,
            limit=8,
        )

        chunks = _retrieve_chunks(message, user_segment=profile.get('segment', 'new_user'))
        gemini_answer = _generate_with_gemini(message, profile, context, chunks, catalog_products, graph_context)

        if gemini_answer and catalog_products:
            ans_lc = gemini_answer.lower()
            # If the model didn't mention any concrete catalog item, fall back to data-driven suggestions.
            if not any((p.get('name') or '').lower() in ans_lc for p in catalog_products[:5] if p.get('name')):
                gemini_answer = None

        answer = gemini_answer or _fallback_answer(message, profile, chunks, catalog_products)

        duration_ms = int((time.time() - started) * 1000)

        return {
            'answer': answer,
            'user_segment': profile.get('segment', 'new_user'),
            'rag_sources': [
                {
                    'title': chunk.title,
                    'file_path': chunk.file_path,
                    'relevance': round(chunk.relevance, 4),
                    'chunk_excerpt': chunk.chunk_excerpt,
                }
                for chunk in chunks
            ],
            'graph_context': graph_context,
            'behavior_insights': {
                'viewed_categories': profile.get('viewed_categories', []),
                'price_sensitivity': profile.get('price_sensitivity', 'medium'),
                'brand_preference': profile.get('brand_preference', []),
                'session_duration': profile.get('session_duration', 0),
            },
            'suggested_actions': _suggest_actions(profile),
            'processing_time_ms': duration_ms,
            'fallback_mode': gemini_answer is None,
        }
