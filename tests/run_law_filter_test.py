# -*- coding: utf-8 -*-
"""
법률 필터 단계별 추적 테스트 러너

각 케이스를 실제 LawClient.filter_content 에 통과시키되,
'어느 단계에서 결정됐는지'를 함께 추적/기록한다.

  단계1 (QUICK): QUICK_VIOLATION_KEYWORDS — 공백 제거 후 substring → 즉시 차단
  단계2 (RAG)  : law_rag.search — 컨텍스트만 (판정 없음). 상위 1~2개 조문 기록
  단계3 (Gemini): VIOLATION_KEYWORDS 카테고리 키워드가 걸려야만 Gemini 호출
                  → 키워드 하나도 안 걸리면 Gemini 미호출 = 자동 통과(auto_pass)

결정단계 분류:
  1_quick      : 단계1 키워드에서 즉시 차단
  3_gemini     : 카테고리 키워드 걸림 → Gemini가 최종 판정 (block/pass 둘 다 가능)
  0_auto_pass  : 어떤 키워드도 안 걸림 → Gemini 미호출 → 통과

사용법 (Windows 콘솔 한글):
  set PYTHONUTF8=1 && set PYTHONIOENCODING=utf-8 && python tests/run_law_filter_test.py
출력: 콘솔 요약 + results_law_test.md
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.law_client import LawClient, ContentType, ViolationCategory  # noqa: E402
from tests.law_filter_cases import CASES  # noqa: E402


def quick_hit(client, title, description):
    """단계1 QUICK 키워드 검사 복제. 걸리면 (law, keyword) 반환."""
    text = (title + " " + description).replace(" ", "")
    for law, keywords in client.QUICK_VIOLATION_KEYWORDS.items():
        for kw in keywords:
            if kw.replace(" ", "") in text:
                return law, kw
    return None, None


def matched_categories(client, full_text, content_type):
    """단계3 진입 조건: 어떤 카테고리 키워드가 걸리는지 (실제 코드 로직 복제)."""
    cats = [
        ViolationCategory.MINOR_TARGET,
        ViolationCategory.ILLEGAL_INGREDIENTS,
        ViolationCategory.REGIONAL_REQUIREMENTS,
        ViolationCategory.FALSE_ADVERTISING,
    ]
    if content_type == ContentType.FUNDING:
        cats += [
            ViolationCategory.UNLICENSED_MANUFACTURING,
            ViolationCategory.UNREALISTIC_ABV,
            ViolationCategory.TRADEMARK_INFRINGEMENT,
            ViolationCategory.FUNDING_REGULATION,
        ]
    hits = []
    for cat in cats:
        kws = client.VIOLATION_KEYWORDS[cat]["keywords"]
        matched_kw = [k for k in kws if k in full_text]  # raw substring (공백 유지)
        if matched_kw:
            hits.append((cat.value, matched_kw))
    return hits


def rag_top(client, title, description, k=2):
    """단계2 RAG 검색 상위 k개 (law_name + 본문 앞부분)."""
    try:
        results = client.law_rag.search(f"{title} {description}", top_k=k)
    except Exception as e:
        return [f"(RAG 오류: {type(e).__name__})"]
    out = []
    for r in results:
        snippet = (r.get("content") or "").replace("\n", " ")[:60]
        out.append(f"{r.get('law_name','?')} · {snippet}")
    return out or ["(검색 결과 없음)"]


async def run_case(client, case):
    ct = ContentType.RECIPE if case["content_type"] == "recipe" else ContentType.FUNDING
    full_text = f"{case['title']} {case['description']} {case['ingredients']}"

    q_law, q_kw = quick_hit(client, case["title"], case["description"])
    cat_hits = matched_categories(client, full_text, ct)
    rag = rag_top(client, case["title"], case["description"])

    result = await client.filter_content(
        title=case["title"], description=case["description"],
        ingredients=case["ingredients"], content_type=ct,
    )

    actual = result.verdict  # block | pass | review (3등급)

    # 결정단계 판정
    is_fallback = any(
        (d.category in ("검토보류", "AI분석불가", "파싱오류")) or ("AI 검토 실패" in (d.reason or ""))
        for d in result.details
    )
    if q_law:
        stage, gemini_called = "1_quick", False
    elif is_fallback:
        stage, gemini_called = "fallback", False
    else:
        stage, gemini_called = "3_gemini", True

    exp = case["expected"]  # block | pass
    correct = (actual == exp)
    if correct:
        outcome = "correct"
    elif actual == "review":
        outcome = "review"             # 보류 — 안전(자동 차단/통과 아님)
    elif exp == "block" and actual == "pass":
        outcome = "fn"                 # 위험: 위반 놓침
    else:                              # exp == pass and actual == block
        outcome = "fp"                 # 정상 차단(사용성 해침)

    if result.details:
        reason = "; ".join(f"[{d.category}/{d.law}] {d.reason}" for d in result.details)
    else:
        reason = result.recommendation

    return {
        "id": case["id"], "category": case["category"],
        "title": case["title"], "expected": exp,
        "actual": actual, "correct": correct, "outcome": outcome, "stage": stage,
        "gemini_called": gemini_called,
        "quick": f"{q_law}:{q_kw}" if q_law else "-",
        "cat_hits": cat_hits,
        "rag": rag,
        "reason": reason,
    }


def fmt_cat_hits(cat_hits):
    if not cat_hits:
        return "-"
    return " | ".join(f"{c}({','.join(kws)})" for c, kws in cat_hits)


def build_report(rows):
    lines = []
    L = lines.append

    L("# 법률 필터 체계적 테스트 결과 — 3등급(block/pass/review) 구조 (results_law_test.md)\n")
    L(f"- 테스트셋: `tests/law_filter_cases.py` (총 {len(rows)}개)")
    L("- 러너: `tests/run_law_filter_test.py` (3등급 + 단계 추적)")
    L("- 구조: 1단계 QUICK 즉시차단 → 2단계 RAG → **3단계 전 콘텐츠 Gemini 1회**(0_auto_pass 경로 없음). 판정=block/pass/review.")
    L("- 카테고리: A=명백한 위반(기대 block), B=애매한 위반(기대 block), C=정상 함정(기대 pass), D=완전 정상(기대 pass)")
    L("- **review** = 자동 차단/통과 안 하고 관리자 검토 큐로. block-기대를 review로 보내면 '안전'(놓침 아님), pass-기대를 review로 보내면 '안전'(오차단 아님).\n")

    # 집계 버킷
    fn = [r for r in rows if r["outcome"] == "fn"]   # 기대 block, 실제 pass (위험)
    fp = [r for r in rows if r["outcome"] == "fp"]    # 기대 pass, 실제 block (사용성)
    rv = [r for r in rows if r["outcome"] == "review"]
    exact = [r for r in rows if r["correct"]]
    total = len(rows)

    # ── 케이스별 상세 ──
    L("## 1. 케이스별 추적\n")
    L("| ID | 분류 | 기대 | 실제 | 결과 | 결정단계 | Gemini | 단계1키워드 |")
    L("|----|------|------|------|------|----------|--------|-------------|")
    omap = {"correct": "✅정확", "review": "🟡검토", "fn": "❌놓침", "fp": "❌오차단"}
    for r in rows:
        gem = "O" if r["gemini_called"] else "-"
        L(f"| {r['id']} | {r['category']} | {r['expected']} | {r['actual']} | {omap[r['outcome']]} | "
          f"{r['stage']} | {gem} | {r['quick']} |")

    L("\n### 검색된 조문(2단계 RAG 상위 1~2개) / 사유\n")
    for r in rows:
        L(f"**{r['id']} [{r['category']}] {r['title']}** — 기대={r['expected']} / 실제={r['actual']} / {omap[r['outcome']]} / 단계={r['stage']}")
        for s in r["rag"]:
            L(f"  - RAG: {s}")
        L(f"  - 사유: {r['reason']}\n")

    # ── 혼동행렬 (3열) ──
    L("## 2. 혼동행렬 (3등급)\n")
    def cell(exp, act):
        return len([r for r in rows if r["expected"] == exp and r["actual"] == act])
    L("| 기대\\실제 | block | review | pass |")
    L("|---|---|---|---|")
    L(f"| **block(A·B)** | {cell('block','block')} (정확) | {cell('block','review')} (보류·안전) | **{cell('block','pass')} (위험 FN)** |")
    L(f"| **pass(C·D)**  | **{cell('pass','block')} (FP)** | {cell('pass','review')} (보류·안전) | {cell('pass','pass')} (정확) |")
    safe = total - len(fn) - len(fp)
    L(f"\n- **엄격 정확도(verdict 완전일치)**: {len(exact)/total:.1%} ({len(exact)}/{total})")
    L(f"- **위험 FN(위반을 자동통과)**: {len(fn)}개 {[r['id'] for r in fn]}")
    L(f"- **FP(정상을 자동차단)**: {len(fp)}개 {[r['id'] for r in fp]}")
    L(f"- **REVIEW(관리자 검토 보류)**: {len(rv)}개 {[r['id'] for r in rv]}")
    L(f"- **안전율(위험 FN·FP 아님)**: {safe/total:.1%} ({safe}/{total}) — 자동 오결정이 없는 비율\n")

    # ── 카테고리별 ──
    L("## 3. 카테고리별 (엄격 정확 / 안전[정확+검토])\n")
    L("| 분류 | 엄격정확 | 안전(정확+검토) |")
    L("|------|----------|------------------|")
    for cat in ["A", "B", "C", "D"]:
        sub = [r for r in rows if r["category"] == cat]
        if not sub:
            L(f"| {cat} | - | - |"); continue
        c = sum(1 for r in sub if r["correct"])
        safe_c = sum(1 for r in sub if r["outcome"] in ("correct", "review"))
        L(f"| {cat} | {c}/{len(sub)} ({c/len(sub):.0%}) | {safe_c}/{len(sub)} ({safe_c/len(sub):.0%}) |")
    L("")

    # ── FN / FP / REVIEW 상세 ──
    L("## 4. 위험 False Negative (위반을 자동 통과 — 가장 위험)\n")
    if not fn:
        L("**없음. 0_auto_pass 경로 제거 효과 — 함의형 위반도 더 이상 검토 없이 통과하지 않음.**\n")
    for r in fn:
        L(f"- **{r['id']} {r['title']}** (단계={r['stage']}) — Gemini가 pass로 판정. 사유: {r['reason']}")
    L("")

    L("## 5. False Positive (정상을 자동 차단 — 사용성 해침)\n")
    if not fp:
        L("**없음. 애매 케이스가 block 대신 review로 빠져 정상 콘텐츠 자동차단 사라짐.**\n")
    for r in fp:
        L(f"- **{r['id']} {r['title']}** (단계={r['stage']}) — 사유: {r['reason']}")
    L("")

    L("## 6. REVIEW로 보류된 케이스 (관리자 검토 큐)\n")
    if not rv:
        L("없음.\n")
    for r in rv:
        tag = "적절(애매 위반)" if r["category"] in ("B",) else (
              "적절(애매 정상)" if r["category"] in ("C",) else "확인 필요")
        L(f"- **{r['id']} [{r['category']}] {r['title']}** (기대={r['expected']}) — {tag}. 사유: {r['reason']}")
    L("")

    return "\n".join(lines), dict(fn=fn, fp=fp, rv=rv, exact=exact, total=total)


async def main():
    client = LawClient()
    print(f"RAG mode={client.law_rag._mode}, "
          f"count={client.law_rag.collection.count() if client.law_rag.collection else 0}")
    print(f"케이스 {len(CASES)}개 실행 (모든 콘텐츠 Gemini 1회 검토)...\n")

    rows = []
    for case in CASES:
        r = await run_case(client, case)
        rows.append(r)
        omark = {"correct": "OK ", "review": "REV", "fn": "FN!", "fp": "FP!"}[r["outcome"]]
        print(f"  [{omark}] {r['id']} {r['category']} "
              f"기대={r['expected']} 실제={r['actual']} 단계={r['stage']}")

    report, agg = build_report(rows)
    out = Path("results_law_test.md")
    out.write_text(report, encoding="utf-8")

    print(f"\n=== 집계 ===")
    print(f"엄격 정확도: {len(agg['exact'])/agg['total']:.1%} ({len(agg['exact'])}/{agg['total']})")
    print(f"위험 FN(자동통과): {len(agg['fn'])}개 {[r['id'] for r in agg['fn']]}")
    print(f"FP(자동차단): {len(agg['fp'])}개 {[r['id'] for r in agg['fp']]}")
    print(f"REVIEW(보류): {len(agg['rv'])}개 {[r['id'] for r in agg['rv']]}")
    print(f"저장: {out}")


if __name__ == "__main__":
    asyncio.run(main())
