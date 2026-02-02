# backend/sermon_agent/nodes/answer_creator.py
# -*- coding: utf-8 -*-
"""
answer_creator.py

역할:
  - 검색된 설교 정보와 사용자 질문을 바탕으로 최종 답변 생성
  - 멀티 프로필 모드에 따라 다른 스타일의 답변 제공
  - 스트리밍 모드 지원

핵심:
  - 답변 시 반드시 출처(설교 날짜, 제목)를 명시
  - "YYYY년 MM월 DD일 '설교 제목' 설교에서는..." 형식

LLM: OpenAI GPT-4o-mini
"""

from __future__ import annotations

import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

# LangSmith trace 데코레이터
try:
    from langsmith import traceable
except Exception:
    def traceable(func):
        return func

from backend.sermon_agent.state.sermon_state import (
    State, Message, SermonSnippet, Citation, AnswerResult, ProfileMode
)

load_dotenv()

# ─────────────────────────────────────────────────────────
# OpenAI API 설정
# ─────────────────────────────────────────────────────────

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANSWER_MODEL = os.getenv("ANSWER_MODEL", "gpt-4o-mini")

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


def _extract_scripture_references(text: str) -> List[str]:
    """텍스트에서 성경 구절 참조 추출."""
    patterns = [
        r'[가-힣]+복음?\s*\d+장\s*\d+절?(?:\s*[-~]\s*\d+절?)?',
        r'[가-힣]+복음?\s*\d+:\d+(?:\s*[-~]\s*\d+)?',
        r'[가-힣]+서?\s*\d+장\s*\d+절?(?:\s*[-~]\s*\d+절?)?',
        r'[가-힣]+서?\s*\d+:\d+(?:\s*[-~]\s*\d+)?',
        r'시편\s*\d+편(?:\s*\d+절?)?',
        r'잠언\s*\d+장\s*\d+절?',
    ]

    references = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        references.extend(matches)

    return list(set(references))


# ─────────────────────────────────────────────────────────
# 시스템 프롬프트
# ─────────────────────────────────────────────────────────

SYSTEM_PROMPT_BASE = """당신은 대덕교회의 설교 아카이브를 기반으로 답변하는 AI 사역 비서입니다.

## 핵심 원칙

1. **출처 명시 필수**: 답변 시 반드시 설교의 날짜와 제목을 인용하세요.
   - 형식: "YYYY년 MM월 DD일 '설교 제목' 설교에서는..."
   - 예시: "2024년 03월 10일 '하나님의 사랑' 설교에서는 요한복음 3장 16절을 통해..."

2. **성경 구절 연결**: 설교 본문(성경 구절)이 있다면 함께 언급하세요.

3. **검색 결과 활용**: 제공된 설교 아카이브 내용만을 바탕으로 답변하세요.
   - 아카이브에 없는 내용은 추측하지 마세요

4. **복수 설교 인용**: 관련 설교가 여러 개면 모두 언급하세요.
"""

PROFILE_PROMPTS = {
    "research": """
## 연구 모드 (Research)
- 깊이 있는 본문 해석과 신학적 분석 제공
- 설교 구조와 논리적 흐름 설명
- 여러 설교 간의 연결점 분석

답변 형식:
1. 관련 설교 개요 (날짜, 제목, 본문)
2. 핵심 신학적 메시지
3. 본문 해석 및 적용
4. 참고 설교 목록
""",
    "counseling": """
## 상담 모드 (Counseling)
- 실생활 적용점과 구체적 예시 제공
- 따뜻하고 공감적인 톤 유지
- 위로와 격려의 메시지 전달

답변 형식:
1. 공감과 이해의 표현
2. 관련 설교에서 찾은 지혜 (날짜, 제목 명시)
3. 실생활 적용 방안
4. 격려의 말씀
""",
    "education": """
## 교육 모드 (Education)
- 이해하기 쉬운 설명과 비유 사용
- 단계별 학습 구조 제시
- 소그룹 나눔 질문 제안 가능

답변 형식:
1. 핵심 개념 요약
2. 관련 설교 내용 (날짜, 제목 명시)
3. 쉬운 설명과 예시
4. 나눔/토론 질문 (선택적)
""",
}


