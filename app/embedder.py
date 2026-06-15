"""
로컬 임베더 싱글톤
paraphrase-multilingual-MiniLM-L12-v2 (다국어 MiniLM, 384차원) 사용
sentence-transformers 미설치 시 자동 비활성화
LAW_EMBED_MODEL 환경변수로 모델 override 가능
"""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

_embedder_instance: Optional["LocalEmbedder"] = None


class LocalEmbedder:
    def __init__(self):
        self.model = None
        self.enabled = False
        self._try_load()

    def _try_load(self):
        import os
        model_name = os.getenv("LAW_EMBED_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            self.enabled = True
            logger.info(f"임베더 로드 완료 ({model_name}, dim={self.model.get_sentence_embedding_dimension()})")
        except Exception as e:
            logger.warning(f"임베더 비활성화 ({model_name}): {e}")

    def embed(self, text: str) -> List[float]:
        if not self.enabled:
            return []
        return self.model.encode(text).tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not self.enabled:
            return []
        return self.model.encode(texts).tolist()


def get_embedder() -> LocalEmbedder:
    global _embedder_instance
    if _embedder_instance is None:
        _embedder_instance = LocalEmbedder()
    return _embedder_instance
