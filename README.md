# 대덕교회 AI 사역 비서

목회자와 교회 리더를 위한 AI 기반 설교 지원 시스템

## 주요 기능

- **설교 아카이브 검색**: 과거 설교를 의미 기반으로 검색 (벡터 검색)
- **멀티 프로필 모드**: 연구용 / 상담용 / 교육용 답변 스타일
- **자동 출처 인용**: "YYYY년 MM월 DD일 '설교제목' 설교에서는..." 형식
- **대화형 인터페이스**: 실시간 질문 및 모드 전환

## 기술 스택

| 분류 | 기술 |
|------|------|
| **LLM** | OpenAI GPT-4o-mini |
| **임베딩** | dragonkue/bge-m3-ko (1024차원, 로컬) |
| **벡터DB** | PostgreSQL + pgvector |
| **백엔드** | FastAPI, LangGraph |
| **프론트엔드** | Next.js, React, Tailwind CSS |
| **인프라** | Oracle Cloud |

## 프로젝트 구조

```
Church/
├── backend/
│   ├── agents/
│   │   └── new_pipeline.py       # 메인 파이프라인 (대화형 인터페이스)
│   ├── sermon_agent/             # LangGraph 노드 모듈
│   │   ├── nodes/
│   │   │   ├── query_router.py       # 질문 분류 (OpenAI)
│   │   │   ├── sermon_retriever.py   # 벡터 검색 (로컬 임베딩)
│   │   │   └── answer_creator.py     # 답변 생성 (OpenAI)
│   │   ├── state/
│   │   │   └── sermon_state.py
│   │   ├── utils/
│   │   │   └── scripture_parser.py
│   │   ├── config.py
│   │   └── graph.py
│   ├── crawling/                 # 대덕교회 크롤러 (모듈화)
│   │   ├── core/
│   │   │   ├── config.py             # 설정
│   │   │   ├── driver.py             # Selenium WebDriver
│   │   │   ├── parser.py             # 텍스트 파싱
│   │   │   ├── extractor.py          # 페이지 추출
│   │   │   └── storage.py            # JSON 저장
│   │   ├── crawler.py                # 메인 크롤러 클래스
│   │   ├── run.py                    # CLI 실행
│   │   └── output/
│   ├── database/
│   ├── embedding/
│   ├── main.py                   # FastAPI 서버
│   └── test_vector_only.py       # 벡터 검색 테스트 (API 비용 없음)
├── frontend/
│   └── src/
│       ├── app/page.tsx
│       └── lib/api.ts
├── .env                          # 환경 변수
├── requirements.txt
├── README.md                     # 이 파일
└── CLAUDE.md                     # 상세 프로젝트 문서
```

## 설치 및 실행

### 1. 환경 변수 설정

`.env` 파일 생성:
```env
# OpenAI (필수)
OPENAI_API_KEY=sk-...

# 데이터베이스 (필수)
DATABASE_URL=postgresql://user:pass@host:5432/church_db

# 선택사항
LANGSMITH_API_KEY=...
LANGSMITH_TRACING=true
```

### 2. 백엔드 실행

```bash
# 가상환경 활성화
.church\Scripts\activate  # Windows
source .church/bin/activate  # Linux/Mac

# 의존성 설치
pip install -r requirements.txt

# FastAPI 서버 실행
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev
```

### 4. 파이프라인 실행

```bash
# 대화형 모드 실행
python -B backend/agents/new_pipeline.py

# 벡터 검색만 테스트 (API 비용 없음)
python -B backend/test_vector_only.py
```

> `-B` 플래그: Python 캐시 파일(__pycache__) 생성 방지

## 대화형 인터페이스

```
============================================================
대덕교회 설교 AI 에이전트
============================================================

[사용법]
  - 질문을 입력하세요
  - 모드 변경: /mode research|counseling|education
  - 종료: /quit 또는 /exit
============================================================

현재 모드: research

[질문] 하나님의 사랑에 대한 설교가 있나요?
```

### 명령어

| 명령어 | 설명 |
|--------|------|
| `/mode research` | 연구 모드 (신학적 분석) |
| `/mode counseling` | 상담 모드 (위로, 격려) |
| `/mode education` | 교육 모드 (쉬운 설명) |
| `/help` | 도움말 |
| `/quit` | 종료 |

## 워크플로우

```
사용자 질문
    │
    ▼
┌─────────────────┐
│  query_router   │ ← 질문 분류, RAG 사용 여부 결정 (GPT-4o-mini)
└────────┬────────┘
         │
    use_rag?
    ├─ Yes ─┐
    │       ▼
    │  ┌─────────────────┐
    │  │ sermon_retriever│ ← 벡터 검색 (bge-m3-ko, pgvector)
    │  └────────┬────────┘
    │           │
    └─── No ────┼───┐
                │   │
                ▼   ▼
         ┌─────────────────┐
         │  answer_creator │ ← 답변 생성 (GPT-4o-mini)
         └────────┬────────┘
                  │
                  ▼
              최종 답변
```

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/chat/sermon` | LangGraph 에이전트 호출 |
| POST | `/auth/signup` | 회원가입 (목업) |
| POST | `/auth/login` | 로그인 (목업) |
| GET | `/health` | 헬스체크 |

### 요청 예시

```bash
curl -X POST http://localhost:8000/chat/sermon \
  -H "Content-Type: application/json" \
  -d '{
    "message": "하나님의 사랑에 대한 설교가 있나요?",
    "profile_mode": "research"
  }'
```

## 크롤러 사용법

```bash
cd backend/crawling

# 테스트 실행 (2페이지, 페이지당 3개)
python run.py

# 전체 크롤링
python run.py --full --all-posts

# 연도별 크롤링
python run.py --full --all-posts --years 2024 2025

# Python 코드에서 사용
from crawling import DaedeokCrawler, CrawlerConfig

config = CrawlerConfig(year_filter=[2024])
crawler = DaedeokCrawler(config)
sermons = crawler.crawl()
crawler.save()
```

## 데이터 현황

- **설교 수**: 160개
- **기간**: 2023년 ~ 2026년
- **교회**: 대덕교회
- **임베딩**: bge-m3-ko (1024차원)

## 라이선스

내부 사용 전용
