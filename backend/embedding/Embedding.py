"""
대덕교회 설교 임베딩 생성 모듈

- 모델: dragonkue/bge-m3-ko (한국어 최적화, 1024차원)
- 방식: A 방식 (설교 1개 = 임베딩 1개)
"""

import json
import os
from typing import List, Dict, Any
from langchain_huggingface import HuggingFaceEmbeddings
from tqdm import tqdm

# 경로 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_FILE = os.path.join(BASE_DIR, "crawling", "output", "daedeok_sermons_2023_2026.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "crawling", "output", "daedeok_sermons_with_embeddings.json")


def create_embedding_model():
    """임베딩 모델 초기화 (dragonkue/bge-m3-ko)"""
    print("임베딩 모델 로딩 중...")

    embeddings_model = HuggingFaceEmbeddings(
        model_name="dragonkue/bge-m3-ko",
        model_kwargs={'device': 'cpu'},  # GPU 사용 시 'cuda'로 변경
        encode_kwargs={'normalize_embeddings': True},
    )

    print("모델 로딩 완료!")
    return embeddings_model


def load_sermons(file_path: str) -> List[Dict[str, Any]]:
    """설교 데이터 로드"""
    with open(file_path, 'r', encoding='utf-8') as f:
        sermons = json.load(f)
    print(f"총 {len(sermons)}개의 설교 데이터 로드됨")
    return sermons


def create_embedding_text(sermon: Dict[str, Any]) -> str:
    """
    임베딩용 텍스트 생성

    제목 + 성경구절 + 요약 내용을 결합하여 더 풍부한 컨텍스트 제공
    """
    parts = []

    # 제목
    if sermon.get('title'):
        parts.append(f"제목: {sermon['title']}")

    # 성경 구절
    if sermon.get('bible_ref'):
        parts.append(f"본문: {sermon['bible_ref']}")

    # 설교 요약 내용
    if sermon.get('content_summary'):
        parts.append(sermon['content_summary'])

    return "\n".join(parts)


def generate_embeddings(sermons: List[Dict[str, Any]], model) -> List[Dict[str, Any]]:
    """
    모든 설교에 대해 임베딩 생성

    A 방식: 설교 1개 = 임베딩 1개
    """
    print("\n임베딩 생성 시작...")

    # 임베딩할 텍스트 준비
    texts = [create_embedding_text(sermon) for sermon in sermons]

    # 배치 처리로 임베딩 생성
    print(f"총 {len(texts)}개 문서 임베딩 중...")
    embeddings = model.embed_documents(texts)

    # 결과에 임베딩 추가
    for i, sermon in enumerate(tqdm(sermons, desc="임베딩 적용")):
        sermon['embedding'] = embeddings[i]

    print(f"\n임베딩 생성 완료! (차원: {len(embeddings[0])})")
    return sermons


def save_sermons_with_embeddings(sermons: List[Dict[str, Any]], output_path: str):
    """임베딩 포함된 설교 데이터 저장"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(sermons, f, ensure_ascii=False, indent=2)
    print(f"저장 완료: {output_path}")


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("대덕교회 설교 임베딩 생성")
    print("=" * 60)
    print(f"모델: dragonkue/bge-m3-ko")
    print(f"방식: A (설교 1개 = 임베딩 1개)")
    print(f"입력: {INPUT_FILE}")
    print(f"출력: {OUTPUT_FILE}")
    print("=" * 60 + "\n")

    # 1. 설교 데이터 로드
    sermons = load_sermons(INPUT_FILE)

    # 2. 임베딩 모델 초기화
    model = create_embedding_model()

    # 3. 임베딩 생성
    sermons_with_embeddings = generate_embeddings(sermons, model)

    # 4. 결과 저장
    save_sermons_with_embeddings(sermons_with_embeddings, OUTPUT_FILE)

    # 5. 결과 요약
    print("\n" + "=" * 60)
    print("임베딩 생성 완료!")
    print(f"총 설교 수: {len(sermons_with_embeddings)}")
    print(f"임베딩 차원: {len(sermons_with_embeddings[0]['embedding'])}")
    print(f"저장 위치: {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
