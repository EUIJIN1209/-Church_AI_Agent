# backend/sermon_agent/state/sermon_state.py
# -*- coding: utf-8 -*-
"""
sermon_state.py

설교 지원 에이전트의 LangGraph State 스키마 정의.

- 목적:
  * 세션 동안 인메모리에 유지되는 ephemeral 컨텍스트 구조 관리
  * 각 노드가 동일한 타입을 바라보도록 함

- 특징:
  * messages는 Annotated[..., operator.add]로 append-only reducer 설정
  * 멀티 프로필 모드 지원 (연구용/상담용/교육용)
  * 스트리밍 모드 지원
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, TypedDict

try:
    # Python 3.11+
    from typing import Annotated
except ImportError:  # Python 3.8~3.10
    from typing_extensions import Annotated

import operator


# ─────────────────────────────────────────────────────────
# 기본 단위 타입
# ─────────────────────────────────────────────────────────

class Message(TypedDict, total=False):
    """
    한 턴의 메시지 단위.
    - role: user / assistant / tool
    - content: 본문
    - created_at: ISO8601 문자열 (UTC 권장)
    - meta: 토큰 사용량, no_store 플래그, tool_name 등 부가 정보
    """
    role: Literal["user", "assistant", "tool"]
    content: str
    created_at: str
    meta: Dict[str, Any]


class SermonSnippet(TypedDict, total=False):
    """
    RAG로 가져온 설교 스니펫 단위.
    """
    sermon_id: str
    source: str  # "sermon_archive"
    title: Optional[str]
    date: Optional[str]  # "YYYY년 MM월 DD일" 형식
    scripture: Optional[str]  # 성경 구절
    summary: str  # 설교 요약/내용
    score: Optional[float]  # Cosine Similarity
    church_name: Optional[str]
    preacher: Optional[str]
    video_url: Optional[str]
    thumbnail_url: Optional[str]
    full_text: Optional[str]


class Citation(TypedDict, total=False):
    """
    답변에 사용된 출처 정보.
    """
    sermon_id: str
    title: str
    date: str
    scripture: Optional[str]
    score: Optional[float]


class AnswerResult(TypedDict, total=False):
    """
    LLM 답변 결과.
    """
    text: str
    citations: List[Citation]
    scripture_refs: List[str]  # 답변에서 추출된 성경 구절
    category: Optional[str]
    profile_mode: str
    model: str
    used_rag: bool
    error: Optional[str]


# ─────────────────────────────────────────────────────────
# 프로필 모드 타입
# ─────────────────────────────────────────────────────────

ProfileMode = Literal["research", "counseling", "education"]


# ─────────────────────────────────────────────────────────
# Router 결정 타입
# ─────────────────────────────────────────────────────────

QuestionCategory = Literal[
    "SERMON_PREP",      # 설교 준비 관련
    "COUNSELING",       # 성도 상담 관련
    "SCRIPTURE_QA",     # 성경 구절/해석 관련
    "SERMON_SEARCH",    # 과거 설교 검색
    "SMALL_TALK",       # 인사/잡담
    "OTHER"             # 기타
]


class RouterDecision(TypedDict, total=False):
    """
    Router 노드의 결정 결과.
    """
    category: QuestionCategory
    use_rag: bool
    reason: str


# ─────────────────────────────────────────────────────────
# State (그래프 전체에서 공유하는 컨텍스트)
# ─────────────────────────────────────────────────────────

class SermonState(TypedDict, total=False):
    # ── 세션/제어 ───────────────────────────────────────
    session_id: str
    user_id: Optional[int]
    end_session: bool
    started_at: str
    last_activity_at: str
    turn_count: int

    # ── 대화 컨텍스트 (append-only) ─────────────────────
    messages: Annotated[List[Message], operator.add]
    rolling_summary: Optional[str]

    # ── 프로필 모드 ─────────────────────────────────────
    profile_mode: ProfileMode  # "research" | "counseling" | "education"
    profile_mode_prompt: Optional[str]

    # ── 사용자 컨텍스트 ─────────────────────────────────
    user_context: Dict[str, Any]

    # ── RAG 관련 ────────────────────────────────────────
    retrieval: Dict[str, Any]  # used_rag, search_query, count, error 등
    rag_snippets: List[SermonSnippet]

    # ── 입출력 ─────────────────────────────────────────
    user_input: Optional[str]
    user_action: Optional[str]  # "chat" | "save" | "reset" 등
    answer: AnswerResult

    # ── Router 결정 값 ──────────────────────────────────
    router: RouterDecision
    next: Optional[str]

    # ── OCR/이미지 처리 관련 ────────────────────────────
    uploaded_images: List[Dict[str, Any]]
    ocr_results: List[Dict[str, Any]]

    # ── 스트리밍 관련 ───────────────────────────────────
    streaming_mode: bool
    streaming_context: Dict[str, Any]  # 스트리밍 재생성용 컨텍스트

    # ── 타이밍/디버그 ───────────────────────────────────
    timing: Dict[str, float]  # 각 노드별 소요 시간


# alias 편의를 위해 짧은 이름도 제공
State = SermonState

__all__ = [
    "Message",
    "SermonSnippet",
    "Citation",
    "AnswerResult",
    "ProfileMode",
    "QuestionCategory",
    "RouterDecision",
    "SermonState",
    "State",
]
