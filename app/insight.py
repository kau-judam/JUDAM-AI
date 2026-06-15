"""
인사이트 대시보드 모듈
집계 + 예측 + 군집화를 통한 AI 인사이트 제공

데이터 소스 우선순위:
  1) DB 연결됨  → user_taste_history(통계), user_profiles(BTI 군집화), _fundings(펀딩 빈도)
  2) DB 없음    → 인메모리 샘플 데이터 fallback
"""

import logging
import os
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from pydantic import BaseModel, Field
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _as_list(v) -> list:
    """JSONB(str/list/None) → list 정규화."""
    if v is None:
        return []
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            parsed = json.loads(v)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return []


def _as_dict(v) -> dict:
    """JSONB(str/dict/None) → dict 정규화."""
    if v is None:
        return {}
    if isinstance(v, dict):
        return v
    if isinstance(v, str):
        try:
            parsed = json.loads(v)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


class InsightRequest(BaseModel):
    """인사이트 요청 모델"""
    period: str = "week"  # day, week, month
    category: Optional[str] = None


class InsightResponse(BaseModel):
    """인사이트 응답 모델"""
    period: str
    summary: str
    statistics: Dict
    predictions: Dict
    clusters: List[Dict]
    ai_report: str = ""
    data_source: str = "memory"   # "db" | "memory"
    preferences: Dict = {}        # BTI분포/축평균/음식·향·과일 빈도 (추가 인사이트)


class PostTrendItem(BaseModel):
    """양조장 게시물 트렌드 입력 항목"""
    keyword: str = ""
    post_count: int = Field(0, ge=0)
    likes: int = Field(0, ge=0)
    comments: int = Field(0, ge=0)
    views: int = Field(0, ge=0)


class FundingSuccessItem(BaseModel):
    """양조장 펀딩 성과 입력 항목"""
    name: str = ""
    achieved_pct: float = Field(0, ge=0)
    status: str = ""
    ingredients: List[str] = Field(default_factory=list)
    taste_vector: Dict[str, float] = Field(default_factory=dict)


class BTIKeywordItem(BaseModel):
    """술BTI 유형별 관심 키워드 입력 항목"""
    bti_code: str = ""
    user_count: int = Field(0, ge=0)
    top_keywords: List[str] = Field(default_factory=list)


class BreweryInsightRequest(BaseModel):
    """백엔드 양조장 인사이트 요청 모델"""
    brewery_id: str
    period: str = "month"
    post_trends: List[PostTrendItem] = Field(default_factory=list)
    funding_success: List[FundingSuccessItem] = Field(default_factory=list)
    bti_keywords: List[BTIKeywordItem] = Field(default_factory=list)


class BreweryInsightResponse(BaseModel):
    """백엔드 양조장 인사이트 응답 모델"""
    summary: str
    recommendation: str
    trend_analysis: List[str] = Field(default_factory=list)
    funding_analysis: List[str] = Field(default_factory=list)
    bti_analysis: List[str] = Field(default_factory=list)


