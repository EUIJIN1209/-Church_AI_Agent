"""
대덕교회 설교 데이터 DB Import 스크립트

사용법:
    python import_data.py

환경변수 (.env 파일):
    DATABASE_URL=postgresql://user:password@host:port/dbname
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any

import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 경로 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERMONS_FILE = os.path.join(BASE_DIR, "crawling", "output", "daedeok_sermons_2023_2026.json")
EMBEDDINGS_FILE = os.path.join(BASE_DIR, "crawling", "output", "daedeok_sermons_with_embeddings.json")

# 임베딩 모델 정보
MODEL_NAME = "dragonkue/bge-m3-ko"
MODEL_VERSION = "1.0"


def get_connection():
    """데이터베이스 연결"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL 환경변수가 설정되지 않았습니다.")
    return psycopg2.connect(database_url)


def load_json(file_path: str) -> List[Dict[str, Any]]:
    """JSON 파일 로드"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def clean_bible_ref(bible_ref: str) -> str:
    """
    bible_ref 데이터 정리
    - 50자 이상이면 파싱 오류로 간주하여 빈 문자열 반환
    - 정상적인 성경 구절: "마 25 : 1 ~ 13" (짧음)
    """
    if not bible_ref:
        return ''
    if len(bible_ref) > 50:
        return ''  # 잘못된 데이터 (설교 내용이 들어간 경우)
    return bible_ref.strip()


def import_sermons(conn, sermons: List[Dict[str, Any]]) -> tuple:
    """sermons 테이블에 데이터 삽입"""
    cursor = conn.cursor()

    # 데이터 준비 및 정리
    values = []
    cleaned_count = 0

    for sermon in sermons:
        # bible_ref 정리
        original_bible_ref = sermon.get('bible_ref', '')
        cleaned_bible_ref = clean_bible_ref(original_bible_ref)

        if original_bible_ref and not cleaned_bible_ref:
            cleaned_count += 1

        values.append((
            sermon['id'],
            sermon['title'],
            sermon.get('sermon_date'),
            cleaned_bible_ref,
            sermon.get('content_summary'),
            sermon.get('video_url'),
            sermon.get('church_name'),
            sermon.get('preacher'),
        ))

    # UPSERT (중복 시 업데이트)
    query = """
        INSERT INTO sermons (id, title, sermon_date, bible_ref, content_summary, video_url, church_name, preacher)
        VALUES %s
        ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            sermon_date = EXCLUDED.sermon_date,
            bible_ref = EXCLUDED.bible_ref,
            content_summary = EXCLUDED.content_summary,
            video_url = EXCLUDED.video_url,
            church_name = EXCLUDED.church_name,
            preacher = EXCLUDED.preacher,
            updated_at = CURRENT_TIMESTAMP
    """

    execute_values(cursor, query, values)
    inserted = cursor.rowcount
    conn.commit()
    cursor.close()

    return inserted, cleaned_count


def import_embeddings(conn, sermons_with_embeddings: List[Dict[str, Any]]) -> int:
    """sermon_embeddings 테이블에 데이터 삽입"""
    cursor = conn.cursor()

    # 기존 같은 모델의 임베딩 삭제 (선택사항 - 중복 방지)
    cursor.execute(
        "DELETE FROM sermon_embeddings WHERE model_name = %s",
        (MODEL_NAME,)
    )

    # 데이터 준비
    values = []
    for sermon in sermons_with_embeddings:
        if 'embedding' not in sermon:
            continue

        # 벡터를 PostgreSQL 형식으로 변환
        embedding_str = '[' + ','.join(map(str, sermon['embedding'])) + ']'

        values.append((
            sermon['id'],
            embedding_str,
            MODEL_NAME,
            MODEL_VERSION,
        ))

    # 삽입
    query = """
        INSERT INTO sermon_embeddings (sermon_id, embedding, model_name, model_version)
        VALUES %s
    """

    execute_values(cursor, query, values)
    inserted = cursor.rowcount
    conn.commit()
    cursor.close()

    return inserted


def main():
    print("=" * 60)
    print("대덕교회 설교 데이터 DB Import")
    print("=" * 60)

    # 파일 확인
    print(f"\n[1] 파일 확인")
    print(f"  원본 데이터: {SERMONS_FILE}")
    print(f"  임베딩 데이터: {EMBEDDINGS_FILE}")

    if not os.path.exists(SERMONS_FILE):
        print(f"  ERROR: {SERMONS_FILE} 파일이 없습니다.")
        return

    if not os.path.exists(EMBEDDINGS_FILE):
        print(f"  ERROR: {EMBEDDINGS_FILE} 파일이 없습니다.")
        return

    # 데이터 로드
    print(f"\n[2] 데이터 로드")
    sermons = load_json(SERMONS_FILE)
    sermons_with_embeddings = load_json(EMBEDDINGS_FILE)
    print(f"  원본 설교: {len(sermons)}개")
    print(f"  임베딩 설교: {len(sermons_with_embeddings)}개")

    # DB 연결
    print(f"\n[3] 데이터베이스 연결")
    try:
        conn = get_connection()
        print("  연결 성공!")
    except Exception as e:
        print(f"  ERROR: {e}")
        return

    try:
        # sermons 테이블 import
        print(f"\n[4] sermons 테이블 Import")
        count, cleaned = import_sermons(conn, sermons)
        print(f"  {count}개 행 처리됨")
        print(f"  bible_ref 정리됨: {cleaned}개 (50자 초과 → 빈 값)")

        # sermon_embeddings 테이블 import
        print(f"\n[5] sermon_embeddings 테이블 Import")
        print(f"  모델: {MODEL_NAME} (v{MODEL_VERSION})")
        count = import_embeddings(conn, sermons_with_embeddings)
        print(f"  {count}개 행 삽입됨")

        print("\n" + "=" * 60)
        print("Import 완료!")
        print("=" * 60)

    except Exception as e:
        print(f"\nERROR: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
