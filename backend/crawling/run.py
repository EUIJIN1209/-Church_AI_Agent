# backend/crawling/run.py
"""
대덕교회 크롤러 CLI 실행 스크립트

사용법:
    python run.py [옵션]

옵션:
    --full            전체 페이지 크롤링 (기본값: 2페이지 테스트)
    --pages START END 페이지 범위 지정 (예: --pages 1 5)
    --all-posts       페이지당 모든 게시물 (기본값: 테스트 모드 3개)
    --years YEAR ...  연도 필터 (예: --years 2024 2025)
    --output FILE     출력 파일명

예시:
    python run.py --full --all-posts --years 2023 2024 2025 2026
    python run.py --pages 1 5 --years 2024
    python run.py  # 테스트 모드 (2페이지, 페이지당 3개)
"""

import sys
import argparse
from pathlib import Path

# 부모 디렉토리를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from crawling.crawler import DaedeokCrawler
from crawling.core import CrawlerConfig


def parse_args():
    """명령줄 인자 파싱"""
    parser = argparse.ArgumentParser(
        description="대덕교회 설교 크롤러",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--full",
        action="store_true",
        help="전체 페이지 크롤링 (1-18)",
    )

    parser.add_argument(
        "--pages",
        nargs=2,
        type=int,
        metavar=("START", "END"),
        help="페이지 범위 지정 (예: --pages 1 5)",
    )

    parser.add_argument(
        "--all-posts",
        action="store_true",
        help="페이지당 모든 게시물 크롤링",
    )

    parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        metavar="YEAR",
        help="연도 필터 (예: --years 2024 2025)",
    )

    parser.add_argument(
        "--output",
        type=str,
        default="daedeok_sermons.json",
        help="출력 파일명 (기본값: daedeok_sermons.json)",
    )

    return parser.parse_args()


def main():
    """메인 실행"""
    args = parse_args()

    # 페이지 범위
    if args.pages:
        start_page, end_page = args.pages
    elif args.full:
        start_page, end_page = 1, 18
    else:
        # 테스트 모드
        start_page, end_page = 1, 2

    # 게시물 수
    posts_per_page = None if args.all_posts else 3

    # 설정 생성
    config = CrawlerConfig(
        start_page=start_page,
        end_page=end_page,
        posts_per_page=posts_per_page,
        year_filter=args.years,
        output_file=args.output,
    )

    # 설정 출력
    print("=" * 60)
    print("대덕교회 설교 크롤러")
    print("=" * 60)
    print(f"URL: {config.base_url}")
    print(f"페이지: {config.start_page} ~ {config.end_page}")
    print(f"게시물/페이지: {posts_per_page or '전체'}")
    print(f"연도 필터: {config.year_filter or '없음'}")
    print(f"출력: {config.output_path}")
    print("=" * 60)

    # 크롤러 실행
    crawler = DaedeokCrawler(config)

    try:
        sermons = crawler.crawl()
        crawler.save()
        print(f"\n[OK] {len(sermons)}개 설교 수집 완료")
        return 0

    except KeyboardInterrupt:
        print("\n\n[!] 사용자에 의해 중단됨")
        return 1

    except Exception as e:
        print(f"\n\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
