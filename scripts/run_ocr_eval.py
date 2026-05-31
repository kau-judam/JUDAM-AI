"""
양조장 OCR 더미 검증
사용법: python scripts/run_ocr_eval.py
선행:   python scripts/gen_dummy_docs.py  (data/dummy_docs/*.png + labels.json)

더미 PNG를 base64로 OCR(extract_brewery_info) 통과 → 추출 vs labels 비교.
서류 판별 정확도 + 필드별 추출 정확도 표 → results_ocr.md. 실패/오판별 표시.
실제 Gemini OCR 라이브 호출.
"""

import asyncio
import base64
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from app.ocr import BreweryOCR  # noqa: E402

DOC_DIR = Path("data/dummy_docs")
RESULTS = Path("results_ocr.md")
FIELDS = ["brewery_name", "registration_number", "owner_name",
          "address", "issue_date", "issuing_authority"]

# 동일하게 취급할 서류 종류 (전통주 면허 = 주류 면허 표기 허용)
TYPE_EQUIV = [{"전통주제조면허증", "주류제조면허증", "주류제조면허"}]


def _norm(s):
    return re.sub(r"\s+", "", str(s or "")).lower()


def type_match(expected, predicted):
    e, p = _norm(expected), _norm(predicted)
    if e == p:
        return True
    for grp in TYPE_EQUIV:
        g = {_norm(x) for x in grp}
        if e in g and p in g:
            return True
    return False


def field_match(field, expected, predicted):
    """label 이 빈 문자열이면 None(채점 제외). 아니면 True/False."""
    if expected == "" or expected is None:
        return None
    e, p = _norm(expected), _norm(predicted)
    if not p:
        return False
    if field == "issue_date":
        return re.sub(r"\D", "", e) == re.sub(r"\D", "", p)
    if field == "registration_number":
        # '제','호' 와 공백 제거 후 포함관계
        e2 = e.replace("제", "").replace("호", "")
        p2 = p.replace("제", "").replace("호", "")
        return e2 == p2 or e2 in p2 or p2 in e2
    return e == p or e in p or p in e


async def main():
    labels_path = DOC_DIR / "labels.json"
    if not labels_path.exists():
        print(f"라벨 없음: {labels_path}\n먼저 실행: python scripts/gen_dummy_docs.py")
        return
    labels = json.loads(labels_path.read_text(encoding="utf-8"))

    ocr = BreweryOCR()
    if not ocr.enabled:
        print("OCR 비활성화 (GEMINI_API_KEY 없음).")
        return

    rows = []          # per-doc 결과
    field_hits = {f: [0, 0] for f in FIELDS}  # [맞음, 채점대상]
    type_correct = 0

    for fname, label in labels.items():
        img = DOC_DIR / fname
        b64 = base64.b64encode(img.read_bytes()).decode()
        res = await ocr.extract_brewery_info(b64, "image/png")
        ext = res.get("extracted", {}) if res.get("status") == "success" else {}

        pred_type = ext.get("document_type", res.get("status", "ERROR"))
        t_ok = type_match(label["document_type"], pred_type)
        type_correct += int(t_ok)

        field_results = {}
        for f in FIELDS:
            m = field_match(f, label.get(f, ""), ext.get(f, ""))
            field_results[f] = (m, ext.get(f, ""))
            if m is not None:
                field_hits[f][1] += 1
                field_hits[f][0] += int(m)

        rows.append({
            "file": fname, "exp_type": label["document_type"], "pred_type": pred_type,
            "type_ok": t_ok, "valid": ext.get("is_valid_document"),
            "conf": ext.get("confidence"), "fields": field_results,
            "status": res.get("status"),
        })
        print(f"[{fname}] 판별 {'O' if t_ok else 'X'} (pred={pred_type}) "
              f"필드 {sum(1 for f in FIELDS if field_results[f][0])}/{sum(1 for f in FIELDS if field_results[f][0] is not None)}")

    n = len(labels)
    type_acc = type_correct / n if n else 0

    # ── results_ocr.md ──
    md = ["# 양조장 OCR 더미 검증 결과\n",
          f"- 더미 서류 {n}종, 실제 Gemini OCR(`gemini-2.5-flash-lite`) 라이브 호출",
          f"- **서류 판별 정확도: {type_correct}/{n} = {type_acc:.0%}**\n",
          "## 1) 서류 판별",
          "| 파일 | 정답 종류 | 예측 종류 | 판별 | is_valid | conf |",
          "|------|-----------|-----------|:----:|:--------:|:----:|"]
    for r in rows:
        md.append(f"| {r['file']} | {r['exp_type']} | {r['pred_type']} | "
                  f"{'✅' if r['type_ok'] else '❌'} | {r['valid']} | {r['conf']} |")

    md.append("\n## 2) 필드별 추출 정확도")
    md.append("| 필드 | 정확도 |")
    md.append("|------|--------|")
    for f in FIELDS:
        hit, tot = field_hits[f]
        md.append(f"| {f} | {hit}/{tot} = {(hit/tot if tot else 0):.0%} |")

    md.append("\n## 3) 서류별 필드 상세 (❌ = 불일치, 예측값 표시)")
    for r in rows:
        md.append(f"\n**{r['file']}** (status={r['status']})")
        md.append("| 필드 | 정답 | 예측 | 일치 |")
        md.append("|------|------|------|:----:|")
        lab = labels[r['file']]
        for f in FIELDS:
            m, pv = r["fields"][f]
            mark = "—(제외)" if m is None else ("✅" if m else "❌")
            md.append(f"| {f} | {lab.get(f,'')} | {pv} | {mark} |")

    # 실패/오판별 요약
    fails = [r for r in rows if not r["type_ok"]]
    md.append("\n## 4) 실패/오판별 케이스")
    if fails:
        for r in fails:
            md.append(f"- ❌ {r['file']}: 정답 `{r['exp_type']}` → 예측 `{r['pred_type']}`")
    else:
        md.append("- 서류 판별 오류 없음 (전 종류 정답).")

    RESULTS.write_text("\n".join(md), encoding="utf-8")
    print(f"\n서류 판별 정확도: {type_acc:.0%} ({type_correct}/{n})")
    print(f"결과 저장: {RESULTS}")


if __name__ == "__main__":
    asyncio.run(main())
