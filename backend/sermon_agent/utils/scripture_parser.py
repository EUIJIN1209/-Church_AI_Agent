# backend/sermon_agent/utils/scripture_parser.py
# -*- coding: utf-8 -*-
"""
scripture_parser.py

성경 구절 파싱 유틸리티.
"""

import re
from typing import List, Optional, Dict, Any


def parse_scripture_reference(text: str) -> List[Dict[str, Any]]:
    """
    텍스트에서 성경 구절 참조를 파싱.

    예:
        - "마태복음 5장 3절"
        - "요한복음 3:16"
        - "고린도전서 13장 1-3절"
        - "시편 23편"

    Returns:
        List[Dict]: 파싱된 성경 구절 정보
    """
    references = []

    # 패턴 1: "책명 장장 절절" 형식
    pattern1 = r'([가-힣]+(?:복음|서)?)\s*(\d+)장\s*(\d+)(?:-(\d+))?절?'
    matches1 = re.finditer(pattern1, text)
    for match in matches1:
        book = match.group(1)
        chapter = int(match.group(2))
        verse_start = int(match.group(3))
        verse_end = int(match.group(4)) if match.group(4) else verse_start
        
        references.append({
            "book": book,
            "chapter": chapter,
            "verse_start": verse_start,
            "verse_end": verse_end,
            "original": match.group(0),
        })

    # 패턴 2: "책명 장:절" 형식
    pattern2 = r'([가-힣]+(?:복음|서)?)\s*(\d+):(\d+)(?:-(\d+))?'
    matches2 = re.finditer(pattern2, text)
    for match in matches2:
        book = match.group(1)
        chapter = int(match.group(2))
        verse_start = int(match.group(3))
        verse_end = int(match.group(4)) if match.group(4) else verse_start
        
        references.append({
            "book": book,
            "chapter": chapter,
            "verse_start": verse_start,
            "verse_end": verse_end,
            "original": match.group(0),
        })

    # 패턴 3: "시편 23편" 같은 형식
    pattern3 = r'(시편)\s*(\d+)편'
    matches3 = re.finditer(pattern3, text)
    for match in matches3:
        book = match.group(1)
        chapter = int(match.group(2))
        
        references.append({
            "book": book,
            "chapter": chapter,
            "verse_start": None,
            "verse_end": None,
            "original": match.group(0),
        })

    return references


def format_scripture_reference(ref: Dict[str, Any]) -> str:
    """
    성경 구절 정보를 표준 형식으로 포맷팅.

    Args:
        ref: parse_scripture_reference의 결과

    Returns:
        str: 포맷팅된 성경 구절 문자열
    """
    book = ref.get("book", "")
    chapter = ref.get("chapter")
    verse_start = ref.get("verse_start")
    verse_end = ref.get("verse_end")

    if verse_start is None:
        return f"{book} {chapter}장"
    
    if verse_start == verse_end:
        return f"{book} {chapter}장 {verse_start}절"
    else:
        return f"{book} {chapter}장 {verse_start}-{verse_end}절"

