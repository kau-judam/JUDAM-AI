"""
술BTI KNN 분류 모델 학습 스크립트
사용법: python scripts/train_knn.py

필요 데이터: data/bti_feedback.json
형식:
[
  {
    "q1": 2, "q2": 2, ..., "q25": [1,2],
    "taste_vector": {...},
    "bti_code": "SLFUL",
    "is_correct": true  // 사용자가 "맞아요" 피드백
  }
]

데이터가 최소 50개 이상 쌓이면 실행 권장.
"""

import asyncio
import json
import pickle
import numpy as np
from pathlib import Path


def load_feedback_data(filepath='data/bti_feedback.json'):
    path = Path(filepath)
    if not path.exists():
        print(f'피드백 데이터 없음: {filepath}')
        print('data/bti_feedback.json 파일이 필요합니다.')
        return None, None

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # is_correct=True인 것만 훈련 데이터로 사용
    valid = [d for d in data if d.get('is_correct', False)]
    print(f'전체 피드백: {len(data)}개, 유효 데이터: {len(valid)}개')

    if len(valid) < 10:
        print('훈련 데이터 부족 (최소 10개 필요)')
        return None, None

    axes = ['sweetness', 'body', 'carbonation', 'flavor',
            'alcohol', 'acidity', 'aroma_intensity', 'finish']
    X = np.array([[d['taste_vector'][a] for a in axes] for d in valid])
    y = np.array([d['bti_code'] for d in valid])

    return X, y


async def load_from_db():
    """DB에서 KNN 학습 데이터 로드"""
    try:
        from app.db import db
        await db.connect()
        rows = await db.get_bti_feedback_for_training()
        if db.pool:
            await db.pool.close()

        axes = ['sweetness', 'body', 'carbonation', 'flavor',
                'alcohol', 'acidity', 'aroma_intensity', 'finish']
        X, y = [], []
        for row in rows:
            tv = json.loads(row['taste_vector']) if isinstance(row['taste_vector'], str) else row['taste_vector']
            if tv:
                X.append([tv.get(a, 5.0) for a in axes])
                y.append(row['bti_code'])

        return (np.array(X), np.array(y)) if X else (None, None)
    except Exception as e:
        print(f'DB 로드 실패 ({e}), JSON fallback 사용')
        return None, None


def train_knn(X, y, k=5):
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.preprocessing import LabelEncoder
    from sklearn.model_selection import cross_val_score

    le = LabelEncoder()
    y_encoded = le.fit_transform(y)

    knn = KNeighborsClassifier(n_neighbors=k, metric='cosine')

    if len(X) >= 10:
        cv = min(5, len(X) // 2)
        scores = cross_val_score(knn, X, y_encoded, cv=cv)
        print(f'교차 검증 정확도: {scores.mean():.2f} (+/- {scores.std():.2f})')

    knn.fit(X, y_encoded)
    return knn, le


def save_model(knn, le, filepath='models/knn_bti_model.pkl'):
    Path('models').mkdir(exist_ok=True)
    with open(filepath, 'wb') as f:
        pickle.dump({'model': knn, 'encoder': le}, f)
    print(f'모델 저장 완료: {filepath}')


def main():
    print('=== 술BTI KNN 모델 학습 ===')

    # DB 우선, 실패 시 JSON fallback
    X, y = asyncio.run(load_from_db())
    if X is None:
        print('DB 데이터 없음 → JSON 파일에서 로드')
        X, y = load_feedback_data()
    else:
        print(f'DB에서 로드 완료: {len(X)}개')
    if X is None:
        return

    print(f'훈련 데이터: {len(X)}개')
    print(f'BTI 코드 종류: {len(set(y))}개')

    knn, le = train_knn(X, y)
    save_model(knn, le)

    print('완료. 서버 재시작 시 자동으로 KNN 모델 로드됩니다.')


if __name__ == '__main__':
    main()
