import time
import re
import json
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin, urlparse, parse_qs
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# .env 파일에서 환경변수 로드
load_dotenv()

# 크롤링할 기본 설정
BASE_URL = "https://ddpc.or.kr/260"  # 주일오전 설교요약 게시판
CHURCH_NAME = "대덕교회"

# 결과를 저장할 파일 이름
OUTPUT_FILE = "output/daedeok_sermons_2023_2026.json"


def create_driver():
    """Selenium WebDriver 생성 (Selenium 4 자동 드라이버 관리)"""
    options = Options()
    options.add_argument("--headless=new")  # 새로운 헤드리스 모드
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # Selenium 4.6+는 자동으로 ChromeDriver를 다운로드/관리함
    driver = webdriver.Chrome(options=options)
    return driver


def parse_date_from_title(title: str) -> Optional[str]:
    """제목에서 날짜 추출 (YYYYMMDD 형식을 YYYY-MM-DD로 변환)"""
    # 제목 형식: "20260111 - 열 처녀 비유"
    date_match = re.search(r"(\d{8})", title)
    if date_match:
        date_str = date_match.group(1)
        # YYYYMMDD -> YYYY-MM-DD
        try:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        except:
            return date_str
    return None


def extract_sermon_title_from_full_title(full_title: str) -> str:
    """전체 제목에서 설교 제목만 추출"""
    # "20260111 - 열 처녀 비유" -> "열 처녀 비유"
    match = re.search(r"-\s*(.+)$", full_title)
    if match:
        return match.group(1).strip()
    return full_title


def extract_post_links_selenium(driver, base_url: str) -> List[tuple]:
    """Selenium으로 게시글 목록 페이지에서 게시글 링크 추출"""
    posts = []

    try:
        # 페이지 로딩 대기 (게시판 위젯이 로드될 때까지)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    ".widget.board, .li_board, .board_list, [data-widget-type='board']",
                )
            )
        )

        # 추가 대기 (동적 콘텐츠 완전 로딩)
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
                    print(f"  Found {len(elements)} elements with selector: {selector}")
                    links.extend(elements)
            except:
                continue

        # 중복 제거하면서 링크 추출
        seen_urls = set()
        for link in links:
            try:
                href = link.get_attribute("href")
                title = link.text.strip()

                if not href or not title:
                    continue

                # idx 파라미터가 있는 링크만
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

            except Exception as e:
                continue

    except Exception as e:
        print(f"  Error extracting links: {e}")

    return posts


def parse_sermon_summary_selenium(driver) -> Dict[str, Any]:
    """
    Selenium으로 상세 페이지에서 설교 요약 파싱
    """
    data = {
        "scripture": "",
        "preacher": "",
        "summary_content": "",
        "paragraphs": [],
    }

    try:
        # 페이지 로딩 대기
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    ".board_view, .board_txt_area, .view_content, [class*='comment_body']",
                )
            )
        )
        time.sleep(2)

        # 본문 영역 찾기 (여러 선택자 시도)
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
            print("  Warning: Content element not found")
            return data

        # 모든 p 태그 찾기
        paragraphs = content_element.find_elements(By.TAG_NAME, "p")

        for p in paragraphs:
            text = p.text.strip()
            if not text:
                continue

            # 성경 구절 추출
            if "본" in text and "문" in text and ":" in text:
                scripture_match = re.search(r":\s*(.+)$", text)
                if scripture_match:
                    raw_scripture = scripture_match.group(1).strip()

                    # 성경 구절 패턴만 추출 (한글 책명 + 장:절 형식)
                    # 예: "마 25 : 1 ~ 13", "창 1:1-31", "대하 31 : 21"
                    clean_match = re.match(
                        r'^([가-힣]+\s*\d+\s*[:\s]*\d*\s*[~\-\s]*\d*)',
                        raw_scripture
                    )
                    if clean_match:
                        data["scripture"] = clean_match.group(1).strip()
                    elif len(raw_scripture) <= 30:
                        # 패턴 매칭 실패해도 30자 이하면 저장
                        data["scripture"] = raw_scripture

            # 설교자 추출
            elif "설교자" in text and ":" in text:
                preacher_match = re.search(r":\s*(.+)$", text)
                if preacher_match:
                    data["preacher"] = preacher_match.group(1).strip()

            # 본문 내용
            else:
                if text and not text.startswith("◈"):
                    data["paragraphs"].append(text)

        # 모든 문단을 하나의 문자열로 합치기
        data["summary_content"] = "\n\n".join(data["paragraphs"])

    except Exception as e:
        print(f"  Error parsing content: {e}")

    return data


