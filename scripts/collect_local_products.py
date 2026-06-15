"""
농사로(api.nongsaro.go.kr) 지역특산물 OpenAPI 수집기

사용법:
  # 1) 단일 작물 원시 응답 확인 (Step 2: 응답 형식 대조용)
  python scripts/collect_local_products.py --probe --crop 사과

  # 2) 전체 수집 → data/local_products.json, data/ingredient_region_map.json 생성
  python scripts/collect_local_products.py

키:
  - .env 의 NONGSARO_API_KEY 를 자동으로 읽음 (없으면 --api-key 로 전달).
  - 키 값은 절대 출력/로그에 남기지 않는다 (마스킹).

설계 메모:
  - 농사로 OpenAPI 는 서비스마다 http://api.nongsaro.go.kr/service/{svc}/{op} 형태이고
    인증 파라미터는 apiKey 이다. 서비스/오퍼레이션/파라미터 이름이 환경마다 다를 수 있어
    상수+CLI 로 바꿀 수 있게 했고, --probe 로 *원시 응답*을 먼저 찍어 실제 필드에 파서를 맞춘다.
  - 응답 파서는 <item> 하위 태그를 통째로 dict 화하는 '스키마 적응형'이라
    필드명을 추측해 박지 않는다 (실제 응답에 있는 키를 그대로 가져옴).
"""

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

# ── 농사로 지역특산물 엔드포인트 (매뉴얼 확정) ──────────────────────────────
# 명세서: http://api.nongsaro.go.kr/service/localSpcprd/localSpcprdLst
BASE_URL = "http://api.nongsaro.go.kr/service"
SERVICE = "localSpcprd"        # 지역특산물 서비스
LIST_OP = "localSpcprdLst"     # 목록 오퍼레이션
KEY_PARAM = "apiKey"           # 인증 파라미터명 (필수)

# 수집 대상 대표 작물(검색어). 전통주 재료 위주.
TARGET_CROPS = [
    "쌀", "사과", "배", "딸기", "포도", "복숭아", "감귤", "고구마",
    "잣", "인삼", "녹차", "대나무", "감", "매실", "오미자", "유자",
]

# 응답 필드 (매뉴얼 확정): 특산물명=cntntsSj, 지역명=areaNm
NAME_FIELD = "cntntsSj"
AREA_FIELD = "areaNm"

# resultCode 해석 (매뉴얼)
RESULT_CODE_MSG = {
    "00": "정상 (조회결과 0건도 정상)",
    "11": "인증키 누락/오류 - .env NONGSARO_API_KEY 확인",
    "13": "서비스/오퍼레이션 오류 - SERVICE/LIST_OP 경로 확인",
    "15": "신청 도메인 외 호출 - 신청 시 등록한 서비스 도메인에서만 호출 가능. "
          "로컬에서 실행하거나 농사로에 도메인 확인 필요",
    "91": "농사로 시스템 오류 - 잠시 후 재시도",
}

OUT_PRODUCTS = Path("data/local_products.json")
OUT_REGION_MAP = Path("data/ingredient_region_map.json")


def mask_key(key: str) -> str:
    if not key:
        return "(없음)"
    return f"***설정됨 (len={len(key)})"   # 키 문자는 절대 출력하지 않음


def resolve_key(cli_key: str) -> str:
    key = cli_key or os.getenv("NONGSARO_API_KEY")
    if not key:
        print("[에러] API 키 없음. .env 에 NONGSARO_API_KEY=... 추가하거나 --api-key 전달.",
              file=sys.stderr)
        sys.exit(2)
    return key


def call_api(key, service, op, params):
    url = f"{BASE_URL}/{service}/{op}"
    q = {KEY_PARAM: key, **params}
    safe_q = {**q, KEY_PARAM: "***"}
    print(f"[요청] {url}  params={safe_q}")
    resp = requests.get(url, params=q, timeout=15)
    return resp


def parse_items(xml_text):
    """XML → (header dict, [item dict...]). <item> 하위 태그를 그대로 dict 화."""
    root = ET.fromstring(xml_text)
    header = {}
    for h in root.iter():
        if h.tag in ("resultCode", "resultMsg", "errMsg", "returnReasonCode"):
            header[h.tag] = (h.text or "").strip()
    items = []
    for item in root.iter("item"):
        d = {}
        for child in item:
            d[child.tag] = (child.text or "").strip() if child.text else ""
        if d:
            items.append(d)
    return header, items


def interpret_result_code(header):
    """resultCode 해석. (code, ok, is_domain_block) 반환. ok=True면 진행 가능(00)."""
    code = header.get("resultCode", "").strip()
    msg = RESULT_CODE_MSG.get(code, f"알 수 없는 코드 (서버 메시지: {header.get('resultMsg', '')})")
    print(f"[resultCode] {code} - {msg}")
    return code, (code == "00"), (code == "15")


