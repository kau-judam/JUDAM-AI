"""
비정상 입력 견고성 점검 (실제 호출).
주요 엔드포인트에 빈값/범위밖/타입오류/누락 입력을 실제로 넣어 HTTP 코드 측정.
판정: 4xx(422/400)=의도된 거부(정상), 500=서버오류(문제).
Gemini 호출은 최소화(direct_input/검증실패 경로 우선). 결과 → _audit2_results.json
사용법: python scripts/run_robustness_audit.py [base_url]
"""
import json
import sys
import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011"

# 유효한 8축 맛벡터(직접입력용 — Gemini 우회)
VALID_TV = {"sweetness": 6.0, "body": 5.0, "carbonation": 5.0, "flavor": 5.0,
            "alcohol": 4.0, "acidity": 5.0, "aroma_intensity": 6.0, "finish": 6.0}
BAD_TV = dict(VALID_TV, sweetness=99.0)  # 범위밖

# 유효한 설문(최소) — 누락/범위 테스트용 베이스
VALID_SURVEY = {f"q{i}": 4 for i in range(1, 23)}
VALID_SURVEY.update({"q1": 3, "q2": 3, "q3": 3, "q23": 3, "q24": [1, 4], "q25": [1, 2]})

# (라벨, METHOD, PATH, JSON, 비고) — expected는 사람이 판정
CASES = [
    # ── survey/convert (Gemini 없음) ──
    ("survey: 빈 body {}", "POST", "/api/survey/convert", {}, "누락"),
    ("survey: q24·q25 누락", "POST", "/api/survey/convert",
     {k: v for k, v in VALID_SURVEY.items() if k not in ("q24", "q25")}, "누락"),
    ("survey: q4=99 (범위밖 1~7)", "POST", "/api/survey/convert",
     dict(VALID_SURVEY, q4=99), "범위밖"),
    ("survey: q4='abc' (타입오류)", "POST", "/api/survey/convert",
     dict(VALID_SURVEY, q4="abc"), "타입"),
    ("survey: q23=9 (범위밖 1~5)", "POST", "/api/survey/convert",
     dict(VALID_SURVEY, q23=9), "범위밖"),
    ("survey: q24=5 (리스트 아닌 int)", "POST", "/api/survey/convert",
     dict(VALID_SURVEY, q24=5), "타입"),
    ("survey: q24=[99] (도메인밖 정수)", "POST", "/api/survey/convert",
     dict(VALID_SURVEY, q24=[99], q25=[99]), "범위밖(가드없음)"),
    ("survey: 정상", "POST", "/api/survey/convert", VALID_SURVEY, "정상"),

    # ── recommend (Gemini 없음) ──
    ("recommend: 빈 body {}", "POST", "/api/recommend", {}, "누락"),
    ("recommend: top_k=0", "POST", "/api/recommend",
     {"user_vector": VALID_TV, "top_k": 0}, "범위밖"),
    ("recommend: top_k=999", "POST", "/api/recommend",
     {"user_vector": VALID_TV, "top_k": 999}, "범위밖"),
    ("recommend: user_vector sweetness=99", "POST", "/api/recommend",
     {"user_vector": BAD_TV}, "범위밖"),
    ("recommend: user_id='ghost123'(미존재)", "POST", "/api/recommend",
     {"user_id": "ghost123"}, "미존재"),
    ("recommend: pool='garbage'", "POST", "/api/recommend",
     {"user_vector": VALID_TV, "pool": "garbage"}, "잘못된 enum"),
    ("recommend: user_vector finish 누락", "POST", "/api/recommend",
     {"user_vector": {k: v for k, v in VALID_TV.items() if k != "finish"}}, "누락"),
    ("recommend: 정상", "POST", "/api/recommend",
     {"user_vector": VALID_TV, "top_k": 3}, "정상"),

    # ── bti/feedback (Gemini 없음, DB off→JSON) ──
    ("bti/feedback: bti_code='ABC'(len3)", "POST", "/api/bti/feedback",
     {"user_id": "u1", "bti_code": "ABC", "is_correct": True}, "범위밖(len)"),
    ("bti/feedback: is_correct 누락", "POST", "/api/bti/feedback",
     {"user_id": "u1", "bti_code": "SHFUH"}, "누락"),
    ("bti/feedback: bti_code='' (빈값)", "POST", "/api/bti/feedback",
     {"user_id": "u1", "bti_code": "", "is_correct": True}, "빈값"),
    ("bti/feedback: 정상(미존재 user)", "POST", "/api/bti/feedback",
     {"user_id": "ghost_audit", "bti_code": "SHFUH", "is_correct": False}, "정상"),

    # ── law/filter (Gemini) — 검증 실패는 무료, 정상 1건만 라이브 ──
    ("law/filter: title 빈값''", "POST", "/api/law/filter",
     {"content_type": "funding", "title": "", "description": "설명"}, "빈값"),
    ("law/filter: description 누락", "POST", "/api/law/filter",
     {"content_type": "funding", "title": "제목"}, "누락"),
    ("law/filter: content_type 누락", "POST", "/api/law/filter",
     {"title": "제목", "description": "설명"}, "누락"),
    ("law/filter: 정상(라이브)", "POST", "/api/law/filter",
     {"content_type": "funding", "title": "오미자 막걸리", "description": "건강에 좋은 전통주",
      "ingredients": ["오미자", "쌀"]}, "정상(Gemini)"),

    # ── funding/register (taste_input=직접입력 → Gemini 우회) ──
    ("funding: name 누락", "POST", "/api/funding/register",
     {"funding_id": "fa1", "taste_input": VALID_TV}, "누락"),
    ("funding: abv=999 (범위밖)", "POST", "/api/funding/register",
     {"funding_id": "fa2", "name": "테스트주", "abv": 999, "taste_input": VALID_TV}, "범위밖"),
    ("funding: abv=-5 (범위밖)", "POST", "/api/funding/register",
     {"funding_id": "fa3", "name": "테스트주", "abv": -5, "taste_input": VALID_TV}, "범위밖"),
    ("funding: taste_input sweetness=99", "POST", "/api/funding/register",
     {"funding_id": "fa4", "name": "테스트주", "taste_input": BAD_TV}, "범위밖"),
    ("funding: 정상(direct_input)", "POST", "/api/funding/register",
     {"funding_id": "fa_ok", "name": "감사테스트주", "abv": 8, "taste_input": VALID_TV}, "정상"),
    ("funding: 중복 funding_id", "POST", "/api/funding/register",
     {"funding_id": "fa_ok", "name": "감사테스트주2", "taste_input": VALID_TV}, "중복"),

    # ── recipe/register (taste_input=직접입력 → Gemini 우회) ──
    ("recipe: main_ingredient 누락", "POST", "/api/recipe/register",
     {"recipe_id": "ra1", "title": "T", "user_id": "u", "abv_range": "8-10",
      "taste_input": VALID_TV}, "누락"),
    ("recipe: user_id 누락", "POST", "/api/recipe/register",
     {"recipe_id": "ra2", "title": "T", "main_ingredient": "쌀", "abv_range": "8-10",
      "taste_input": VALID_TV}, "누락"),
    ("recipe: 정상(direct_input)", "POST", "/api/recipe/register",
     {"recipe_id": "ra_ok", "title": "감사레시피", "user_id": "u", "main_ingredient": "쌀",
      "abv_range": "8-10", "flavor_tags": ["달콤"], "taste_input": VALID_TV}, "정상"),

    # ── image/generate (Gemini/SD — 검증 실패 케이스만, 라이브 생성 제외) ──
    ("image: name 누락", "POST", "/api/image/generate",
     {"description": "설명"}, "누락"),
    ("image: description 누락", "POST", "/api/image/generate",
     {"name": "이름"}, "누락"),
    ("image: taste_vector 값 타입오류", "POST", "/api/image/generate",
     {"name": "이름", "description": "설명", "taste_vector": {"sweetness": "abc"}}, "타입"),
]


def short(resp):
    try:
        j = resp.json()
        s = json.dumps(j, ensure_ascii=False)
    except Exception:
        s = resp.text
    return s[:160]


def main():
    out = []
    for label, method, path, payload, note in CASES:
        url = BASE + path
        try:
            r = requests.request(method, url, json=payload, timeout=120)
            code = r.status_code
            body = short(r)
            err500 = (code == 500)
        except Exception as e:
            code = "EXC"
            body = f"{type(e).__name__}: {e}"
            err500 = True
        verdict = "❌500" if err500 else ("✅거부" if str(code).startswith("4") else "✅정상")
        out.append({"label": label, "note": note, "code": code,
                    "verdict": verdict, "body": body})
        tag = "ERR500" if err500 else ("reject4xx" if str(code).startswith("4") else "ok")
        print(f"[{code}] {tag}  {label.encode('ascii','replace').decode()}")

    with open("_audit2_results.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    n500 = sum(1 for o in out if o["verdict"] == "❌500")
    print(f"\n총 {len(out)}건, 500/EXC {n500}건. 저장: _audit2_results.json")


if __name__ == "__main__":
    main()
