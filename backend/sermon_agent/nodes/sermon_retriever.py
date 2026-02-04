# backend/sermon_agent/nodes/sermon_retriever.py
# -*- coding: utf-8 -*-
"""
sermon_retriever.py

역할:
  1) user_input과 profile_mode를 기반으로 설교 아카이브 검색
  2) PGVector 기반 벡터 검색 (Cosine Similarity)
  3) 검색 결과를 SermonSnippet 형태로 변환하여 state에 저장

임베딩 모델: dragonkue/bge-m3-ko (1024차원)
"""

from __future__ import annotations

import os
import time
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import psycopg
from psycopg_pool import ConnectionPool
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings

# LangSmith trace 데코레이터
try:
    from langsmith import traceable
except Exception:

    def traceable(func):
        return func


from backend.sermon_agent.state.sermon_state import State, Message, SermonSnippet

load_dotenv()

# ─────────────────────────────────────────────────────────
# 설정
# ─────────────────────────────────────────────────────────

DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise RuntimeError("DATABASE_URL not configured")

if DB_URL.startswith("postgresql+psycopg://"):
    DB_URL = DB_URL.replace("postgresql+psycopg://", "postgresql://", 1)

# Retriever 파라미터
TOP_K = int(os.getenv("SERMON_RETRIEVER_TOP_K", "5"))
SIMILARITY_FLOOR = float(os.getenv("SERMON_RETRIEVER_SIM_FLOOR", "0.3"))

# 임베딩 모델 설정
EMBEDDING_MODEL_NAME = "dragonkue/bge-m3-ko"
EMBEDDING_DIMENSION = 1024
EMBEDDING_CACHE_SIZE = 30

# 전역 상태 (싱글톤)
_embeddings_model: Optional[HuggingFaceEmbeddings] = None
_connection_pool: Optional[ConnectionPool] = None
_embedding_cache: Dict[str, List[float]] = {}
_cache_order: List[str] = []


# ─────────────────────────────────────────────────────────
# 유틸리티 함수
# ─────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_embeddings_model() -> HuggingFaceEmbeddings:
    """임베딩 모델 (싱글톤)."""
    global _embeddings_model
    if _embeddings_model is None:
        print(f"  [Embedding] {EMBEDDING_MODEL_NAME} 모델 로딩 중...", flush=True)
        _embeddings_model = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL_NAME,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        print(f"  [Embedding] 모델 로딩 완료 ({EMBEDDING_DIMENSION}차원)", flush=True)
    return _embeddings_model


def _get_connection_pool() -> ConnectionPool:
    """DB 연결 풀 (싱글톤)."""
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
        print("  [DB Pool] 연결 풀 초기화 완료", flush=True)
    return _connection_pool


def _embed_text(text: str) -> List[float]:
    """텍스트 임베딩 (캐싱 포함)."""
    text_to_embed = (text or "").strip()
    if not text_to_embed:
        return [0.0] * EMBEDDING_DIMENSION

    cache_key = hashlib.md5(text_to_embed.encode("utf-8")).hexdigest()

    global _embedding_cache, _cache_order
    if cache_key in _embedding_cache:
        return _embedding_cache[cache_key]

    try:
        model = _get_embeddings_model()
        embedding = model.embed_query(text_to_embed)

        # 캐시 저장 (FIFO)
        _embedding_cache[cache_key] = embedding
        _cache_order.append(cache_key)

        if len(_cache_order) > EMBEDDING_CACHE_SIZE:
            oldest_key = _cache_order.pop(0)
            _embedding_cache.pop(oldest_key, None)

        return embedding

    except Exception as e:
        print(f"  [Embedding ERROR] {e}", flush=True)
        return [0.0] * EMBEDDING_DIMENSION


def _build_search_query(
    user_input: str,
    profile_mode: str,
) -> str:
    """프로필 모드에 따라 검색 쿼리 구성."""
    base_query = user_input.strip()

    mode_prefix = {
        "research": "신학적 해석, 본문 연구, 설교 구조",
        "counseling": "실생활 적용, 목회 상담, 공동체",
        "education": "교육적 설명, 이해하기 쉬운",
    }.get(profile_mode, "")

    if mode_prefix:
        return f"{mode_prefix} {base_query}"

    return base_query


# ─────────────────────────────────────────────────────────
# 벡터 검색
# ─────────────────────────────────────────────────────────


