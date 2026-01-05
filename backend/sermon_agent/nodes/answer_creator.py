# backend/sermon_agent/nodes/answer_creator.py
# -*- coding: utf-8 -*-
"""
answer_creator.py

역할:
  - 검색된 설교 정보와 사용자 질문을 바탕으로 최종 답변 생성
  - 멀티 프로필 모드에 따라 다른 스타일의 답변 제공
    * research: 학술적, 깊이 있는 답변
    * counseling: 실생활 적용 중심 답변
    * education: 교육적, 이해하기 쉬운 답변
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

# LangSmith trace 데코레이터
try:
    from langsmith import traceable
except Exception:
    def traceable(func):
        return func

from backend.sermon_agent.state.sermon_state import State, SermonSnippet, ProfileMode

load_dotenv()

ANSWER_MODEL = os.getenv("ANSWER_MODEL", "gpt-4o-mini")

_client = OpenAI()

def _get_client() -> OpenAI:
    return _client


def _get_profile_prompt(mode: ProfileMode) -> str:
    """
    프로필 모드에 따른 시스템 프롬프트 반환.
    """
    prompts = {
        "research": """
당신은 설교 연구를 지원하는 학술적 AI 어시스턴트입니다.

## 역할
- 깊이 있는 본문 해석과 신학적 분석 제공
- 설교 구조와 논리적 흐름 제안
- 학술적 참고 자료와 배경 지식 제공

## 답변 스타일
- 정확하고 깊이 있는 설명
- 신학적 용어 사용 가능
- 학술적 근거 제시
- 구조화된 논리적 흐름
""",
        "counseling": """
당신은 목회 상담을 지원하는 실용적 AI 어시스턴트입니다.

## 역할
- 실생활 적용점과 구체적 예시 제공
- 성도 상담에 도움이 되는 실용적 조언
- 공동체 문제 해결 방안 제시
- 따뜻하고 공감적인 톤

## 답변 스타일
- 실용적이고 구체적인 예시
- 공감과 이해를 바탕으로 한 조언
- 실생활 적용 중심
- 따뜻하고 친근한 톤
""",
        "education": """
당신은 설교 교육을 지원하는 교육적 AI 어시스턴트입니다.

## 역할
- 이해하기 쉬운 설명과 비유 제공
- 단계별 학습 구조 제시
- 핵심 개념의 명확한 정리
- 교육적 질문과 토론 주제 제안

