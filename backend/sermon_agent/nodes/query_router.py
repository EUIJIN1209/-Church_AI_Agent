# backend/sermon_agent/nodes/query_router.py
# -*- coding: utf-8 -*-
"""
query_router.py

역할:
  - 현재 턴의 user_input을 보고,
    1) 이 발화가 어떤 타입인지 분류
       - SERMON_PREP        : 설교 준비 관련 질문
       - COUNSELING         : 성도 상담 관련 질문
       - SCRIPTURE_QA       : 성경 구절/해석 관련 질문
       - SERMON_SEARCH      : 과거 설교 검색 요청
       - SMALL_TALK         : 인사·잡담
       - OTHER              : 그 외
    2) RAG 사용 여부 판단
       - use_rag         : 설교 아카이브 검색이 필요한 경우 True

  - 결정 결과는 state["router"]에 dict로 저장
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Literal, Optional, TypedDict

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

# LangSmith trace 데코레이터 (없으면 no-op)
try:
    from langsmith import traceable
except Exception:  # pragma: no cover
    def traceable(func):
        return func

from backend.sermon_agent.state.sermon_state import State
from datetime import datetime, timezone

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

load_dotenv()

ROUTER_MODEL = os.getenv("ROUTER_MODEL", "gpt-4o-mini")

# 모듈 로드 시점에 즉시 초기화하여 cold start 방지
_client = OpenAI()

def _get_client() -> OpenAI:
    return _client


class RouterDecision(BaseModel):
    """
    LLM이 반환해야 하는 JSON 스키마.
    """
    category: Literal[
        "SERMON_PREP",
        "COUNSELING",
        "SCRIPTURE_QA",
        "SERMON_SEARCH",
        "SMALL_TALK",
        "OTHER"
    ] = Field(
        description=(
            "발화의 주된 타입.\n"
            "- SERMON_PREP: 설교 준비, 본문 해석, 설교 구조, 적용점 등을 묻는 질문\n"
            "- COUNSELING: 성도 상담, 목회 상담, 실생활 적용 등을 묻는 질문\n"
            "- SCRIPTURE_QA: 성경 구절 해석, 신학적 질문 등\n"
            "- SERMON_SEARCH: 과거 설교 검색, 특정 주제의 설교 찾기 등\n"
            "- SMALL_TALK: 인사/감사/잡담/테스트 등\n"
            "- OTHER: 위에 해당하지 않는 기타"
        )
    )
    use_rag: bool = Field(
        description=(
            "설교 아카이브 검색이 필요한 질문이면 true.\n"
            "예: '과거에 이 본문으로 설교한 적이 있나요?', '고난에 대한 설교를 찾아주세요' 등."
        )
    )
    reason: str = Field(
        description="왜 이렇게 판단했는지 간단히 한국어로 설명."
    )


SYSTEM_PROMPT = """
너는 설교 지원 AI 에이전트의 '라우터' 역할을 한다.
사용자(목사님)의 한 발화를 보고 아래 항목을 판단해 JSON으로만 답하라.

1) category:
   - SERMON_PREP        : 설교 준비, 본문 해석, 설교 구조, 적용점, 나눔 질문 생성 등을 묻는 질문
   - COUNSELING         : 성도 상담, 목회 상담, 실생활 적용, 교회 공동체 문제 등을 묻는 질문
   - SCRIPTURE_QA       : 성경 구절 해석, 신학적 질문, 성경 배경 지식 등
   - SERMON_SEARCH      : 과거 설교 검색, 특정 주제/본문의 설교 찾기 등
   - SMALL_TALK         : 인사, 감사, 테스트, 잡담 등
   - OTHER              : 위에 해당하지 않는 경우

2) use_rag (bool):
   - 과거 설교 아카이브 검색이 필요한 질문이면 true.
   - 예: '과거에 이 본문으로 설교한 적이 있나요?', '고난에 대한 설교를 찾아주세요',
         '마태복음 5장으로 설교한 적이 있나요?' 등.
   - 단순 정보 제공이나 일반적인 질문은 false.

반드시 아래 형태의 JSON만 출력하라:

{
  "category": "SERMON_PREP" | "COUNSELING" | "SCRIPTURE_QA" | "SERMON_SEARCH" | "SMALL_TALK" | "OTHER",
  "use_rag": true/false,
  "reason": "판단 이유"
}
"""


@traceable
def query_router_node(state: State) -> State:
    """
    LangGraph 노드: 사용자 질문을 분석하여 카테고리와 RAG 사용 여부를 결정.

    입력:
      - user_input: str (현재 질문)
      - profile_mode: ProfileMode (현재 프로필 모드)

    출력/갱신:
      - state["router"]: RouterDecision 결과
      - state["next"]: 다음 노드 이름
    """
    user_input = state.get("user_input") or ""
    profile_mode = state.get("profile_mode", "research")

    if not user_input.strip():
        # 빈 입력 처리
        state["router"] = {
            "category": "OTHER",
            "use_rag": False,
            "reason": "입력이 비어있음",
        }
        state["next"] = "answer_creator"
        return state

    try:
        client = _get_client()
        
        # 프로필 모드에 따른 컨텍스트 추가
        mode_context = {
            "research": "연구 모드: 학술적이고 깊이 있는 답변을 원하는 상황",
            "counseling": "상담 모드: 실생활 적용과 목회 상담에 초점",
            "education": "교육 모드: 교육적이고 이해하기 쉬운 설명을 원하는 상황",
        }.get(profile_mode, "")

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"현재 모드: {mode_context}\n\n사용자 질문: {user_input}",
            },
        ]

        response = client.chat.completions.create(
            model=ROUTER_MODEL,
            messages=messages,
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        result_text = response.choices[0].message.content or "{}"
        result_dict = json.loads(result_text)

        # RouterDecision 검증
        decision = RouterDecision(**result_dict)

        router_output = {
            "category": decision.category,
            "use_rag": decision.use_rag,
            "reason": decision.reason,
        }

        state["router"] = router_output

        # 다음 노드 결정
        if decision.use_rag:
            state["next"] = "sermon_retriever"
        else:
            state["next"] = "answer_creator"

        print(f"[query_router] category={decision.category}, use_rag={decision.use_rag}")

    except Exception as e:
        print(f"[query_router] 오류 발생: {e}")
        # 오류 시 기본값
        state["router"] = {
            "category": "OTHER",
            "use_rag": False,
            "reason": f"라우터 오류: {str(e)}",
        }
        state["next"] = "answer_creator"

    return state

