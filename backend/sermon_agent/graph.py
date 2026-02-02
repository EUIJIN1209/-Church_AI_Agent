# backend/sermon_agent/graph.py
# -*- coding: utf-8 -*-
"""
graph.py

설교 지원 에이전트의 LangGraph 워크플로우 정의.

워크플로우:
  1. query_router: 질문 분석 및 라우팅 결정
     - RAG 필요시 -> sermon_retriever
     - RAG 불필요시 -> answer_creator
     - 특수 액션(save, reset) -> END
  2. sermon_retriever: 설교 아카이브 벡터 검색
  3. answer_creator: 최종 답변 생성 (OpenAI LLM)

LLM: OpenAI GPT-4o-mini
임베딩: dragonkue/bge-m3-ko (1024차원)
"""

from __future__ import annotations

from typing import Literal

from langgraph.graph import StateGraph, END

from backend.sermon_agent.state.sermon_state import State
from backend.sermon_agent.nodes.query_router import query_router_node
from backend.sermon_agent.nodes.sermon_retriever import sermon_retriever_node
from backend.sermon_agent.nodes.answer_creator import answer_creator_node


# ─────────────────────────────────────────────────────────
# 라우팅 함수
# ─────────────────────────────────────────────────────────


def route_after_router(
    state: State,
) -> Literal["sermon_retriever", "answer_creator", "__end__"]:
    """
    query_router 결과에 따라 다음 노드 결정.

    Returns:
        - "sermon_retriever": RAG 검색 필요
        - "answer_creator": RAG 불필요, 바로 답변 생성
        - "__end__": 특수 액션 (save, reset 등), 즉시 종료
    """
    # next 필드가 있으면 그것을 우선 사용
    next_node = state.get("next")
    if next_node == "end":
        return END

    # router 결정에서 use_rag 확인
    router = state.get("router") or {}
    use_rag = router.get("use_rag", False)

    if use_rag:
        return "sermon_retriever"
    else:
        return "answer_creator"


# ─────────────────────────────────────────────────────────
# 그래프 생성
# ─────────────────────────────────────────────────────────


def create_sermon_agent_graph() -> StateGraph:
    """
    설교 지원 에이전트의 LangGraph 워크플로우 생성.

    그래프 구조:
        START
          │
          ▼
        query_router ──(end)──> END
          │
          ├──(use_rag=true)──> sermon_retriever ──> answer_creator ──> END
          │
          └──(use_rag=false)──> answer_creator ──> END

    Returns:
        컴파일된 StateGraph
    """
    # 그래프 생성
    workflow = StateGraph(State)

    # 노드 추가
    workflow.add_node("query_router", query_router_node)
    workflow.add_node("sermon_retriever", sermon_retriever_node)
    workflow.add_node("answer_creator", answer_creator_node)

    # 엣지 정의
    # 시작 -> query_router
    workflow.set_entry_point("query_router")

    # query_router -> sermon_retriever / answer_creator / END
    workflow.add_conditional_edges(
        "query_router",
        route_after_router,
        {
            "sermon_retriever": "sermon_retriever",
            "answer_creator": "answer_creator",
            END: END,
        },
    )

    # sermon_retriever -> answer_creator
    workflow.add_edge("sermon_retriever", "answer_creator")

    # answer_creator -> END
    workflow.add_edge("answer_creator", END)

    return workflow.compile()


# ─────────────────────────────────────────────────────────
# 싱글톤 인스턴스
# ─────────────────────────────────────────────────────────

_graph_instance = None


def get_sermon_agent_graph():
    """
    설교 에이전트 그래프 인스턴스 가져오기 (싱글톤).

    최초 호출 시 그래프를 생성하고 캐싱.
    """
    global _graph_instance
    if _graph_instance is None:
        print("[graph] Initializing sermon agent graph...", flush=True)
        _graph_instance = create_sermon_agent_graph()
        print("[graph] Graph initialized successfully", flush=True)
    return _graph_instance


def reset_graph():
    """
    그래프 인스턴스 리셋 (테스트용).
    """
    global _graph_instance
    _graph_instance = None
