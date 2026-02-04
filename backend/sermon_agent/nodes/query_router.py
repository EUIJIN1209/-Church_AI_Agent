# backend/sermon_agent/nodes/query_router.py
# -*- coding: utf-8 -*-
"""
query_router.py

역할:
  - 현재 턴의 user_input을 보고 분류 및 라우팅 결정
    1) 발화 타입 분류 (SERMON_PREP, COUNSELING, SCRIPTURE_QA, SERMON_SEARCH, SMALL_TALK, OTHER)
    2) RAG 사용 여부 판단 (설교 아카이브 검색 필요 여부)

  - 결정 결과는 state["router"]에 저장
  - 메시지 로그를 state["messages"]에 append

LLM: OpenAI GPT-4o-mini
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

# LangSmith trace 데코레이터
try:
    from langsmith import traceable
except Exception:

    def traceable(func):
        return func


from backend.sermon_agent.state.sermon_state import (
    State,
    Message,
    RouterDecision,
    QuestionCategory,
)

load_dotenv()

# ─────────────────────────────────────────────────────────
# OpenAI API 설정
# ─────────────────────────────────────────────────────────

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ROUTER_MODEL = os.getenv("ROUTER_MODEL", "gpt-4o-mini")

_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


# ─────────────────────────────────────────────────────────
# 유틸리티 함수
# ─────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_json(text: str) -> str:
    """응답에서 JSON 블록만 추출."""
    # ```json ... ``` 형식 처리
    if "```" in text:
        lines = text.split("\n")
        json_lines = []
        in_json = False
        for line in lines:
            if line.strip().startswith("```json"):
                in_json = True
                continue
            elif line.strip() == "```":
                in_json = False
                continue
            if in_json:
                json_lines.append(line)
        if json_lines:
            return "\n".join(json_lines)

    # { ... } 블록 추출
    start = text.find("{")
    if start == -1:
        raise ValueError(f"JSON 시작점 없음: {text[:100]}")

    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    raise ValueError(f"JSON 종료점 없음: {text[:100]}")


# ─────────────────────────────────────────────────────────
# Pydantic 스키마
# ─────────────────────────────────────────────────────────


class RouterDecisionSchema(BaseModel):
    """LLM이 반환해야 하는 JSON 스키마."""

    category: Literal[
        "SERMON_PREP",
        "COUNSELING",
        "SCRIPTURE_QA",
        "SERMON_SEARCH",
        "SMALL_TALK",
        "OTHER",
    ] = Field(
        description=(
            "발화 타입:\n"
            "- SERMON_PREP: 설교 준비, 본문 해석, 설교 구조, 적용점 등\n"
            "- COUNSELING: 성도 상담, 목회 상담, 실생활 적용 등\n"
            "- SCRIPTURE_QA: 성경 구절 해석, 신학적 질문 등\n"
            "- SERMON_SEARCH: 과거 설교 검색, 특정 주제의 설교 찾기 등\n"
            "- SMALL_TALK: 인사/감사/잡담/테스트 등\n"
            "- OTHER: 위에 해당하지 않는 기타"
        )
    )
    use_rag: bool = Field(
        description=(
            "설교 아카이브 검색이 필요하면 true.\n"
            "예: '설교를 찾아줘', '~에 대해 어떻게 말씀하셨나요?', '과거 설교 검색' 등"
        )
    )
    reason: str = Field(description="판단 이유 (한국어로 간단히)")


# ─────────────────────────────────────────────────────────
# 시스템 프롬프트
# ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
너는 대덕교회 설교 지원 AI 에이전트의 '라우터' 역할을 한다.
사용자(목사님/성도님)의 한 발화를 보고 아래 항목을 판단해 JSON으로만 답하라.

1) category:
   - SERMON_PREP    : 설교 준비, 본문 해석, 설교 구조, 적용점, 나눔 질문 생성 등
   - COUNSELING     : 성도 상담, 목회 상담, 실생활 적용, 교회 공동체 문제 등
   - SCRIPTURE_QA   : 성경 구절 해석, 신학적 질문, 성경 배경 지식 등
   - SERMON_SEARCH  : 과거 설교 검색, 특정 주제/본문의 설교 찾기 등
   - SMALL_TALK     : 인사, 감사, 테스트, 잡담 등
   - OTHER          : 위에 해당하지 않는 경우

2) use_rag (bool):
   - 과거 설교 아카이브 검색이 필요한 질문이면 true
   - 예시 (true):
     * '하나님의 사랑에 대한 설교를 찾아줘'
     * '고난에 대해 어떻게 말씀하셨나요?'
     * '감사에 대한 설교가 있나요?'
     * '마태복음 5장으로 설교한 적 있나요?'
     * 설교/말씀/본문/주제 관련 질문 대부분
   - 예시 (false):
     * '안녕하세요' (인사)
     * '테스트입니다' (잡담)

3) reason: 판단 이유를 간단히 한국어로 설명

반드시 아래 형태의 JSON만 출력:
{
  "category": "SERMON_PREP" | "COUNSELING" | "SCRIPTURE_QA" | "SERMON_SEARCH" | "SMALL_TALK" | "OTHER",
  "use_rag": true | false,
  "reason": "판단 이유"
}
"""


# ─────────────────────────────────────────────────────────
# LLM 호출
# ─────────────────────────────────────────────────────────


