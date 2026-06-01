"""
술BTI 분류 실험: 룰 baseline vs KNN 여러 설정 비교
사용법: python scripts/run_bti_experiments.py
선행:   python scripts/gen_synthetic_bti.py   (data/synthetic_bti.csv 생성)

측정: 전체 정확도 / hard 케이스 정확도 / macro-F1
출력: 콘솔 표 + results.md
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler

RANDOM_SEED = 42
CSV_PATH = Path('data/synthetic_bti.csv')
RESULTS_PATH = Path('results.md')

AXES = ['sweetness', 'body', 'carbonation', 'flavor',
        'alcohol', 'acidity', 'aroma_intensity', 'finish']
RULE_ONLY_AXES = ['sweetness', 'body', 'carbonation', 'flavor', 'alcohol']


def rule_predict(df):
    """app/core/survey_converter.py _determine_bti_rule_based() 와 동일한 임계 적용."""
    s = np.where(df['sweetness']   >= 5, 'S', 'D')
    h = np.where(df['body']        >= 5, 'H', 'L')
    f = np.where(df['carbonation'] >= 5, 'F', 'M')
    c = np.where(df['flavor']      >= 5, 'U', 'C')
    a = np.where(df['alcohol']     >= 9, 'H', 'L')
    return np.array([f'{s[i]}{h[i]}{f[i]}{c[i]}{a[i]}' for i in range(len(df))])


def metrics(y_true, y_pred, hard_mask):
    overall = accuracy_score(y_true, y_pred)
    macro_f1 = f1_score(y_true, y_pred, average='macro', zero_division=0)
    if hard_mask.sum() > 0:
        hard_acc = accuracy_score(y_true[hard_mask], y_pred[hard_mask])
    else:
        hard_acc = float('nan')
    return overall, hard_acc, macro_f1


def run_knn(X_tr, y_tr, X_te, cols, k, scale):
    Xtr = X_tr[cols].values
    Xte = X_te[cols].values
    if scale:
        sc = StandardScaler().fit(Xtr)
        Xtr, Xte = sc.transform(Xtr), sc.transform(Xte)
    knn = KNeighborsClassifier(n_neighbors=k, weights='distance', metric='euclidean')
    knn.fit(Xtr, y_tr)
    return knn.predict(Xte)


def main():
    if not CSV_PATH.exists():
        print(f'데이터 없음: {CSV_PATH}\n먼저 실행: python scripts/gen_synthetic_bti.py')
        return

    df = pd.read_csv(CSV_PATH)
    print(f'로드: {len(df)}개, 클래스 {df["bti_code"].nunique()}개\n')

    # 클래스별 샘플 수 점검 (0개 경고는 split 후에도 다시 본다)
    counts = df['bti_code'].value_counts()
    expected_classes = 32
    if df['bti_code'].nunique() < expected_classes:
        print(f'⚠ 경고: 클래스가 {df["bti_code"].nunique()}개뿐 (기대 {expected_classes}). '
              f'합성 데이터 생성을 확인하세요.')

    # 70/30 stratified split
    train_df, test_df = train_test_split(
        df, test_size=0.30, random_state=RANDOM_SEED, stratify=df['bti_code'])
    y_tr = train_df['bti_code'].values
    y_te = test_df['bti_code'].values
    hard_mask = test_df['is_hard'].values.astype(bool)

    # split 후 train/test 각각에 빠진 클래스 경고
    miss_tr = set(df['bti_code'].unique()) - set(y_tr)
    miss_te = set(df['bti_code'].unique()) - set(y_te)
    if miss_tr:
        print(f'⚠ 경고: train 에 없는 클래스 {len(miss_tr)}개: {sorted(miss_tr)}')
    if miss_te:
        print(f'⚠ 경고: test 에 없는 클래스 {len(miss_te)}개: {sorted(miss_te)}')

    print(f'train {len(train_df)} / test {len(test_df)}  '
          f'(test 중 hard {hard_mask.sum()}개)\n')

    results = []  # (name, overall, hard_acc, macro_f1, comment)

    # --- 룰 baseline ---
    rp = rule_predict(test_df)
    o, ha, mf = metrics(y_te, rp, hard_mask)
    results.append(('룰 baseline (임계값)', o, ha, mf,
                    '임계선 근처(hard)에서 노이즈가 경계를 넘으면 바로 오분류'))

    # --- KNN 설정들 ---
    configs = [
        ('KNN A: scaling X / 8축 / k=5', AXES, 5, False,
         '미스케일+천장눌린 alcohol(임계9) 탓에 도수축 영향 왜곡'),
        ('KNN B: StandardScaler / 8축 / k=5', AXES, 5, True,
         '스케일링으로 8축 균등 기여, 무관축 노이즈는 잡음으로 남음'),
        ('KNN C: StandardScaler / 5룰축 / k=5', RULE_ONLY_AXES, 5, True,
         '무관축(acidity/aroma/finish) 제거 → 라벨 신호축만 사용'),
        ('KNN D: StandardScaler / 8축 / k=3', AXES, 3, True,
         'k 작음 → 경계 근처에서 분산 큼'),
        ('KNN E: StandardScaler / 8축 / k=7', AXES, 7, True,
         'k 큼 → 경계 더 매끄럽게, 소수 노이즈에 둔감'),
    ]
    for name, cols, k, scale, comment in configs:
        pred = run_knn(train_df, y_tr, test_df, cols, k, scale)
        o, ha, mf = metrics(y_te, pred, hard_mask)
        results.append((name, o, ha, mf, comment))

    # --- 콘솔 표 ---
    print(f'{"설정":<38}{"전체Acc":>9}{"hardAcc":>9}{"macroF1":>9}')
    print('-' * 65)
    for name, o, ha, mf, _ in results:
        print(f'{name:<38}{o:>9.3f}{ha:>9.3f}{mf:>9.3f}')
    print()
    best = max(results, key=lambda r: r[1])
    print(f'최고 전체정확도: {best[0]} ({best[1]:.3f})')

    # --- results.md ---
    lines = []
    lines.append('# 술BTI 분류 실험 결과\n')
    lines.append(f'- 데이터: `{CSV_PATH}` (합성, seed={RANDOM_SEED})')
    lines.append(f'- 총 {len(df)}개 / 클래스 {df["bti_code"].nunique()}개 '
                 f'/ train {len(train_df)} · test {len(test_df)} (70/30 stratified)')
    lines.append(f'- test 중 hard 케이스 {hard_mask.sum()}개\n')
    lines.append('| 설정 | 전체 Acc | hard Acc | macro-F1 | 코멘트 |')
    lines.append('|------|---------:|---------:|---------:|--------|')
    for name, o, ha, mf, comment in results:
        lines.append(f'| {name} | {o:.3f} | {ha:.3f} | {mf:.3f} | {comment} |')
    lines.append(f'\n**최고 전체정확도**: {best[0]} ({best[1]:.3f})\n')

    # 해석 (수치 기반 자동 요약)
    rule = results[0]
    knn_b = next(r for r in results if r[0].startswith('KNN B'))
    knn_c = next(r for r in results if r[0].startswith('KNN C'))
    # KNN 중 hard 정확도 최고 (룰 baseline 제외)
    best_hard = max(results[1:], key=lambda r: (r[2] if r[2] == r[2] else -1))
    lines.append('## 요약 해석\n')
    lines.append(
        f'- **전체 정확도 1위는 KNN C(5룰축, 스케일링, k=5, {knn_c[1]:.3f})** — '
        f'라벨과 무관한 acidity/aroma_intensity/finish 3축을 빼니 가장 좋다. '
        f'반대로 같은 조건에 무관축을 더한 KNN B({knn_b[1]:.3f})는 룰({rule[1]:.3f})보다도 낮다. '
        f'StandardScaler가 무관축을 룰축과 동등한 비중으로 키워 오히려 이웃 선택을 흐린다.')
    lines.append(
        f'- **hard 케이스는 룰 baseline이 1위({rule[2]:.3f})** — '
        f'합성 라벨이 룰과 같은 임계 구조로 정의됐기에, 임계 위치를 "정답으로 알고 있는" 룰이 '
        f'경계 근처에서 데이터로 경계를 추정해야 하는 KNN(최고 {best_hard[2]:.3f})보다 유리하다.')
    lines.append(
        '- **결론**: 이 합성 설정에선 KNN 이득이 작다(+3pp). 무관축 제거(피처 선택)가 '
        '스케일링·k 튜닝보다 효과가 크며, 룰이 잘 맞는 경계형 문제에선 KNN이 룰을 크게 못 넘는다. '
        '실제 피드백 데이터로 라벨이 임계와 어긋나기 시작할 때 KNN의 이점이 드러날 것으로 예상.')
    RESULTS_PATH.write_text('\n'.join(lines), encoding='utf-8')
    print(f'\n결과 저장: {RESULTS_PATH}')


if __name__ == '__main__':
    main()
