# backend/crawling/crawler.py
"""
대덕교회 설교 크롤러 메인 모듈
"""

import time
from typing import List, Dict, Any, Optional

from .core import (
    CrawlerConfig,
    create_driver,
    parse_date_from_title,
    extract_sermon_title,
    extract_post_links,
    parse_sermon_content,
    save_to_json,
)


class DaedeokCrawler:
    """대덕교회 설교 크롤러"""

    def __init__(self, config: Optional[CrawlerConfig] = None):
        """
        크롤러 초기화

        Args:
            config: 크롤러 설정 (None이면 기본 설정 사용)
        """
        self.config = config or CrawlerConfig()
        self.driver = None
        self.sermons: List[Dict[str, Any]] = []

    def start(self):
        """WebDriver 시작"""
        if self.driver is None:
            print("WebDriver 초기화 중...")
            self.driver = create_driver(headless=True)
            print("WebDriver 준비 완료")

    def stop(self):
        """WebDriver 종료"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            print("WebDriver 종료됨")

    def crawl(self) -> List[Dict[str, Any]]:
        """
        크롤링 실행

        Returns:
            수집된 설교 데이터 리스트
        """
        self.start()
        self.sermons = []

        total_posts = 0
        skipped_by_year = 0

        try:
            for page in range(self.config.start_page, self.config.end_page + 1):
                print(f"\n{'='*60}")
                print(f"페이지 {page}/{self.config.end_page} 처리 중")
                print(f"{'='*60}")

                # 페이지 URL
                if page == 1:
                    page_url = self.config.base_url
                else:
                    page_url = f"{self.config.base_url}?page={page}"

                print(f"URL: {page_url}")
                self.driver.get(page_url)

                # 게시글 링크 추출
                posts = extract_post_links(
                    self.driver,
                    timeout=self.config.page_load_timeout
                )
                print(f"게시글 {len(posts)}개 발견")

                if not posts:
                    continue

                # 게시글 수 제한
                if self.config.posts_per_page:
                    posts = posts[:self.config.posts_per_page]

                # 각 게시글 처리
                for idx, (post_id, full_title, detail_url) in enumerate(posts, 1):
                    print(f"\n[{idx}/{len(posts)}] {full_title}")

                    # 날짜 추출 및 필터링
                    date = parse_date_from_title(full_title)
                    if date and self.config.year_filter:
                        year = int(date[:4])
                        if year not in self.config.year_filter:
                            print(f"  [SKIP] {year}년 (필터: {self.config.year_filter})")
                            skipped_by_year += 1
                            continue

                    # 설교 제목 추출
                    sermon_title = extract_sermon_title(full_title)

                    # 상세 페이지 크롤링
                    try:
                        self.driver.get(detail_url)
                        content = parse_sermon_content(self.driver)

                        if not content["summary_content"]:
                            print(f"  [SKIP] 내용 없음")
                            continue

                        # 데이터 저장
                        sermon_entry = {
                            "id": int(post_id),
                            "title": sermon_title,
                            "sermon_date": date,
                            "bible_ref": content["scripture"],
                            "content_summary": content["summary_content"],
                            "video_url": detail_url,
                            "church_name": self.config.church_name,
                            "preacher": content["preacher"],
                        }

                        self.sermons.append(sermon_entry)
                        total_posts += 1
                        print(f"  [OK] {sermon_title} ({len(content['summary_content'])}자)")

                    except Exception as e:
                        print(f"  [ERROR] {e}")

                    # 대기
                    time.sleep(self.config.delay_between_posts)

                # 페이지 간 대기
                time.sleep(self.config.delay_between_pages)

        finally:
            self.stop()

        # 결과 요약
        print(f"\n{'='*60}")
        print(f"크롤링 완료!")
        print(f"수집: {total_posts}개 / 스킵(연도 필터): {skipped_by_year}개")
        print(f"{'='*60}")

        return self.sermons

    def save(self, filepath: Optional[str] = None) -> str:
        """
        수집된 데이터 저장

        Args:
            filepath: 저장 경로 (None이면 config 설정 사용)

        Returns:
            저장된 파일 경로
        """
        path = filepath or self.config.output_path
        save_to_json(self.sermons, path)
        print(f"저장됨: {path}")
        return path


def run_crawler(
    start_page: int = 1,
    end_page: int = 18,
    year_filter: Optional[List[int]] = None,
    output_file: str = "daedeok_sermons.json",
) -> List[Dict[str, Any]]:
    """
    간편 실행 함수

    Args:
        start_page: 시작 페이지
        end_page: 종료 페이지
        year_filter: 연도 필터
        output_file: 출력 파일명

    Returns:
        수집된 설교 데이터
    """
    config = CrawlerConfig(
        start_page=start_page,
        end_page=end_page,
        year_filter=year_filter,
        output_file=output_file,
    )

    crawler = DaedeokCrawler(config)
    sermons = crawler.crawl()
    crawler.save()

    return sermons


# ─────────────────────────────────────────────────────────
# 메인 실행
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("대덕교회 설교 크롤러")
    print("=" * 60)

    sermons = run_crawler(
        start_page=1,
        end_page=18,
        year_filter=[2023, 2024, 2025, 2026],
        output_file="daedeok_sermons_2023_2026.json",
    )

    print(f"\n총 {len(sermons)}개 설교 수집 완료")