def _search_sermons(query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    PGVector 기반 설교 검색 (Cosine Similarity).

    Returns:
        유사도 순으로 정렬된 설교 목록
    """
    query_text = (query_text or "").strip()
    if not query_text:
        return []

    # 임베딩 생성
    embed_start = time.time()
    qvec = _embed_text(query_text)
    embed_time = time.time() - embed_start

    qvec_str = "[" + ",".join(f"{v:.6f}" for v in qvec) + "]"

    # SQL 쿼리
    sql = """
        SELECT
            s.id,
            s.title,
            s.sermon_date,
            s.bible_ref,
            s.content_summary,
            s.video_url,
            s.church_name,
            s.preacher,
            (1 - (e.embedding <=> %(qvec)s::vector)) AS similarity
        FROM sermon_embeddings e
        JOIN sermons s ON s.id = e.sermon_id
        ORDER BY e.embedding <=> %(qvec)s::vector
        LIMIT %(limit)s
    """

    # DB 검색
    db_start = time.time()
    rows = []
    pool = _get_connection_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"qvec": qvec_str, "limit": top_k})
            rows = cur.fetchall()
    db_time = time.time() - db_start

    # 결과 가공
    results: List[Dict[str, Any]] = []
    for r in rows:
        similarity = float(r[8]) if r[8] is not None else 0.0

        if similarity < SIMILARITY_FLOOR:
            continue

        # 날짜 포맷팅
        date_str = None
        if r[2]:
            if hasattr(r[2], "strftime"):
                date_str = r[2].strftime("%Y년 %m월 %d일")
            else:
                date_str = str(r[2])

        results.append(
            {
                "sermon_id": str(r[0]),
                "title": r[1] or "",
                "date": date_str,
                "bible_ref": r[3] or "",
                "content_summary": r[4] or "",
                "video_url": r[5] or None,
                "church_name": r[6] or "대덕교회",
                "preacher": r[7] or "",
                "similarity": round(similarity, 4),
            }
        )

    print(
        f"  [Search] '{query_text[:30]}...' -> {len(results)}개 "
        f"(embed: {embed_time:.2f}s, db: {db_time:.2f}s)",
        flush=True,
    )

    return results


# ─────────────────────────────────────────────────────────
# 메인 노드 함수
# ─────────────────────────────────────────────────────────


@traceable
def sermon_retriever_node(state: State) -> Dict[str, Any]:
    """
    LangGraph 노드: 설교 아카이브에서 관련 설교 검색.

    입력:
      - state["user_input"]: 현재 질문
      - state["profile_mode"]: 프로필 모드

    출력:
      - rag_snippets: List[SermonSnippet]
      - retrieval: 검색 메타데이터
      - messages: 로그 메시지 (append)
      - timing: 소요 시간
    """
    start_time = time.time()

    user_input = state.get("user_input") or ""
    profile_mode = state.get("profile_mode", "research")

    print(f"[retriever] input='{user_input[:50]}...'", flush=True)

    # 빈 입력
    if not user_input.strip():
        tool_msg: Message = {
            "role": "tool",
            "content": "[retriever] empty input -> no results",
            "created_at": _now_iso(),
            "meta": {"retrieval": {"used_rag": False}},
        }
        elapsed = time.time() - start_time
        return {
            "rag_snippets": [],
            "retrieval": {"used_rag": False, "count": 0},
            "messages": [tool_msg],
            "timing": {"retriever": elapsed},
        }

    try:
        # 검색 쿼리 구성
        search_query = _build_search_query(user_input, profile_mode)

        # 설교 검색
        sermon_results = _search_sermons(search_query, top_k=TOP_K)

        # SermonSnippet으로 변환
        snippets: List[SermonSnippet] = []
        for r in sermon_results:
            snippet: SermonSnippet = {
                "sermon_id": r["sermon_id"],
                "source": "sermon_archive",
                "title": r["title"],
                "date": r["date"],
                "scripture": r["bible_ref"],
                "summary": r["content_summary"],
                "score": r["similarity"],
                "church_name": r.get("church_name"),
                "preacher": r.get("preacher"),
                "video_url": r.get("video_url"),
            }
            snippets.append(snippet)

        retrieval_info = {
            "used_rag": True,
            "search_query": search_query,
            "count": len(snippets),
            "top_scores": [s["score"] for s in snippets[:3]],
        }

        log_content = (
            f"[retriever] found {len(snippets)} sermons "
            f"(query: '{search_query[:30]}...')"
        )
        tool_msg: Message = {
            "role": "tool",
            "content": log_content,
            "created_at": _now_iso(),
            "meta": {"retrieval": retrieval_info},
        }

        print(f"[retriever] found {len(snippets)} sermons", flush=True)

    except Exception as e:
        print(f"[retriever] ERROR: {e}", flush=True)
        import traceback

        traceback.print_exc()

        snippets = []
        retrieval_info = {
            "used_rag": True,
            "error": str(e),
            "count": 0,
        }
        tool_msg: Message = {
            "role": "tool",
            "content": f"[retriever] error: {e}",
            "created_at": _now_iso(),
            "meta": {"error": str(e)},
        }

    elapsed = time.time() - start_time
    print(f"[retriever] completed in {elapsed:.2f}s", flush=True)

    return {
        "rag_snippets": snippets,
        "retrieval": retrieval_info,
        "messages": [tool_msg],
        "timing": {"retriever": elapsed},
    }


# ─────────────────────────────────────────────────────────
# 독립 실행 함수
# ─────────────────────────────────────────────────────────


def search_sermons_standalone(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """독립 실행 가능한 설교 검색 함수."""
    return _search_sermons(query, top_k)


if __name__ == "__main__":
    print("=" * 60)
    print("설교 벡터 검색 테스트")
    print("=" * 60)

    test_queries = [
        "하나님의 사랑에 대한 설교",
        "고난과 인내",
        "감사하는 삶",
    ]

    for query in test_queries:
        print(f"\n검색어: {query}")
        print("-" * 40)
        results = search_sermons_standalone(query, top_k=3)

        if not results:
            print("  검색 결과 없음")
            continue

        for i, r in enumerate(results, 1):
            print(f"  {i}. [{r['date']}] {r['title']}")
            print(f"     성경: {r['bible_ref']}, 유사도: {r['similarity']:.2%}")
