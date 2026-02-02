# 대덕교회 AI 사역 비서

목회자와 교회 리더를 위한 AI 기반 설교 지원 시스템

## 주요 기능

- **설교 아카이브 검색**: 과거 설교를 의미 기반으로 검색 (벡터 검색)
- **멀티 프로필 모드**: 연구용 / 상담용 / 교육용 답변 스타일
- **자동 출처 인용**: "YYYY년 MM월 DD일 '설교제목' 설교에서는..." 형식

## 기술 스택

| 분류 | 기술 |
|------|------|
| **LLM** | OpenAI GPT-4o-mini |
| **임베딩** | dragonkue/bge-m3-ko (1024차원) |
| **벡터DB** | PostgreSQL + pgvector |
| **백엔드** | FastAPI, LangGraph |
| **프론트엔드** | Next.js, React, Tailwind CSS |
| **인프라** | Oracle Cloud |

## 프로젝트 구조

```
Church/
├── backend/
│   ├── agents/
│   │   └── new_pipeline.py       # 메인 파이프라인 (진입점)
│   ├── sermon_agent/             # LangGraph 노드 모듈
│   │   ├── nodes/
│   │   │   ├── query_router.py       # 질문 분류 및 RAG 결정
│   │   │   ├── sermon_retriever.py   # 벡터 검색
│   │   │   └── answer_creator.py     # 답변 생성
│   │   ├── state/
│   │   │   └── sermon_state.py       # State 스키마
│   │   └── graph.py                  # 워크플로우 정의
│   ├── crawling/                 # 대덕교회 크롤러
│   ├── database/                 # DB 스크립트
│   ├── embedding/                # 임베딩 생성
│   ├── main.py                   # FastAPI 서버
│   └── test_vector_only.py       # 벡터 검색 테스트
├── frontend/                     # Next.js 프론트엔드
│   └── src/
│       ├── app/page.tsx          # 메인 페이지
│       └── lib/api.ts            # API 클라이언트
├── .env                          # 환경 변수
├── requirements.txt              # Python 의존성
└── CLAUDE.md                     # 상세 프로젝트 문서
```

## 설치 및 실행

### 1. 환경 변수 설정





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

### 4. 파이프라인 테스트

```bash
# 전체 파이프라인 테스트
python backend/agents/new_pipeline.py

# 벡터 검색만 테스트 (API 비용 없음)
python backend/test_vector_only.py
```

## 워크플로우

```
사용자 질문
    │
    ▼
┌─────────────────┐
│  query_router   │ ← 질문 분류, RAG 사용 여부 결정
└────────┬────────┘
         │
    use_rag?
    ├─ Yes ─┐
    │       ▼
    │  ┌─────────────────┐
    │  │ sermon_retriever│ ← 벡터 검색 (pgvector)
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

## 프로필 모드

| 모드 | 설명 |
|------|------|
| `research` | 신학적 분석, 본문 해석, 설교 구조 |
| `counseling` | 실생활 적용, 공감적 톤, 위로와 격려 |
| `education` | 쉬운 설명, 비유 사용, 나눔 질문 |

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

대덕교회 설교 데이터 수집:

```bash
cd backend/crawling

# 테스트 실행 (2페이지만)
python run.py

# 전체 크롤링
python run.py --full --all-posts

# 연도별 크롤링 (API 제한 대응)
python run.py --full --all-posts --years 2024
```

## 데이터 현황

- **설교 수**: 160개
- **기간**: 2023년 ~ 2026년
- **교회**: 대덕교회
- **임베딩**: bge-m3-ko (1024차원)

## 라이선스

내부 사용 전용
