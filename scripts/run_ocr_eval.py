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

    pos_rows = []      # 정상 서류 결과
    neg_rows = []      # 비정상(걸러져야 할) 결과
    field_hits = {f: [0, 0] for f in FIELDS}  # [맞음, 채점대상]
    type_correct = 0   # 정상 서류 한정
    # 혼동행렬 (is_valid 기준): expect_valid × predicted_valid
    cm = {"TP": 0, "FN": 0, "FP": 0, "TN": 0}

    for fname, label in labels.items():
        expect_valid = label.get("expect_valid", True)
        img = DOC_DIR / fname
        b64 = base64.b64encode(img.read_bytes()).decode()
        res = await ocr.extract_brewery_info(b64, "image/png")
        ext = res.get("extracted", {}) if res.get("status") == "success" else {}

        pred_type = ext.get("document_type", res.get("status", "ERROR"))
        pred_valid = bool(ext.get("is_valid_document", False))

        # 혼동행렬 집계
        if expect_valid and pred_valid:
            cm["TP"] += 1            # 정상 → valid (정상 통과)
        elif expect_valid and not pred_valid:
            cm["FN"] += 1            # 정상 → invalid (false reject)
        elif (not expect_valid) and pred_valid:
            cm["FP"] += 1            # 비정상 → valid (false accept = 위험)
        else:
            cm["TN"] += 1            # 비정상 → invalid (올바르게 거름)

        if expect_valid:
            # 정상 서류: 종류 판별 + 필드 추출 채점
            t_ok = type_match(label["document_type"], pred_type)
            type_correct += int(t_ok)
            field_results = {}
            for f in FIELDS:
                m = field_match(f, label.get(f, ""), ext.get(f, ""))
                field_results[f] = (m, ext.get(f, ""))
                if m is not None:
                    field_hits[f][1] += 1
                    field_hits[f][0] += int(m)
            pos_rows.append({
                "file": fname, "exp_type": label["document_type"], "pred_type": pred_type,
                "type_ok": t_ok, "valid": pred_valid,
                "conf": ext.get("confidence"), "fields": field_results,
                "status": res.get("status"),
            })
            print(f"[정상][{fname}] 판별 {'O' if t_ok else 'X'} (pred={pred_type}) valid={pred_valid}")
        else:
            ok = (not pred_valid)   # 걸러내야 정답
            neg_rows.append({
                "file": fname, "neg_kind": label.get("neg_kind", ""),
                "note": label.get("note", ""), "pred_type": pred_type,
                "valid": pred_valid, "ok": ok,
                "reason": ext.get("rejection_reason"),
                "conf": ext.get("confidence"), "status": res.get("status"),
            })
            print(f"[비정상][{fname}] {'거름 O' if ok else 'FALSE ACCEPT X'} "
                  f"(pred={pred_type}, valid={pred_valid})")

    n_pos = len(pos_rows)
    n_neg = len(neg_rows)
    n = len(labels)
    type_acc = type_correct / n_pos if n_pos else 0
    false_accept = cm["FP"]   # 비정상을 valid 로 통과시킴 (위험)
    false_reject = cm["FN"]   # 정상을 invalid 로 거부함

    # ── results_ocr.md ──
    md = ["# 양조장 OCR 더미 검증 결과\n",
          f"- 더미 서류 {n}종 (정상 {n_pos} + 비정상 {n_neg}), "
          f"실제 Gemini OCR(`gemini-2.5-flash-lite`) 라이브 호출",
          f"- **정상 서류 판별 정확도: {type_correct}/{n_pos} = {type_acc:.0%}**",
          f"- **False Accept (위조/무관 → valid, 위험): {false_accept}/{n_neg}**",
          f"- **False Reject (정상 → invalid): {false_reject}/{n_pos}**\n",
          "## 0) is_valid 혼동행렬 (positive + negative)",
          "| 실제 \\ 예측 | valid(통과) | invalid(거름) |",
          "|------------|:-----------:|:-------------:|",
          f"| **정상 서류({n_pos})** | {cm['TP']} (TP) | {cm['FN']} (FN=false reject) |",
          f"| **비정상({n_neg})** | {cm['FP']} (FP=false accept ⚠) | {cm['TN']} (TN) |",
          "",
          "## 1) 정상 서류 판별",
          "| 파일 | 정답 종류 | 예측 종류 | 판별 | is_valid | conf |",
          "|------|-----------|-----------|:----:|:--------:|:----:|"]
    for r in pos_rows:
        md.append(f"| {r['file']} | {r['exp_type']} | {r['pred_type']} | "
                  f"{'✅' if r['type_ok'] else '❌'} | {r['valid']} | {r['conf']} |")

    md.append("\n## 2) 비정상(걸러져야 할) 입력")
    md.append("| 파일 | 종류 | 예측 종류 | is_valid | 결과 | rejection_reason |")
    md.append("|------|------|-----------|:--------:|:----:|------------------|")
    for r in neg_rows:
        mark = "✅ 거름" if r["ok"] else "❌ FALSE ACCEPT"
        md.append(f"| {r['file']} | {r['neg_kind']} | {r['pred_type']} | "
                  f"{r['valid']} | {mark} | {r['reason'] or ''} |")

    md.append("\n## 3) 정상 서류 필드별 추출 정확도")
    md.append("| 필드 | 정확도 |")
    md.append("|------|--------|")
    for f in FIELDS:
        hit, tot = field_hits[f]
        md.append(f"| {f} | {hit}/{tot} = {(hit/tot if tot else 0):.0%} |")

    md.append("\n## 4) 정상 서류별 필드 상세 (❌ = 불일치, 예측값 표시)")
    for r in pos_rows:
        md.append(f"\n**{r['file']}** (status={r['status']})")
        md.append("| 필드 | 정답 | 예측 | 일치 |")
        md.append("|------|------|------|:----:|")
        lab = labels[r['file']]
        for f in FIELDS:
            m, pv = r["fields"][f]
            mark = "—(제외)" if m is None else ("✅" if m else "❌")
            md.append(f"| {f} | {lab.get(f,'')} | {pv} | {mark} |")

    # 실패/오판별 요약
    type_fails = [r for r in pos_rows if not r["type_ok"]]
    fa = [r for r in neg_rows if not r["ok"]]
    fr = [r for r in pos_rows if not r["valid"]]
    md.append("\n## 5) 실패/위험 케이스")
    md.append("\n**False Accept (비정상을 valid 로 통과 — 위험):**")
    if fa:
        for r in fa:
            md.append(f"- ❌ {r['file']} ({r['neg_kind']}) → pred `{r['pred_type']}`, valid=True")
    else:
        md.append("- 없음 (모든 비정상 입력을 걸러냄).")
    md.append("\n**False Reject (정상을 invalid 로 거부):**")
    if fr:
        for r in fr:
            md.append(f"- ⚠ {r['file']} ({r['exp_type']}) → valid=False")
    else:
        md.append("- 없음 (모든 정상 서류를 통과).")
    md.append("\n**종류 오판별 (정상 서류):**")
    if type_fails:
        for r in type_fails:
            md.append(f"- {r['file']}: 정답 `{r['exp_type']}` → 예측 `{r['pred_type']}`")
    else:
        md.append("- 없음 (정상 서류 전 종류 정답).")

    # 발급일/개업일 혼동(#1) 자동 점검
    md.append("\n## 6) 발급일/개업일 혼동 점검 (#1)")
    biz = next((r for r in pos_rows if "사업자등록증" in r["file"]
                and r["exp_type"] == "사업자등록증"), None)
    if biz:
        m, pv = biz["fields"].get("issue_date", (None, ""))
        gt = labels[biz["file"]].get("issue_date", "")
        verdict = "✅ 발급일 정확" if m else "❌ 혼동(개업일 추출 의심)"
        md.append(f"- 사업자등록증 issue_date 정답(발급일) `{gt}` vs 예측 `{pv}` → {verdict}")
        md.append("- (개업연월일 `2020-03-15` ≠ 발급일 `2020-03-20`. 둘을 혼동하면 발급일에 개업일이 들어감.)")
    else:
        md.append("- 사업자등록증 케이스 없음.")

    RESULTS.write_text("\n".join(md), encoding="utf-8")
    print(f"\n정상 판별 정확도: {type_acc:.0%} ({type_correct}/{n_pos}) | "
          f"False Accept {false_accept}/{n_neg} | False Reject {false_reject}/{n_pos}")
    print(f"결과 저장: {RESULTS}")


if __name__ == "__main__":
    asyncio.run(main())
