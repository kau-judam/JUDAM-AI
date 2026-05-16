"""
전통주 신규 등록 모니터링 크롤러
koreansool.co.kr 에서 새로운 전통주를 감지하면 auto_pipeline 을 트리거합니다.
"""

import logging
import os
import hashlib
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# 감지된 항목 캐시 파일 (중복 크롤링 방지)
_CACHE_FILE = Path(__file__).parent.parent.parent / "data" / "crawler_seen.json"

TARGET_URL = "https://www.koreansool.co.kr/goods/goods_list.php?catCd=001"


def _load_seen_ids() -> set:
    """이미 처리된 항목 ID 로드"""
    try:
        if _CACHE_FILE.exists():
            with open(_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get("seen_ids", []))
    except Exception as e:
        logger.warning(f"캐시 로드 실패: {e}")
    return set()


def _save_seen_ids(seen_ids: set):
    """처리된 항목 ID 저장"""
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"seen_ids": list(seen_ids), "updated_at": datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"캐시 저장 실패: {e}")


def _make_id(name: str) -> str:
    """이름 기반 고유 ID 생성"""
    return hashlib.md5(name.encode("utf-8")).hexdigest()[:12]


def crawl_koreansool() -> List[Dict]:
    """
    koreansool.co.kr 에서 전통주 목록 크롤링

    Returns:
        새롭게 발견된 전통주 리스트 (각 항목은 name, abv, brewery, region, description 포함)
    """
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        logger.error("requests 또는 beautifulsoup4 가 설치되지 않았습니다. pip install requests beautifulsoup4")
        return []

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        resp = requests.get(TARGET_URL, headers=headers, timeout=10)
        resp.raise_for_status()
        resp.encoding = "utf-8"
    except Exception as e:
        logger.error(f"koreansool.co.kr 요청 실패: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    drinks = []

    # 상품 카드 파싱 (실제 페이지 구조에 따라 조정)
    items = soup.select(".goods_list_item") or soup.select(".item_info_cont") or soup.select("li.item")

    if not items:
        # 더 넓은 범위로 시도
        items = soup.find_all("div", class_=lambda c: c and ("item" in c or "goods" in c or "product" in c))

    for item in items[:50]:  # 최대 50개
        try:
            # 이름 추출
            name_tag = (
                item.select_one(".goods_name") or
                item.select_one(".item_name") or
                item.select_one("strong") or
                item.select_one("h3") or
                item.select_one("h4")
            )
            if not name_tag:
                continue
            name = name_tag.get_text(strip=True)
            if not name or len(name) < 2:
                continue

            # 가격/도수/설명 추출 (있으면)
            desc_tag = item.select_one(".item_desc") or item.select_one("p")
            description = desc_tag.get_text(strip=True) if desc_tag else ""

            drinks.append({
                "name": name,
                "description": description,
                "abv": 0.0,
                "brewery": "",
                "region": "",
                "ingredients": "",
                "features": description[:200] if description else name,
            })
        except Exception as e:
            logger.warning(f"항목 파싱 실패: {e}")
            continue

    logger.info(f"koreansool.co.kr 크롤링 완료: {len(drinks)}개 항목")
    return drinks


def check_new_entries(auto_pipeline=None) -> Dict:
    """
    새로운 전통주 항목 감지 후 auto_pipeline 트리거

    Args:
        auto_pipeline: AutoPipeline 인스턴스 (None이면 벡터 생성 건너뜀)

    Returns:
        결과 딕셔너리 {status, new_count, new_items, total_seen}
    """
    seen_ids = _load_seen_ids()
    all_drinks = crawl_koreansool()

    new_items = []
    for drink in all_drinks:
        item_id = _make_id(drink["name"])
        if item_id not in seen_ids:
            drink["crawler_id"] = item_id
            new_items.append(drink)
            seen_ids.add(item_id)

    processed = []
    if new_items and auto_pipeline is not None:
        for drink in new_items:
            try:
                vector = auto_pipeline.create_taste_vector(drink, use_gemini=True)
                drink["taste_vector"] = vector
                processed.append(drink)
                logger.info(f"새 항목 처리 완료: {drink['name']}")
            except Exception as e:
                logger.error(f"auto_pipeline 처리 실패 ({drink['name']}): {e}")
                drink["taste_vector"] = {}
                processed.append(drink)
    else:
        processed = new_items

    if new_items:
        _save_seen_ids(seen_ids)

    return {
        "status": "ok",
        "checked_at": datetime.now().isoformat(),
        "new_count": len(new_items),
        "new_items": [{"name": d["name"], "crawler_id": d.get("crawler_id", "")} for d in processed],
        "total_seen": len(seen_ids),
    }
