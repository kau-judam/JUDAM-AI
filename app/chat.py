"""
Chat API Endpoint
Handles user queries with context-aware responses
"""

import logging
import os
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

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

# 키워드별 후속 질문 매핑
KEYWORD_QUESTION_MAP = {
    '막걸리':   ['막걸리 도수는 얼마나 되나요?',        '막걸리 보관 방법이 궁금해요'],
    '청주':     ['청주와 막걸리의 차이가 뭔가요?',       '청주에 어울리는 안주가 있나요?'],
    '탁주':     ['탁주와 청주 차이가 무엇인가요?',       '탁주 만드는 방법이 궁금해요'],
    '소주':     ['소주와 전통주의 차이는 뭔가요?',       '소주 대신 즐길 수 있는 전통주가 있나요?'],
    '약주':     ['약주와 청주는 같은 건가요?',           '약주에 어울리는 음식을 추천해줘요'],
    '동동주':   ['동동주와 막걸리의 차이가 뭔가요?',     '동동주 만드는 방법이 궁금해요'],
    '누룩':     ['누룩이 막걸리에 어떤 역할을 하나요?',  '좋은 누룩을 고르는 방법이 있나요?'],
    '양조':     ['전통주 양조 과정이 궁금해요',          '가정에서 전통주 담그는 방법이 있나요?'],
    '전통주':   ['전통주 종류를 알려주세요',             '전통주 초보자에게 추천하는 술은?'],
    '도수':     ['도수별 추천 전통주를 알려주세요',       '도수 낮은 막걸리를 추천해주세요'],
    '안주':     ['막걸리에 어울리는 안주는 무엇인가요?', '전통주별 최고의 안주 페어링이 궁금해요'],
    '페어링':   ['음식과 막걸리 페어링 방법을 알려주세요', '특별한 날 페어링 추천이 있나요?'],
    '발효':     ['전통주 발효 기간은 얼마나 걸리나요?',  '발효 온도가 맛에 영향을 주나요?'],
    '양조장':   ['국내 유명 전통주 양조장을 추천해주세요', '양조장 견학이 가능한 곳이 있나요?'],
}

DEFAULT_QUESTIONS = ['어떤 전통주를 추천해드릴까요?', '전통주 페어링이 궁금하신가요?']


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


def generate_suggested_questions(message: str) -> List[str]:
    """키워드 기반 후속 질문 2개 생성 (Gemini 호출 없음)"""
    for kw, questions in KEYWORD_QUESTION_MAP.items():
        if kw in message:
            return questions[:2]
    return DEFAULT_QUESTIONS


class ChatRequest(BaseModel):
    """Chat request model"""
    message: str
    user_id: str
    history: Optional[List[Dict[str, str]]] = []


class ChatResponse(BaseModel):
    """Chat response model"""
    response: str
    context: str
    suggested_questions: List[str] = []


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Process user message and return response

    Args:
        request: Chat request with message, user_id, and history

    Returns:
        Chat response with answer, context, and suggested_questions
    """
    try:
        import google.generativeai as genai

        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")

        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('gemini-2.5-flash-lite')

        # 전통주 관련 여부 확인 (현재 메시지 + 히스토리 맥락 포함)
        is_related = is_traditional_alcohol_related(request.message, request.history)

        # 비관련 질문이면 즉시 거절 (Gemini 호출 절약)
        if not is_related:
            suggested = generate_suggested_questions(request.message)
            return ChatResponse(
                response="죄송합니다. 저는 전통주(막걸리, 청주, 탁주 등) 관련 질문만 답변드릴 수 있어요. 전통주에 대해 궁금한 점을 물어봐 주세요!",
                context="out_of_scope",
                suggested_questions=suggested
            )

        # 대화 히스토리 구성 (content 키 지원)
        context_parts = []
        if request.history:
            for item in request.history:
                role = item.get("role", "")
                # 'content' 또는 'message' 키 모두 지원
                content = item.get("content") or item.get("message", "")
                if role == "user" and content:
                    context_parts.append(f"사용자: {content}")
                elif role == "assistant" and content:
                    context_parts.append(f"어시스턴트: {content}")

        context_str = "\n".join(context_parts) if context_parts else "이전 대화 없음"

        # 시스템 프롬프트 (한국어, 전통주 특화)
        system_prompt = """당신은 주담(Juddam) 전통주 플랫폼의 전문 AI 어시스턴트입니다.
막걸리, 청주, 탁주, 약주, 소주, 동동주 등 한국 전통주에 관한 질문에만 답변하세요.
답변은 간결하고 실용적으로, 한국어로 작성하세요.
전통주와 무관한 질문에는 정중히 거절하세요."""

        full_prompt = f"""{system_prompt}

이전 대화:
{context_str}

현재 질문: {request.message}

답변:"""

        response = model.generate_content(full_prompt)
        result_text = response.text.strip()

        # 키워드 기반 후속 질문 생성
        suggested = generate_suggested_questions(request.message)

        return ChatResponse(
            response=result_text,
            context="traditional_korean_alcohol",
            suggested_questions=suggested
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {e}")
        s = str(e)
        if '429' in s or 'quota exceeded' in s.lower() or 'resource_exhausted' in s.lower():
            raise HTTPException(status_code=503, detail="현재 AI 서비스가 일시적으로 혼잡합니다. 잠시 후 다시 시도해주세요.")
        raise HTTPException(status_code=500, detail="챗봇 서비스 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
