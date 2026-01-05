# backend/sermon_agent/config.py
# -*- coding: utf-8 -*-
"""
config.py

설교 지원 에이전트 설정 파일.
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()


class SermonAgentConfig:
    """설교 에이전트 설정 클래스"""

    # OpenAI 설정
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ROUTER_MODEL = os.getenv("ROUTER_MODEL", "gpt-4o-mini")
    ANSWER_MODEL = os.getenv("ANSWER_MODEL", "gpt-4o-mini")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    # 데이터베이스 설정
    DATABASE_URL = os.getenv("DATABASE_URL")

    # 검색 설정
    SERMON_RETRIEVER_RAW_TOP_K = int(os.getenv("SERMON_RETRIEVER_RAW_TOP_K", "10"))
    SERMON_RETRIEVER_CONTEXT_TOP_K = int(os.getenv("SERMON_RETRIEVER_CONTEXT_TOP_K", "5"))
    SERMON_RETRIEVER_SIM_FLOOR = float(os.getenv("SERMON_RETRIEVER_SIM_FLOOR", "0.3"))

    # 프로필 모드 기본값
    DEFAULT_PROFILE_MODE = os.getenv("DEFAULT_PROFILE_MODE", "research")

    # 임베딩 캐시 설정
    EMBEDDING_CACHE_SIZE = int(os.getenv("EMBEDDING_CACHE_SIZE", "30"))

    @classmethod
    def validate(cls) -> Dict[str, Any]:
        """
        설정 검증 및 누락된 항목 확인.

        Returns:
            Dict[str, Any]: 검증 결과
        """
        errors = []
        warnings = []

        if not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY가 설정되지 않았습니다.")

        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL이 설정되지 않았습니다.")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }


# 전역 설정 인스턴스
config = SermonAgentConfig()

