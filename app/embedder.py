"""
ko-sbert 로컬 임베더 싱글톤
jhgan/ko-sroberta-multitask 모델 사용
sentence-transformers 미설치 시 자동 비활성화
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
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer("jhgan/ko-sroberta-multitask")
            self.enabled = True
            logger.info("ko-sbert 임베더 로드 완료 (jhgan/ko-sroberta-multitask)")
        except Exception as e:
            logger.warning(f"ko-sbert 임베더 비활성화: {e}")

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
