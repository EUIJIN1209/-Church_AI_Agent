# backend/crawling/core/extractor.py
"""
페이지 콘텐츠 추출
"""

import time
from typing import Dict, Any, List, Tuple
from urllib.parse import urlparse, parse_qs

from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .parser import parse_scripture_reference, parse_preacher


def extract_post_links(driver: WebDriver, timeout: int = 15) -> List[Tuple[str, str, str]]:
    """
    게시글 목록 페이지에서 게시글 링크 추출

    Args:
        driver: Selenium WebDriver
        timeout: 페이지 로딩 타임아웃 (초)

    Returns:
        List of (post_id, title, url) tuples
    """
    posts = []

    try:
        # 페이지 로딩 대기
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR,
                ".widget.board, .li_board, .board_list, [data-widget-type='board']"
            ))
        )

        # 추가 대기 (동적 콘텐츠 로딩)
        time.sleep(3)

        # 여러 선택자 시도
        selectors = [
            ".li_board .li_body a",
            ".board_list a",
            ".widget.board a[href*='idx']",
            "a[href*='idx']",
            ".title a",
            ".list_text_title a",
        ]

        links = []
        for selector in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    links.extend(elements)
            except:
                continue

        # 중복 제거
        seen_urls = set()
        for link in links:
            try:
                href = link.get_attribute("href")
                title = link.text.strip()

                if not href or not title:
                    continue

                if "idx" not in href:
                    continue

                if href in seen_urls:
                    continue

                seen_urls.add(href)

                # idx 추출
                parsed = urlparse(href)
                query_params = parse_qs(parsed.query)
                idx = query_params.get("idx", ["unknown"])[0]

                posts.append((idx, title, href))

            except:
                continue

    except Exception as e:
        print(f"  Error extracting links: {e}")

    return posts


def parse_sermon_content(driver: WebDriver, timeout: int = 10) -> Dict[str, Any]:
    """
    상세 페이지에서 설교 내용 파싱

    Args:
        driver: Selenium WebDriver
        timeout: 페이지 로딩 타임아웃 (초)

    Returns:
        Dict with scripture, preacher, summary_content, paragraphs
    """
    data = {
        "scripture": "",
        "preacher": "",
        "summary_content": "",
        "paragraphs": [],
    }

    try:
        # 페이지 로딩 대기
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR,
                ".board_view, .board_txt_area, .view_content, [class*='comment_body']"
            ))
        )
        time.sleep(2)

        # 본문 영역 찾기
        content_selectors = [
            "[class*='comment_body']",
            ".board_txt_area",
            ".view_content",
            ".board_view .content",
            ".fr-view",
        ]

        content_element = None
        for selector in content_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    content_element = elements[0]
                    break
            except:
                continue

        if not content_element:
            return data

        # 모든 p 태그 파싱
        paragraphs = content_element.find_elements(By.TAG_NAME, "p")

        for p in paragraphs:
            text = p.text.strip()
            if not text:
                continue

            # 성경 구절 추출
            scripture = parse_scripture_reference(text)
            if scripture:
                data["scripture"] = scripture
                continue

            # 설교자 추출
            preacher = parse_preacher(text)
            if preacher:
                data["preacher"] = preacher
                continue

            # 본문 내용
            if not text.startswith("◈"):
                data["paragraphs"].append(text)

        # 문단 합치기
        data["summary_content"] = "\n\n".join(data["paragraphs"])

    except Exception as e:
        print(f"  Error parsing content: {e}")

    return data
