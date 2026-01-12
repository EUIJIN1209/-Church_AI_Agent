"""
서강감리교회 설교를 위한 메인 크롤러 로직.
"""
import time
import re
from typing import Optional, List
from urllib.parse import urljoin

from .config import CrawlerConfig, GeminiConfig, validate_config
from .models import SermonData, CrawlStats
from .http_client import HTTPClient
from .image_processor import ImageProcessor
from .gemini_client import GeminiClient
from .storage import SermonStorage
from .exceptions import (
    HTTPRequestException,
    ImageDownloadException,
    OCRException,
    CrawlerException,
)


class SeokangCrawler:
    """서강감리교회 설교 주보를 위한 메인 크롤러."""

    def __init__(
        self,
        use_ocr: bool = True,
        page_start: int = None,
        page_end: int = None,
        posts_per_page: int = None,
        year_filter: list = None,
    ):
        """
        크롤러를 초기화합니다.

        Args:
            use_ocr: Gemini OCR 사용 여부 (API 키 필요)
            page_start: 시작 페이지 번호 (기본값은 설정에서)
            page_end: 종료 페이지 번호 (기본값은 설정에서)
            posts_per_page: 페이지당 최대 게시물 수 (전체는 None)
            year_filter: 수집할 연도 리스트 (예: [2025, 2026] 또는 None for all)
        """
        # 설정 검증
        if use_ocr:
            validate_config()

        # 컴포넌트 초기화
        self.http_client = HTTPClient()
        self.image_processor = ImageProcessor()
        self.storage = SermonStorage()
        self.stats = CrawlStats()

        # OCR이 활성화된 경우 Gemini 클라이언트 초기화
        self.gemini_client = None
        if use_ocr and GeminiConfig.API_KEY:
            try:
                self.gemini_client = GeminiClient()
            except Exception as e:
                print(f"⚠ Failed to initialize Gemini client: {e}")
                print("Continuing without OCR...")

        # 크롤링 매개변수
        self.page_start = page_start or CrawlerConfig.PAGE_START
        self.page_end = page_end or CrawlerConfig.PAGE_END
        self.posts_per_page = posts_per_page or CrawlerConfig.POSTS_PER_PAGE
        self.year_filter = year_filter if year_filter is not None else getattr(CrawlerConfig, 'YEAR_FILTER', None)

        # 필터링된 게시글 카운터
        self.filtered_count = 0

    def crawl(self) -> List[SermonData]:
        """
        설교 크롤링을 시작합니다.

        Returns:
            SermonData 객체의 리스트
        """
        print("\n" + "=" * 60)
        print("Starting Seokang Church Sermon Crawler")
        print(f"Pages: {self.page_start} to {self.page_end}")
        print(f"OCR enabled: {self.gemini_client is not None}")
        if self.year_filter:
            print(f"Year filter: {self.year_filter}")
        print("=" * 60)

        self.stats.start()
        sermons = []

        try:
            for page in range(self.page_start, self.page_end + 1):
                print(f"\n{'='*60}")
                print(f"Processing List Page: {page}/{self.page_end}")
                print(f"{'='*60}")

                page_sermons = self._crawl_page(page)
                sermons.extend(page_sermons)

                self.stats.total_pages += 1

                # 페이지 간 지연
                if page < self.page_end:
                    time.sleep(CrawlerConfig.DELAY_BETWEEN_PAGES)

        except KeyboardInterrupt:
            print("\n\n⚠ Crawling interrupted by user")
        except Exception as e:
            print(f"\n\n✗ Crawling error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.stats.finish()

        # 결과 저장
        self._save_results(sermons)

        # 통계 출력
        self.stats.print_summary()

        # 연도 필터링 통계 추가
        if self.year_filter and self.filtered_count > 0:
            print(f"\nFiltered out: {self.filtered_count} posts (not in years {self.year_filter})")

        return sermons

    def _crawl_page(self, page: int) -> List[SermonData]:
        """단일 목록 페이지를 크롤링합니다."""
        sermons = []

        # 매개변수 준비
        params = CrawlerConfig.BOARD_PARAMS.copy()
        params["page"] = page

        try:
            # 페이지 HTML 가져오기
            soup = self.http_client.get_soup(CrawlerConfig.LIST_URL, params)
            if not soup:
                print(f"  ✗ Failed to fetch page {page}")
                return sermons

            # 게시물 링크 추출
            post_links = self._extract_post_links(soup)
            print(f"Found {len(post_links)} posts on this page")

            self.stats.total_posts += len(post_links)

            # 설정된 경우 게시물 제한
            if self.posts_per_page:
                post_links = post_links[: self.posts_per_page]
                print(f"Processing first {len(post_links)} posts (test mode)")

            # 각 게시물 크롤링
            for idx, (seq_id, href) in enumerate(post_links, 1):
                print(f"\n[{idx}/{len(post_links)}] Scraping Post Seq: {seq_id}")

                sermon = self._crawl_post(seq_id, href)
                if sermon:
                    sermons.append(sermon)
                    self.stats.add_success(sermon.ocr_used)
                else:
                    self.stats.add_failure()

                # 게시물 간 지연
                if idx < len(post_links):
                    time.sleep(CrawlerConfig.DELAY_BETWEEN_POSTS)

        except HTTPRequestException as e:
            print(f"  ✗ HTTP error on page {page}: {e}")
        except Exception as e:
            print(f"  ✗ Error on page {page}: {e}")
            import traceback
            traceback.print_exc()

        return sermons

    def _extract_post_links(self, soup) -> List[tuple]:
        """목록 페이지에서 게시물 링크를 추출합니다."""
        links = soup.find_all("a", href=lambda href: href and "view.asp" in href)

        # 중복 제거
        unique_links = []
        seen_seq = set()

        for link in links:
            href = link["href"]
            seq_match = re.search(r"seq=(\d+)", href)
            if seq_match:
                seq_id = seq_match.group(1)
                if seq_id not in seen_seq:
                    seen_seq.add(seq_id)
                    unique_links.append((seq_id, href))

        return unique_links

    def _crawl_post(self, seq_id: str, href: str) -> Optional[SermonData]:
        """단일 설교 게시물을 크롤링합니다."""
        try:
            # 전체 URL 구성
            if href.startswith("http"):
                detail_url = href
            else:
                detail_url = urljoin(CrawlerConfig.BASE_URL, href)

            print(f"URL: {detail_url}")

            # 게시물 HTML 가져오기
            soup = self.http_client.get_soup(detail_url)
            if not soup:
                print(f"  ✗ Failed to fetch post")
                return None

            # 제목 추출
            title = self._extract_title(soup, seq_id)
            print(f"  Title: {title}")

            # 연도 필터 체크 (날짜를 먼저 확인하여 API 호출 절약)
            if self.year_filter:
                date_str = self._extract_date(soup)
                year = self._extract_year_from_date(date_str)
                if year and year not in self.year_filter:
                    print(f"  ⊘ Skipped (year {year} not in filter)")
                    self.filtered_count += 1
                    return None
                elif year:
                    print(f"  ✓ Year {year} matches filter")

            # 이미지 추출
            image_urls = self.image_processor.extract_all_images(soup, detail_url)
            print(f"  Found {len(image_urls)} image(s)")

            # OCR이 활성화된 경우 시도
            ocr_result = None
            if self.gemini_client and image_urls:
                ocr_result = self._try_ocr_on_images(image_urls)

            # 설교 데이터 생성
            if ocr_result:
                # 3줄 요약 생성
                summary = self._generate_summary(ocr_result.summary, ocr_result.title)

                sermon = SermonData.from_ocr(
                    seq=seq_id,
                    link=detail_url,
                    ocr_result=ocr_result,
                    summary=summary,
                    image_urls=image_urls[:3],
                )
                print(f"  ✓ Saved with OCR data")
            else:
                # HTML 파싱으로 대체
                content = self._extract_content(soup)
                date = self._extract_date(soup)

                sermon = SermonData.from_html(
                    seq=seq_id,
                    title=title,
                    content=content,
                    date=date,
                    link=detail_url,
                    image_urls=image_urls[:3],
                )
                print(f"  ⚠ Saved without OCR (HTML only)")

            return sermon

        except Exception as e:
            print(f"  ✗ Error parsing seq {seq_id}: {e}")
            return None

    def _try_ocr_on_images(self, image_urls: List[str]):
        """성공할 때까지 각 이미지에 대해 OCR을 시도합니다."""
        for img_idx, img_url in enumerate(image_urls, 1):
            print(f"  Trying image {img_idx}/{len(image_urls)}: {img_url}")

            try:
                # 이미지 다운로드
                img_bytes = self.http_client.download_image(img_url)
                print(f"    Downloaded {len(img_bytes)} bytes")

                # 텍스트 추출
                ocr_result = self.gemini_client.extract_text_from_image(img_bytes)

                if ocr_result and ocr_result.is_valid():
                    print(f"    ✓ OCR successful!")
                    print(f"    Title: {ocr_result.title}")
                    print(f"    Date: {ocr_result.date}")
                    print(f"    Summary length: {len(ocr_result.summary)} chars")
                    return ocr_result
                else:
                    print(f"    ✗ OCR failed or result too short")

            except (ImageDownloadException, OCRException) as e:
                print(f"    ✗ Error: {e}")

            # 이미지 간 지연
            if img_idx < len(image_urls):
                time.sleep(CrawlerConfig.DELAY_BETWEEN_IMAGES)

        return None

    def _generate_summary(self, content: str, title: str) -> Optional[str]:
        """Gemini를 사용하여 3줄 요약을 생성합니다."""
        if not self.gemini_client:
            return None

        try:
            print(f"  Generating 3-line summary...")
            summary = self.gemini_client.generate_summary(content, title)
            if summary:
                print(f"  ✓ Summary generated")
            else:
                print(f"  ⚠ Summary generation failed")
            return summary
        except Exception as e:
            print(f"  ⚠ Summary error: {e}")
            return None

    def _extract_title(self, soup, seq_id: str) -> str:
        """게시물 페이지에서 제목을 추출합니다."""
        title_tag = soup.find("td", class_="subject") or soup.find(
            "font", class_="title"
        )

        if not title_tag:
            # 대안 검색
            title_candidates = soup.find_all(
                "td", class_=lambda x: x and "subject" in x.lower()
            )
            if title_candidates:
                return title_candidates[0].get_text(strip=True)
            elif soup.title:
                return soup.title.text.strip()
            else:
                return f"Post {seq_id}"

        return title_tag.get_text(strip=True)

    def _extract_content(self, soup) -> str:
        """게시물 페이지에서 내용을 추출합니다."""
        content_tag = soup.find("td", class_="content") or soup.find(
            "div", id="content"
        )
        if content_tag:
            return content_tag.get_text(separator="\n", strip=True)
        return ""

    def _extract_date(self, soup) -> str:
        """게시물 페이지에서 날짜를 추출합니다."""
        date_match = re.search(r"\d{4}-\d{2}-\d{2}", soup.text)
        return date_match.group(0) if date_match else "Unknown"

    def _extract_year_from_date(self, date_str: str) -> Optional[int]:
        """날짜 문자열에서 연도를 추출합니다."""
        if not date_str or date_str == "Unknown":
            return None
        # YYYY-MM-DD 형식에서 연도 추출
        year_match = re.match(r"(\d{4})", date_str)
        if year_match:
            return int(year_match.group(1))
        return None

    def _save_results(self, sermons: List[SermonData]):
        """크롤링된 설교를 저장소에 저장합니다."""
        try:
            self.storage.save(sermons)
            print(f"Data saved to: {self.storage.get_file_path()}")
        except Exception as e:
            print(f"✗ Failed to save data: {e}")

    def close(self):
        """리소스를 정리합니다."""
        self.http_client.close()
