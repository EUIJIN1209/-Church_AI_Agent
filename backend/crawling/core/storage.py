# backend/crawling/core/storage.py
"""
데이터 저장/로드
"""

import json
import os
from typing import List, Dict, Any
from datetime import datetime


def save_to_json(
    data: List[Dict[str, Any]],
    filepath: str,
    backup: bool = True
) -> str:
    """
    데이터를 JSON 파일로 저장

    Args:
        data: 저장할 데이터 리스트
        filepath: 저장 경로
        backup: 기존 파일 백업 여부

    Returns:
        저장된 파일 경로
    """
    # 디렉토리 생성
    directory = os.path.dirname(filepath)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)

    # 기존 파일 백업
    if backup and os.path.exists(filepath):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = filepath.replace(".json", f"_backup_{timestamp}.json")
        os.rename(filepath, backup_path)
        print(f"  Backup created: {backup_path}")

    # 저장
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return filepath


def load_from_json(filepath: str) -> List[Dict[str, Any]]:
    """
    JSON 파일에서 데이터 로드

    Args:
        filepath: 파일 경로

    Returns:
        로드된 데이터 리스트
    """
    if not os.path.exists(filepath):
        return []

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def merge_sermons(
    existing: List[Dict[str, Any]],
    new: List[Dict[str, Any]],
    key: str = "id"
) -> List[Dict[str, Any]]:
    """
    기존 데이터와 새 데이터 병합 (중복 제거)

    Args:
        existing: 기존 데이터
        new: 새 데이터
        key: 중복 체크 키

    Returns:
        병합된 데이터
    """
    existing_ids = {item.get(key) for item in existing}

    merged = list(existing)
    for item in new:
        if item.get(key) not in existing_ids:
            merged.append(item)

    return merged
