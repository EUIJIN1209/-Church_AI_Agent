# backend/agents/new_pipeline.py
# -*- coding: utf-8 -*-
"""
new_pipeline.py

대덕교회 설교 AI 에이전트 파이프라인.

워크플로우:
  START → query_router → [sermon_retriever] → answer_creator → END

노드:
  1. query_router: 질문 분석 및 RAG 사용 여부 결정
  2. sermon_retriever: 설교 아카이브 벡터 검색 (RAG 필요시)
  3. answer_creator: 최종 답변 생성

LLM: OpenAI GPT-4o-mini
임베딩: dragonkue/bge-m3-ko (1024차원)
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# 프로젝트 루트 경로 설정
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv()

# LangGraph
from langgraph.graph import StateGraph, END

# sermon_agent 모듈
from backend.sermon_agent.state.sermon_state import State
from backend.sermon_agent.nodes.query_router import query_router_node
from backend.sermon_agent.nodes.sermon_retriever import sermon_retriever_node
from backend.sermon_agent.nodes.answer_creator import answer_creator_node

# LangSmith (선택적)
try:
    from langsmith import traceable
except ImportError:
    def traceable(func):
        return func


# ─────────────────────────────────────────────────────────
# 환경 변수 확인
# ─────────────────────────────────────────────────────────

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

if not OPENAI_API_KEY:
    print("[WARNING] OPENAI_API_KEY가 설정되지 않았습니다.")

if not DATABASE_URL:
    print("[WARNING] DATABASE_URL이 설정되지 않았습니다.")


# ─────────────────────────────────────────────────────────
# 유틸리티
# ─────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─────────────────────────────────────────────────────────
# 라우팅 함수
# ─────────────────────────────────────────────────────────

def route_after_router(state: State) -> str:
    """
    query_router 결과에 따라 다음 노드 결정.

    - next == "end" → END (특수 액션: save, reset 등)
    - use_rag == True → sermon_retriever
    - use_rag == False → answer_creator
    """
    next_node = state.get("next")
    router = state.get("router", {})
    use_rag = router.get("use_rag", False)

    if next_node == "end":
        return END

    if use_rag:
        return "sermon_retriever"
    else:
        return "answer_creator"


# ─────────────────────────────────────────────────────────
# 그래프 빌드
# ─────────────────────────────────────────────────────────

_compiled_graph = None

def build_graph():
    """LangGraph 워크플로우 구성."""
    graph = StateGraph(State)

    # 노드 등록
    graph.add_node("query_router", query_router_node)
    graph.add_node("sermon_retriever", sermon_retriever_node)
    graph.add_node("answer_creator", answer_creator_node)

    # 시작점
    graph.set_entry_point("query_router")

    # query_router → 조건부 분기
    graph.add_conditional_edges(
        "query_router",
        route_after_router,
        {
            "sermon_retriever": "sermon_retriever",
            "answer_creator": "answer_creator",
            END: END,
        }
    )

    # sermon_retriever → answer_creator
    graph.add_edge("sermon_retriever", "answer_creator")

    # answer_creator → END
    graph.add_edge("answer_creator", END)

    return graph.compile()


def get_graph():
    """컴파일된 그래프 반환 (싱글톤)."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


# ─────────────────────────────────────────────────────────
# 실행 함수
# ─────────────────────────────────────────────────────────

