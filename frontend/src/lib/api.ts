"use client";

/**
 * Next.js ↔ FastAPI 통신 유틸
 *
 * - NEXT_PUBLIC_API_BASE_URL 환경변수를 기준으로 FastAPI 서버와 통신
 * - 로그인/회원가입, 설교 챗 API 틀만 구현
 */

export type ProfileMode = "research" | "counseling" | "education";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(
  path: string,
  options: RequestInit & { parseJson?: boolean } = {},
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const { parseJson = true, ...rest } = options;

  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
    ...rest,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      // FastAPI 오류 포맷: {"detail": "..."}
      // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access
      if (data?.detail) detail = String(data.detail);
    } catch {
      // ignore
    }
    throw new Error(`API ${res.status}: ${detail}`);
  }

  if (!parseJson) {
    // @ts-expect-error - caller가 직접 처리
    return res as T;
  }

  return (await res.json()) as T;
}

// ─────────────────────────────────────────────────────────
// Auth API (틀만) - FastAPI /auth와 매칭
// ─────────────────────────────────────────────────────────

export interface AuthResponse {
  user_id: string;
  access_token: string;
}

export async function apiSignup(input: {
  username: string;
  password: string;
}): Promise<AuthResponse> {
  return request<AuthResponse>("/auth/signup", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function apiLogin(input: {
  username: string;
  password: string;
}): Promise<AuthResponse> {
  return request<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

// ─────────────────────────────────────────────────────────
// 설교 챗 API - LangGraph 에이전트 연결
// ─────────────────────────────────────────────────────────

export interface SermonChatRequest {
  user_id: string;
  question: string;
  profile_mode?: ProfileMode;
  session_id?: string;
}

export interface SermonChatResponse {
  answer: string;
  references: Array<{
    sermon_id?: string;
    title?: string;
    date?: string;
    scripture?: string;
    thumbnail_url?: string;
  }>;
  scripture_refs: string[];
  category?: string;
}

export async function apiSermonChat(
  input: SermonChatRequest,
): Promise<SermonChatResponse> {
  return request<SermonChatResponse>("/chat/sermon", {
    method: "POST",
    body: JSON.stringify({
      profile_mode: "research",
      session_id: "default",
      ...input,
    }),
  });
}