def probe(key, crop):
    """단일 작물 1회 호출 → 원시 응답 + 파싱 결과 출력 (Step 3)."""
    try:
        resp = call_api(key, SERVICE, LIST_OP,
                        {"sText": crop, "numOfRows": 5, "pageNo": 1})
    except requests.exceptions.ConnectionError as e:
        print("\n[네트워크 차단 의심] api.nongsaro.go.kr 에 연결 실패.")
        print("→ EC2 보안그룹/아웃바운드에서 api.nongsaro.go.kr(80) 허용이 필요한지 확인하세요.")
        print(f"  원인: {e}")
        sys.exit(3)

    print(f"\n[HTTP] {resp.status_code}")
    print("===== 원시 응답 (앞 1500자) =====")
    print(resp.text[:1500])
    print("================================\n")

    try:
        header, items = parse_items(resp.text)
    except ET.ParseError as e:
        print(f"[파싱 실패] XML 아님(JSON일 수 있음): {e}")
        return

    code, ok, _ = interpret_result_code(header)
    print(f"[item 수] {len(items)}")
    if items:
        print(f"[첫 item 의 필드 키] {list(items[0].keys())}")
        print(f"[첫 item] {items[0]}")
        nm = items[0].get(NAME_FIELD)
        ar = items[0].get(AREA_FIELD)
        print(f"[추출] {NAME_FIELD}(특산물명)={nm!r}, {AREA_FIELD}(지역명)={ar!r}")
    elif ok:
        print("조회결과 0건 (정상). 다른 검색어로 시도해 보세요.")


def collect_all(key):
    """대표 작물 전체 수집 → json 2종 생성."""
    products = []
    region_map = {}
    for crop in TARGET_CROPS:
        try:
            resp = call_api(key, SERVICE, LIST_OP,
                            {"sText": crop, "numOfRows": 50, "pageNo": 1})
        except requests.exceptions.ConnectionError as e:
            print(f"[네트워크 차단] {crop}: {e}")
            print("→ EC2 아웃바운드에서 api.nongsaro.go.kr(80) 허용 확인 필요.")
            sys.exit(3)

        if resp.status_code != 200:
            print(f"[{crop}] HTTP {resp.status_code} → 건너뜀")
            continue
        try:
            header, items = parse_items(resp.text)
        except ET.ParseError:
            print(f"[{crop}] XML 파싱 실패 → 건너뜀")
            continue

        code, ok, is_domain_block = interpret_result_code(header)
        if is_domain_block:
            # 코드 15: 도메인 차단 → 우회하지 말고 중단/보고
            print("\n[중단] resultCode 15 (신청 도메인 외 호출). 수집을 중단합니다.")
            print("→ 농사로 신청 시 등록한 서비스 도메인에서 실행하거나, 도메인 등록을 확인하세요.")
            sys.exit(4)
        if not ok:
            print(f"[{crop}] 비정상 코드 → 건너뜀")
            continue

        for it in items:
            name = it.get(NAME_FIELD)
            area = it.get(AREA_FIELD)
            products.append({"query": crop, "name": name, "area": area, "raw": it})
            if name and area:
                region_map.setdefault(name, [])
                if area not in region_map[name]:
                    region_map[name].append(area)
        print(f"[{crop}] item {len(items)}개 수집")

    OUT_PRODUCTS.parent.mkdir(parents=True, exist_ok=True)
    OUT_PRODUCTS.write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_REGION_MAP.write_text(json.dumps(region_map, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n=== 수집 완료 ===")
    print(f"local_products.json: {len(products)}개 레코드")
    print(f"ingredient_region_map.json: {len(region_map)}개 매핑")
    sample = dict(list(region_map.items())[:5])
    print(f"매핑 샘플: {json.dumps(sample, ensure_ascii=False)}")


def main():
    global SERVICE, LIST_OP, KEY_PARAM
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-key", default=None, help="농사로 apiKey (없으면 .env NONGSARO_API_KEY)")
    ap.add_argument("--probe", action="store_true", help="단일 작물 원시 응답만 출력")
    ap.add_argument("--crop", default="사과", help="probe 시 검색할 작물")
    ap.add_argument("--service", default=SERVICE)
    ap.add_argument("--list-op", default=LIST_OP)
    ap.add_argument("--key-param", default=KEY_PARAM)
    args = ap.parse_args()

    SERVICE, LIST_OP, KEY_PARAM = args.service, args.list_op, args.key_param
    key = resolve_key(args.api_key)
    print(f"[키] {mask_key(key)}  service={SERVICE}/{LIST_OP}  keyParam={KEY_PARAM}")

    if args.probe:
        probe(key, args.crop)
    else:
        collect_all(key)


if __name__ == "__main__":
    main()
