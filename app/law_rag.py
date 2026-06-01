"""
법령 ChromaDB RAG 모듈
- 1순위: PersistentClient(rag_db/law)의 'law_articles' 조문 단위 인덱스 (MiniLM 임베딩)
- fallback: EphemeralClient 'law_documents' 9개 설명 단위 (인덱스 없거나 Persistent 불가 시)
기존 동작(9개 설명 단위)을 절대 깨지 않도록 fallback 유지.
"""

import json
import logging

logger = logging.getLogger(__name__)

PERSIST_PATH = "rag_db/law"
ARTICLE_COLLECTION = "law_articles"
DESC_COLLECTION = "law_documents"


class LawRAG:
    """법령 ChromaDB 저장 + RAG 검색"""

    def __init__(self):
        self._available = False
        self._initialized = False        # True면 검색 가능 (조문 인덱스 or 설명 적재 완료)
        self._mode = "none"              # persistent_articles | ephemeral
        self.collection = None
        self._persist_client = None
        self._chromadb = None

        try:
            import chromadb
            self._chromadb = chromadb

            # 1순위: Persistent 조문 인덱스
            try:
                self._persist_client = chromadb.PersistentClient(path=PERSIST_PATH)
                acol = self._persist_client.get_or_create_collection(
                    ARTICLE_COLLECTION, metadata={"hnsw:space": "cosine"})
                if acol.count() > 0:
                    self.collection = acol
                    self._available = True
                    self._initialized = True
                    self._mode = "persistent_articles"
                    logger.info(f"법령 조문 인덱스 사용: {acol.count()}개 청크 (PersistentClient/{ARTICLE_COLLECTION})")
                    return
            except Exception as pe:
                logger.warning(f"PersistentClient 사용 불가 → Ephemeral fallback: {pe}")

            # fallback: Ephemeral 9개 설명 단위 (기존 동작)
            self.client = chromadb.EphemeralClient()
            self.collection = self.client.get_or_create_collection(
                DESC_COLLECTION, metadata={"hnsw:space": "cosine"})
            self._available = True
            self._mode = "ephemeral"
        except Exception as e:
            logger.warning(f"ChromaDB 초기화 실패 (RAG 비활성화): {e}")

    def initialize(self, law_data: list):
        """법령 설명 적재 (fallback 경로). 조문 인덱스가 이미 있으면 건너뜀."""
        if not self._available or self._initialized:
            return  # 조문 인덱스 사용 중이면 9개 설명 적재 불필요

        documents, metadatas, ids = [], [], []
        for i, law in enumerate(law_data):
            if hasattr(law, 'name'):
                name, law_id = law.name, law.law_id
                keywords, description = law.keywords, law.description
            else:
                name = law.get('name', '')
                law_id = law.get('law_id', '')
                keywords = law.get('keywords', [])
                description = law.get('description', '')

            content = f"{name}: {description}. 관련 키워드: {', '.join(keywords)}"
            documents.append(content)
            metadatas.append({
                'law_name': name,
                'law_id': law_id,
                'keywords': json.dumps(keywords, ensure_ascii=False)
            })
            ids.append(f"law_{i}")

        if not documents:
            return

        try:
            self.collection.add(documents=documents, metadatas=metadatas, ids=ids)
            self._initialized = True
            logger.info(f"법령 RAG 초기화 완료(설명 단위): {len(documents)}개 적재 [{self._mode}]")
        except Exception as e:
            logger.error(f"ChromaDB 적재 실패: {e}")

    def build_article_index(self, records: list, rebuild: bool = False) -> int:
        """
        data/law_articles.json 레코드를 MiniLM 임베딩하여 Persistent 'law_articles'에 적재.
        반환: 적재된 청크 수. count>0이고 rebuild=False면 스킵.
        """
        if self._chromadb is None:
            logger.error("ChromaDB 미사용 — 조문 인덱스 빌드 불가")
            return 0
        if self._persist_client is None:
            self._persist_client = self._chromadb.PersistentClient(path=PERSIST_PATH)

        col = self._persist_client.get_or_create_collection(
            ARTICLE_COLLECTION, metadata={"hnsw:space": "cosine"})

        if col.count() > 0 and not rebuild:
            logger.info(f"조문 인덱스 이미 존재({col.count()}개) → 스킵 (rebuild=True로 재적재)")
            self.collection = col
            self._available = True
            self._initialized = True
            self._mode = "persistent_articles"
            return col.count()

        # rebuild: 기존 컬렉션 비우고 재생성
        if col.count() > 0 and rebuild:
            self._persist_client.delete_collection(ARTICLE_COLLECTION)
            col = self._persist_client.get_or_create_collection(
                ARTICLE_COLLECTION, metadata={"hnsw:space": "cosine"})

        from app.embedder import get_embedder
        embedder = get_embedder()
        if not embedder.enabled:
            logger.error("임베더 비활성화 — sentence-transformers 설치 확인")
            return 0

        ids = [r["id"] for r in records]
        docs = [r["text"] for r in records]
        metas = [{
            "law_name": r.get("law_name", ""),
            "law_id": str(r.get("law_id", "")),
            "article_no": str(r.get("article_no", "")),
            "article_title": r.get("article_title", ""),
        } for r in records]

        # 배치 임베딩 + 적재
        BATCH = 64
        added = 0
        for i in range(0, len(records), BATCH):
            chunk_docs = docs[i:i + BATCH]
            embs = embedder.embed_batch(chunk_docs)
            col.add(ids=ids[i:i + BATCH], documents=chunk_docs,
                    embeddings=embs, metadatas=metas[i:i + BATCH])
            added += len(chunk_docs)
            logger.info(f"임베딩 적재 진행: {added}/{len(records)}")

        self.collection = col
        self._available = True
        self._initialized = True
        self._mode = "persistent_articles"
        logger.info(f"조문 인덱스 빌드 완료: {added}개 청크 [{ARTICLE_COLLECTION}]")
        return added

    def search(self, query: str, top_k: int = 3) -> list:
        """관련 법령/조문 검색. 반환: [{'law_name','law_id','content','keywords'}]"""
        if not self._available or not self._initialized:
            return []

        try:
            count = self.collection.count()
            if count == 0:
                return []

            from app.embedder import get_embedder
            embedder = get_embedder()
            if embedder.enabled:
                query_embedding = embedder.embed(query)
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(top_k, count)
                )
            else:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=min(top_k, count)
                )

            laws = []
            for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
                laws.append({
                    'law_name': meta.get('law_name', ''),
                    'law_id': meta.get('law_id', ''),
                    'content': doc,
                    'keywords': json.loads(meta['keywords']) if meta.get('keywords') else [],
                })
            return laws
        except Exception as e:
            logger.error(f"ChromaDB 검색 실패: {e}")
            return []
