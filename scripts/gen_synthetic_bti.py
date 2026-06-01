"""
술BTI KNN 검증용 합성 데이터 생성기
사용법: python scripts/gen_synthetic_bti.py

목적
----
실제 피드백 데이터(data/bti_feedback.json)가 부족하므로, 룰 분류기와 KNN을
공정하게 비교하기 위한 합성 라벨 데이터를 만든다.

설계 근거 (app/core/survey_converter.py 에서 확인한 사실)
- 8축 맛벡터는 모두 (...)/7*10 형태의 0~10 스케일 파생 점수.
  alcohol 도 실제 도수(ABV)가 아니라 0~10 스케일 점수다.
- 룰 분류 _determine_bti_rule_based() 임계값:
    sweetness  >= 5 -> 'S' else 'D'
    body       >= 5 -> 'H' else 'L'
    carbonation>= 5 -> 'F' else 'M'
    flavor     >= 5 -> 'U' else 'C'
    alcohol    >= 9 -> 'H' else 'L'   (★ 5번째 축만 임계가 9, 나머지는 5)
  -> 5개 이진 룰축 = 2^5 = 32개 타입.
- 무관축(라벨과 무관): acidity / aroma_intensity / finish.

★ 정답 라벨은 노이즈를 입히기 *전*의 원형(archetype) 타입이다.
  노이즈 섞인 값으로 룰을 다시 돌려 라벨을 만들지 않는다. (룰의 한계를 측정해야 하므로)
"""

import csv
from pathlib import Path

import numpy as np

RANDOM_SEED = 42

# 8축 (survey_converter.py 의 axes 순서와 동일)
AXES = ['sweetness', 'body', 'carbonation', 'flavor',
        'alcohol', 'acidity', 'aroma_intensity', 'finish']

# 라벨 코드를 만드는 5개 룰축과 (저, 고) 글자
RULE_AXES = ['sweetness', 'body', 'carbonation', 'flavor', 'alcohol']
LETTERS = {
    'sweetness':   ('D', 'S'),   # low, high
    'body':        ('L', 'H'),
    'carbonation': ('M', 'F'),
    'flavor':      ('C', 'U'),
    'alcohol':     ('L', 'H'),
}
NONRULE_AXES = ['acidity', 'aroma_intensity', 'finish']

# 축별 임계값
THRESHOLD = {
    'sweetness': 5.0, 'body': 5.0, 'carbonation': 5.0, 'flavor': 5.0,
    'alcohol': 9.0,
}

# 룰축 원형 중심값 (clear: 임계선에서 확실히 떨어뜨림 / hard: 임계선 근처)
#   임계 5 축은 대칭(2.5 / 7.5), 임계 9 축(alcohol)은 천장(10)에 가까우므로 비대칭 배치.
CENTERS = {
    # axis: {'low_clear', 'high_clear', 'low_hard', 'high_hard'}
    'sweetness':   {'low_clear': 2.5, 'high_clear': 7.5, 'low_hard': 4.2, 'high_hard': 5.8},
    'body':        {'low_clear': 2.5, 'high_clear': 7.5, 'low_hard': 4.2, 'high_hard': 5.8},
    'carbonation': {'low_clear': 2.5, 'high_clear': 7.5, 'low_hard': 4.2, 'high_hard': 5.8},
    'flavor':      {'low_clear': 2.5, 'high_clear': 7.5, 'low_hard': 4.2, 'high_hard': 5.8},
    # alcohol: 임계 9, 범위 ~1.6~10. 'H'는 천장에 눌려있어 9.5 / 'L'은 5.0 으로 멀리.
    'alcohol':     {'low_clear': 5.0, 'high_clear': 9.5, 'low_hard': 8.2, 'high_hard': 9.3},
}

# 가우시안 노이즈 표준편차
#   감각(룰)축 σ≈1.0. alcohol은 임계(9)가 천장(10) 바로 아래라 사용 가능 폭이 좁으므로
#   범위에 비례해 σ를 0.6으로 줄인다 (안 줄이면 H 샘플 절반이 9 밑으로 떨어져 라벨 의미가 흐려짐).
SIGMA = {
    'sweetness': 1.0, 'body': 1.0, 'carbonation': 1.0, 'flavor': 1.0,
    'alcohol': 0.6,
}
SIGMA_NONRULE = 1.5   # 무관축은 더 넓게 흩뿌려 라벨 신호가 없도록

PER_TYPE = 47          # 타입당 샘플 수 (32 * 47 = 1504)
HARD_RATIO = 0.30      # 30% 는 hard 케이스
CLAMP = (0.0, 10.0)

OUT_PATH = Path('data/synthetic_bti.csv')


def all_archetypes():
    """32개 타입의 (코드, {축: 'low'/'high'}) 목록 생성."""
    archs = []
    for bits in range(32):
        side = {}
        code = ''
        for i, axis in enumerate(RULE_AXES):
            hi = bool((bits >> i) & 1)
            side[axis] = 'high' if hi else 'low'
            code += LETTERS[axis][1 if hi else 0]
        archs.append((code, side))
    return archs


def sample_one(rng, side, is_hard, hard_axes):
    """원형 side(축별 low/high)와 hard 여부로 8축 한 행을 생성."""
    vec = {}
    for axis in RULE_AXES:
        lo_hi = side[axis]              # 'low' or 'high'
        near = is_hard and axis in hard_axes
        key = f"{lo_hi}_{'hard' if near else 'clear'}"
        center = CENTERS[axis][key]
        val = center + rng.normal(0.0, SIGMA[axis])
        vec[axis] = float(np.clip(val, *CLAMP))
    # 무관축: 라벨과 무관하게 중앙(5) 근처로 넓게 분포
    for axis in NONRULE_AXES:
        val = 5.0 + rng.normal(0.0, SIGMA_NONRULE)
        vec[axis] = float(np.clip(val, *CLAMP))
    return vec


def main():
    rng = np.random.default_rng(RANDOM_SEED)
    archs = all_archetypes()

    n_hard = int(round(PER_TYPE * HARD_RATIO))
    rows = []
    for code, side in archs:
        # 어떤 인덱스가 hard 인지 타입 내에서 셔플
        hard_flags = [True] * n_hard + [False] * (PER_TYPE - n_hard)
        rng.shuffle(hard_flags)
        for is_hard in hard_flags:
            if is_hard:
                # 1~2개 룰축을 임계선 근처로
                k = int(rng.integers(1, 3))
                hard_axes = set(rng.choice(RULE_AXES, size=k, replace=False).tolist())
            else:
                hard_axes = set()
            vec = sample_one(rng, side, is_hard, hard_axes)
            row = {a: round(vec[a], 2) for a in AXES}
            row['bti_code'] = code          # ★ 노이즈 전 원형 타입 = 정답 라벨
            row['is_hard'] = int(is_hard)
            rows.append(row)

    # 셔플 (타입이 블록으로 몰리지 않게)
    rng.shuffle(rows)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = AXES + ['bti_code', 'is_hard']
    with open(OUT_PATH, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    # 요약
    n = len(rows)
    n_hard_total = sum(r['is_hard'] for r in rows)
    print(f'=== 합성 BTI 데이터 생성 완료 (seed={RANDOM_SEED}) ===')
    print(f'총 {n}개  ({len(archs)}타입 x {PER_TYPE}개)')
    print(f'hard: {n_hard_total}개 ({n_hard_total / n * 100:.1f}%), clear: {n - n_hard_total}개')
    print(f'클래스 수: {len(set(r["bti_code"] for r in rows))}개')
    print(f'저장: {OUT_PATH}')


if __name__ == '__main__':
    main()
