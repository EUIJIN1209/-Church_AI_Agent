"""
backend/main.py

FastAPI 진입점.
- Next.js 프론트엔드가 호출하는 인증/챗 API를 제공
- LangGraph 기반 설교 에이전트와 연결
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.sermon_agent.graph import get_sermon_agent_graph
from backend.sermon_agent.state.sermon_state import State, ProfileMode
from backend.auth.routes import router as auth_router


app = FastAPI(title="Sermon AI Backend", version="0.1.0")

# CORS 설정: Next.js 프론트엔드에서 호출 가능하도록 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 필요 시 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 인증 라우터 등록
app.include_router(auth_router)


# ─────────────────────────────────────────────────────────
# Pydantic 모델
# ─────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    user_id: str
    question: str
    profile_mode: ProfileMode = "research"
    session_id: str = "default"


class ChatResponse(BaseModel):
    answer: str
    references: list
    scripture_refs: list
    category: Optional[str] = None


# ─────────────────────────────────────────────────────────
# LangGraph 설교 에이전트 Chat API
# ─────────────────────────────────────────────────────────


_graph = get_sermon_agent_graph()


@app.post("/chat/sermon", response_model=ChatResponse)
async def chat_sermon(payload: ChatRequest) -> ChatResponse:
    """
    설교 지원 에이전트와의 단일 턴 대화.

    Next.js 프론트엔드에서 호출:
      - body: { user_id, question, profile_mode, session_id }
      - 응답: 설교 답변 텍스트 + 참고 설교 목록 + 성경 구절 참조
    """
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="질문이 비어 있습니다.")

    now = datetime.now(timezone.utc).isoformat()

    # LangGraph 초기 상태 구성 (단일 턴)
    initial_state: State = {
        "session_id": payload.session_id,
        "user_id": None,  # TODO: users/profiles 구조와 연결 시 UUID ↔ profile_id 매핑
        "end_session": False,
        "started_at": now,
        "last_activity_at": now,
        "turn_count": 1,
        "messages": [],
        "rolling_summary": None,
        "profile_mode": payload.profile_mode,
        "profile_mode_prompt": None,
        "user_context": {},
        "retrieval": {},
        "rag_snippets": [],
        "user_input": payload.question,
        "answer": {},
        "user_action": None,
        "router": {},
        "next": None,
        "uploaded_images": [],
        "ocr_results": [],
        "streaming_mode": False,
        "streaming_context": {},
    }

    try:
        result: Dict[str, Any] = _graph.invoke(initial_state)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"LangGraph 실행 오류: {e}") from e

    answer_block: Dict[str, Any] = result.get("answer") or {}
    router_block: Dict[str, Any] = result.get("router") or {}

    return ChatResponse(
        answer=answer_block.get("text", ""),
        references=answer_block.get("citations", []),  # answer_creator에서 citations로 반환
        scripture_refs=answer_block.get("scripture_refs", []),
        category=router_block.get("category"),
    )


@app.get("/health")
async def health() -> Dict[str, str]:
    """헬스체크 엔드포인트 (Next.js / 모니터링용)."""
    return {"status": "ok"}


