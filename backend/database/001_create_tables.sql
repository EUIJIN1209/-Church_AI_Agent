-- ============================================================
-- 대덕교회 AI 사역 비서 - 데이터베이스 초기화 스크립트
-- ============================================================
-- 실행 순서: 1번 (테이블 생성)
-- PostgreSQL 14+ 및 pgvector 확장 필요
-- ============================================================

-- 1. pgvector 확장 활성화
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- SERMON DATA LAYER (AI 에이전트 핵심 검색 영역)
-- ============================================================

-- 2. sermons 테이블 (설교 원본 데이터)
CREATE TABLE IF NOT EXISTS sermons (
    id BIGINT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    sermon_date DATE,
    bible_ref VARCHAR(100),
    content_summary TEXT,
    video_url TEXT,
    church_name VARCHAR(50),
    preacher VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE sermons IS '설교 원본 데이터';
COMMENT ON COLUMN sermons.id IS '고유 번호 (크롤링 idx)';
COMMENT ON COLUMN sermons.title IS '설교 제목';
COMMENT ON COLUMN sermons.sermon_date IS '설교 날짜';
COMMENT ON COLUMN sermons.bible_ref IS '성경 본문 구절';
COMMENT ON COLUMN sermons.content_summary IS '설교 요약 내용';
COMMENT ON COLUMN sermons.video_url IS '설교 영상/게시글 링크';
COMMENT ON COLUMN sermons.church_name IS '교회명';
COMMENT ON COLUMN sermons.preacher IS '설교자';

-- 3. sermon_embeddings 테이블 (임베딩 벡터 데이터)
CREATE TABLE IF NOT EXISTS sermon_embeddings (
    id BIGSERIAL PRIMARY KEY,
    sermon_id BIGINT NOT NULL REFERENCES sermons(id) ON DELETE CASCADE,
    embedding VECTOR(1024) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE sermon_embeddings IS '설교 임베딩 벡터 데이터';
COMMENT ON COLUMN sermon_embeddings.sermon_id IS 'sermons.id 참조';
COMMENT ON COLUMN sermon_embeddings.embedding IS '1024차원 벡터 (bge-m3-ko)';
COMMENT ON COLUMN sermon_embeddings.model_name IS '임베딩 모델명';
COMMENT ON COLUMN sermon_embeddings.model_version IS '모델 버전';

-- ============================================================
-- USER DATA LAYER (사용자 관리)
-- ============================================================

-- 4. users 테이블 (사용자 계정)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE users IS '사용자 계정';
COMMENT ON COLUMN users.role IS '역할 (admin/user)';

-- 5. profiles 테이블 (사용자 프로필)
CREATE TABLE IF NOT EXISTS profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100),
    department VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE profiles IS '사용자 프로필';

-- 6. chat_sessions 테이블 (AI 채팅 세션)
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    current_thought TEXT,
    last_action VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE chat_sessions IS 'AI 채팅 세션';
COMMENT ON COLUMN chat_sessions.current_thought IS 'AI 추론 상태';
COMMENT ON COLUMN chat_sessions.last_action IS '마지막 액션 (VECTOR_SEARCH / REPLY_GENERATION)';

-- ============================================================
-- 완료 메시지
-- ============================================================
SELECT 'Tables created successfully!' AS status;
