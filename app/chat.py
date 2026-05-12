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


class ChatRequest(BaseModel):
    """Chat request model"""
    message: str
    user_id: str
    history: Optional[List[Dict[str, str]]] = []


class ChatResponse(BaseModel):
    """Chat response model"""
    response: str
    context: str


@router.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Process user message and return response

    Args:
        request: Chat request with message, user_id, and history

    Returns:
        Chat response with answer and context
    """
    try:
        import google.generativeai as genai

        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")

        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')

        # Build conversation context
        context_parts = []
        if request.history:
            for item in request.history:
                if item.get("role") == "user":
                    context_parts.append(f"User: {item.get('message', '')}")
                elif item.get("role") == "assistant":
                    context_parts.append(f"Assistant: {item.get('message', '')}")

        context = "\n".join(context_parts) if context_parts else "No previous conversation"

        # System prompt
        system_prompt = """
You are a helpful assistant for Juddam, a traditional Korean alcohol platform.
Answer questions about makgeolli, traditional Korean alcohol, brewing, and related topics.
Keep responses concise and helpful.
"""

        full_prompt = f"{system_prompt}\n\nPrevious conversation:\n{context}\n\nCurrent question: {request.message}"

        response = model.generate_content(full_prompt)
        result_text = response.text.strip()

        return ChatResponse(
            response=result_text,
            context="traditional_korean_alcohol"
        )

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
