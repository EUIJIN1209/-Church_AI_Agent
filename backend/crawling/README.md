# Daedeok Church Sermon Crawler

대덕교회 주보 이미지를 OCR로 분석하여 설교 데이터를 자동으로 수집하는 크롤러입니다.

## 📁 프로젝트 구조

```
backend/crawling/
├── core/                      # 핵심 모듈
│   ├── __init__.py
│   ├── config.py             # 설정 관리
│   ├── models.py             # 데이터 모델
│   ├── exceptions.py         # 커스텀 예외
│   ├── http_client.py        # HTTP 요청 처리
│   ├── image_processor.py    # 이미지 추출/필터링
│   ├── gemini_client.py      # Gemini API (OCR, 요약)
│   ├── storage.py            # 데이터 저장
│   └── crawler.py            # 메인 크롤링 로직
│
├── output/                    # 출력 파일
│   ├── file.json             # 크롤링 결과
│   └── sermons_backup_*.json # 자동 백업
│
├── run.py                     # 실행 스크립트
├── README.md                  # 문서 (이 파일)
└── crawl_daedeok.py          # [Deprecated] 기존 파일
```

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 필수 패키지 설치
pip install requests beautifulsoup4 pillow python-dotenv

# API 키 설정 (.env 파일 또는 환경변수)
export GEMINI_API_KEY="your_api_key_here"
```

### 2. 기본 실행 (테스트 모드)

```bash
# 2페이지, 페이지당 3개 게시글만 크롤링
python run.py
```

### 3. 전체 크롤링

```bash
# 모든 페이지 크롤링 (페이지 수는 사이트에 따라 자동 조정)
python run.py --full --all-posts
```

## 📖 사용법

### 명령줄 옵션

```bash
# OCR 없이 실행 (빠르지만 정확도 낮음)
python run.py --no-ocr

# 특정 페이지 범위 지정
python run.py --pages 1 5

# 모든 게시글 크롤링 (테스트 모드 해제)
python run.py --all-posts

# 연도별 크롤링 (API 제한 대응)
python run.py --full --all-posts --years 2025 2026  # 2025-2026년만
python run.py --full --all-posts --years 2024       # 2024년만
python run.py --full --all-posts --years 2023       # 2023년만

# 조합 예시: 1-5페이지, 모든 게시글, OCR 사용
python run.py --pages 1 5 --all-posts
```

### 🎯 연도별 크롤링 (권장)

API 제한을 피하면서 안전하게 크롤링하려면 연도별로 나눠서 실행하세요:

```bash
# 1단계: 2025-2026년 데이터 수집
python run.py --full --all-posts --years 2025 2026

# 2단계: 2024년 데이터 수집 (다음날 또는 API 제한 해제 후)
python run.py --full --all-posts --years 2024

# 3단계: 2023년 데이터 수집
python run.py --full --all-posts --years 2023
```

**장점:**
- ✅ API 호출 수를 분산하여 제한 회피
- ✅ 실패 시 특정 연도만 재시도 가능
- ✅ 중복 수집 방지

### Python 코드에서 사용

```python
from crawling.core import DaedeokCrawler

# 크롤러 생성 (연도 필터 포함)
crawler = DaedeokCrawler(
    use_ocr=True,
    page_start=1,
    page_end=10,  # 대덕교회 페이지 수에 맞게 조정
    posts_per_page=None,  # 모든 게시글
    year_filter=[2024]  # 2024년만 수집
)

# 크롤링 실행
sermons = crawler.crawl()

# 결과 확인
for sermon in sermons:
    print(f"{sermon.title} - {sermon.date}")