## 답변 스타일
- 명확하고 이해하기 쉬운 설명
- 비유와 예시 활용
- 단계별 구조화
- 교육적 질문 포함
""",
    }
    return prompts.get(mode, prompts["research"])


def _format_sermon_context(snippets: List[SermonSnippet]) -> str:
    """
    검색된 설교 스니펫을 컨텍스트 텍스트로 변환.
    """
    if not snippets:
        return ""

    context_parts = ["## 참고 설교 아카이브\n"]
    
    for i, snippet in enumerate(snippets, 1):
        parts = [f"### {i}. {snippet.get('title', '제목 없음')}"]
        
        if snippet.get("date"):
            parts.append(f"**날짜**: {snippet['date']}")
        
        if snippet.get("scripture"):
            parts.append(f"**성경 구절**: {snippet['scripture']}")
        
        if snippet.get("summary"):
            parts.append(f"**요약**: {snippet['summary']}")
        
        context_parts.append("\n".join(parts))
        context_parts.append("")  # 빈 줄

    return "\n".join(context_parts)


def _extract_scripture_references(text: str) -> List[str]:
    """
    텍스트에서 성경 구절 참조를 추출 (간단한 휴리스틱).
    예: "마태복음 5장 3절", "요한복음 3:16" 등
    """
    import re
    
    # 간단한 패턴 매칭 (실제로는 더 정교한 파싱 필요)
    patterns = [
        r'[가-힣]+복음?\s*\d+장\s*\d+절?',
        r'[가-힣]+복음?\s*\d+:\d+',
        r'[가-힣]+서?\s*\d+장\s*\d+절?',
        r'[가-힣]+서?\s*\d+:\d+',
    ]
    
    references = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        references.extend(matches)
    
    return list(set(references))  # 중복 제거


@traceable
def answer_creator_node(state: State) -> State:
    """
    LangGraph 노드: 최종 답변 생성.

    입력:
      - user_input: str (현재 질문)
      - profile_mode: ProfileMode (현재 프로필 모드)
      - rag_snippets: List[SermonSnippet] (검색된 설교들)
      - router: Dict (질문 카테고리 등)

    출력/갱신:
      - state["answer"]: 최종 답변 (텍스트, 참고 설교 목록 등)
    """
    user_input = state.get("user_input") or ""
    profile_mode = state.get("profile_mode", "research")
    rag_snippets: List[SermonSnippet] = state.get("rag_snippets") or []
    router = state.get("router") or {}
    category = router.get("category", "OTHER")

    if not user_input.strip():
        state["answer"] = {
            "text": "질문을 입력해주세요.",
            "references": [],
            "scripture_refs": [],
        }
        return state

    try:
        client = _get_client()

        # 프로필 모드에 따른 시스템 프롬프트
        system_prompt = _get_profile_prompt(profile_mode)
        
        # 설교 컨텍스트 구성
        sermon_context = _format_sermon_context(rag_snippets) if rag_snippets else ""

        # 사용자 메시지 구성
        user_message_parts = [f"질문: {user_input}"]
        
        if sermon_context:
            user_message_parts.append("\n" + sermon_context)
        
        if category == "SERMON_PREP":
            user_message_parts.append(
                "\n위 질문에 대해 설교 준비에 도움이 되는 답변을 제공해주세요. "
                "참고 설교가 있다면 그것을 바탕으로 과거 설교와의 연결점을 제시해주세요."
            )
        elif category == "COUNSELING":
            user_message_parts.append(
                "\n위 질문에 대해 목회 상담에 도움이 되는 실용적이고 공감적인 답변을 제공해주세요."
            )
        elif category == "SCRIPTURE_QA":
            user_message_parts.append(
                "\n위 질문에 대해 성경 구절 해석과 신학적 배경을 포함한 답변을 제공해주세요."
            )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "\n".join(user_message_parts)},
        ]

        response = client.chat.completions.create(
            model=ANSWER_MODEL,
            messages=messages,
            temperature=0.7,
            stream=state.get("streaming_mode", False),
        )

        if state.get("streaming_mode", False):
            # 스트리밍 모드 처리 (추후 구현)
            answer_text = ""
            for chunk in response:
                if chunk.choices[0].delta.content:
                    answer_text += chunk.choices[0].delta.content
        else:
            answer_text = response.choices[0].message.content or ""

        # 성경 구절 참조 추출
        scripture_refs = _extract_scripture_references(answer_text)

        # 참고 설교 목록 구성
        references = []
        for snippet in rag_snippets:
            ref = {
                "sermon_id": snippet.get("sermon_id"),
                "title": snippet.get("title"),
                "date": snippet.get("date"),
                "scripture": snippet.get("scripture"),
                "thumbnail_url": snippet.get("thumbnail_url"),
            }
            references.append(ref)

        state["answer"] = {
            "text": answer_text,
            "references": references,
            "scripture_refs": scripture_refs,
            "category": category,
            "profile_mode": profile_mode,
        }

        print(f"[answer_creator] 답변 생성 완료 (카테고리: {category}, 모드: {profile_mode})")

    except Exception as e:
        print(f"[answer_creator] 오류 발생: {e}")
        state["answer"] = {
            "text": f"답변 생성 중 오류가 발생했습니다: {str(e)}",
            "references": [],
            "scripture_refs": [],
            "error": str(e),
        }

    return state

