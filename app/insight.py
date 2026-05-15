"""
인사이트 대시보드 모듈
집계 + 예측 + 군집화를 통한 AI 인사이트 제공
"""

import logging
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from pydantic import BaseModel
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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


class InsightDashboard:
    """인사이트 대시보드 시스템"""

    def __init__(self, data_file: str = "data/processed/makgeolli_with_vectors.json"):
        self.data_file = Path(data_file)
        self.drinks = []
        self.load_data()

        # 사용자 데이터 (시뮬레이션)
        self.user_data = self._generate_sample_user_data()

    def load_data(self):
        """데이터 로드"""
        if self.data_file.exists():
            with open(self.data_file, 'r', encoding='utf-8') as f:
                self.drinks = json.load(f)
            logger.info(f"데이터 로드 완료: {len(self.drinks)}개")
        else:
            logger.warning(f"데이터 파일 없음: {self.data_file}")

    def _generate_sample_user_data(self) -> List[Dict]:
        """샘플 사용자 데이터 생성"""
        base_date = datetime.now() - timedelta(days=30)

        data = []
        for i in range(100):
            user_id = f"user_{i}"
            for day in range(30):
                date = base_date + timedelta(days=day)
                # 랜덤으로 막걸리 선택
                if self.drinks:
                    drink = self.drinks[i % len(self.drinks)]
                    data.append({
                        "user_id": user_id,
                        "drink_id": drink['id'],
                        "drink_name": drink['name'],
                        "rating": (i % 5) + 1,
                        "date": date.strftime("%Y-%m-%d"),
                        "taste_vector": drink['taste_vector']
                    })

        return data

    def aggregate_statistics(self, period: str = "week") -> Dict:
        """
        통계 집계 (현재 데이터 기반)

        Args:
            period: 기간 (day, week, month)

        Returns:
            집계된 통계
        """
        # 기간별 날짜 계산
        now = datetime.now()
        if period == "day":
            start_date = now - timedelta(days=1)
        elif period == "week":
            start_date = now - timedelta(weeks=1)
        else:  # month
            start_date = now - timedelta(days=30)

        # 기간 내 데이터 필터링
        period_data = [
            d for d in self.user_data
            if datetime.strptime(d['date'], "%Y-%m-%d") >= start_date
        ]

        if not period_data:
            return {
                "total_reviews": 0,
                "avg_rating": 0.0,
                "top_drinks": [],
                "taste_distribution": {}
            }

        # 기본 통계
        total_reviews = len(period_data)
        avg_rating = sum(d['rating'] for d in period_data) / total_reviews

        # 상위 막걸리
        drink_counts = defaultdict(int)
        drink_ratings = defaultdict(list)

        for d in period_data:
            drink_counts[d['drink_name']] += 1
            drink_ratings[d['drink_name']].append(d['rating'])

        top_drinks = sorted(
            drink_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        top_drinks_with_rating = [
            {
                "name": name,
                "count": count,
                "avg_rating": sum(drink_ratings[name]) / len(drink_ratings[name])
            }
            for name, count in top_drinks
        ]

        # 맛 분포
        taste_distribution = {
            'sweetness': 0.0,
            'body': 0.0,
            'carbonation': 0.0,
            'flavor': 0.0,
            'alcohol': 0.0,
            'acidity': 0.0,
            'aroma_intensity': 0.0,
            'finish': 0.0
        }

        for d in period_data:
            for axis in taste_distribution.keys():
                taste_distribution[axis] += d['taste_vector'].get(axis, 0.0)

        for axis in taste_distribution.keys():
            taste_distribution[axis] = round(taste_distribution[axis] / total_reviews, 2)

        return {
            "total_reviews": total_reviews,
            "avg_rating": round(avg_rating, 2),
            "top_drinks": top_drinks_with_rating,
            "taste_distribution": taste_distribution
        }

    def predict_trends(self, period: str = "week") -> Dict:
        """
        트렌드 예측 (지수평활법 기반)

        Args:
            period: 기간 (day, week, month)

        Returns:
            예측된 트렌드
        """
        # 간단한 지수평활법 구현
        alpha = 0.3  # 평활 계수

        # 일별 리뷰 수 추이
        daily_counts = defaultdict(int)
        for d in self.user_data:
            daily_counts[d['date']] += 1

        # 정렬
        sorted_dates = sorted(daily_counts.keys())
        counts = [daily_counts[date] for date in sorted_dates]

        if len(counts) < 2:
            return {
                "trend": "stable",
                "predicted_growth": 0.0,
                "next_period_prediction": 0
            }

        # 지수평활법으로 다음 기간 예측
        smoothed = counts[0]
        for count in counts[1:]:
            smoothed = alpha * count + (1 - alpha) * smoothed

        # 트렌드 판단
        if smoothed > counts[-1] * 1.1:
            trend = "increasing"
        elif smoothed < counts[-1] * 0.9:
            trend = "decreasing"
        else:
            trend = "stable"

        # 성장률 예측
        if len(counts) >= 2:
            growth_rate = (counts[-1] - counts[0]) / counts[0] * 100
        else:
            growth_rate = 0.0

        return {
            "trend": trend,
            "predicted_growth": round(growth_rate, 2),
            "next_period_prediction": round(smoothed),
            "current_average": round(sum(counts[-7:]) / min(7, len(counts)))
        }

    def cluster_users(self, n_clusters: int = 5) -> List[Dict]:
        """
        사용자 군집화 (K-Means 기반)

        Args:
            n_clusters: 군집 수

        Returns:
            군집화 결과
        """
        # 간단한 군집화 로직 (맛 벡터 기반)
        clusters = []

        # 맛 벡터 기반 군집화
        taste_axes = ['sweetness', 'body', 'carbonation', 'flavor', 'alcohol', 'acidity', 'aroma_intensity', 'finish']

        # 사용자별 평균 맛 벡터 계산
        user_taste_vectors = defaultdict(lambda: {axis: 0.0 for axis in taste_axes})
        user_counts = defaultdict(int)

        for d in self.user_data:
            user_id = d['user_id']
            for axis in taste_axes:
                user_taste_vectors[user_id][axis] += d['taste_vector'].get(axis, 0.0)
            user_counts[user_id] += 1

        # 정규화
        for user_id in user_taste_vectors:
            count = user_counts[user_id]
            for axis in taste_axes:
                user_taste_vectors[user_id][axis] /= count

        # 간단한 군집화 (맛 벡터 기반)
        cluster_centers = [
            {'sweetness': 8.0, 'body': 5.0, 'carbonation': 5.0, 'flavor': 6.0, 'alcohol': 5.0, 'acidity': 4.0, 'aroma_intensity': 5.0, 'finish': 5.0},
            {'sweetness': 4.0, 'body': 5.0, 'carbonation': 6.0, 'flavor': 5.0, 'alcohol': 5.0, 'acidity': 8.0, 'aroma_intensity': 5.0, 'finish': 5.0},
            {'sweetness': 5.0, 'body': 8.0, 'carbonation': 4.0, 'flavor': 6.0, 'alcohol': 6.0, 'acidity': 5.0, 'aroma_intensity': 5.0, 'finish': 6.0},
            {'sweetness': 5.0, 'body': 4.0, 'carbonation': 8.0, 'flavor': 5.0, 'alcohol': 5.0, 'acidity': 6.0, 'aroma_intensity': 5.0, 'finish': 5.0},
            {'sweetness': 5.0, 'body': 5.0, 'carbonation': 5.0, 'flavor': 5.0, 'alcohol': 5.0, 'acidity': 5.0, 'aroma_intensity': 5.0, 'finish': 5.0}
        ]

        cluster_names = [
            "단맛 선호형",
            "산미 선호형",
            "바디감 선호형",
            "탄산 선호형",
            "밸런스형"
        ]

        cluster_descriptions = [
            "달콤한 맛을 선호하는 사용자 그룹",
            "새콤한 산미를 선호하는 사용자 그룹",
            "묵직한 바디감을 선호하는 사용자 그룹",
            "청량한 탄산감을 선호하는 사용자 그룹",
            "균형 잡힌 맛을 선호하는 사용자 그룹"
        ]

        # 각 사용자를 가장 가까운 군집에 할당
        cluster_assignments = defaultdict(list)
        cluster_counts = defaultdict(int)

        for user_id, vector in user_taste_vectors.items():
            # 가장 가까운 군집 찾기
            min_distance = float('inf')
            best_cluster = 0

            for i, center in enumerate(cluster_centers):
                distance = sum((vector[axis] - center[axis]) ** 2 for axis in taste_axes) ** 0.5
                if distance < min_distance:
                    min_distance = distance
                    best_cluster = i

            cluster_assignments[best_cluster].append(user_id)
            cluster_counts[best_cluster] += 1

        # 군집 결과 생성
        for i in range(n_clusters):
            clusters.append({
                "cluster_id": i,
                "name": cluster_names[i],
                "description": cluster_descriptions[i],
                "user_count": cluster_counts[i],
                "percentage": round(cluster_counts[i] / len(user_taste_vectors) * 100, 2) if user_taste_vectors else 0,
                "taste_profile": cluster_centers[i]
            })

        return clusters

    async def _generate_ai_report(self, statistics: Dict, predictions: Dict, clusters: List[Dict]) -> str:
        """
        Gemini를 사용해 양조장용 자연어 인사이트 리포트 생성

        Args:
            statistics: 집계 통계
            predictions: 트렌드 예측
            clusters: 사용자 군집

        Returns:
            AI 자연어 리포트 (3~5문장)
        """
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            return "GEMINI_API_KEY가 설정되지 않아 AI 리포트를 생성할 수 없습니다."

        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_api_key)
            model = genai.GenerativeModel('gemini-2.5-flash-lite')

            top_drinks = statistics.get('top_drinks', [])[:3]
            taste_dist = statistics.get('taste_distribution', {})
            trend = predictions.get('trend', 'stable')
            growth = predictions.get('predicted_growth', 0.0)
            largest_cluster = max(clusters, key=lambda x: x['user_count']) if clusters else {}

            top_drinks_str = ', '.join([f"{d['name']}({d['count']}회)" for d in top_drinks]) if top_drinks else '없음'
            taste_summary = ', '.join([f"{k}:{v:.1f}" for k, v in list(taste_dist.items())[:4]])
            cluster_name = largest_cluster.get('name', '알 수 없음')
            cluster_pct = largest_cluster.get('percentage', 0)

            prompt = f"""당신은 전통주 양조장 컨설턴트입니다. 다음 플랫폼 데이터를 바탕으로 양조장 운영자를 위한 인사이트 리포트를 3~5문장으로 작성해주세요. 한국어로, 실용적인 비즈니스 조언 위주로 작성하세요.

[플랫폼 데이터]
- 인기 전통주: {top_drinks_str}
- 맛 분포 (평균): {taste_summary}
- 트렌드: {trend} (성장률 {growth:.1f}%)
- 주요 고객 취향: {cluster_name} ({cluster_pct:.1f}%)

리포트:"""

            response = model.generate_content(prompt)
            return response.text.strip()

        except Exception as e:
            logger.error(f"AI 리포트 생성 실패: {e}")
            return f"AI 리포트 생성 중 오류가 발생했습니다: {str(e)[:100]}"

    async def get_insights(self, period: str = "week") -> InsightResponse:
        """
        인사이트 대시보드 메인 함수

        Args:
            period: 기간 (day, week, month)

        Returns:
            인사이트 결과
        """
        # 통계 집계
        statistics = self.aggregate_statistics(period)

        # 트렌드 예측
        predictions = self.predict_trends(period)

        # 군집화
        clusters = self.cluster_users()

        # 요약 생성
        summary = self._generate_summary(statistics, predictions, clusters)

        # Gemini AI 리포트 생성
        ai_report = await self._generate_ai_report(statistics, predictions, clusters)

        return InsightResponse(
            period=period,
            summary=summary,
            statistics=statistics,
            predictions=predictions,
            clusters=clusters,
            ai_report=ai_report
        )

    def _generate_summary(self, statistics: Dict, predictions: Dict, clusters: List[Dict]) -> str:
        """인사이트 요약 생성"""
        total_reviews = statistics['total_reviews']
        avg_rating = statistics['avg_rating']
        trend = predictions['trend']
        growth = predictions['predicted_growth']

        # 가장 큰 군집
        largest_cluster = max(clusters, key=lambda x: x['user_count']) if clusters else None

        summary_parts = []

        if total_reviews > 0:
            summary_parts.append(f"최근 {total_reviews}건의 리뷰가 있으며, 평균 평점은 {avg_rating}점입니다.")

        if trend == "increasing":
            summary_parts.append(f"리뷰 수가 {growth:.1f}% 증가하는 추세입니다.")
        elif trend == "decreasing":
            summary_parts.append(f"리뷰 수가 {abs(growth):.1f}% 감소하는 추세입니다.")
        else:
            summary_parts.append("리뷰 수가 안정적인 추세입니다.")

        if largest_cluster:
            summary_parts.append(f"가장 많은 사용자({largest_cluster['percentage']}%)는 '{largest_cluster['name']}' 취향을 가지고 있습니다.")

        return " ".join(summary_parts)