def _call_router_llm(text: str, profile_mode: str) -> RouterDecisionSchema:
    """OpenAI API를 사용한 라우터 결정."""
    client = _get_client()

    mode_context = {
        "research": "연구 모드: 학술적/깊이 있는 답변",
        "counseling": "상담 모드: 실생활 적용/목회 상담",
        "education": "교육 모드: 교육적/쉬운 설명",
    }.get(profile_mode, "")

    user_prompt = f"""현재 모드: {mode_context}
사용자 질문: {text}
"""

    response = client.chat.completions.create(
        model=ROUTER_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = json.loads(_extract_json(raw))

    return RouterDecisionSchema(**data)


# ─────────────────────────────────────────────────────────
# 메인 노드 함수
# ─────────────────────────────────────────────────────────


@traceable
def query_router_node(state: State) -> Dict[str, Any]:
    """
    LangGraph 노드: 사용자 질문을 분석하여 카테고리와 RAG 사용 여부 결정.

    입력:
      - state["user_input"]: 현재 질문
      - state["user_action"]: 사용자 액션 (chat, save, reset 등)
      - state["profile_mode"]: 프로필 모드

    출력:
      - router: RouterDecision
      - next: 다음 노드 이름
      - messages: 로그 메시지 (append)
      - timing: 소요 시간
    """
    start_time = time.time()

    text = (state.get("user_input") or "").strip()
    action = (state.get("user_action") or "chat").strip()
    profile_mode = state.get("profile_mode", "research")

    # print(f"[router] action='{action}', input='{text[:50] if text else '(empty)'}...'", flush=True)

    # ── 특수 액션 처리 ──────────────────────────────────

    # 저장 액션
    if action == "save":
        router_info: RouterDecision = {
            "category": "OTHER",
            "use_rag": False,
            "reason": "저장 액션: 대화 내용 저장",
        }
        tool_msg: Message = {
            "role": "tool",
            "content": "[router] action=save -> persist",
            "created_at": _now_iso(),
            "meta": {"no_store": True, "router": router_info},
        }
        elapsed = time.time() - start_time
        return {
            "router": router_info,
            "next": "end",
            "messages": [tool_msg],
            "timing": {"router": elapsed},
        }

    # 리셋 액션
    if action in ("reset", "reset_save", "reset_drop"):
        router_info: RouterDecision = {
            "category": "OTHER",
            "use_rag": False,
            "reason": f"리셋 액션: {action}",
        }
        tool_msg: Message = {
            "role": "tool",
            "content": f"[router] action={action} -> end",
            "created_at": _now_iso(),
            "meta": {"no_store": True, "router": router_info},
        }
        elapsed = time.time() - start_time
        return {
            "router": router_info,
            "next": "end",
            "messages": [tool_msg],
            "timing": {"router": elapsed},
        }

    # 빈 입력
    if not text:
        router_info: RouterDecision = {
            "category": "OTHER",
            "use_rag": False,
            "reason": "빈 입력",
        }
        tool_msg: Message = {
            "role": "tool",
            "content": "[router] empty input -> end",
            "created_at": _now_iso(),
            "meta": {"router": router_info},
        }
        elapsed = time.time() - start_time
        return {
            "router": router_info,
            "next": "end",
            "messages": [tool_msg],
            "timing": {"router": elapsed},
        }

    # ── LLM 라우터 호출 ─────────────────────────────────

    try:
        decision = _call_router_llm(text, profile_mode)
        router_info: RouterDecision = {
            "category": decision.category,
            "use_rag": decision.use_rag,
            "reason": decision.reason,
        }

        log_content = (
            f"[router] category={decision.category}, "
            f"use_rag={decision.use_rag}, "
            f"reason={decision.reason[:50]}..."
        )
        tool_msg: Message = {
            "role": "tool",
            "content": log_content,
            "created_at": _now_iso(),
            "meta": {"router": router_info},
        }

        # 다음 노드 결정
        if decision.use_rag:
            next_node = "sermon_retriever"
        else:
            next_node = "answer_creator"

        print(f"[router] -> {next_node} (category={decision.category})", flush=True)

    except Exception as e:
        print(f"[router] ERROR: {e}", flush=True)
        # 에러 시 안전하게 RAG 사용
        router_info: RouterDecision = {
            "category": "SERMON_SEARCH",
            "use_rag": True,
            "reason": f"라우터 오류로 기본 검색 모드: {str(e)[:50]}",
        }
        tool_msg: Message = {
            "role": "tool",
            "content": f"[router] error -> fallback to RAG: {e}",
            "created_at": _now_iso(),
            "meta": {"error": str(e), "router": router_info},
        }
        next_node = "sermon_retriever"

    elapsed = time.time() - start_time
    print(f"[router] completed in {elapsed:.2f}s", flush=True)

    return {
        "router": router_info,
        "next": next_node,
        "messages": [tool_msg],
        "timing": {"router": elapsed},
    }


# ─────────────────────────────────────────────────────────
# 테스트
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_inputs = [
        "하나님의 사랑에 대한 설교를 찾아줘",
        "고난 중에 어떻게 믿음을 지킬 수 있을까요?",
        "안녕하세요",
        "마태복음 5장에 대해 설명해주세요",
    ]

    for text in test_inputs:
        print(f"\n입력: {text}")
        result = query_router_node(
            {
                "user_input": text,
                "profile_mode": "research",
            }
        )
        print(f"결과: {result['router']}")
