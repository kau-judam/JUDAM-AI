"""
JS 포팅 검증: web/survey/index.html 의 convertSurvey(JS) vs app/core/survey_converter.py
사용법: python scripts/verify_js_port.py
필요:   node (PATH)

방법
----
1. index.html 에서 convertSurvey~tasteSummary 블록을 그대로 추출(단일 소스).
2. 무작위 설문 200개 생성(seed 고정).
3. Node 로 JS convertSurvey 실행 → {axes(raw), bti4}.
4. Python: 기존 SurveyToVectorConverter 의 _calculate_* 를 호출해 raw 8축 산출
   (q23/q25 보정은 convert() 와 동일 절차) + convert() 의 bti_code[:4] 를 정답으로 사용.
   - mirror(raw) 가 production convert() 와 일치하는지 assert 로 자체검증.
5. 8축(|diff|<=1e-9) + BTI4(문자열) 100% 일치 여부 리포트. 불일치 시 입력/축 출력.

app/ 는 읽기/호출만, 수정하지 않음.
"""

import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.survey_converter import SurveyToVectorConverter, SurveyResponse  # noqa: E402

HTML = ROOT / "web" / "survey" / "index.html"
AXES = ['sweetness', 'body', 'carbonation', 'flavor',
        'alcohol', 'acidity', 'aroma_intensity', 'finish']
N = 200
SEED = 42
TOL = 1e-9


def extract_js():
    src = HTML.read_text(encoding="utf-8")
    start = src.index("function convertSurvey")
    end = src.index("/* ===PORT_END===")
    return src[start:end]


def make_surveys():
    rng = random.Random(SEED)
    out = []
    for _ in range(N):
        s = {"q1": rng.randint(1, 5), "q2": rng.randint(1, 5), "q3": rng.randint(1, 5),
             "q23": rng.randint(1, 5),
             "q24": rng.sample(range(1, 6), rng.randint(1, 3)),
             "q25": rng.sample(range(1, 6), rng.randint(1, 3))}
        for i in range(4, 23):
            s[f"q{i}"] = rng.randint(1, 7)
        out.append(s)
    return out


def run_node(js_block, surveys):
    harness = js_block + """
const fs = require('fs');
const input = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
process.stdout.write(JSON.stringify(input.map(s => convertSurvey(s))));
"""
    with tempfile.TemporaryDirectory() as d:
        jsf = Path(d) / "harness.js"
        inf = Path(d) / "input.json"
        jsf.write_text(harness, encoding="utf-8")
        inf.write_text(json.dumps(surveys), encoding="utf-8")
        r = subprocess.run(["node", str(jsf), str(inf)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print("[node 실행 실패]\n", r.stderr)
            sys.exit(1)
        return json.loads(r.stdout)


def py_compute(conv, s):
    """기존 _calculate_* 호출 + convert() 와 동일한 q23/q25 보정으로 raw 8축 산출."""
    sweetness = conv._calculate_sweetness(s['q4'], s['q5'], s['q6'], s['q7'], s['q8'], s['q9'])
    body = conv._calculate_body(s['q10'], s['q11'], s['q13'], s['q6'])
    carbonation = conv._calculate_carbonation(s['q14'], s['q15'], s['q7'])
    flavor = conv._calculate_flavor(s['q17'], s['q18'], s['q20'], s['q9'])
    alcohol = conv._calculate_alcohol(s['q21'], s['q12'], s['q13'], conv._get_alcohol_base(s['q2']))
    acidity = conv._calculate_acidity(s['q5'], s['q14'], s['q19'], s['q18'])
    aroma = conv._calculate_aroma_intensity(s['q15'], s['q16'], s['q17'], s['q18'])
    finish = conv._calculate_finish(s['q8'], s['q16'], s['q14'])
    # q23 (convert() 260-268 과 동일)
    for key, value in conv.fruit_taste_map.get(s['q23'], {}).items():
        if key == 'citrus':   aroma = min(10, aroma + value * 0.1)
        elif key == 'berry':  flavor = min(10, flavor + value * 0.1)
        elif key == 'tropical': sweetness = min(10, sweetness + value * 0.1)
    # q25 (convert() 273-285 와 동일)
    for code in s['q25']:
        a = conv.aroma_map.get(code)
        if a == 'other_fruit':  flavor = min(10, flavor + 0.7)
        elif a == 'citrus':     aroma = min(10, aroma + 0.7)
        elif a == 'flower':     aroma = min(10, aroma + 0.7)
        elif a == 'herb':       flavor = min(10, flavor + 0.7)
        elif a == 'rice':       body = min(10, body + 0.7)
    axes = {'sweetness': sweetness, 'body': body, 'carbonation': carbonation, 'flavor': flavor,
            'alcohol': alcohol, 'acidity': acidity, 'aroma_intensity': aroma, 'finish': finish}
    bti4 = (('S' if sweetness >= 5 else 'D') + ('H' if body >= 5 else 'L') +
            ('F' if carbonation >= 5 else 'M') + ('U' if flavor >= 5 else 'C'))
    return axes, bti4


def main():
    surveys = make_surveys()
    js_results = run_node(extract_js(), surveys)
    conv = SurveyToVectorConverter()

    n_axis_ok = n_bti_ok = n_full_ok = 0
    n_axis_total = N * len(AXES)
    n_axis_hits = 0
    mismatches = []

    for i, s in enumerate(surveys):
        py_axes, py_bti = py_compute(conv, s)

        # 자체검증: mirror(raw) 가 production convert() 와 일치하는지
        vec = conv.convert(SurveyResponse(**s))
        for ax in AXES:
            assert round(py_axes[ax], 2) == vec[ax], f"mirror≠convert at {ax} (sample {i})"
        assert py_bti == vec['bti_code'][:4], f"mirror bti≠convert at sample {i}"

        js = js_results[i]
        axis_ok = True
        for ax in AXES:
            diff = abs(py_axes[ax] - js['axes'][ax])
            if diff <= TOL:
                n_axis_hits += 1
            else:
                axis_ok = False
                if len(mismatches) < 20:
                    mismatches.append((i, ax, py_axes[ax], js['axes'][ax], diff, s))
        bti_ok = (py_bti == js['bti4'])
        if axis_ok: n_axis_ok += 1
        if bti_ok: n_bti_ok += 1
        if axis_ok and bti_ok: n_full_ok += 1
        if not bti_ok and len(mismatches) < 20:
            mismatches.append((i, 'BTI4', py_bti, js['bti4'], '-', s))

    print(f"=== JS 포팅 검증 (n={N}, seed={SEED}, tol={TOL}) ===")
    print(f"8축 값 일치: {n_axis_hits}/{n_axis_total} = {n_axis_hits/n_axis_total*100:.2f}%")
    print(f"8축 전부 일치한 샘플: {n_axis_ok}/{N}")
    print(f"BTI4 일치 샘플: {n_bti_ok}/{N}")
    print(f"★ 8축+BTI4 모두 일치: {n_full_ok}/{N} = {n_full_ok/N*100:.2f}%")

    if mismatches:
        print(f"\n불일치 {len(mismatches)}건 (최대 20):")
        for i, ax, pv, jv, diff, s in mismatches:
            print(f"  sample {i} | {ax}: py={pv} js={jv} diff={diff}")
            print(f"    입력={s}")
    else:
        print("\n불일치 없음 — 포팅 정확.")


if __name__ == "__main__":
    main()