def main():
    """메인 실행 함수"""
    dashboard = InsightDashboard()

    print("=== 인사이트 대시보드 테스트 ===\n")

    # 1. 주간 인사이트
    print("--- 1. 주간 인사이트 ---")
    insights = dashboard.get_insights(period="week")

    print(f"요약: {insights.summary}\n")

    print("통계:")
    print(f"  총 리뷰 수: {insights.statistics['total_reviews']}")
    print(f"  평균 평점: {insights.statistics['avg_rating']}")
    print(f"  상위 막걸리:")
    for drink in insights.statistics['top_drinks'][:3]:
        print(f"    - {drink['name']}: {drink['count']}회 (평점 {drink['avg_rating']})")

    print("\n맛 분포:")
    for axis, value in insights.statistics['taste_distribution'].items():
        print(f"  {axis}: {value}")

    print("\n예측:")
    print(f"  트렌드: {insights.predictions['trend']}")
    print(f"  예상 성장률: {insights.predictions['predicted_growth']}%")
    print(f"  다음 기간 예측: {insights.predictions['next_period_prediction']}건")

    print("\n군집화:")
    for cluster in insights['clusters']:
        print(f"  {cluster['name']}: {cluster['user_count']}명 ({cluster['percentage']}%)")

    # 2. 월간 인사이트
    print("\n--- 2. 월간 인사이트 ---")
    insights = dashboard.get_insights(period="month")

    print(f"요약: {insights.summary}")
    print(f"총 리뷰 수: {insights.statistics['total_reviews']}")
    print(f"평균 평점: {insights.statistics['avg_rating']}")


if __name__ == "__main__":
    main()
