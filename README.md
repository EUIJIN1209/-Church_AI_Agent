# Church-AI-Agent
# 설교비서 에이전트 (Sermon Assistant)

## 프로젝트 구조 (Project Structure)

```
Church/
├── backend/
│   └── agents/
│       └── new_pipeline.py          # AI 에이전트 파이프라인
│
├── frontend/                         # Next.js 프론트엔드
│   ├── src/
│   │   ├── app/                     # Next.js App Router
│   │   │   ├── globals.css         # 글로벌 스타일
│   │   │   ├── layout.tsx          # 루트 레이아웃
│   │   │   └── page.tsx            # 메인 페이지
│   │   │
│   │   └── lib/                    # 유틸리티 라이브러리
│   │       └── api.ts              # API 통신 모듈
│   │
│   ├── .gitignore                  # Git 제외 파일 설정
│   ├── package.json                # 의존성 관리
│   ├── package-lock.json           # 의존성 버전 잠금
│   ├── tsconfig.json               # TypeScript 설정
│   ├── postcss.config.mjs          # PostCSS 설정
│   └── README.md                   # Frontend 문서
│
├── .env                             # 환경 변수
├── .gitignore                       # 프로젝트 Git 제외 설정
├── requirements.txt                 # Python 의존성
└── README.md                        # 프로젝트 문서

```

### Backend

#### agents/
- **new_pipeline.py**: AI 에이전트의 핵심 파이프라인 로직

### Frontend (Next.js)

#### src/app/
- **globals.css**: 전역 CSS 스타일 정의
- **layout.tsx**: Next.js App Router의 루트 레이아웃 컴포넌트
- **page.tsx**: 메인 페이지 컴포넌트

#### src/lib/
- **api.ts**: 백엔드 API와 통신하는 유틸리티 함수들

#### Configuration Files
- **package.json**: 프로젝트 의존성 및 스크립트 정의
- **tsconfig.json**: TypeScript 컴파일러 설정
- **postcss.config.mjs**: PostCSS 처리 설정

## 기술 스택 (Tech Stack)

### Frontend
- Next.js (React Framework)
- TypeScript
- PostCSS

### Backend
- Python
- AI Agent Pipeline