def _get_system_prompt(mode: ProfileMode) -> str:
    """프로필 모드에 따른 시스템 프롬프트."""
    specific = PROFILE_PROMPTS.get(mode, PROFILE_PROMPTS["research"])
    return SYSTEM_PROMPT_BASE + specific


# ─────────────────────────────────────────────────────────
# 컨텍스트 포맷팅
# ─────────────────────────────────────────────────────────

def _format_sermon_context(snippets: List[SermonSnippet]) -> str:
    """검색된 설교를 LLM 컨텍스트로 포맷팅."""
    if not snippets:
        return ""

    lines = [
        "=" * 50,
        "[참고 설교 아카이브] 아래 내용만을 바탕으로 답변하세요",
        "=" * 50,
        ""
    ]

    for i, s in enumerate(snippets, 1):
        lines.append(f"[설교 {i}]")
        lines.append(f"  제목: {s.get('title', '제목 없음')}")
        lines.append(f"  날짜: {s.get('date', '날짜 미상')}")

        if s.get("scripture"):
            lines.append(f"  성경 본문: {s['scripture']}")

        if s.get("preacher"):
            lines.append(f"  설교자: {s['preacher']}")

        if s.get("score"):
            lines.append(f"  관련도: {s['score']:.1%}")

        if s.get("summary"):
            lines.append(f"  \n  [설교 내용]")
            lines.append(f"  {s['summary']}")

        lines.append("-" * 50)

    lines.append("")
    lines.append("위 설교 내용을 바탕으로 질문에 답변하세요. 반드시 날짜와 제목을 인용하세요.")
    lines.append("=" * 50)

    return "\n".join(lines)


def _build_user_prompt(
    user_input: str,
    sermon_context: str,
    category: str,
) -> str:
    """사용자 프롬프트 구성."""
    parts = [f"## 질문\n{user_input}"]

    if sermon_context:
        parts.append(f"\n{sermon_context}")

    category_hints = {
        "SERMON_PREP": "\n\n[지시] 설교 준비에 도움이 되도록 과거 설교와의 연결점을 제시해주세요.",
        "COUNSELING": "\n\n[지시] 목회 상담에 활용할 수 있도록 공감과 실용적 조언을 포함해주세요.",
        "SCRIPTURE_QA": "\n\n[지시] 성경 구절 해석과 신학적 배경을 설명해주세요.",
        "SERMON_SEARCH": "\n\n[지시] 검색된 설교 목록을 정리하고 각 설교의 핵심 메시지를 요약해주세요.",
    }

    if category in category_hints:
        parts.append(category_hints[category])

    return "\n".join(parts)


# ─────────────────────────────────────────────────────────
# Fallback 메시지
# ─────────────────────────────────────────────────────────

def _build_fallback_text(
    user_input: str,
    snippets: List[SermonSnippet],
    error: str,
) -> str:
    """LLM 오류 시 fallback 응답."""
    lines = [
        "죄송합니다. 답변 생성 중 문제가 발생했습니다.",
        "",
    ]

    if snippets:
        lines.append("## 검색된 설교 목록")
        for i, s in enumerate(snippets, 1):
            lines.append(f"{i}. [{s.get('date')}] {s.get('title')}")
            if s.get("scripture"):
                lines.append(f"   성경: {s['scripture']}")
        lines.append("")

    lines.append(f"오류: {error[:100]}")
    lines.append("다시 시도해 주세요.")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────
# LLM 호출 (일반)
# ─────────────────────────────────────────────────────────

def _run_answer_llm(
    user_input: str,
    profile_mode: ProfileMode,
    sermon_context: str,
    category: str,
) -> str:
    """OpenAI API를 사용한 답변 생성."""
    client = _get_client()

    system_prompt = _get_system_prompt(profile_mode)
    user_prompt = _build_user_prompt(user_input, sermon_context, category)

    response = client.chat.completions.create(
        model=ANSWER_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=2000,
    )

    return response.choices[0].message.content or ""