class InsightDashboard:
    """인사이트 대시보드 시스템"""

    def __init__(self, data_file: str = "data/processed/makgeolli_with_vectors.json"):
        self.data_file = Path(data_file)
        self.drinks: List[Dict] = []
        self.load_data()

        # 인메모리 fallback용 샘플 데이터
        self.user_data: List[Dict] = self._generate_sample_user_data()

        # 추가 인사이트(선호 분포)용 샘플 프로필 — DB 없이도 데모 가능
        self.sample_profiles: List[Dict] = self._generate_sample_profiles()

        # DB / fundings 참조 — startup_event 에서 set_db() 로 주입
        self.db: Any = None
        self._fundings: Dict[str, Dict] = {}

    # ------------------------------------------------------------------
    # 초기화 헬퍼
    # ------------------------------------------------------------------

    def set_db(self, db: Any, fundings: Dict[str, Dict] = None) -> None:
        """
        DB 인스턴스 및 펀딩 저장소 주입.
        startup_event 에서 반드시 호출해야 DB 경로가 활성화된다.
        fundings 는 main.py 의 _fundings dict 를 참조로 넘기면
        이후 등록·수정이 자동으로 반영된다.
        """
        self.db = db
        if fundings is not None:
            self._fundings = fundings
        logger.info(
            "InsightDashboard DB 주입 완료 — "
            f"db_connected={db.db_connected if db else False}, "
            f"fundings={len(self._fundings)}개"
        )

    def load_data(self) -> None:
        """JSON 데이터 로드 (인메모리 fallback 용)"""
        if self.data_file.exists():
            with open(self.data_file, "r", encoding="utf-8") as f:
                self.drinks = json.load(f)
            logger.info(f"데이터 로드 완료: {len(self.drinks)}개")
        else:
            logger.warning(f"데이터 파일 없음: {self.data_file}")

    def _generate_sample_user_data(self) -> List[Dict]:
        """인메모리 fallback 용 샘플 사용자 데이터 생성"""
        base_date = datetime.now() - timedelta(days=30)
        data: List[Dict] = []
        for i in range(100):
            user_id = f"user_{i}"
            for day in range(30):
                date = base_date + timedelta(days=day)
                if self.drinks:
                    drink = self.drinks[i % len(self.drinks)]
                    data.append(
                        {
                            "user_id": user_id,
                            "drink_id": drink["id"],
                            "drink_name": drink["name"],
                            "rating": (i % 5) + 1,
                            "date": date.strftime("%Y-%m-%d"),
                            "taste_vector": drink["taste_vector"],
                        }
                    )
        return data

    def _generate_sample_profiles(self) -> List[Dict]:
        """선호 분포 인사이트용 샘플 사용자 프로필 (DB 없을 때 fallback, 결정적)."""
        import random
        rng = random.Random(42)
        fruits = ["감귤류", "베리류", "사과", "포도", "망고"]
        foods = ["고기", "해산물", "매운음식", "디저트", "치즈"]
        aromas = ["과일향", "감귤향", "꽃향", "허브향", "쌀향"]
        profiles: List[Dict] = []
        for _ in range(120):
            sd, hl, fm, uc = rng.choice("SD"), rng.choice("HL"), rng.choice("FM"), rng.choice("UC")
            ah = rng.choice("HL")
            bti = f"{sd}{hl}{fm}{uc}{ah}"
            tv = {
                "sweetness": 7.0 if sd == "S" else 3.0, "body": 7.0 if hl == "H" else 3.0,
                "carbonation": 7.0 if fm == "F" else 3.0, "flavor": 7.0 if uc == "U" else 3.0,
                "alcohol": 8.0 if ah == "H" else 4.0, "acidity": rng.uniform(3, 7),
                "aroma_intensity": rng.uniform(3, 7), "finish": rng.uniform(3, 7),
            }
            tv = {k: round(v + rng.uniform(-0.8, 0.8), 2) for k, v in tv.items()}
            profiles.append({
                "bti_code": bti,
                "preferred_fruit": rng.choice(fruits),
                "preferred_food_pairing": rng.sample(foods, rng.randint(1, 3)),
                "preferred_aroma": rng.sample(aromas, rng.randint(1, 2)),
                "taste_vector": tv,
            })
        return profiles

    @staticmethod
    def _aggregate_preferences(profiles: List[Dict], data_source: str) -> Dict:
        """프로필 리스트 → 선호 분포 인사이트 집계 (DB/메모리 공용)."""
        axes = ["sweetness", "body", "carbonation", "flavor",
                "alcohol", "acidity", "aroma_intensity", "finish"]
        bti4 = defaultdict(int)
        bti5 = defaultdict(int)
        fruit = defaultdict(int)
        food = defaultdict(int)
        aroma = defaultdict(int)
        axis_sum = {a: 0.0 for a in axes}
        axis_n = 0

        for p in profiles:
            code = (p.get("bti_code") or "").strip()
            if code:
                bti5[code] += 1
                bti4[code[:4]] += 1
            fr = (p.get("preferred_fruit") or "").strip()
            if fr:
                fruit[fr] += 1
            for f in (p.get("preferred_food_pairing") or []):
                if f:
                    food[f] += 1
            for a in (p.get("preferred_aroma") or []):
                if a:
                    aroma[a] += 1
            tv = p.get("taste_vector") or {}
            if isinstance(tv, dict) and tv:
                for a in axes:
                    axis_sum[a] += float(tv.get(a, 0.0) or 0.0)
                axis_n += 1

        def _top(d, k=None):
            items = sorted(d.items(), key=lambda x: x[1], reverse=True)
            return [{"key": kk, "count": vv} for kk, vv in (items[:k] if k else items)]

        return {
            "profile_count": len(profiles),
            "bti4_distribution": _top(bti4),
            "bti5_distribution": _top(bti5),
            "axis_preference_avg": (
                {a: round(axis_sum[a] / axis_n, 2) for a in axes} if axis_n else {}
            ),
            "food_pairing_top": _top(food, 5),
            "aroma_distribution": _top(aroma),
            "fruit_distribution": _top(fruit),
            "data_source": data_source,
        }

    async def preference_breakdown(self) -> Dict:
        """선호 분포 인사이트. DB 연결 시 user_profiles, 아니면 샘플 프로필."""
        if self.db and self.db.db_connected:
            try:
                rows = await self.db.fetch(
                    """
                    SELECT bti_code, preferred_fruit, preferred_food_pairing,
                           preferred_aroma, taste_vector
                    FROM user_profiles
                    """
                )
                if rows:
                    profiles = []
                    for r in rows:
                        profiles.append({
                            "bti_code": r.get("bti_code") or "",
                            "preferred_fruit": r.get("preferred_fruit") or "",
                            "preferred_food_pairing": _as_list(r.get("preferred_food_pairing")),
                            "preferred_aroma": _as_list(r.get("preferred_aroma")),
                            "taste_vector": _as_dict(r.get("taste_vector")),
                        })
                    return self._aggregate_preferences(profiles, "db")
                logger.info("user_profiles 비어있음 → 선호분포 샘플 fallback")
            except Exception as e:
                logger.warning(f"DB 선호분포 조회 실패, 샘플 fallback: {e}")
        return self._aggregate_preferences(self.sample_profiles, "memory")

    # ==================================================================
    # 통계 집계
    # ==================================================================

    async def aggregate_statistics(self, period: str = "week") -> Dict:
        """
        통계 집계
        - DB 연결 시 : user_taste_history + drinks 테이블
        - DB 없을 시 : 인메모리 샘플 데이터 fallback
        """
        if self.db and self.db.db_connected:
            try:
                return await self._aggregate_from_db(period)
            except Exception as e:
                logger.warning(f"DB 통계 조회 실패, 인메모리 fallback: {e}")
        return self._aggregate_from_memory(period)

    async def _aggregate_from_db(self, period: str) -> Dict:
        """DB의 user_taste_history 테이블에서 기간별 통계 집계"""
        period_map = {"day": timedelta(days=1), "week": timedelta(days=7), "month": timedelta(days=30)}
        cutoff = datetime.now() - period_map.get(period, timedelta(days=7))

        rows = await self.db.fetch(
            """
            SELECT
                uth.user_id,
                uth.drink_id,
                COALESCE(d.name, uth.drink_id) AS drink_name,
                uth.rating,
                uth.created_at,
                uth.taste_vector
            FROM user_taste_history uth
            LEFT JOIN drinks d ON uth.drink_id = d.id
            WHERE uth.created_at >= $1
            ORDER BY uth.created_at DESC
            """,
            cutoff,
        )

        if not rows:
            return {
                "total_reviews": 0,
                "avg_rating": 0.0,
                "top_drinks": [],
                "taste_distribution": {},
                "funding_top": self._get_funding_stats(),
                "data_source": "db",
            }

        taste_axes = ["sweetness", "body", "carbonation", "flavor",
                      "alcohol", "acidity", "aroma_intensity", "finish"]
        total_reviews = len(rows)
        rated = [r for r in rows if r.get("rating")]
        avg_rating = round(sum(r["rating"] for r in rated) / len(rated), 2) if rated else 0.0

        drink_counts: Dict[str, int] = defaultdict(int)
        drink_ratings: Dict[str, list] = defaultdict(list)
        taste_sum = {axis: 0.0 for axis in taste_axes}
        taste_count = 0

        for r in rows:
            name = r.get("drink_name") or r.get("drink_id") or "알 수 없음"
            drink_counts[name] += 1
            if r.get("rating"):
                drink_ratings[name].append(r["rating"])

            tv = r.get("taste_vector")
            if tv:
                if isinstance(tv, str):
                    tv = json.loads(tv)
                if isinstance(tv, dict):
                    for axis in taste_axes:
                        taste_sum[axis] += tv.get(axis, 0.0)
                    taste_count += 1

        top_drinks = sorted(drink_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_drinks_with_rating = [
            {
                "name": name,
                "count": count,
                "avg_rating": round(
                    sum(drink_ratings[name]) / len(drink_ratings[name]), 2
                ) if drink_ratings[name] else 0.0,
            }
            for name, count in top_drinks
        ]
        taste_distribution = (
            {axis: round(taste_sum[axis] / taste_count, 2) for axis in taste_axes}
            if taste_count > 0 else {}
        )

        return {
            "total_reviews": total_reviews,
            "avg_rating": avg_rating,
            "top_drinks": top_drinks_with_rating,
            "taste_distribution": taste_distribution,
            "funding_top": self._get_funding_stats(),
            "data_source": "db",
        }

    def _aggregate_from_memory(self, period: str) -> Dict:
        """인메모리 샘플 데이터에서 집계 (DB 없을 때 fallback)"""
        now = datetime.now()
        if period == "day":
            start_date = now - timedelta(days=1)
        elif period == "week":
            start_date = now - timedelta(weeks=1)
        else:
            start_date = now - timedelta(days=30)

        period_data = [
            d for d in self.user_data
            if datetime.strptime(d["date"], "%Y-%m-%d") >= start_date
        ]

        if not period_data:
            return {
                "total_reviews": 0,
                "avg_rating": 0.0,
                "top_drinks": [],
                "taste_distribution": {},
                "funding_top": self._get_funding_stats(),
                "data_source": "memory",
            }

        total_reviews = len(period_data)
        avg_rating = sum(d["rating"] for d in period_data) / total_reviews

        drink_counts: Dict[str, int] = defaultdict(int)
        drink_ratings: Dict[str, list] = defaultdict(list)
        for d in period_data:
            drink_counts[d["drink_name"]] += 1
            drink_ratings[d["drink_name"]].append(d["rating"])

        top_drinks = sorted(drink_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_drinks_with_rating = [
            {
                "name": name,
                "count": count,
                "avg_rating": round(
                    sum(drink_ratings[name]) / len(drink_ratings[name]), 2
                ),
            }
            for name, count in top_drinks
        ]

        taste_distribution = {
            "sweetness": 0.0, "body": 0.0, "carbonation": 0.0, "flavor": 0.0,
            "alcohol": 0.0, "acidity": 0.0, "aroma_intensity": 0.0, "finish": 0.0,
        }
        for d in period_data:
            for axis in taste_distribution:
                taste_distribution[axis] += d["taste_vector"].get(axis, 0.0)
        for axis in taste_distribution:
            taste_distribution[axis] = round(taste_distribution[axis] / total_reviews, 2)

        return {
            "total_reviews": total_reviews,
            "avg_rating": round(avg_rating, 2),
            "top_drinks": top_drinks_with_rating,
            "taste_distribution": taste_distribution,
            "funding_top": self._get_funding_stats(),
            "data_source": "memory",
        }

    # ==================================================================
    # 펀딩 통계
    # ==================================================================

    def _get_funding_stats(self) -> List[Dict]:
        """
        _fundings 인메모리에서 등록된 펀딩 전통주 목록 반환 (최신 10개).
        등록 빈도 대용으로 최근 등록 순 정렬 사용.
        """
        if not self._fundings:
            return []
        items = [
            {
                "funding_id": fid,
                "name": info.get("name", ""),
                "brewery": info.get("brewery", ""),
                "region": info.get("region", ""),
                "registered_at": info.get("registered_at", ""),
            }
            for fid, info in self._fundings.items()
        ]
        items.sort(key=lambda x: x.get("registered_at", ""), reverse=True)
        return items[:10]

    # ==================================================================
    # 트렌드 예측 (지수평활법 — 인메모리 기반 유지)
    # ==================================================================

    def predict_trends(self, period: str = "week") -> Dict:
        """트렌드 예측 (지수평활법 기반)"""
        alpha = 0.3
        daily_counts: Dict[str, int] = defaultdict(int)
        for d in self.user_data:
            daily_counts[d["date"]] += 1

        sorted_dates = sorted(daily_counts.keys())
        counts = [daily_counts[date] for date in sorted_dates]

        if len(counts) < 2:
            return {"trend": "stable", "predicted_growth": 0.0, "next_period_prediction": 0}

        smoothed = counts[0]
        for count in counts[1:]:
            smoothed = alpha * count + (1 - alpha) * smoothed

        if smoothed > counts[-1] * 1.1:
            trend = "increasing"
        elif smoothed < counts[-1] * 0.9:
            trend = "decreasing"
        else:
            trend = "stable"

        growth_rate = (counts[-1] - counts[0]) / counts[0] * 100

        return {
            "trend": trend,
            "predicted_growth": round(growth_rate, 2),
            "next_period_prediction": round(smoothed),
            "current_average": round(sum(counts[-7:]) / min(7, len(counts))),
        }

    # ==================================================================
    # 사용자 군집화 — BTI 분포
    # ==================================================================

    async def cluster_users(self, n_clusters: int = 5) -> List[Dict]:
        """
        사용자 군집화
        - DB 연결 시 : user_profiles 테이블의 bti_code 분포
        - DB 없을 시 : 인메모리 맛벡터 k-means fallback
        """
        if self.db and self.db.db_connected:
            try:
                return await self._cluster_from_db()
            except Exception as e:
                logger.warning(f"DB 군집화 조회 실패, 인메모리 fallback: {e}")
        return self._cluster_from_memory(n_clusters)

    async def _cluster_from_db(self) -> List[Dict]:
        """user_profiles.bti_code 기반 BTI 분포 계산"""
        rows = await self.db.fetch(
            """
            SELECT bti_code, COUNT(*) AS count
            FROM user_profiles
            WHERE bti_code IS NOT NULL AND bti_code != ''
            GROUP BY bti_code
            ORDER BY count DESC
            """
        )

        if not rows:
            logger.info("user_profiles BTI 데이터 없음 → 인메모리 fallback")
            return self._cluster_from_memory()

        total = sum(r["count"] for r in rows)

        # BTI 코드 첫 두 글자 (S/D × H/L) 기준 클러스터 분류
        CLUSTER_DEFS = [
            ("단맛+묵직형",    "달콤하고 바디감 있는 전통주 선호",    lambda c: len(c) >= 2 and c[0] == "S" and c[1] == "H"),
            ("단맛+가벼운형",  "달콤하면서 가벼운 전통주 선호",       lambda c: len(c) >= 2 and c[0] == "S" and c[1] == "L"),
            ("드라이+묵직형",  "드라이하고 바디감 있는 전통주 선호",  lambda c: len(c) >= 2 and c[0] == "D" and c[1] == "H"),
            ("드라이+가벼운형","드라이하면서 가벼운 전통주 선호",     lambda c: len(c) >= 2 and c[0] == "D" and c[1] == "L"),
            ("기타",           "기타 BTI 유형",                        lambda c: True),
        ]

        cluster_counts_map: Dict[str, int] = {name: 0 for name, _, _ in CLUSTER_DEFS}
        for row in rows:
            code = row["bti_code"] or ""
            cnt = row["count"]
            for name, _, check in CLUSTER_DEFS:
                if check(code):
                    cluster_counts_map[name] += cnt
                    break

        clusters = []
        for i, (name, desc, _) in enumerate(CLUSTER_DEFS):
            cnt = cluster_counts_map[name]
            clusters.append(
                {
                    "cluster_id": i,
                    "name": name,
                    "description": desc,
                    "user_count": cnt,
                    "percentage": round(cnt / total * 100, 2) if total > 0 else 0.0,
                    "data_source": "db",
                }
            )
        return clusters

    def _cluster_from_memory(self, n_clusters: int = 5) -> List[Dict]:
        """인메모리 맛벡터 기반 k-means 군집화 (기존 로직)"""
        taste_axes = ["sweetness", "body", "carbonation", "flavor",
                      "alcohol", "acidity", "aroma_intensity", "finish"]

        user_taste_vectors: Dict[str, Dict] = defaultdict(lambda: {a: 0.0 for a in taste_axes})
        user_counts: Dict[str, int] = defaultdict(int)

        for d in self.user_data:
            uid = d["user_id"]
            for axis in taste_axes:
                user_taste_vectors[uid][axis] += d["taste_vector"].get(axis, 0.0)
            user_counts[uid] += 1

        for uid in user_taste_vectors:
            cnt = user_counts[uid]
            for axis in taste_axes:
                user_taste_vectors[uid][axis] /= cnt

        cluster_centers = [
            {"sweetness": 8.0, "body": 5.0, "carbonation": 5.0, "flavor": 6.0,
             "alcohol": 5.0, "acidity": 4.0, "aroma_intensity": 5.0, "finish": 5.0},
            {"sweetness": 4.0, "body": 5.0, "carbonation": 6.0, "flavor": 5.0,
             "alcohol": 5.0, "acidity": 8.0, "aroma_intensity": 5.0, "finish": 5.0},
            {"sweetness": 5.0, "body": 8.0, "carbonation": 4.0, "flavor": 6.0,
             "alcohol": 6.0, "acidity": 5.0, "aroma_intensity": 5.0, "finish": 6.0},
            {"sweetness": 5.0, "body": 4.0, "carbonation": 8.0, "flavor": 5.0,
             "alcohol": 5.0, "acidity": 6.0, "aroma_intensity": 5.0, "finish": 5.0},
            {"sweetness": 5.0, "body": 5.0, "carbonation": 5.0, "flavor": 5.0,
             "alcohol": 5.0, "acidity": 5.0, "aroma_intensity": 5.0, "finish": 5.0},
        ]
        cluster_names = ["단맛 선호형", "산미 선호형", "바디감 선호형", "탄산 선호형", "밸런스형"]
        cluster_descriptions = [
            "달콤한 맛을 선호하는 사용자 그룹",
            "새콤한 산미를 선호하는 사용자 그룹",
            "묵직한 바디감을 선호하는 사용자 그룹",
            "청량한 탄산감을 선호하는 사용자 그룹",
            "균형 잡힌 맛을 선호하는 사용자 그룹",
        ]

        cluster_assign: Dict[int, list] = defaultdict(list)
        cluster_cnt_m: Dict[int, int] = defaultdict(int)

        for uid, vector in user_taste_vectors.items():
            min_dist = float("inf")
            best = 0
            for i, center in enumerate(cluster_centers):
                dist = sum((vector[a] - center[a]) ** 2 for a in taste_axes) ** 0.5
                if dist < min_dist:
                    min_dist = dist
                    best = i
            cluster_assign[best].append(uid)
            cluster_cnt_m[best] += 1

        clusters = []
        for i in range(n_clusters):
            clusters.append(
                {
                    "cluster_id": i,
                    "name": cluster_names[i],
                    "description": cluster_descriptions[i],
                    "user_count": cluster_cnt_m[i],
                    "percentage": round(
                        cluster_cnt_m[i] / len(user_taste_vectors) * 100, 2
                    ) if user_taste_vectors else 0,
                    "taste_profile": cluster_centers[i],
                    "data_source": "memory",
                }
            )
        return clusters

    @staticmethod
    def empty_brewery_insight() -> BreweryInsightResponse:
        """분석 데이터가 없거나 처리에 실패했을 때 반환할 기본 응답"""
        return BreweryInsightResponse(
            summary="현재 기간에는 분석할 데이터가 충분하지 않습니다.",
            recommendation="게시물, 펀딩, 술BTI 데이터가 더 쌓이면 더 정확한 인사이트를 제공할 수 있습니다.",
            trend_analysis=[],
            funding_analysis=[],
            bti_analysis=[],
        )

    @staticmethod
    def _engagement_score(item: PostTrendItem) -> int:
        return (
            item.views
            + item.likes * 5
            + item.comments * 10
            + item.post_count * 20
        )

    def _build_brewery_insight_fallback(
        self,
        request: BreweryInsightRequest,
    ) -> BreweryInsightResponse:
        """입력 데이터만으로 항상 생성 가능한 규칙 기반 인사이트"""
        if not request.post_trends and not request.funding_success and not request.bti_keywords:
            return self.empty_brewery_insight()

        trend_items = sorted(
            request.post_trends,
            key=self._engagement_score,
            reverse=True,
        )
        funding_items = sorted(
            request.funding_success,
            key=lambda item: item.achieved_pct,
            reverse=True,
        )
        bti_items = sorted(
            request.bti_keywords,
            key=lambda item: item.user_count,
            reverse=True,
        )

        trend_analysis = [
            (
                f"{item.keyword} 키워드는 게시물 {item.post_count}건에서 "
                f"조회수 {item.views:,}회, 좋아요 {item.likes:,}개, "
                f"댓글 {item.comments:,}개를 기록했습니다."
            )
            for item in trend_items[:3]
            if item.keyword
        ]

        taste_labels = {
            "sweetness": "단맛",
            "body": "바디감",
            "carbonation": "탄산감",
            "flavor": "풍미",
            "alcohol": "도수감",
            "acidity": "산미",
            "aroma_intensity": "향의 강도",
            "finish": "여운",
        }
        funding_analysis = []
        for item in funding_items[:3]:
            if not item.name:
                continue
            ingredients = "·".join(item.ingredients[:3])
            top_tastes = sorted(
                item.taste_vector.items(),
                key=lambda pair: pair[1],
                reverse=True,
            )[:2]
            taste_text = "·".join(
                taste_labels.get(axis, axis) for axis, _ in top_tastes
            )
            details = []
            if ingredients:
                details.append(f"주요 재료는 {ingredients}")
            if taste_text:
                details.append(f"강한 맛 특성은 {taste_text}")
            detail_text = f", {', '.join(details)}입니다" if details else ""
            funding_analysis.append(
                f"{item.name} 펀딩은 목표 대비 {item.achieved_pct:g}%를 달성했고"
                f"{detail_text}."
            )

        bti_analysis = []
        for item in bti_items[:3]:
            if not item.bti_code:
                continue
            keywords = "·".join(item.top_keywords[:3]) or "집계된 키워드 없음"
            bti_analysis.append(
                f"{item.bti_code} 유형 사용자 {item.user_count}명의 주요 관심 키워드는 "
                f"{keywords}입니다."
            )

        signals = []
        if trend_items and trend_items[0].keyword:
            signals.append(f"{trend_items[0].keyword} 콘텐츠")
        if funding_items and funding_items[0].name:
            signals.append(f"{funding_items[0].name} 펀딩")
        if bti_items and bti_items[0].bti_code:
            signals.append(f"{bti_items[0].bti_code} 취향군")

        if signals:
            summary = f"{'·'.join(signals)}에서 유의미한 관심 신호가 확인됩니다."
        else:
            summary = "현재 입력 데이터에서 뚜렷한 관심 키워드를 확인하기 어렵습니다."

        target = bti_items[0].bti_code if bti_items and bti_items[0].bti_code else "관심 고객"
        features = []
        if bti_items:
            features.extend(bti_items[0].top_keywords)
        if funding_items:
            features.extend(funding_items[0].ingredients)
        if not features and trend_items and trend_items[0].keyword:
            features.append(trend_items[0].keyword)
        unique_features = list(dict.fromkeys(feature for feature in features if feature))[:3]

        if unique_features:
            recommendation = (
                f"{target} 유형을 타깃으로 {'·'.join(unique_features)} 특성을 반영한 "
                "제품과 콘텐츠를 기획하는 것을 추천합니다."
            )
        else:
            recommendation = "반응 데이터가 더 쌓일 때까지 콘텐츠와 펀딩 성과를 지속적으로 관찰하는 것을 추천합니다."

        return BreweryInsightResponse(
            summary=summary,
            recommendation=recommendation,
            trend_analysis=trend_analysis,
            funding_analysis=funding_analysis,
            bti_analysis=bti_analysis,
        )

    async def _generate_brewery_ai_narrative(
        self,
        request: BreweryInsightRequest,
        fallback: BreweryInsightResponse,
    ) -> Dict[str, str]:
        """Gemini로 요약 문장을 보강하고 실패 시 빈 업데이트를 반환"""
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            return {}

        try:
            import google.generativeai as genai

            genai.configure(api_key=gemini_api_key)
            model = genai.GenerativeModel("gemini-2.5-flash-lite")
            prompt = f"""
전통주 양조장 운영 데이터를 분석해 한국어 인사이트를 작성해줘.
입력에 없는 사실은 추정하지 말고, 자동 의사결정이 아닌 운영 참고용으로 작성해.

요청 데이터:
{json.dumps(request.model_dump(), ensure_ascii=False)}

규칙 기반 분석:
{json.dumps(fallback.model_dump(), ensure_ascii=False)}

다음 JSON 형식만 반환해.
{{
  "summary": "데이터에서 확인되는 핵심 흐름 한 문장",
  "recommendation": "실행 가능한 기획 제안 한 문장"
}}
"""
            response = await model.generate_content_async(
                prompt,
                generation_config={"max_output_tokens": 400},
            )
            response_text = (getattr(response, "text", "") or "").strip()
            json_start = response_text.find("{")
            json_end = response_text.rfind("}")
            if json_start < 0 or json_end <= json_start:
                return {}

            parsed = json.loads(response_text[json_start:json_end + 1])
            if not isinstance(parsed, dict):
                return {}

            updates = {}
            for key in ("summary", "recommendation"):
                value = parsed.get(key)
                if isinstance(value, str) and value.strip():
                    updates[key] = value.strip()
            return updates
        except Exception:
            logger.exception("Brewery insight Gemini generation failed")
            return {}

    async def generate_brewery_insights(
        self,
        request: BreweryInsightRequest,
    ) -> BreweryInsightResponse:
        """백엔드 집계 데이터를 기반으로 양조장 인사이트를 생성"""
        fallback = self._build_brewery_insight_fallback(request)
        if not request.post_trends and not request.funding_success and not request.bti_keywords:
            return fallback

        narrative_updates = await self._generate_brewery_ai_narrative(
            request,
            fallback,
        )
        return fallback.model_copy(update=narrative_updates)

    # ==================================================================
    # AI 리포트
    # ==================================================================

    async def _generate_ai_report(
        self, statistics: Dict, predictions: Dict, clusters: List[Dict]
    ) -> str:
        """Gemini를 사용해 양조장용 자연어 인사이트 리포트 생성 (3~5문장)"""
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            return "GEMINI_API_KEY가 설정되지 않아 AI 리포트를 생성할 수 없습니다."

        try:
            import google.generativeai as genai

            genai.configure(api_key=gemini_api_key)
            model = genai.GenerativeModel("gemini-2.5-flash-lite")

            top_drinks = statistics.get("top_drinks", [])[:3]
            taste_dist = statistics.get("taste_distribution", {})
            trend = predictions.get("trend", "stable")
            growth = predictions.get("predicted_growth", 0.0)
            largest_cluster = max(clusters, key=lambda x: x["user_count"]) if clusters else {}
            data_src = statistics.get("data_source", "memory")

            top_drinks_str = (
                ", ".join([f"{d['name']}({d['count']}회)" for d in top_drinks])
                if top_drinks else "없음"
            )
            taste_summary = ", ".join(
                [f"{k}:{v:.1f}" for k, v in list(taste_dist.items())[:4]]
            )
            cluster_name = largest_cluster.get("name", "알 수 없음")
            cluster_pct = largest_cluster.get("percentage", 0)

            prompt = f"""당신은 전통주 양조장 컨설턴트입니다. 다음 플랫폼 데이터를 바탕으로 양조장 운영자를 위한 인사이트 리포트를 3~5문장으로 작성해주세요. 한국어로, 실용적인 비즈니스 조언 위주로 작성하세요.

[플랫폼 데이터 (출처: {data_src})]
- 인기 전통주: {top_drinks_str}
- 맛 분포 (평균): {taste_summary}
- 트렌드: {trend} (성장률 {growth:.1f}%)
- 주요 고객 취향: {cluster_name} ({cluster_pct:.1f}%)

리포트:"""

            response = await model.generate_content_async(prompt)
            return response.text.strip()

        except Exception as e:
            logger.error(f"AI 리포트 생성 실패: {e}")
            s = str(e)
            if "429" in s or "quota exceeded" in s.lower() or "resource_exhausted" in s.lower():
                return "현재 AI 서비스가 일시적으로 혼잡합니다. 잠시 후 다시 시도해주세요."
            return "AI 서비스에 연결할 수 없습니다. 잠시 후 다시 시도해주세요."

    # ==================================================================
    # 메인 인사이트
    # ==================================================================

    async def get_insights(self, period: str = "week") -> InsightResponse:
        """
        인사이트 대시보드 메인 함수.
        DB 연결 여부에 따라 실제 데이터 또는 인메모리 데이터 사용.
        """
        # 통계 집계 (async — DB 또는 메모리)
        statistics = await self.aggregate_statistics(period)

        # 트렌드 예측 (sync — 인메모리 기반)
        predictions = self.predict_trends(period)

        # 군집화 (async — DB BTI 분포 또는 메모리 k-means)
        clusters = await self.cluster_users()

        # 선호 분포 인사이트 (BTI4/5·축평균·음식·향·과일)
        preferences = await self.preference_breakdown()

        # 요약 생성
        summary = self._generate_summary(statistics, predictions, clusters)

        # Gemini AI 리포트
        ai_report = await self._generate_ai_report(statistics, predictions, clusters)

        return InsightResponse(
            period=period,
            summary=summary,
            statistics=statistics,
            predictions=predictions,
            clusters=clusters,
            ai_report=ai_report,
            data_source=statistics.get("data_source", "memory"),
            preferences=preferences,
        )

    def _generate_summary(
        self, statistics: Dict, predictions: Dict, clusters: List[Dict]
    ) -> str:
        """인사이트 요약 생성"""
        total_reviews = statistics.get("total_reviews", 0)
        avg_rating = statistics.get("avg_rating", 0.0)
        trend = predictions.get("trend", "stable")
        growth = predictions.get("predicted_growth", 0.0)
        data_src = statistics.get("data_source", "memory")
        src_label = "(실제 DB)" if data_src == "db" else "(샘플 데이터)"

        largest_cluster = (
            max(clusters, key=lambda x: x["user_count"]) if clusters else None
        )

        parts = []
        if total_reviews > 0:
            parts.append(
                f"최근 {total_reviews}건의 리뷰{src_label}가 있으며, "
                f"평균 평점은 {avg_rating}점입니다."
            )

        if trend == "increasing":
            parts.append(f"리뷰 수가 {growth:.1f}% 증가하는 추세입니다.")
        elif trend == "decreasing":
            parts.append(f"리뷰 수가 {abs(growth):.1f}% 감소하는 추세입니다.")
        else:
            parts.append("리뷰 수가 안정적인 추세입니다.")

        if largest_cluster:
            parts.append(
                f"가장 많은 사용자({largest_cluster['percentage']}%)는 "
                f"'{largest_cluster['name']}' 취향을 가지고 있습니다."
            )

        return " ".join(parts)


def main():
    """메인 실행 함수 (단독 테스트용)"""
    import asyncio

    async def _run():
        dashboard = InsightDashboard()
        print("=== 인사이트 대시보드 테스트 ===\n")

        print("--- 주간 인사이트 ---")
        insights = await dashboard.get_insights(period="week")
        print(f"요약: {insights.summary}")
        print(f"데이터 소스: {insights.data_source}")
        print(f"총 리뷰 수: {insights.statistics['total_reviews']}")
        print(f"평균 평점: {insights.statistics['avg_rating']}")
        print("상위 전통주:")
        for drink in insights.statistics.get("top_drinks", [])[:3]:
            print(f"  - {drink['name']}: {drink['count']}회 (평점 {drink['avg_rating']})")
        print("\n예측:")
        print(f"  트렌드: {insights.predictions['trend']}")
        print(f"  예상 성장률: {insights.predictions['predicted_growth']}%")
        print(f"  다음 기간 예측: {insights.predictions['next_period_prediction']}건")
        print("\n군집화:")
        for cluster in insights.clusters:
            print(f"  {cluster['name']}: {cluster['user_count']}명 ({cluster['percentage']}%)")
        print(f"\nAI 리포트:\n{insights.ai_report}")

        print("\n--- 월간 인사이트 ---")
        insights_m = await dashboard.get_insights(period="month")
        print(f"요약: {insights_m.summary}")
        print(f"총 리뷰 수: {insights_m.statistics['total_reviews']}")
        print(f"평균 평점: {insights_m.statistics['avg_rating']}")

    asyncio.run(_run())


if __name__ == "__main__":
    main()
