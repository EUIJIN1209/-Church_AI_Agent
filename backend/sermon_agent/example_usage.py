# backend/sermon_agent/example_usage.py
# -*- coding: utf-8 -*-
"""
example_usage.py

설교 지원 에이전트 사용 예제.
"""

from datetime import datetime, timezone
from backend.sermon_agent.graph import get_sermon_agent_graph
from backend.sermon_agent.state.sermon_state import State


def example_basic_query():
    """기본 질문 예제"""
    graph = get_sermon_agent_graph()

    # 초기 상태 구성
    initial_state: State = {
        "session_id": "test_session_001",
        "user_id": 1,
        "end_session": False,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "last_activity_at": datetime.now(timezone.utc).isoformat(),
        "turn_count": 1,
        "messages": [],
        "rolling_summary": None,
        "profile_mode": "research",  # "research" | "counseling" | "education"
        "profile_mode_prompt": None,
        "user_context": {},
        "retrieval": {},
        "rag_snippets": [],
        "user_input": "마태복음 5장 3절로 설교한 적이 있나요?",
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

    # 결과 출력
    print("=" * 50)
    print("질문:", result.get("user_input"))
    print("=" * 50)
    print("\n답변:")
    print(result.get("answer", {}).get("text", ""))
    print("\n참고 설교:")
    for ref in result.get("answer", {}).get("references", []):
        print(f"  - {ref.get('title')} ({ref.get('date')})")
    print("=" * 50)


def example_counseling_mode():
    """상담 모드 예제"""
    graph = get_sermon_agent_graph()

    initial_state: State = {
        "session_id": "test_session_002",
        "user_id": 1,
        "end_session": False,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "last_activity_at": datetime.now(timezone.utc).isoformat(),
        "turn_count": 1,
        "messages": [],
        "rolling_summary": None,
        "profile_mode": "counseling",  # 상담 모드
        "profile_mode_prompt": None,
        "user_context": {},
        "retrieval": {},
        "rag_snippets": [],
        "user_input": "고난을 겪는 성도에게 어떻게 위로의 말씀을 전할까요?",
        "answer": {},
        "user_action": None,
        "router": {},
        "next": None,
        "uploaded_images": [],
        "ocr_results": [],
        "streaming_mode": False,
        "streaming_context": {},
    }

    result = graph.invoke(initial_state)

    print("=" * 50)
    print("질문:", result.get("user_input"))
    print("모드: 상담 모드")
    print("=" * 50)
    print("\n답변:")
    print(result.get("answer", {}).get("text", ""))
    print("=" * 50)


def example_education_mode():
    """교육 모드 예제"""
    graph = get_sermon_agent_graph()

    initial_state: State = {
        "session_id": "test_session_003",
        "user_id": 1,
        "end_session": False,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "last_activity_at": datetime.now(timezone.utc).isoformat(),
        "turn_count": 1,
        "messages": [],
        "rolling_summary": None,
        "profile_mode": "education",  # 교육 모드
        "profile_mode_prompt": None,
        "user_context": {},
        "retrieval": {},
        "rag_snippets": [],
        "user_input": "요한복음 3장 16절을 청소년들에게 어떻게 설명하면 좋을까요?",
        "answer": {},
        "user_action": None,
        "router": {},
        "next": None,
        "uploaded_images": [],
        "ocr_results": [],
        "streaming_mode": False,
        "streaming_context": {},
    }

    result = graph.invoke(initial_state)

    print("=" * 50)
    print("질문:", result.get("user_input"))
    print("모드: 교육 모드")
    print("=" * 50)
    print("\n답변:")
    print(result.get("answer", {}).get("text", ""))
    print("=" * 50)


if __name__ == "__main__":
    print("설교 지원 에이전트 사용 예제\n")
    
    print("\n[예제 1] 기본 질문 (연구 모드)")
    example_basic_query()
    
    print("\n[예제 2] 상담 모드")
    example_counseling_mode()
    
    print("\n[예제 3] 교육 모드")
    example_education_mode()

