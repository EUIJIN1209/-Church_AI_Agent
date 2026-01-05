# backend/sermon_agent/nodes/sermon_retriever.py
# -*- coding: utf-8 -*-
"""
sermon_retriever.py

역할:
  1) user_input과 profile_mode를 기반으로 설교 아카이브 검색
  2) PGVector 기반 벡터 검색으로 관련 설교 찾기
  3) 검색 결과를 SermonSnippet 형태로 변환하여 state에 저장
"""

from __future__ import annotations

import os
import hashlib
from typing import Any, Dict, List, Optional, Tuple

import psycopg
from psycopg_pool import ConnectionPool
from dotenv import load_dotenv
from openai import OpenAI

# LangSmith trace 데코레이터
try:
    from langsmith import traceable
except Exception:
    def traceable(func):
        return func

from backend.sermon_agent.state.sermon_state import State, SermonSnippet

load_dotenv()

# -------------------------------------------------------------------
# DB URL
# -------------------------------------------------------------------
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise RuntimeError("DATABASE_URL not configured")

if DB_URL.startswith("postgresql+psycopg://"):
    DB_URL = DB_URL.replace("postgresql+psycopg://", "postgresql://", 1)

# -------------------------------------------------------------------
# Retriever tunable parameters
# -------------------------------------------------------------------
RAW_TOP_K = int(os.getenv("SERMON_RETRIEVER_RAW_TOP_K", "10"))
CONTEXT_TOP_K = int(os.getenv("SERMON_RETRIEVER_CONTEXT_TOP_K", "5"))
SIMILARITY_FLOOR = float(os.getenv("SERMON_RETRIEVER_SIM_FLOOR", "0.3"))

# -------------------------------------------------------------------
# OpenAI 임베딩 설정
# -------------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not configured in .env")

OPENAI_MODEL = "text-embedding-3-small"  # 1536차원
EMBEDDING_CACHE_SIZE = 30

# 전역 상태
_openai_client: Optional[OpenAI] = None
_connection_pool: Optional[ConnectionPool] = None
_embedding_cache: Dict[str, List[float]] = {}
_cache_order: List[str] = []


def _get_openai_client() -> OpenAI:
    """OpenAI 클라이언트 가져오기 또는 생성 (싱글톤)"""
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=OPENAI_API_KEY)
        print("  ✅ [OpenAI] 클라이언트 초기화 완료", flush=True)
    return _openai_client


def _get_connection_pool() -> ConnectionPool:
    """DB 연결 풀 가져오기 또는 생성 (싱글톤)"""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = ConnectionPool(
            conninfo=DB_URL,
            min_size=1,
            max_size=3,
            timeout=30,
            max_lifetime=300,
            max_idle=60,
            reconnect_timeout=10,
        )
        print("  ✅ [DB Pool] 연결 풀 초기화 완료", flush=True)
    return _connection_pool


def _embed_text(text: str) -> List[float]:
    """
    OpenAI API를 사용한 임베딩 생성 (캐싱 포함)
    """
    text_to_embed = (text or "").strip()
    if not text_to_embed:
        return [0.0] * 1536

    cache_key = hashlib.md5(text_to_embed.encode("utf-8")).hexdigest()

    global _embedding_cache, _cache_order
    if cache_key in _embedding_cache:
        return _embedding_cache[cache_key]

    try:
        client = _get_openai_client()
        response = client.embeddings.create(model=OPENAI_MODEL, input=text_to_embed)
        embedding = response.data[0].embedding

        # 캐시 저장 (FIFO 방식)
        _embedding_cache[cache_key] = embedding
        _cache_order.append(cache_key)

        if len(_cache_order) > EMBEDDING_CACHE_SIZE:
            oldest_key = _cache_order.pop(0)
            _embedding_cache.pop(oldest_key, None)

        return embedding

    except Exception as e:
        print(f"  ❌ [OpenAI API 오류] {e}", flush=True)
        return [0.0] * 1536


def _build_search_query(
    user_input: str,
    profile_mode: str,
    user_context: Optional[Dict[str, Any]],
) -> str:
    """
    프로필 모드에 따라 검색 쿼리를 구성.

    - research: 학술적, 깊이 있는 검색
    - counseling: 실생활 적용 중심 검색
    - education: 교육적, 이해하기 쉬운 검색
    """
    base_query = user_input.strip()

    # 프로필 모드에 따른 쿼리 보강
    mode_prefix = {
        "research": "신학적 해석, 본문 연구, 설교 구조",
        "counseling": "실생활 적용, 목회 상담, 공동체",
        "education": "교육적 설명, 이해하기 쉬운",
    }.get(profile_mode, "")

    if mode_prefix:
        return f"{mode_prefix} {base_query}"
    
    return base_query


