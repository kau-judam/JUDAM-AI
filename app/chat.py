"""
Chat API Endpoint
Handles user queries with context-aware responses
"""

import json
import logging
import os
import re
from typing import Any, AsyncGenerator, List, Dict, Optional, Tuple
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from app.db import db

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# 전통주 관련 키워드 리스트
TRADITIONAL_ALCOHOL_KEYWORDS = [
    '막걸리', '청주', '탁주', '소주', '약주', '동동주', '누룩', '양조', '전통주',
    '막걸', '탁배기', '보리술', '곡주', '도수', '안주', '페어링', '술',
    '발효', '쌀술', '약주', '모주', '이화주', '감주', '식혜', '주막',
    '양조장', '브루어리', '효모', '당화', '담금', '숙성', '향', '산미',
    '단맛', '바디', '탄산', '풍미', '여운'
]

DEFAULT_QUESTIONS = [
    '추천한 술 중 도수가 가장 낮은 술은 무엇인가요?',
    '첫 번째 추천 술에 어울리는 안주는 무엇인가요?',
    '추천한 술들의 맛 차이를 비교해 주세요.',
]


def is_traditional_alcohol_related(message: str, history: Optional[List[Dict[str, str]]] = None) -> bool:
    """전통주 관련 메시지인지 확인 (히스토리 맥락 포함)"""
    if any(kw in message for kw in TRADITIONAL_ALCOHOL_KEYWORDS):
        return True
    # 히스토리에 전통주 키워드가 있으면 맥락상 관련 질문으로 판단
    if history:
        for item in history:
            content = item.get("content") or item.get("message", "")
            if any(kw in content for kw in TRADITIONAL_ALCOHOL_KEYWORDS):
                return True
    return False


class ChatRequest(BaseModel):
    """Chat request model"""
    message: str
    user_id: Optional[str] = None
    history: List[Dict[str, Any]] = Field(default_factory=list)


class ChatStreamRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response model"""
    response: str
    context: str
    suggested_questions: List[str] = Field(default_factory=list)
    referenced_drinks: Optional[List[Dict[str, Any]]] = None
    next_actions: Optional[List[str]] = None
    intent: Optional[str] = None
    personalization_source: Optional[str] = None


def _drink_catalog(recommender: Any) -> List[Dict[str, Any]]:
    """추천 시스템이 실제 보유한 전통주만 중복 없이 반환한다."""
    catalog: List[Dict[str, Any]] = []
    seen = set()
    for pool_name in ("drinks", "funding_drinks", "approved_drinks"):
        for drink in getattr(recommender, pool_name, []) or []:
            drink_id = str(drink.get("id") or "")
            name = str(drink.get("name") or "")
            if not name or (drink_id, name) in seen:
                continue
            seen.add((drink_id, name))
            catalog.append(drink)
    return catalog


def _public_drink(drink: Dict[str, Any]) -> Dict[str, Any]:
    """챗봇 응답에 포함할 실제 제품 필드를 정리한다."""
    return {
        "id": drink.get("id"),
        "name": drink.get("name", ""),
        "brewery": drink.get("brewery", ""),
        "abv": drink.get("abv", 0),
        "region": drink.get("region", ""),
        "features": drink.get("features", ""),
    }


def _history_drinks(history: List[Dict[str, Any]], catalog: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """직전 응답이 참조한 실제 제품을 대화 기록에서 복원한다."""
    by_name = {str(drink.get("name")): drink for drink in catalog}
    found: List[Dict[str, Any]] = []
    for item in reversed(history):
        refs = item.get("referenced_drinks") or []
        for ref in refs:
            name = ref.get("name") if isinstance(ref, dict) else str(ref)
            if name in by_name and by_name[name] not in found:
                found.append(by_name[name])
        content = str(item.get("content") or item.get("message") or "")
        for name, drink in by_name.items():
            if name and name in content and drink not in found:
                found.append(drink)
        if found:
            break
    return found


def _detect_intent(message: str, contextual_drinks: List[Dict[str, Any]]) -> str:
    """현재 질문과 직전 추천 제품을 바탕으로 챗봇 의도를 분류한다."""
    compact = re.sub(r"\s+", "", message)
    if any(word in compact for word in ("비교", "차이", "뭐가더")):
        return "compare_drinks"
    if any(word in compact for word in ("가장낮은도수", "낮은도수", "도수가낮")):
        return "lowest_abv"
    if any(word in compact for word in ("안주", "페어링", "어울리는음식")):
        return "food_pairing"
    if any(word in compact for word in ("설명", "특징", "어떤술", "알려줘")):
        return "drink_explanation"
    return "recommend_drinks"


async def _personalization(req: Request, user_id: Optional[str]) -> Tuple[Optional[Dict[str, float]], str, List[str]]:
    """실제 취향 이력 또는 설문 프로필에서 개인화 입력을 가져온다."""
    if not user_id:
        return None, "general", []
    recommender = req.app.state.recommender
    history = getattr(recommender, "user_taste_history", {}).get(user_id, [])
    if history:
        return recommender.get_evolved_taste_vector(user_id), "taste_history", []

    profile = getattr(req.app.state, "user_profiles", {}).get(user_id)
    if not profile and getattr(db, "db_connected", False):
        try:
            profile = await db.get_user_profile(user_id)
        except Exception as exc:
            logger.warning("챗봇 사용자 프로필 조회 실패: %s", type(exc).__name__)
    if profile:
        taste_vector = profile.get("taste_vector")
        if isinstance(taste_vector, str):
            try:
                taste_vector = json.loads(taste_vector)
            except json.JSONDecodeError:
                taste_vector = None
        if taste_vector:
            return taste_vector, "survey_profile", profile.get("preferred_food_pairing", []) or []
    return None, "general", []


def _select_drinks(
    intent: str,
    message: str,
    contextual_drinks: List[Dict[str, Any]],
    catalog: List[Dict[str, Any]],
    recommender: Any,
    taste_vector: Optional[Dict[str, float]],
    food_pairings: List[str],
) -> List[Dict[str, Any]]:
    """의도에 맞는 실제 제품만 선택한다."""
    mentioned = [drink for drink in catalog if str(drink.get("name") or "") in message]
    base = mentioned or contextual_drinks
    if intent == "lowest_abv" and base:
        return [min(base, key=lambda drink: float(drink.get("abv") or 0))]
    if intent in {"food_pairing", "drink_explanation"} and base:
        if "첫 번째" in message or "첫번째" in message:
            return base[:1]
        return base[:3]
    if intent == "compare_drinks" and base:
        return base[:3]
    if taste_vector:
        return recommender.recommend(
            user_vector=taste_vector,
            top_k=3,
            pool="all",
            user_food_pairings=food_pairings,
        )
    return sorted(catalog, key=lambda drink: (float(drink.get("abv") or 0), str(drink.get("name") or "")))[:3]


def _build_answer(intent: str, drinks: List[Dict[str, Any]], personalization_source: str) -> str:
    """실제 제품 데이터만 사용해 챗봇 답변을 구성한다."""
    if not drinks:
        return "현재 추천 가능한 실제 전통주 제품 데이터가 없습니다."
    general_note = "사용자 취향 데이터가 없어 일반 추천으로 안내드립니다. " if personalization_source == "general" else ""
    if intent == "lowest_abv":
        drink = drinks[0]
        return f"{general_note}앞서 언급한 제품 중 도수가 가장 낮은 술은 {drink['name']}({drink.get('abv', 0)}도)입니다."
    if intent == "food_pairing":
        lines = []
        for drink in drinks:
            feature = str(drink.get("features") or "제품 특성에 맞는 담백한 한식 안주")
            lines.append(f"{drink['name']}: {feature}")
        return general_note + "안주 페어링은 다음과 같습니다. " + " / ".join(lines)
    if intent == "compare_drinks":
        lines = [
            f"{drink['name']}({drink.get('abv', 0)}도, {drink.get('brewery') or '양조장 정보 없음'}): "
            f"{drink.get('features') or '상세 특징 정보 없음'}"
            for drink in drinks
        ]
        return general_note + "제품별 차이를 비교하면 " + " / ".join(lines)
    if intent == "drink_explanation":
        drink = drinks[0]
        return (
            f"{general_note}{drink['name']}은 {drink.get('brewery') or '양조장 정보 미상'} 제품이며 "
            f"도수는 {drink.get('abv', 0)}도입니다. {drink.get('features') or '상세 특징 정보는 없습니다.'}"
        )
    names = ", ".join(f"{drink['name']}({drink.get('abv', 0)}도)" for drink in drinks)
    prefix = "취향 정보를 반영한 추천입니다. " if personalization_source != "general" else general_note
    return f"{prefix}실제 등록 제품 중 {names}을 추천합니다."


async def _generate_next_actions(
    question: str,
    answer: str,
    drinks: List[Dict[str, Any]],
) -> List[str]:
    """질문·답변·추천 제품에 관련된 후속 질문을 Gemini로 생성한다."""
    try:
        import google.generativeai as genai

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not configured")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash-lite")
        drink_names = [str(drink.get("name")) for drink in drinks]
        prompt = f"""다음 전통주 대화에 직접 관련된 후속 질문 2~3개만 JSON 문자열 배열로 반환하세요.