# ─────────────────────────────────────────────────────────
# LLM 호출 (스트리밍)
# ─────────────────────────────────────────────────────────

def _run_answer_llm_stream(
    user_input: str,
    profile_mode: ProfileMode,
    sermon_context: str,
    category: str,
) -> Generator[str, None, None]:
    """OpenAI API 스트리밍 답변 생성."""
    client = _get_client()

    system_prompt = _get_system_prompt(profile_mode)
    user_prompt = _build_user_prompt(user_input, sermon_context, category)

    try:
        response = client.chat.completions.create(
            model=ANSWER_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=2000,
            stream=True,
        )

        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    except Exception as e:
        yield f"\n\n[오류 발생: {str(e)}]"


# ─────────────────────────────────────────────────────────
# Citations 구성
# ─────────────────────────────────────────────────────────

def _build_citations(snippets: List[SermonSnippet]) -> List[Citation]:
    """SermonSnippet에서 Citation 목록 생성."""
    citations: List[Citation] = []

    for s in snippets:
        citation: Citation = {
            "sermon_id": s.get("sermon_id", ""),
            "title": s.get("title", ""),
            "date": s.get("date", ""),
            "scripture": s.get("scripture"),
            "score": s.get("score"),
        }
        citations.append(citation)

    return citations


# ─────────────────────────────────────────────────────────
# 메인 노드 함수
# ─────────────────────────────────────────────────────────

