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
    - sermon_id: 설교 ID
    - source: "sermon_archive" 등 출처
    - title: 설교 제목
    - date: 설교 날짜
    - scripture: 성경 구절
    - summary: 요약 또는 발췌
    - score: 유사도/랭킹 점수
    - thumbnail_url: 주보 이미지 썸네일 URL (있는 경우)
    """
    sermon_id: str
    source: str
    title: Optional[str]
    date: Optional[str]
    scripture: Optional[str]
    summary: str
    score: Optional[float]
    thumbnail_url: Optional[str]
    full_text: Optional[str]  # 전체 설교 텍스트 (필요시)


# ─────────────────────────────────────────────────────────
# 프로필 모드 타입
# ─────────────────────────────────────────────────────────

ProfileMode = Literal["research", "counseling", "education"]


# ─────────────────────────────────────────────────────────
# State (그래프 전체에서 공유하는 컨텍스트)
# ─────────────────────────────────────────────────────────

class SermonState(TypedDict, total=False):
    # ── 세션/제어 ───────────────────────────────────────
    session_id: str
    user_id: Optional[int]  # 목사님 사용자 ID
    end_session: bool
    started_at: str
    last_activity_at: str
    turn_count: int

    # ── 대화 컨텍스트 ───────────────────────────────────
    messages: Annotated[List[Message], operator.add]
    rolling_summary: Optional[str]

    # ── 프로필 모드 ─────────────────────────────────────
    profile_mode: ProfileMode  # "research" | "counseling" | "education"
    profile_mode_prompt: Optional[str]  # 현재 모드에 맞는 프롬프트

    # ── 사용자 컨텍스트 ─────────────────────────────────
    user_context: Dict[str, Any]  # 목사님의 선호도, 교회 정보 등

    # ── RAG 관련 ────────────────────────────────────────
    retrieval: Dict[str, Any]  # used_rag / rag_snippets / search_query ...
    rag_snippets: List[SermonSnippet]  # 검색된 설교 스니펫들

    # ── 입출력 ─────────────────────────────────────────
    user_input: Optional[str]
    answer: Dict[str, Any]  # 최종 답변 (텍스트, 참고 설교 목록 등)
    user_action: Optional[str]  # 사용자 액션 (업로드, 검색 등)

    # ── Router 결정 값 ──────────────────────────────────
    router: Dict[str, Any]  # 질문 타입, RAG 사용 여부 등
    next: Optional[str]  # 다음 노드

    # ── OCR/이미지 처리 관련 ────────────────────────────
    uploaded_images: List[Dict[str, Any]]  # 업로드된 주보 이미지 정보
    ocr_results: List[Dict[str, Any]]  # OCR 처리 결과

    # ── 스트리밍 관련 ───────────────────────────────────
    streaming_mode: bool  # 스트리밍 모드 활성화 여부
    streaming_context: Dict[str, Any]  # 스트리밍용 컨텍스트


# alias 편의를 위해 짧은 이름도 제공
State = SermonState

__all__ = [
    "Message",
    "SermonSnippet",
    "ProfileMode",
    "SermonState",
    "State",
]

