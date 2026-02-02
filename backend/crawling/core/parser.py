# backend/crawling/core/parser.py
"""
텍스트 파싱 유틸리티
"""

import re
from typing import Optional


def parse_date_from_title(title: str) -> Optional[str]:
    """
    제목에서 날짜 추출

    Args:
        title: 게시글 제목 (예: "20260111 - 열 처녀 비유")

    Returns:
        날짜 문자열 (YYYY-MM-DD) 또는 None
    """
    date_match = re.search(r"(\d{8})", title)
    if date_match:
        date_str = date_match.group(1)
        try:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        except:
            return date_str
    return None


def extract_sermon_title(full_title: str) -> str:
    """
    전체 제목에서 설교 제목만 추출

    Args:
        full_title: 전체 제목 (예: "20260111 - 열 처녀 비유")

    Returns:
        설교 제목 (예: "열 처녀 비유")
    """
    match = re.search(r"-\s*(.+)$", full_title)
    if match:
        return match.group(1).strip()
    return full_title


def parse_scripture_reference(text: str) -> Optional[str]:
    """
    본문에서 성경 구절 참조 추출

    Args:
        text: 본문 텍스트 (예: "본 문 : 마 25 : 1 ~ 13")

    Returns:
        성경 구절 (예: "마 25 : 1 ~ 13") 또는 None
    """
    if "본" in text and "문" in text and ":" in text:
        scripture_match = re.search(r":\s*(.+)$", text)
        if scripture_match:
            raw_scripture = scripture_match.group(1).strip()

            # 성경 구절 패턴만 추출 (한글 책명 + 장:절 형식)
            clean_match = re.match(
                r'^([가-힣]+\s*\d+\s*[:\s]*\d*\s*[~\-\s]*\d*)',
                raw_scripture
            )
            if clean_match:
                return clean_match.group(1).strip()
            elif len(raw_scripture) <= 30:
                return raw_scripture

    return None


def parse_preacher(text: str) -> Optional[str]:
    """
    본문에서 설교자 추출

    Args:
        text: 본문 텍스트 (예: "설교자 : 홍길동 목사")

    Returns:
        설교자 이름 또는 None
    """
    if "설교자" in text and ":" in text:
        preacher_match = re.search(r":\s*(.+)$", text)
        if preacher_match:
            return preacher_match.group(1).strip()

    return None
