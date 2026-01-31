"""
서강감리교회 크롤러를 실행하는 메인 진입점.

사용법:
    python run.py [옵션]

옵션:
    --no-ocr          OCR 비활성화 (빠르지만 덜 정확함)
    --full            모든 페이지 크롤링 (기본값: 2페이지 테스트 모드)
    --pages START END 페이지 범위 지정 (예: --pages 1 5)
    --all-posts       페이지당 모든 게시물 크롤링 (기본값: 테스트 모드에서 3개 게시물)
    --years YEAR ...  수집할 연도 지정 (예: --years 2025 2026 또는 --years 2024)

예시:
    python run.py --full --all-posts --years 2025 2026  # 2025-2026년 데이터 전체 수집
    python run.py --full --all-posts --years 2024       # 2024년 데이터만 수집
    python run.py --pages 1 5 --years 2023              # 1-5페이지에서 2023년 데이터만 수집
"""

import sys
import argparse
from pathlib import Path

# 부모 디렉토리를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from crawling.core import SeokangCrawler, CrawlerConfig


def parse_args():
    """명령줄 인자를 파싱합니다."""
    parser = argparse.ArgumentParser(
        description="Seokang Church Sermon Crawler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--no-ocr",
        action="store_true",
        help="Disable OCR (faster but less accurate)",
    )

    parser.add_argument(
        "--full",
        action="store_true",
        help="Crawl all pages (1-17)",
    )

    parser.add_argument(
        "--pages",
        nargs=2,
        type=int,
        metavar=("START", "END"),
        help="Specify page range (e.g., --pages 1 5)",
    )

    parser.add_argument(
        "--all-posts",
        action="store_true",
        help="Crawl all posts per page (default: 3 in test mode)",
    )

    parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        metavar="YEAR",
        help="Filter by year (e.g., --years 2025 2026 or --years 2024)",
    )

    return parser.parse_args()


def main():
    """메인 진입점."""
    args = parse_args()

    # 페이지 범위 결정
    if args.pages:
        page_start, page_end = args.pages
    elif args.full:
        page_start = 1
        page_end = 17
    else:
        # 테스트 모드: 2페이지
        page_start = 1
        page_end = 2

    # 페이지당 게시물 수 결정
    posts_per_page = None if args.all_posts else 3

    # 연도 필터 결정
    year_filter = args.years if args.years else None

    # 크롤러 생성 및 실행
    crawler = SeokangCrawler(
        use_ocr=not args.no_ocr,
        page_start=page_start,
        page_end=page_end,
        posts_per_page=posts_per_page,
        year_filter=year_filter,
    )

    try:
        sermons = crawler.crawl()
        print(f"\n[OK] Successfully crawled {len(sermons)} sermons")
        return 0
    except KeyboardInterrupt:
        print("\n\n[!] Interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n[X] Fatal error: {e}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        crawler.close()


if __name__ == "__main__":
    sys.exit(main())
