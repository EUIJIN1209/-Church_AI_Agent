# backend/crawling/core/config.py
"""
크롤러 설정
"""

import os
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class CrawlerConfig:
    """크롤러 설정 클래스"""

    # 대덕교회 설정
    base_url: str = "https://ddpc.or.kr/260"
    church_name: str = "대덕교회"

    # 페이지 설정
    start_page: int = 1
    end_page: int = 18
    posts_per_page: Optional[int] = None  # None = 전체

    # 필터
    year_filter: Optional[List[int]] = None

    # 출력 설정
    output_dir: str = "output"
    output_file: str = "daedeok_sermons.json"

    # 대기 시간 (초)
    delay_between_posts: float = 2.0
    delay_between_pages: float = 3.0
    page_load_timeout: int = 15

    @property
    def output_path(self) -> str:
        """출력 파일 전체 경로"""
        return os.path.join(self.output_dir, self.output_file)

    def __post_init__(self):
        """출력 디렉토리 생성"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)


# 기본 설정 인스턴스
default_config = CrawlerConfig(
    year_filter=[2023, 2024, 2025, 2026]
)
