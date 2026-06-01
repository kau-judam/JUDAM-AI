"""
법령 조문 수집 → data/law_articles.json (재현용)
사용법: python scripts/build_law_index.py

- app/law_client.py 의 LawClient.LAWS(9개 법령)를 대상으로
  국가법령정보센터 OPEN API(lawSearch.do → lawService.do) 호출.
- 조문 단위(조문여부=='조문')만 추출, 긴 조문은 ~CHUNK_CHARS 단위로 분할.
- 헤더: User-Agent/Referer (LAW_USER_AGENT/LAW_REFERER 환경변수 override).
- OC = .env 의 LAW_API_KEY. 키 값은 출력하지 않는다.
- 실패한 법령은 건너뛰고 기록. 호출 사이 지연(rate limit 배려).

응답 구조(검증됨):
  search : LawSearch.law[]  →  법령일련번호(MST), 법령ID, 법령명한글
  detail : lawService.do?MST=...  →  법령.조문.조문단위[] (조문번호/조문제목/조문내용/조문여부/항/호)
"""

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.law_client import LawClient  # noqa: E402  (LAWS 클래스 속성만 사용)

OC = os.getenv("LAW_API_KEY")
HEADERS = {
    "User-Agent": os.getenv(
        "LAW_USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ),
    "Referer": os.getenv("LAW_REFERER", "https://www.law.go.kr/"),
}
SEARCH_URL = "https://www.law.go.kr/DRF/lawSearch.do"
DETAIL_URL = "https://www.law.go.kr/DRF/lawService.do"
OUT = Path("data/law_articles.json")
CHUNK_CHARS = 800        # 조문 텍스트 분할 기준 (~512 토큰 근사)
DELAY_SEC = 0.7          # 호출 사이 지연


def _get_json(url, params):
    full = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(full, headers=HEADERS)
    raw = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")
    return json.loads(raw)


def _as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def _collect_text(o, acc):
    """조문단위 안의 모든 '*내용'(조문내용/항내용/호내용/목내용...) 문자열 수집."""
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, str) and k.endswith("내용"):
                acc.append(v.strip())
            else:
                _collect_text(v, acc)
    elif isinstance(o, list):
        for x in o:
            _collect_text(x, acc)


def _chunk(text, size=CHUNK_CHARS):
    text = text.strip()
    if len(text) <= size:
        return [text] if text else []
    chunks, buf = [], ""
    for line in text.split("\n"):
        if len(buf) + len(line) + 1 > size and buf:
            chunks.append(buf.strip())
            buf = ""
        buf += line + "\n"
    if buf.strip():
        chunks.append(buf.strip())
    return chunks


def find_mst(law_name):
    """법령명으로 검색 → 정확히 일치하는 현행 법령의 MST 반환."""
    data = _get_json(SEARCH_URL, {"OC": OC, "target": "law", "query": law_name,
                                  "type": "JSON", "display": 20})
    laws = _as_list(data.get("LawSearch", {}).get("law"))
    if not laws:
        return None, None
    # 법령명 정확 일치 우선, 없으면 첫 결과
    exact = [l for l in laws if l.get("법령명한글", "").replace(" ", "") == law_name.replace(" ", "")]
    chosen = exact[0] if exact else laws[0]
    return chosen.get("법령일련번호"), chosen.get("법령ID")


def fetch_articles(mst, law_name, law_id):
    data = _get_json(DETAIL_URL, {"OC": OC, "target": "law", "MST": mst, "type": "JSON"})
    units = _as_list(data.get("법령", {}).get("조문", {}).get("조문단위"))
    records = []
    for u in units:
        if u.get("조문여부") != "조문":      # '전문'(장/절 제목) 제외
            continue
        no = str(u.get("조문번호", "")).strip()
        akey = str(u.get("조문키", "")).strip().replace(" ", "")  # 조문 고유키 (중복 방지)
        title = (u.get("조문제목") or "").strip()
        acc = []
        _collect_text(u, acc)
        # 중복 제거(순서 유지)
        seen, parts = set(), []
        for t in acc:
            if t and t not in seen:
                seen.add(t)
                parts.append(t)
        full = "\n".join(parts).strip()
        if not full:
            continue
        # 삭제된 조문(빈 플레이스홀더) 제외 — 검색 노이즈 방지
        raw_content = (u.get("조문내용") or "").strip()
        if re.match(r"^제?\s*\d+조(의\d+)?\s*삭제", raw_content) or raw_content.replace(" ", "").startswith("삭제"):
            continue
        for ci, chunk in enumerate(_chunk(full)):
            records.append({
                "id": f"{law_name}_제{no}조_{akey or 'x'}" + (f"_{ci}" if ci else ""),
                "law_name": law_name,
                "law_id": law_id or law_name,
                "mst": mst,
                "article_no": no,
                "article_title": title,
                "text": f"{law_name} 제{no}조({title}): {chunk}" if title else f"{law_name} 제{no}조: {chunk}",
            })
    return records


def main():
    if not OC:
        print("[중단] LAW_API_KEY 없음. .env 확인.")
        sys.exit(2)

    all_records = []
    ok_laws, failed = 0, []
    laws = LawClient.LAWS  # 클래스 속성 (인스턴스화 안 함)
    print(f"대상 법령 {len(laws)}개")

    for name in laws:
        try:
            mst, law_id = find_mst(name)
            if not mst:
                print(f"  [skip] {name}: 검색 결과 없음")
                failed.append((name, "no_search_result"))
                continue
            time.sleep(DELAY_SEC)
            recs = fetch_articles(mst, name, law_id)
            if not recs:
                print(f"  [skip] {name}: 조문 없음 (MST={mst})")
                failed.append((name, "no_articles"))
                continue
            all_records.extend(recs)
            ok_laws += 1
            print(f"  [ok] {name}: 조문/청크 {len(recs)}개 (MST={mst})")
        except Exception as e:
            print(f"  [fail] {name}: {type(e).__name__} {str(e)[:120]}")
            failed.append((name, str(e)[:80]))
        time.sleep(DELAY_SEC)

    # ID 유일성 최종 보장 (혹시 모를 충돌 시 접미사)
    seen = {}
    for r in all_records:
        rid = r["id"]
        if rid in seen:
            seen[rid] += 1
            r["id"] = f"{rid}__{seen[rid]}"
        else:
            seen[rid] = 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(all_records, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n=== 수집 완료 ===")
    print(f"성공 법령: {ok_laws}/{len(laws)}")
    print(f"총 조문/청크: {len(all_records)}개")
    if failed:
        print(f"실패/건너뜀: {failed}")
    print(f"저장: {OUT}")


if __name__ == "__main__":
    main()
