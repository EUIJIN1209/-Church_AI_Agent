# 설교 지원 AI 에이전트

LangGraph 기반의 설교 지원 AI 에이전트입니다. 멀티 프로필 모드(연구용/상담용/교육용)를 지원하여 목사님의 설교 준비를 효율적으로 지원합니다.

## 주요 기능

### 1. 지능형 질문 라우팅
- 사용자 질문을 분석하여 카테고리 분류
- 설교 준비, 상담, 성경 해석, 설교 검색 등 자동 분류
- RAG 검색 필요 여부 자동 판단

### 2. 설교 아카이브 검색 (RAG)
- PGVector 기반 벡터 검색으로 관련 설교 자동 검색
- 의미 기반 검색으로 키워드 매칭의 한계 극복
- 과거 설교와의 연결점 자동 제시

### 3. 멀티 프로필 모드
- **연구 모드 (research)**: 깊이 있는 본문 해석과 신학적 분석
- **상담 모드 (counseling)**: 실생활 적용 중심의 실용적 조언
- **교육 모드 (education)**: 이해하기 쉬운 교육적 설명

### 4. 구조화된 답변 생성
- 성경 구절 하이라이트
- 참고 설교 목록 자동 추출
- 프로필 모드에 따른 맞춤형 답변 스타일

## 프로젝트 구조

```
backend/sermon_agent/
├── __init__.py
├── config.py                 # 설정 파일
├── graph.py                  # LangGraph 워크플로우 정의
├── example_usage.py          # 사용 예제
├── README.md
├── state/
│   ├── __init__.py
│   └── sermon_state.py       # State 스키마 정의
├── nodes/
│   ├── __init__.py
│   ├── query_router.py       # 질문 라우팅 노드
│   ├── sermon_retriever.py   # 설교 검색 노드
│   └── answer_creator.py     # 답변 생성 노드
└── utils/
    ├── __init__.py
    └── scripture_parser.py   # 성경 구절 파싱 유틸리티
```

## 워크플로우

```
[시작]
  ↓
[query_router] - 질문 분석 및 라우팅 결정
  ↓
  ├─ use_rag=True → [sermon_retriever] - 설교 아카이브 검색
  │                    ↓
  └─ use_rag=False ────┘
                      ↓
              [answer_creator] - 최종 답변 생성
                      ↓
                   [종료]
```

## 설치 및 설정

### 1. 환경 변수 설정

`.env` 파일에 다음 변수들을 설정하세요:

```env
# OpenAI API
OPENAI_API_KEY=your_openai_api_key
ROUTER_MODEL=gpt-4o-mini
ANSWER_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small

# 데이터베이스
DATABASE_URL=postgresql://user:password@localhost:5432/sermon_db

# 검색 설정
SERMON_RETRIEVER_RAW_TOP_K=10
SERMON_RETRIEVER_CONTEXT_TOP_K=5
SERMON_RETRIEVER_SIM_FLOOR=0.3

# 기본 프로필 모드
DEFAULT_PROFILE_MODE=research
```

### 2. 데이터베이스 스키마

설교 아카이브를 위한 데이터베이스 테이블이 필요합니다:

```sql
-- sermons 테이블
CREATE TABLE sermons (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    date DATE,
    scripture VARCHAR(255),
    summary TEXT,
    full_text TEXT,
    thumbnail_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- sermon_embeddings 테이블 (PGVector)
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE sermon_embeddings (
    id SERIAL PRIMARY KEY,
    sermon_id INTEGER REFERENCES sermons(id) ON DELETE CASCADE,
    field VARCHAR(50) NOT NULL,  -- 'title' 또는 'summary'
    embedding vector(1536),  -- text-embedding-3-small 차원
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 벡터 검색을 위한 인덱스
CREATE INDEX ON sermon_embeddings USING ivfflat (embedding vector_cosine_ops);
```

## 사용 방법

### 기본 사용 예제

```python
from datetime import datetime, timezone
from backend.sermon_agent.graph import get_sermon_agent_graph
from backend.sermon_agent.state.sermon_state import State

# 그래프 인스턴스 가져오기
graph = get_sermon_agent_graph()

# 초기 상태 구성
initial_state: State = {
    "session_id": "session_001",
    "user_id": 1,
    "end_session": False,
    "started_at": datetime.now(timezone.utc).isoformat(),
    "last_activity_at": datetime.now(timezone.utc).isoformat(),
    "turn_count": 1,
    "messages": [],
    "rolling_summary": None,
    "profile_mode": "research",  # 또는 "counseling", "education"
    "profile_mode_prompt": None,
    "user_context": {},
    "retrieval": {},
    "rag_snippets": [],
    "user_input": "마태복음 5장 3절로 설교한 적이 있나요?",
    "answer": {},
    "user_action": None,
    "router": {},
    "next": None,
    "uploaded_images": [],
    "ocr_results": [],
    "streaming_mode": False,
    "streaming_context": {},
}

# 그래프 실행
result = graph.invoke(initial_state)

# 결과 확인
print(result["answer"]["text"])
for ref in result["answer"]["references"]:
    print(f"- {ref['title']} ({ref['date']})")
```

### 프로필 모드 전환

프로필 모드를 변경하면 답변 스타일이 자동으로 변경됩니다:

```python
# 연구 모드
state["profile_mode"] = "research"

# 상담 모드
state["profile_mode"] = "counseling"

# 교육 모드
state["profile_mode"] = "education"
```

## API 통합 예제

FastAPI와 통합하는 예제:

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from backend.sermon_agent.graph import get_sermon_agent_graph
from backend.sermon_agent.state.sermon_state import State, ProfileMode

app = FastAPI()
graph = get_sermon_agent_graph()


class ChatRequest(BaseModel):
    user_id: int
    question: str
    profile_mode: ProfileMode = "research"
    session_id: str = "default"


class ChatResponse(BaseModel):
    answer: str
    references: list
    scripture_refs: list
    category: str


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    initial_state: State = {
        "session_id": request.session_id,
        "user_id": request.user_id,
        "profile_mode": request.profile_mode,
        "user_input": request.question,
        # ... 나머지 필드 초기화
    }
    
    result = graph.invoke(initial_state)
    
    return ChatResponse(
        answer=result["answer"]["text"],
        references=result["answer"]["references"],
        scripture_refs=result["answer"]["scripture_refs"],
        category=result["router"]["category"],
    )
```

## 확장 가능성

### 1. OCR 통합
- 주보 이미지 업로드 시 Gemini 2.0 Flash로 OCR 처리
- 추출된 텍스트를 자동으로 설교 아카이브에 추가

### 2. 나눔 질문 자동 생성
- 설교 본문을 바탕으로 소그룹 예배용 질문지 자동 생성

### 3. 시계열 분석
- 특정 주제에 대한 지난 수년간의 설교 변화 양상 리포트

### 4. 스트리밍 지원
- 실시간 스트리밍 답변 생성 (현재 기본 구조 포함)

## 주의사항

1. **데이터베이스 연결**: PGVector 확장이 설치되어 있어야 합니다.
2. **임베딩 모델**: 현재 `text-embedding-3-small` 사용 중이며, 한국어 최적화를 위해 `bge-m3-ko` 등으로 변경 가능합니다.
3. **토큰 사용량**: OpenAI API 사용량에 주의하세요.
4. **캐싱**: 임베딩 캐싱으로 API 호출 최소화 (최대 30개 캐시)

## 라이선스

이 프로젝트는 내부 사용을 위한 것입니다.

