# backend/sermon_agent/graph.py
# -*- coding: utf-8 -*-
"""
graph.py

설교 지원 에이전트의 LangGraph 워크플로우 정의.

워크플로우:
  1. query_router: 질문 분석 및 라우팅 결정
  2. sermon_retriever: 설교 아카이브 검색 (RAG 필요시)
  3. answer_creator: 최종 답변 생성
"""

from __future__ import annotations

from typing import Literal

from langgraph.graph import StateGraph, END

from backend.sermon_agent.state.sermon_state import State
from backend.sermon_agent.nodes.query_router import query_router_node
from backend.sermon_agent.nodes.sermon_retriever import sermon_retriever_node
from backend.sermon_agent.nodes.answer_creator import answer_creator_node


def should_use_rag(state: State) -> Literal["sermon_retriever", "answer_creator"]:
    """
    라우터 결과에 따라 RAG 검색 여부 결정.
    """
    router = state.get("router") or {}
    use_rag = router.get("use_rag", False)
    
    if use_rag:
        return "sermon_retriever"
    else:
        return "answer_creator"


def create_sermon_agent_graph() -> StateGraph:
    """
    설교 지원 에이전트의 LangGraph 워크플로우 생성.

    Returns:
        StateGraph: 구성된 그래프
    """
    # 그래프 생성
    workflow = StateGraph(State)

    # 노드 추가
    workflow.add_node("query_router", query_router_node)
    workflow.add_node("sermon_retriever", sermon_retriever_node)
    workflow.add_node("answer_creator", answer_creator_node)

    # 엣지 정의
    # 시작 → query_router
    workflow.set_entry_point("query_router")

    # query_router → sermon_retriever 또는 answer_creator
    workflow.add_conditional_edges(
        "query_router",
        should_use_rag,
        {
            "sermon_retriever": "sermon_retriever",
            "answer_creator": "answer_creator",
        },
    )

    # sermon_retriever → answer_creator
    workflow.add_edge("sermon_retriever", "answer_creator")

    # answer_creator → END
    workflow.add_edge("answer_creator", END)

    return workflow.compile()


# 전역 그래프 인스턴스 (싱글톤)
_graph_instance = None


def get_sermon_agent_graph():
    """
    설교 에이전트 그래프 인스턴스 가져오기 (싱글톤).
    """
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = create_sermon_agent_graph()
    return _graph_instance