def run_pipeline(
    question: str,
    profile_mode: str = "research",
    session_id: str = "default",
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    설교 AI 에이전트 파이프라인 실행.

    Args:
        question: 사용자 질문
        profile_mode: 프로필 모드 ("research", "counseling", "education")
        session_id: 세션 ID
        user_id: 사용자 ID (선택)

    Returns:
        Dict containing:
            - answer: 답변 텍스트
            - citations: 참고 설교 목록
            - scripture_refs: 성경 구절 참조
            - category: 질문 카테고리
            - used_rag: RAG 사용 여부
    """
    graph = get_graph()
    now = _now_iso()

    # 초기 상태 구성
    initial_state: State = {
        "session_id": session_id,
        "user_id": user_id,
        "end_session": False,
        "started_at": now,
        "last_activity_at": now,
        "turn_count": 1,
        "messages": [],
        "rolling_summary": None,
        "profile_mode": profile_mode,
        "profile_mode_prompt": None,
        "user_context": {},
        "retrieval": {},
        "rag_snippets": [],
        "user_input": question,
        "answer": {},
        "user_action": None,
        "router": {},
        "next": None,
        "uploaded_images": [],
        "ocr_results": [],
        "streaming_mode": False,
        "streaming_context": {},
    }

    # 그래프 실행
    result = graph.invoke(initial_state)

    # 결과 추출
    answer_data = result.get("answer", {})
    router_data = result.get("router", {})

    return {
        "answer": answer_data.get("text", ""),
        "citations": answer_data.get("citations", []),
        "scripture_refs": answer_data.get("scripture_refs", []),
        "category": router_data.get("category", "OTHER"),
        "used_rag": answer_data.get("used_rag", False),
        "profile_mode": profile_mode,
    }


# ─────────────────────────────────────────────────────────
# 에이전트 역할 정의
# ─────────────────────────────────────────────────────────

AGENT_ROLE = """
대덕교회 설교 AI 사역 비서

당신은 대덕교회의 설교 아카이브를 기반으로 목회자와 성도를 돕는 AI 비서입니다.

[주요 역할]
1. 과거 설교 검색 및 요약
2. 설교 준비 지원 (본문 해석, 적용점 제안)
3. 성도 상담 지원 (위로, 격려의 말씀 제공)
4. 교육 자료 작성 지원 (쉬운 설명, 나눔 질문)

[프로필 모드]
- research (연구): 신학적 분석, 깊이 있는 본문 해석
- counseling (상담): 따뜻한 톤, 실생활 적용, 위로와 격려
- education (교육): 쉬운 설명, 비유 사용, 소그룹 질문

[데이터 출처]
- 대덕교회 주일 설교 아카이브 (2023-2026년, 160개)
- 답변 시 반드시 설교 날짜와 제목을 인용합니다.
"""


# ─────────────────────────────────────────────────────────
# 대화형 인터페이스
# ─────────────────────────────────────────────────────────

def interactive_mode():
    """대화형 모드로 에이전트 실행."""
    print("=" * 60)
    print("대덕교회 설교 AI 에이전트")
    print("=" * 60)
    print(AGENT_ROLE)
    print("=" * 60)
    print("\n[사용법]")
    print("  - 질문을 입력하세요")
    print("  - 모드 변경: /mode research|counseling|education")
    print("  - 종료: /quit 또는 /exit")
    print("=" * 60)

    current_mode = "research"
    print(f"\n현재 모드: {current_mode}")

    while True:
        try:
            user_input = input("\n[질문] ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n종료합니다.")
            break

        if not user_input:
            continue

        # 명령어 처리
        if user_input.startswith("/"):
            cmd = user_input.lower()

            if cmd in ("/quit", "/exit", "/q"):
                print("종료합니다.")
                break

            elif cmd.startswith("/mode"):
                parts = cmd.split()
                if len(parts) == 2 and parts[1] in ("research", "counseling", "education"):
                    current_mode = parts[1]
                    print(f"모드 변경: {current_mode}")
                else:
                    print("사용법: /mode research|counseling|education")
                continue

            elif cmd == "/help":
                print("\n[명령어]")
                print("  /mode <모드>  - 모드 변경 (research, counseling, education)")
                print("  /quit         - 종료")
                print("  /help         - 도움말")
                continue

            else:
                print(f"알 수 없는 명령어: {user_input}")
                continue

        # 질문 처리
        print(f"[모드] {current_mode}")
        print("-" * 60)
        print("처리 중...")

        try:
            result = run_pipeline(user_input, profile_mode=current_mode)

            print(f"\n[카테고리] {result['category']}")
            print(f"[RAG 사용] {result['used_rag']}")

            if result['citations']:
                print(f"\n[참고 설교]")
                for i, ref in enumerate(result['citations'], 1):
                    print(f"  {i}. [{ref.get('date')}] {ref.get('title')}")

            print(f"\n[답변]")
            print("-" * 60)
            print(result['answer'])
            print("-" * 60)

        except Exception as e:
            print(f"\n[오류] {e}")


# ─────────────────────────────────────────────────────────
# 메인 실행
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    interactive_mode()