@traceable
def answer_creator_node(state: State) -> Dict[str, Any]:
    """
    LangGraph 노드: 최종 답변 생성.

    입력:
      - state["user_input"]: 현재 질문
      - state["profile_mode"]: 프로필 모드
      - state["rag_snippets"]: 검색된 설교들
      - state["router"]: 라우터 결정 (category 포함)
      - state["streaming_mode"]: 스트리밍 여부

    출력:
      - answer: AnswerResult
      - messages: 로그 메시지 (append)
      - streaming_context: 스트리밍용 컨텍스트
      - timing: 소요 시간
    """
    start_time = time.time()

    user_input = state.get("user_input") or ""
    profile_mode = state.get("profile_mode", "research")
    rag_snippets: List[SermonSnippet] = state.get("rag_snippets") or []
    router = state.get("router") or {}
    category = router.get("category", "OTHER")
    streaming_mode = state.get("streaming_mode", False)

    # print(f"[answer] mode={profile_mode}, snippets={len(rag_snippets)}, streaming={streaming_mode}", flush=True)

    # 빈 입력
    if not user_input.strip():
        answer: AnswerResult = {
            "text": "질문을 입력해주세요.",
            "citations": [],
            "scripture_refs": [],
            "category": category,
            "profile_mode": profile_mode,
            "model": ANSWER_MODEL,
            "used_rag": False,
        }
        tool_msg: Message = {
            "role": "tool",
            "content": "[answer] empty input",
            "created_at": _now_iso(),
            "meta": {},
        }
        elapsed = time.time() - start_time
        return {
            "answer": answer,
            "messages": [tool_msg],
            "timing": {"answer": elapsed},
        }

    # 설교 컨텍스트 구성
    if rag_snippets:
        sermon_context = _format_sermon_context(rag_snippets)
    else:
        sermon_context = """
[알림] 관련 설교를 찾지 못했습니다.
제공된 설교 아카이브에서 해당 주제와 관련된 설교가 검색되지 않았습니다.
"""

    # 스트리밍 모드: 컨텍스트만 저장하고 LLM 호출 스킵
    if streaming_mode:
        print(f"[answer] streaming mode - skipping LLM call", flush=True)

        answer: AnswerResult = {
            "text": "",  # 스트리밍으로 채워질 예정
            "citations": _build_citations(rag_snippets),
            "scripture_refs": [],
            "category": category,
            "profile_mode": profile_mode,
            "model": ANSWER_MODEL,
            "used_rag": bool(rag_snippets),
        }

        streaming_context = {
            "user_input": user_input,
            "profile_mode": profile_mode,
            "sermon_context": sermon_context,
            "category": category,
        }

        tool_msg: Message = {
            "role": "tool",
            "content": "[answer] streaming mode - context prepared",
            "created_at": _now_iso(),
            "meta": {"streaming": True},
        }

        elapsed = time.time() - start_time
        return {
            "answer": answer,
            "messages": [tool_msg],
            "streaming_context": streaming_context,
            "timing": {"answer": elapsed},
        }

    # 일반 모드: LLM 호출
    try:
        llm_start = time.time()
        answer_text = _run_answer_llm(
            user_input,
            profile_mode,
            sermon_context,
            category,
        )
        llm_time = time.time() - llm_start

        scripture_refs = _extract_scripture_references(answer_text)
        citations = _build_citations(rag_snippets)

        answer: AnswerResult = {
            "text": answer_text,
            "citations": citations,
            "scripture_refs": scripture_refs,
            "category": category,
            "profile_mode": profile_mode,
            "model": ANSWER_MODEL,
            "used_rag": bool(rag_snippets),
        }

        log_content = (
            f"[answer] generated ({len(answer_text)} chars, {llm_time:.2f}s)"
        )
        tool_msg: Message = {
            "role": "tool",
            "content": log_content,
            "created_at": _now_iso(),
            "meta": {
                "llm_time": llm_time,
                "citations_count": len(citations),
            },
        }

        # assistant 메시지도 추가
        assistant_msg: Message = {
            "role": "assistant",
            "content": answer_text,
            "created_at": _now_iso(),
            "meta": {
                "model": ANSWER_MODEL,
                "category": category,
                "profile_mode": profile_mode,
            },
        }

        print(f"[answer] generated {len(answer_text)} chars in {llm_time:.2f}s", flush=True)

    except Exception as e:
        print(f"[answer] ERROR: {e}", flush=True)
        import traceback
        traceback.print_exc()

        # Fallback
        answer_text = _build_fallback_text(user_input, rag_snippets, str(e))

        answer: AnswerResult = {
            "text": answer_text,
            "citations": _build_citations(rag_snippets),
            "scripture_refs": [],
            "category": category,
            "profile_mode": profile_mode,
            "model": ANSWER_MODEL,
            "used_rag": bool(rag_snippets),
            "error": str(e),
        }

        tool_msg: Message = {
            "role": "tool",
            "content": f"[answer] error: {e}",
            "created_at": _now_iso(),
            "meta": {"error": str(e)},
        }

        assistant_msg: Message = {
            "role": "assistant",
            "content": answer_text,
            "created_at": _now_iso(),
            "meta": {"error": str(e)},
        }

    elapsed = time.time() - start_time
    print(f"[answer] completed in {elapsed:.2f}s", flush=True)

    return {
        "answer": answer,
        "messages": [tool_msg, assistant_msg],
        "timing": {"answer": elapsed},
    }


# ─────────────────────────────────────────────────────────
# 스트리밍 함수 (외부 호출용)
# ─────────────────────────────────────────────────────────

def stream_answer(streaming_context: Dict[str, Any]) -> Generator[str, None, None]:
    """
    스트리밍 컨텍스트를 사용해 답변 스트리밍.

    Usage:
        result = graph.invoke(state)
        ctx = result["streaming_context"]
        for chunk in stream_answer(ctx):
            print(chunk, end="", flush=True)
    """
    user_input = streaming_context.get("user_input", "")
    profile_mode = streaming_context.get("profile_mode", "research")
    sermon_context = streaming_context.get("sermon_context", "")
    category = streaming_context.get("category", "OTHER")

    yield from _run_answer_llm_stream(
        user_input,
        profile_mode,
        sermon_context,
        category,
    )