# 리소스 정리
crawler.close()
```

## 📊 출력 데이터 형식

```json
{
  "seq": "게시글 ID",
  "title": "설교 제목",
  "content": "설교 전체 내용",
  "summary": "• 핵심 포인트 1\n• 핵심 포인트 2\n• 핵심 포인트 3",
  "date": "2026-01-11",
  "scripture": "마태복음 25:1-13",
  "discussion_questions": ["질문 1", "질문 2"],
  "church_name": "대덕교회",
  "ocr_used": true,
  "image_urls": ["이미지1.jpg", "이미지2.jpg"],
  "link": "https://ddpc.or.kr/..."
}
```

## ⚙️ 설정 커스터마이징

`core/config.py`에서 다음 설정을 변경할 수 있습니다:

```python
class CrawlerConfig:
    # 대덕교회 설정
    BASE_URL = "https://ddpc.or.kr/260"
    CHURCH_NAME = "대덕교회"
    
    PAGE_START = 1               # 시작 페이지
    PAGE_END = 10                # 종료 페이지 (사이트에 맞게 조정)
    POSTS_PER_PAGE = None        # 페이지당 게시글 수 (None = 전체)
    YEAR_FILTER = [2024]         # 수집할 연도 (None = 전체)

    DELAY_BETWEEN_POSTS = 3      # 게시글 간 대기 시간 (초)
    DELAY_BETWEEN_PAGES = 5      # 페이지 간 대기 시간 (초)
    DELAY_BETWEEN_IMAGES = 3     # 이미지 간 대기 시간 (초)
```

**연도 필터 설정 예시:**
```python
YEAR_FILTER = [2025, 2026]  # 2025-2026년만
YEAR_FILTER = [2024]        # 2024년만
YEAR_FILTER = None          # 모든 연도
```

## 🔧 주요 기능

### 1. OCR (Optical Character Recognition)
- Gemini 2.5 Flash API를 사용하여 주보 이미지에서 텍스트 추출
- 구조화된 데이터 추출: 제목, 날짜, 성경 구절, 본문, 나눔 질문

### 2. AI 요약
- 설교 내용을 정확히 3개 포인트로 자동 요약
- 성경적 교훈과 적용점 포함

### 3. Rate Limiting 처리
- API 429 에러 자동 감지 및 재시도
- 적절한 대기 시간 자동 계산

### 4. 이미지 필터링
- 작은 아이콘/로고 자동 제외
- 설교 관련 이미지 우선 처리

### 5. 자동 백업
- 기존 데이터 자동 백업
- 타임스탬프 포함

### 6. 연도별 필터링
- 2024년부터 크롤링하여 API 할당량 절약
- 중복 방지 및 효율적 데이터 수집

## 🛠️ 개발

### 새 기능 추가

```python
# 1. 새 크롤러 서브클래스 생성
from crawling.core import DaedeokCrawler

class CustomCrawler(DaedeokCrawler):
    def _extract_content(self, soup):
        # 커스텀 로직
        pass

# 2. 새 스토리지 백엔드 추가
from crawling.core import SermonStorage

class DatabaseStorage(SermonStorage):
    def save(self, sermons):
        # DB 저장 로직
        pass
```

### 테스트

```python
# 단위 테스트 예시
from crawling.core import ImageProcessor

processor = ImageProcessor()
images = processor.extract_all_images(soup, base_url)
assert len(images) > 0
```

## 🐛 트러블슈팅

### API 키 오류
```
WARNING: GEMINI_API_KEY not found!
```
→ `.env` 파일에 `GEMINI_API_KEY=your_key` 추가

### Rate Limit 오류
```
⏳ Rate limit hit. Waiting 15.0s...
```
→ 정상 동작입니다. 자동으로 재시도됩니다.
→ 2024년부터 크롤링을 시작하여 할당량을 절약하세요.

### OCR 실패
```
✗ OCR failed or result too short
```
→ 이미지 품질이 낮거나 텍스트가 부족할 수 있습니다. HTML 파싱으로 fallback됩니다.

## 📝 변경 이력

### v2.2.0 (2026-01-26)
- 🏛️ **대덕교회 사이트로 변경**
- 🔗 새 URL: https://ddpc.or.kr/260
- 📋 "주일오전 설교요약" 게시판 크롤링
- 💰 API 할당량 관리: 2024년부터 크롤링 권장

### v2.1.0 (2026-01-12)
- 🎯 **연도별 필터링 기능 추가**
- 📅 `--years` 명령줄 옵션 지원
- ⚡ API 제한 대응을 위한 분할 크롤링
- 📊 필터링된 게시글 통계 추가

### v2.0.0 (2026-01-10)
- ✨ 모듈화된 아키텍처로 전면 리팩토링
- 📦 core/ 패키지로 기능별 분리
- 🎯 단일 책임 원칙 적용
- 🔧 설정 관리 개선
- 📊 통계 및 로깅 강화
- 🧪 테스트 용이성 향상

### v1.0.0
- 초기 릴리즈 (단일 파일 구조)

## 📄 라이선스

MIT License

## 👥 기여

Pull Request를 환영합니다!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request