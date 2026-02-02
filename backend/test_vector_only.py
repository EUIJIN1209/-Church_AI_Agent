#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
벡터 검색만 테스트하는 스크립트 (OpenAI API 불필요)

사용법:
    cd backend
    python test_vector_only.py
"""

import os
import sys
import hashlib
from typing import List, Dict, Any

# Windows 콘솔 UTF-8 설정
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# .env 로드
from dotenv import load_dotenv
load_dotenv()

# DB 연결
import psycopg
from psycopg_pool import ConnectionPool
from langchain_huggingface import HuggingFaceEmbeddings

# -------------------------------------------------------------------
# 설정
# -------------------------------------------------------------------
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    print("[ERROR] DATABASE_URL 환경변수가 설정되지 않았습니다.")
    sys.exit(1)

EMBEDDING_MODEL_NAME = "dragonkue/bge-m3-ko"
EMBEDDING_DIMENSION = 1024
SIMILARITY_FLOOR = 0.3
TOP_K = 5

# 전역 변수
_embeddings_model = None
_connection_pool = None


def get_embeddings_model():
    """임베딩 모델 로드 (싱글톤)"""
    global _embeddings_model
    if _embeddings_model is None:
        print(f"[INFO] 임베딩 모델 로딩 중: {EMBEDDING_MODEL_NAME}")
        print("       (첫 실행 시 모델 다운로드로 시간이 걸릴 수 있습니다)")
        _embeddings_model = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL_NAME,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True},
        )
        print(f"[OK] 모델 로딩 완료 ({EMBEDDING_DIMENSION}차원)")
    return _embeddings_model


def get_connection_pool():
    """DB 연결 풀 (싱글톤)"""
    global _connection_pool
    if _connection_pool is None:
        print(f"[INFO] DB 연결 중...")
        _connection_pool = ConnectionPool(
            conninfo=DB_URL,
            min_size=1,
            max_size=3,
            timeout=30,
        )
        print("[OK] DB 연결 완료")
    return _connection_pool


def embed_text(text: str) -> List[float]:
    """텍스트를 벡터로 변환"""
    model = get_embeddings_model()
    return model.embed_query(text)


def search_sermons(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    PGVector 기반 설교 검색 (Cosine Similarity)
    """
    print(f"\n[SEARCH] {query}")
    print("-" * 50)

    # 쿼리 임베딩 생성
    print("   벡터 변환 중...")
    qvec = embed_text(query)
    qvec_str = "[" + ",".join(f"{v:.6f}" for v in qvec) + "]"

    # SQL 쿼리
    sql = """
        SELECT
            s.id,
            s.title,
            s.sermon_date,
            s.bible_ref,
            s.content_summary,
            s.church_name,
            s.preacher,
            (1 - (e.embedding <=> %(qvec)s::vector)) AS similarity
        FROM sermon_embeddings e
        JOIN sermons s ON s.id = e.sermon_id
        ORDER BY e.embedding <=> %(qvec)s::vector
        LIMIT %(limit)s
    """

    pool = get_connection_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"qvec": qvec_str, "limit": top_k})
            rows = cur.fetchall()

    # 결과 가공
    results = []
    for r in rows:
        similarity = float(r[7]) if r[7] is not None else 0.0

        if similarity < SIMILARITY_FLOOR:
            continue

        # 날짜 포맷팅
        date_str = None
        if r[2]:
            if hasattr(r[2], 'strftime'):
                date_str = r[2].strftime("%Y년 %m월 %d일")
            else:
                date_str = str(r[2])

        results.append({
            "id": r[0],
            "title": r[1] or "",
            "date": date_str,
            "bible_ref": r[3] or "",
            "summary": r[4] or "",
            "church_name": r[5] or "대덕교회",
            "preacher": r[6] or "",
            "similarity": round(similarity, 4),
        })

    return results


def print_results(results: List[Dict[str, Any]]):
    """검색 결과 출력"""
    if not results:
        print("   [NO RESULT] 검색 결과 없음 (유사도 30% 미만)")
        return

    for i, r in enumerate(results, 1):
        print(f"\n   {i}. [{r['date']}] {r['title']}")
        print(f"      [성경] {r['bible_ref']}")
        print(f"      [유사도] {r['similarity']:.2%}")
        if r['summary']:
            summary = r['summary'][:150] + "..." if len(r['summary']) > 150 else r['summary']
            print(f"      [요약] {summary}")


def main():
    print("=" * 60)
    print("대덕교회 설교 벡터 검색 테스트")
    print("=" * 60)
    print(f"임베딩 모델: {EMBEDDING_MODEL_NAME}")
    print(f"유사도 기준: {SIMILARITY_FLOOR:.0%} 이상")
    print(f"검색 결과: 상위 {TOP_K}개")
    print("=" * 60)

    # 테스트 쿼리
    test_queries = [
        "하나님의 사랑에 대한 설교를 찾아줘",
        "고난 중에 어떻게 믿음을 지킬 수 있을까?",
        "성령의 역할과 능력",
        "감사하는 삶",
        "기도의 중요성",
    ]

    for query in test_queries:
        results = search_sermons(query, top_k=3)
        print_results(results)
        print()

    print("=" * 60)
    print("[DONE] 테스트 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
