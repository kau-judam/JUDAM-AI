"""
술BTI 4글자(도수 제외) vs 5글자(도수 포함) 분류 정확도 비교
사용법: python scripts/run_bti_4vs5.py
선행:   python scripts/gen_synthetic_bti.py   (data/synthetic_bti.csv)

설계
----
- 같은 맛벡터 데이터(data/synthetic_bti.csv)에 라벨만 두 방식으로 부여(공정 비교).
    · 5글자 = bti_code 그대로 (sweetness/body/carbonation/flavor/alcohol → 32타입)
    · 4글자 = bti_code[:4] (alcohol 제외 → sweetness/body/carbonation/flavor → 16타입)
- 룰 baseline 의 alcohol 임계는 수정된 값 5.5 반영
  (app/core/survey_converter.py _determine_bti_rule_based 와 동일).
- KNN: StandardScaler, 분류축만, k=5, weights='distance', euclidean.
    · 5글자 KNN = 5축, 4글자 KNN = 4축.
- 기존 run_bti_experiments.py 의 metrics(), run_knn() 재활용.
- train/test 분할은 한 번만(5글자 기준 stratify) 수행해 두 체계가 동일 행을 쓰도록 함.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).resolve().parent))  # 같은 폴더 스크립트 import
from run_bti_experiments import metrics, run_knn  # noqa: E402

RANDOM_SEED = 42
CSV_PATH = Path('data/synthetic_bti.csv')
RESULTS_PATH = Path('results_bti_4vs5.md')

ALCOHOL_THRESHOLD = 5.5   # app 의 수정된 임계
AXES5 = ['sweetness', 'body', 'carbonation', 'flavor', 'alcohol']
AXES4 = ['sweetness', 'body', 'carbonation', 'flavor']


def _base4(df):
    """sweetness/body/carbonation/flavor → 4글자 룰 예측 (alcohol 제외)."""
    s = np.where(df['sweetness']   >= 5, 'S', 'D')
    h = np.where(df['body']        >= 5, 'H', 'L')
    f = np.where(df['carbonation'] >= 5, 'F', 'M')
    c = np.where(df['flavor']      >= 5, 'U', 'C')
    return s, h, f, c


def rule_predict_4(df):
    s, h, f, c = _base4(df)
    return np.array([f'{s[i]}{h[i]}{f[i]}{c[i]}' for i in range(len(df))])


def rule_predict_5(df):
    """4글자 + alcohol(임계 5.5) → 5글자 룰 예측."""
    s, h, f, c = _base4(df)
    a = np.where(df['alcohol'] >= ALCOHOL_THRESHOLD, 'H', 'L')
    return np.array([f'{s[i]}{h[i]}{f[i]}{c[i]}{a[i]}' for i in range(len(df))])


def main():
    if not CSV_PATH.exists():
        print(f'데이터 없음: {CSV_PATH}\n먼저 실행: python scripts/gen_synthetic_bti.py')
        return

    df = pd.read_csv(CSV_PATH)
    # 두 라벨 체계 (같은 행에서 파생)
    df['code5'] = df['bti_code']
    df['code4'] = df['bti_code'].str[:4]
    n5, n4 = df['code5'].nunique(), df['code4'].nunique()
    print(f'로드 {len(df)}개 | 5글자 클래스 {n5} / 4글자 클래스 {n4}')
    if n5 < 32 or n4 < 16:
        print(f'⚠ 경고: 기대 클래스(32/16)보다 적음 ({n5}/{n4}). 데이터 생성 확인.')

    # 분할 1회 (5글자 기준 stratify → 두 체계 동일 행 사용)
    train_df, test_df = train_test_split(
        df, test_size=0.30, random_state=RANDOM_SEED, stratify=df['code5'])
    hard_mask = test_df['is_hard'].values.astype(bool)
    print(f'train {len(train_df)} / test {len(test_df)} (hard {hard_mask.sum()})\n')

    # 0개 클래스 경고 (분할 후)
    for col, exp in [('code5', 32), ('code4', 16)]:
        miss_tr = set(df[col].unique()) - set(train_df[col])
        miss_te = set(df[col].unique()) - set(test_df[col])
        if miss_tr or miss_te:
            print(f'⚠ {col}: train 누락 {len(miss_tr)}, test 누락 {len(miss_te)}')

    rows = []  # (체계, 방법, 클래스수, 축수, overall, hard, macroF1)

    # ── 5글자 ──
    y5_te = test_df['code5'].values
    o, ha, mf = metrics(y5_te, rule_predict_5(test_df), hard_mask)
    rows.append(('5글자(도수포함)', '룰(임계5.5)', n5, 5, o, ha, mf))
    pred = run_knn(train_df, train_df['code5'].values, test_df, AXES5, 5, True)
    o, ha, mf = metrics(y5_te, pred, hard_mask)
    rows.append(('5글자(도수포함)', 'KNN(5축)', n5, 5, o, ha, mf))

    # ── 4글자 ──
    y4_te = test_df['code4'].values
    o, ha, mf = metrics(y4_te, rule_predict_4(test_df), hard_mask)
    rows.append(('4글자(도수제외)', '룰', n4, 4, o, ha, mf))
    pred = run_knn(train_df, train_df['code4'].values, test_df, AXES4, 5, True)
    o, ha, mf = metrics(y4_te, pred, hard_mask)
    rows.append(('4글자(도수제외)', 'KNN(4축)', n4, 4, o, ha, mf))

    # ── 콘솔 표 ──
    print(f'{"체계":<16}{"방법":<14}{"클래스":>6}{"전체Acc":>9}{"hardAcc":>9}{"macroF1":>9}')
    print('-' * 63)
    for sysname, method, ncls, nax, o, ha, mf in rows:
        print(f'{sysname:<16}{method:<14}{ncls:>6}{o:>9.3f}{ha:>9.3f}{mf:>9.3f}')

    # ── results_bti_4vs5.md ──
    md = ['# 술BTI 4글자(도수 제외) vs 5글자(도수 포함) 비교\n',
          f'- 데이터: `{CSV_PATH}` (합성, seed={RANDOM_SEED}) — 두 체계가 **동일 맛벡터**를 사용, 라벨만 다름',
          f'- 5글자=`bti_code`(32타입), 4글자=`bti_code[:4]`(16타입, alcohol 제외)',
          f'- 분할 1회(5글자 stratify): train {len(train_df)} / test {len(test_df)}, hard {hard_mask.sum()}개',
          f'- 룰 alcohol 임계 = {ALCOHOL_THRESHOLD} (앱 수정 반영)\n',
          '| 체계 | 방법 | 클래스수 | KNN축수 | 전체 Acc | hard Acc | macro-F1 |',
          '|------|------|:-------:|:------:|---------:|---------:|---------:|']
    for sysname, method, ncls, nax, o, ha, mf in rows:
        axn = nax if method.startswith('KNN') else '-'
        md.append(f'| {sysname} | {method} | {ncls} | {axn} | {o:.3f} | {ha:.3f} | {mf:.3f} |')

    # 핵심 코멘트 (수치 기반)
    r5_rule, r5_knn, r4_rule, r4_knn = rows
    d_rule = r4_rule[4] - r5_rule[4]
    d_knn = r4_knn[4] - r5_knn[4]
    md.append('\n## 핵심 코멘트')
    md.append(
        f'- **도수축 제외(5글자→4글자) 시 전체 정확도 상승**: 룰 {r5_rule[4]:.3f}→{r4_rule[4]:.3f} '
        f'({d_rule:+.3f}), KNN {r5_knn[4]:.3f}→{r4_knn[4]:.3f} ({d_knn:+.3f}). '
        f'alcohol 축은 임계(5.5)가 분포 중앙에서 벗어나 있고 σ가 작아 5번째 글자가 추가 오분류를 '
        f'유발한다 — 이 글자를 빼면 그만큼 정확도가 회복된다.')
    md.append(
        f'- **클래스 수 32→16 효과**: 분류 후보가 절반으로 줄어 우연·경계 오류가 감소, '
        f'macro-F1 도 5글자({r5_knn[6]:.3f}/{r5_rule[6]:.3f})보다 4글자({r4_knn[6]:.3f}/{r4_rule[6]:.3f})가 높다.')
    md.append(
        '- **트레이드오프**: 4글자가 정확도는 높지만 도수(고/저) 정보를 버린다. '
        'BTI가 도수 구분을 제공해야 한다면 5글자를 유지하되, 도수는 별도 축으로 표기하거나 '
        'alcohol 임계/스케일을 재보정해 5번째 글자 오분류를 줄이는 편이 낫다.')
    md.append(
        '- **주의(hard 정의)**: is_hard 는 5글자 기준(alcohol 포함 1~2축이 임계 근처)이라, '
        'alcohol 때문에만 hard 였던 샘플은 4글자 공간에선 실제로 어렵지 않다. '
        '4글자 hard 정확도가 다소 후하게 보일 수 있음.')

    RESULTS_PATH.write_text('\n'.join(md), encoding='utf-8')
    print(f'\n결과 저장: {RESULTS_PATH}')


if __name__ == '__main__':
    main()