질문: {question}
답변: {answer}
실제 언급 가능 제품: {json.dumps(drink_names, ensure_ascii=False)}
답변과 무관한 질문이나 목록에 없는 제품명은 쓰지 마세요."""
        response = await model.generate_content_async(prompt, generation_config={"max_output_tokens": 180})
        parsed = json.loads(response.text.strip().replace("```json", "").replace("```", "").strip())
        actions = [str(item).strip() for item in parsed if str(item).strip()]
        if not 2 <= len(actions) <= 3:
            raise ValueError("invalid next action count")
        return actions
    except Exception as exc:
        logger.warning("챗봇 후속 질문 생성 fallback: %s", type(exc).__name__)
        return DEFAULT_QUESTIONS[:3]


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request) -> ChatResponse:
    """
    Process user message and return response

    Args:
        request: Chat request with message, user_id, and history
        req: FastAPI Request (app.state 접근용)

    Returns:
        Chat response with answer, context, and suggested_questions
    """
    recommender = req.app.state.recommender
    catalog = _drink_catalog(recommender)
    contextual_drinks = _history_drinks(request.history, catalog)
    is_related = is_traditional_alcohol_related(request.message, request.history) or bool(contextual_drinks)
    if not is_related:
        return ChatResponse(
            response="죄송합니다. 저는 전통주 관련 질문만 답변드릴 수 있어요.",
            context="out_of_scope",
            suggested_questions=DEFAULT_QUESTIONS,
            next_actions=DEFAULT_QUESTIONS,
            intent="out_of_scope",
            personalization_source="general",
        )

    taste_vector, personalization_source, food_pairings = await _personalization(req, request.user_id)
    intent = _detect_intent(request.message, contextual_drinks)
    selected = _select_drinks(
        intent,
        request.message,
        contextual_drinks,
        catalog,
        recommender,
        taste_vector,
        food_pairings,
    )
    answer = _build_answer(intent, selected, personalization_source)
    next_actions = await _generate_next_actions(request.message, answer, selected)
    referenced = [_public_drink(drink) for drink in selected]
    return ChatResponse(
        response=answer,
        context="traditional_korean_alcohol",
        suggested_questions=next_actions,
        referenced_drinks=referenced,
        next_actions=next_actions,
        intent=intent,
        personalization_source=personalization_source,
    )


async def _stream_gemini(message: str) -> AsyncGenerator[str, None]:
    """Gemini 스트리밍 응답 SSE 제너레이터"""
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        yield f"data: {json.dumps({'type': 'error', 'content': 'GEMINI_API_KEY 미설정'}, ensure_ascii=False)}\n\n"
        return

    if not is_traditional_alcohol_related(message):
        payload = {"type": "off_topic", "content": "전통주 관련 질문만 답변드릴 수 있어요."}
        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        return

    try:
        from google import genai as google_genai

        client = google_genai.Client(api_key=gemini_api_key)
        prompt = (
            "한국 전통주 전문 AI입니다. 막걸리·청주·탁주·약주 관련 질문만 답변합니다. "
            "3~5문장으로 간결하게 한국어로 답변하세요.\n\n"
            f"질문: {message}\n답변:"
        )

        full_text = ""
        async for chunk in await client.aio.models.generate_content_stream(
            model="gemini-2.5-flash-lite",
            contents=prompt
        ):
            text = chunk.text or ""
            if text:
                full_text += text
                payload = {"type": "chunk", "content": text}
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

        done_payload = {"type": "done", "content": "", "full_response": full_text}
        yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n"

    except Exception as e:
        logger.error(f"스트리밍 챗봇 오류: {e}")
        error_payload = {"type": "error", "content": "오류가 발생했습니다."}
        yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"


@router.post("/chat/stream")
async def chat_stream(request: ChatStreamRequest):
    """전통주 챗봇 스트리밍 엔드포인트 (SSE)"""
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY가 설정되지 않았습니다.")

    return StreamingResponse(
        _stream_gemini(request.message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )
