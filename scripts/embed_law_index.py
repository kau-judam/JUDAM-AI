"""
data/law_articles.json → MiniLM 임베딩 → PersistentClient(rag_db/law) 'law_articles' 적재
사용법:
  python scripts/embed_law_index.py            # count>0 이면 스킵
  python scripts/embed_law_index.py --rebuild  # 기존 인덱스 지우고 재적재

선행: scripts/build_law_index.py (조문 수집)
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv  # noqa: E402
load_dotenv()

from app.law_rag import LawRAG  # noqa: E402

SRC = Path("data/law_articles.json")


def main():
    rebuild = "--rebuild" in sys.argv
    if not SRC.exists():
        print(f"[중단] {SRC} 없음. 먼저: python scripts/build_law_index.py")
        sys.exit(2)

    records = json.loads(SRC.read_text(encoding="utf-8"))
    print(f"레코드 {len(records)}개 로드 (rebuild={rebuild})")

    rag = LawRAG()
    n = rag.build_article_index(records, rebuild=rebuild)
    print(f"적재 완료: {n}개 청크 → rag_db/law/law_articles")

    # 간단 검증
    for q in ["숙취 해소", "청소년 주류 판매", "원금 보장"]:
        hits = rag.search(q, top_k=2)
        print(f"  [검색] '{q}' → {[h['law_name']+' '+h['content'][:24] for h in hits]}")


if __name__ == "__main__":
    main()
