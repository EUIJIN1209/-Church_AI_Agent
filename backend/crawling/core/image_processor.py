"""
이미지 처리 및 추출 유틸리티.
"""
from bs4 import BeautifulSoup
from typing import List
from urllib.parse import urljoin

from .config import CrawlerConfig


class ImageProcessor:
    """웹 페이지에서 이미지를 처리하고 추출합니다."""

    def __init__(self):
        self.excluded_keywords = CrawlerConfig.EXCLUDED_IMAGE_KEYWORDS
        self.priority_keywords = CrawlerConfig.PRIORITY_IMAGE_KEYWORDS
        self.min_size = CrawlerConfig.MIN_IMAGE_SIZE

    def extract_all_images(self, soup: BeautifulSoup, page_url: str) -> List[str]:
        """
        웹 페이지에서 관련된 모든 이미지를 추출합니다.

        Args:
            soup: 페이지의 BeautifulSoup 객체
            page_url: 상대 URL 변환을 위한 기본 URL

        Returns:
            우선순위별로 정렬된 이미지 URL 목록
        """
        images = []
        seen_urls = set()

        # 모든 img 태그 찾기
        img_tags = soup.find_all("img")

        for img in img_tags:
            # 이미지 소스 가져오기
            src = img.get("src") or img.get("data-src")
            if not src:
                continue

            # 절대 URL로 변환
            image_url = urljoin(page_url, src)

            # 중복 제거
            if image_url in seen_urls:
                continue
            seen_urls.add(image_url)

            # 크기 속성으로 작은 이미지 필터링
            if self._is_too_small(img):
                continue

            # 파일명 키워드로 필터링
            if self._is_excluded_image(image_url):
                continue

            images.append(image_url)

        # 우선순위별 정렬
        return self._sort_by_priority(images)

    def _is_too_small(self, img_tag) -> bool:
        """width/height 속성을 기반으로 이미지가 너무 작은지 확인합니다."""
        width = img_tag.get("width")
        height = img_tag.get("height")

        if width and height:
            try:
                if int(width) < self.min_size or int(height) < self.min_size:
                    return True
            except (ValueError, TypeError):
                pass

        return False

    def _is_excluded_image(self, image_url: str) -> bool:
        """이미지 URL에 제외할 키워드가 포함되어 있는지 확인합니다."""
        url_lower = image_url.lower()
        return any(keyword in url_lower for keyword in self.excluded_keywords)

    def _sort_by_priority(self, images: List[str]) -> List[str]:
        """
        우선순위별로 이미지를 정렬합니다 (설교 관련 이미지 우선).

        Args:
            images: 이미지 URL 목록

        Returns:
            우선순위 이미지가 먼저 오는 정렬된 목록
        """
        priority_images = []
        other_images = []

        for img_url in images:
            url_lower = img_url.lower()
            if any(keyword in url_lower for keyword in self.priority_keywords):
                priority_images.append(img_url)
            else:
                other_images.append(img_url)

        return priority_images + other_images

    def filter_valid_images(
        self, image_urls: List[str], max_count: int = 3
    ) -> List[str]:
        """
        이미지 URL을 필터링하고 제한합니다.

        Args:
            image_urls: 이미지 URL 목록
            max_count: 반환할 최대 이미지 수

        Returns:
            필터링된 이미지 URL 목록
        """
        return image_urls[:max_count]