def _search_sermons(
    query_text: str,
    user_id: Optional[int] = None,
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """
    PGVector 기반 설교 검색.

    설교 테이블 구조 가정:
    - sermons 테이블: id, title, date, scripture, summary, full_text, thumbnail_url, user_id
    - sermon_embeddings 테이블: sermon_id, embedding (vector), field ('title' 또는 'summary')
    """
    query_text = (query_text or "").strip()
    if not query_text:
        return []

    # 임베딩 계산
    try:
        qvec = _embed_text(query_text)
    except Exception as e:
        print(f"[sermon_retriever] embed failed: {e}")
        return []

    qvec_str = "[" + ",".join(f"{v:.6f}" for v in qvec) + "]"

    # PGVector 검색
    sql = """
        SELECT
            s.id,
            s.title,
            s.date,
            s.scripture,
            s.summary,
            s.full_text,
            s.thumbnail_url,
            (1 - (e.embedding <=> %(qvec)s::vector)) AS similarity
        FROM sermon_embeddings e
        JOIN sermons s ON s.id = e.sermon_id
        WHERE e.field = 'summary'
    """
    params = {"qvec": qvec_str, "limit": top_k}

    # 사용자 필터 추가 (해당 사용자의 설교만 검색)
    if user_id:
        sql += " AND s.user_id = %(user_id)s"
        params["user_id"] = user_id

    sql += """
        ORDER BY e.embedding <=> %(qvec)s::vector
        LIMIT %(limit)s
    """
    params["limit"] = top_k

    rows = []
    pool = _get_connection_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    # 결과 가공
    results: List[Dict[str, Any]] = []
    for r in rows:
        similarity = float(r[7]) if r[7] is not None else None
        
        # similarity floor 적용
        if similarity is not None and similarity < SIMILARITY_FLOOR:
            continue

        results.append({
            "sermon_id": str(r[0]),
            "title": r[1] or "",
            "date": r[2].isoformat() if r[2] else None,
            "scripture": r[3] or "",
            "summary": r[4] or "",
            "full_text": r[5] or "",
            "thumbnail_url": r[6] or None,
            "similarity": similarity,
        })

    # similarity 내림차순 정렬
    results.sort(key=lambda x: (x["similarity"] is not None, x["similarity"]), reverse=True)

    return results[:CONTEXT_TOP_K]


@traceable
def sermon_retriever_node(state: State) -> State:
    """
    LangGraph 노드: 설교 아카이브에서 관련 설교 검색.

    입력:
      - user_input: str (현재 질문)
      - profile_mode: ProfileMode (현재 프로필 모드)
      - user_id: Optional[int] (사용자 ID)

    출력/갱신:
      - state["rag_snippets"]: List[SermonSnippet]
      - state["retrieval"]: 검색 메타데이터
    """
    user_input = state.get("user_input") or ""
    profile_mode = state.get("profile_mode", "research")
    user_id = state.get("user_id")
    user_context = state.get("user_context") or {}

    if not user_input.strip():
        state["rag_snippets"] = []
        state["retrieval"] = {"used_rag": False, "rag_snippets": []}
        return state

    try:
        # 검색 쿼리 구성
        search_query = _build_search_query(user_input, profile_mode, user_context)

        # 설교 검색
        sermon_results = _search_sermons(
            query_text=search_query,
            user_id=user_id,
            top_k=RAW_TOP_K,
        )

        # SermonSnippet 형태로 변환
        snippets: List[SermonSnippet] = []
        for r in sermon_results:
            snippet: SermonSnippet = {
                "sermon_id": r["sermon_id"],
                "source": "sermon_archive",
                "title": r["title"],
                "date": r["date"],
                "scripture": r["scripture"],
                "summary": r["summary"],
                "score": r["similarity"],
                "thumbnail_url": r.get("thumbnail_url"),
                "full_text": r.get("full_text"),
            }
            snippets.append(snippet)

        state["rag_snippets"] = snippets
        state["retrieval"] = {
            "used_rag": True,
            "rag_snippets": snippets,
            "search_query": search_query,
            "count": len(snippets),
        }

        print(f"[sermon_retriever] 검색 완료: {len(snippets)}개 설교 발견")

    except Exception as e:
        print(f"[sermon_retriever] 오류 발생: {e}")
        state["rag_snippets"] = []
        state["retrieval"] = {
            "used_rag": True,
            "rag_snippets": [],
            "error": str(e),
        }

    return state

