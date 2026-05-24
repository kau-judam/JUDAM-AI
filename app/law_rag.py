"""
법령 ChromaDB RAG 모듈
법령 정보를 벡터 DB에 적재하고 관련 법령 검색
"""

import json
import logging

logger = logging.getLogger(__name__)


class LawRAG:
    """법령 조문 ChromaDB 저장 + RAG 검색"""

    def __init__(self):
        self._available = False
        self._initialized = False
        try:
            import chromadb
            self.client = chromadb.EphemeralClient()
            self.collection = self.client.get_or_create_collection(
                name="law_documents",
                metadata={"hnsw:space": "cosine"}
            )
            self._available = True
        except Exception as e:
            logger.warning(f"ChromaDB 초기화 실패 (RAG 비활성화): {e}")

    def initialize(self, law_data: list):
        """법령 정보 ChromaDB에 적재. law_data: LawInfo 객체 또는 dict 리스트"""
        if not self._available or self._initialized:
            return

        documents, metadatas, ids = [], [], []

        for i, law in enumerate(law_data):
            # LawInfo dataclass 또는 dict 모두 지원
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
            logger.info(f"법령 RAG 초기화 완료: {len(documents)}개 법령 적재")
        except Exception as e:
            logger.error(f"ChromaDB 적재 실패: {e}")

    def search(self, query: str, top_k: int = 3) -> list:
        """관련 법령 검색. 반환: [{'law_name', 'law_id', 'content', 'keywords'}]"""
        if not self._available or not self._initialized:
            return []

        try:
            count = self.collection.count()
            if count == 0:
                return []

            results = self.collection.query(
                query_texts=[query],
                n_results=min(top_k, count)
            )

            laws = []
            for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
                laws.append({
                    'law_name': meta['law_name'],
                    'law_id': meta['law_id'],
                    'content': doc,
                    'keywords': json.loads(meta.get('keywords', '[]'))
                })
            return laws
        except Exception as e:
            logger.error(f"ChromaDB 검색 실패: {e}")
            return []
