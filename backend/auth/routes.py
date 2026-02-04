# backend/auth/routes.py
# -*- coding: utf-8 -*-
"""
인증 API 라우트

- POST /auth/signup - 회원가입
- POST /auth/login - 로그인
- GET /auth/me - 현재 사용자 정보
"""

import os
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv

from backend.auth.utils import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)

load_dotenv()

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)

# DB 연결
DATABASE_URL = os.getenv("DATABASE_URL")


def get_db_connection():
    """DB 연결 생성."""
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


# ─────────────────────────────────────────────────────────
# Pydantic 모델
# ─────────────────────────────────────────────────────────


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    user_id: int
    email: str
    name: Optional[str]
    role: str
    access_token: str


class UserResponse(BaseModel):
    user_id: int
    email: str
    name: Optional[str]
    role: str


# ─────────────────────────────────────────────────────────
# 헬퍼 함수
# ─────────────────────────────────────────────────────────


def get_user_by_email(email: str) -> Optional[dict]:
    """이메일로 사용자 조회."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.id, u.email, u.password_hash, u.role, p.name
                FROM users u
                LEFT JOIN profiles p ON u.id = p.user_id
                WHERE u.email = %s
                """,
                (email,),
            )
            return cur.fetchone()
    finally:
        conn.close()


def create_user(email: str, password: str, name: Optional[str] = None) -> dict:
    """새 사용자 생성."""
    password_hash = hash_password(password)

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # users 테이블에 삽입
            cur.execute(
                """
                INSERT INTO users (email, password_hash, role)
                VALUES (%s, %s, %s)
                RETURNING id, email, role, created_at
                """,
                (email, password_hash, "user"),
            )
            user = cur.fetchone()

            # profiles 테이블에 삽입 (이름이 있으면)
            if name:
                cur.execute(
                    """
                    INSERT INTO profiles (user_id, name)
                    VALUES (%s, %s)
                    """,
                    (user["id"], name),
                )

            conn.commit()
            return {**user, "name": name}
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다.")
    finally:
        conn.close()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Optional[dict]:
    """현재 로그인한 사용자 정보 (토큰에서 추출)."""
    if not credentials:
        return None

    payload = decode_access_token(credentials.credentials)
    if not payload:
        return None

    return {
        "user_id": int(payload["sub"]),
        "email": payload["email"],
        "role": payload["role"],
    }


# ─────────────────────────────────────────────────────────
# API 엔드포인트
# ─────────────────────────────────────────────────────────


@router.post("/signup", response_model=AuthResponse)
async def signup(payload: SignupRequest) -> AuthResponse:
    """
    회원가입 API.

    - 이메일 중복 검사
    - 비밀번호 해싱 후 저장
    - JWT 토큰 발급
    """
    # 이메일 중복 확인
    existing = get_user_by_email(payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다.")

    # 비밀번호 길이 검증
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="비밀번호는 6자 이상이어야 합니다.")

    # 사용자 생성
    user = create_user(payload.email, payload.password, payload.name)

    # JWT 토큰 생성
    token = create_access_token(user["id"], user["email"], user["role"])

    return AuthResponse(
        user_id=user["id"],
        email=user["email"],
        name=user.get("name"),
        role=user["role"],
        access_token=token,
    )


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest) -> AuthResponse:
    """
    로그인 API.

    - 이메일로 사용자 조회
    - 비밀번호 검증
    - JWT 토큰 발급
    """
    # 사용자 조회
    user = get_user_by_email(payload.email)
    if not user:
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")

    # 비밀번호 검증
    if not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")

    # JWT 토큰 생성
    token = create_access_token(user["id"], user["email"], user["role"])

    return AuthResponse(
        user_id=user["id"],
        email=user["email"],
        name=user.get("name"),
        role=user["role"],
        access_token=token,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)) -> UserResponse:
    """
    현재 로그인한 사용자 정보.

    - Authorization: Bearer <token> 헤더 필요
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    # DB에서 최신 정보 조회
    user = get_user_by_email(current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    return UserResponse(
        user_id=user["id"],
        email=user["email"],
        name=user.get("name"),
        role=user["role"],
    )