def crawl_sermons(
    start_page: int = 1,
    end_page: int = 9,
    posts_per_page: int = None,
    year_filter: List[int] = None,
):
    """
    대덕교회 설교 요약 크롤링 (Selenium 버전)
    """
    sermons = []
    total_posts = 0
    skipped_by_year = 0

    # WebDriver 생성
    print("Initializing Chrome WebDriver...")
    driver = create_driver()

    try:
        for page in range(start_page, end_page + 1):
            print(f"\n{'='*60}")
            print(f"Processing List Page: {page}/{end_page}")
            print(f"{'='*60}")

            # 페이지 URL 구성
            if page == 1:
                page_url = BASE_URL
            else:
                page_url = f"{BASE_URL}?page={page}"

            print(f"Loading: {page_url}")
            driver.get(page_url)

            # 게시글 링크 추출
            posts = extract_post_links_selenium(driver, BASE_URL)
            print(f"Found {len(posts)} posts on this page")

            if not posts:
                print(f"  No posts found on page {page}")
                continue

            # 게시글 수 제한 (테스트용)
            if posts_per_page:
                posts = posts[:posts_per_page]
                print(f"Processing first {posts_per_page} posts (test mode)")

            # 각 게시글 처리
            for idx, (post_id, full_title, detail_url) in enumerate(posts, 1):
                print(f"\n[{idx}/{len(posts)}] Processing: {full_title}")
                print(f"  URL: {detail_url}")

                # 제목에서 날짜 추출
                date = parse_date_from_title(full_title)
                if date:
                    print(f"  Date: {date}")

                    # 연도 필터 적용
                    if year_filter:
                        year = int(date[:4])
                        if year not in year_filter:
                            print(f"  [SKIP] Year {year} not in filter {year_filter}")
                            skipped_by_year += 1
                            continue
                        else:
                            print(f"  [OK] Year {year} matches filter")
                else:
                    print(f"  Warning: Could not parse date from title")

                # 설교 제목만 추출
                sermon_title = extract_sermon_title_from_full_title(full_title)

                # 상세 페이지 크롤링
                try:
                    driver.get(detail_url)
                    sermon_data = parse_sermon_summary_selenium(driver)

                    if not sermon_data["summary_content"]:
                        print(f"  Warning: No summary content found")
                        continue

                    print(f"  Title: {sermon_title}")
                    print(f"  Scripture: {sermon_data['scripture']}")
                    print(f"  Preacher: {sermon_data['preacher']}")
                    print(
                        f"  Summary length: {len(sermon_data['summary_content'])} chars"
                    )

                    # 데이터 저장 (DB sermons 테이블 컬럼에 맞춤)
                    sermon_entry = {
                        "id": int(post_id),  # PK
                        "title": sermon_title,
                        "sermon_date": date or None,
                        "bible_ref": sermon_data["scripture"],
                        "content_summary": sermon_data["summary_content"],
                        "video_url": detail_url,
                        "church_name": CHURCH_NAME,
                        # 추가 필드 (DB에는 없지만 유용한 정보)
                        "preacher": sermon_data["preacher"],
                    }

                    sermons.append(sermon_entry)
                    total_posts += 1
                    print(f"  [OK] Saved successfully")

                except Exception as e:
                    print(f"  [ERROR] Error parsing post {post_id}: {e}")
                    import traceback

                    traceback.print_exc()

                # 게시글 간 대기 (서버 부하 방지)
                time.sleep(2)

            # 페이지 간 대기
            print(f"\nWaiting 3 seconds before next page...")
            time.sleep(3)

    finally:
        # WebDriver 종료
        driver.quit()
        print("\nWebDriver closed.")

    # JSON 파일로 저장
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(sermons, f, ensure_ascii=False, indent=2)

    # 결과 요약
    print("\n" + "=" * 60)
    print("Crawling Completed!")
    print(f"Total sermon summaries collected: {total_posts}")
    print(f"Skipped by year filter: {skipped_by_year}")
    print(f"Data saved to: {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    # 설정
    START_PAGE = 1
    END_PAGE = 18  # 전체 페이지 (1-18)
    POSTS_PER_PAGE = None  # 전체 게시글
    YEAR_FILTER = [2023, 2024, 2025, 2026]  # 2023~2026년 (약 3년치)

    print("=" * 60)
    print("Daedeok Church Sermon Summary Crawler (Selenium)")
    print("=" * 60)
    print(f"Target: {BASE_URL} (주일오전 설교요약)")
    print(f"Pages: {START_PAGE} to {END_PAGE}")
    print(f"Posts per page: {POSTS_PER_PAGE if POSTS_PER_PAGE else 'All'}")
    print(f"Year filter: {YEAR_FILTER if YEAR_FILTER else 'None (All years)'}")
    print(f"Output: {OUTPUT_FILE}")
    print()
    print("Note: Selenium을 사용하여 동적 콘텐츠를 크롤링합니다.")
    print("=" * 60 + "\n")

    crawl_sermons(
        start_page=START_PAGE,
        end_page=END_PAGE,
        posts_per_page=POSTS_PER_PAGE,
        year_filter=YEAR_FILTER,
    )
