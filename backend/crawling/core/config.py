"""
서강감리교회 크롤러 설정
"""
import os
from pathlib import Path

# 환경 변수 로드
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv이 설치되지 않았습니다. 시스템 환경변수만 사용합니다.")


class CrawlerConfig:
    """크롤러 메인 설정"""

    # 기본 URL
    BASE_URL = "http://www.seokang.or.kr/EZ/rb/"
    LIST_URL = "http://www.seokang.or.kr/EZ/rb/board.asp"

    # 게시판 파라미터
    BOARD_PARAMS = {
        "BoardModule": "Board",
        "tbcode": "bible02"
    }

    # 크롤링 설정
    PAGE_START = 1
    PAGE_END = 17  # 전체 페이지 크롤링
    POSTS_PER_PAGE = None  # 페이지당 모든 게시글 크롤링

    # 연도 필터 설정 (None이면 모든 연도 수집)
    # 예: [2025, 2026] 또는 [2024] 또는 [2023]
    YEAR_FILTER = [2025, 2026]  # 2025-2026년 데이터만 수집

    # 요청 설정
    REQUEST_TIMEOUT = 30
    REQUEST_ENCODING = "euc-kr"

    # Rate Limiting (초 단위)
    DELAY_BETWEEN_POSTS = 3
    DELAY_BETWEEN_PAGES = 5
    DELAY_BETWEEN_IMAGES = 3

    # 요청용 User Agent
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    )

    # HTTP 요청 헤더
    HTTP_HEADERS = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    # 이미지 다운로드 헤더
    IMAGE_HEADERS = {
        "User-Agent": USER_AGENT,
        "Referer": "http://www.seokang.or.kr/",
    }

    # 이미지 필터링 설정
    MIN_IMAGE_SIZE = 100  # 픽셀
    MIN_IMAGE_BYTES = 10000  # 10KB

    # 제외할 이미지 키워드
    EXCLUDED_IMAGE_KEYWORDS = ["icon", "logo", "banner", "btn", "bullet"]

    # 우선순위 이미지 키워드
    PRIORITY_IMAGE_KEYWORDS = ["sermon", "설교", "주보", "bulletin", "content", "board"]


class GeminiConfig:
    """Gemini API 설정"""

    # API 설정
    API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    API_URL = "https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent"

    # API 타임아웃
    OCR_TIMEOUT = 60
    SUMMARY_TIMEOUT = 30

    # 생성 설정
    OCR_TEMPERATURE = 0.2
    OCR_MAX_TOKENS = 8000

    SUMMARY_TEMPERATURE = 0.3
    SUMMARY_MAX_TOKENS = 800

    # Rate Limit 설정
    RATE_LIMIT_WAIT = 15  # 초
    RATE_LIMIT_RETRY_BUFFER = 2  # 추가 대기 시간 (초)

    # 컨텐츠 검증
    MIN_CONTENT_LENGTH = 100
    SUMMARY_POINTS_COUNT = 3


class StorageConfig:
    """데이터 저장 설정"""

    # 기본 경로
    BASE_DIR = Path(__file__).parent.parent
    OUTPUT_DIR = BASE_DIR / "output"

    # 출력 파일
    DEFAULT_OUTPUT_FILE = OUTPUT_DIR / "church.json"
    BACKUP_FILE = OUTPUT_DIR / "sermons_backup.json"

    # 출력 디렉토리 생성
    OUTPUT_DIR.mkdir(exist_ok=True)


class ChurchConfig:
    """교회 관련 설정"""

    CHURCH_NAME = "서강감리교회"
    CHURCH_WEBSITE = "http://www.seokang.or.kr"


# 설정 검증
def validate_config():
    """설정값 검증"""
    if not GeminiConfig.API_KEY:
        print("\n" + "=" * 60)
        print("WARNING: GEMINI_API_KEY not found!")
        print("OCR will be skipped. Please set your API key:")
        print("  export GEMINI_API_KEY='your_api_key'")
        print("=" * 60 + "\n")
        return False
    return True
