"use client";

import { useState, useRef, useEffect } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { apiSermonChat, type SermonChatResponse } from "@/lib/api";

type MainView = "home" | "chat";
type ProfileMode = "research" | "counseling" | "education";

// 메시지 타입
interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  references?: SermonChatResponse["references"];
  category?: string;
  timestamp: Date;
}

// 사용자 정보 타입
interface UserInfo {
  userId: string;
  email: string;
  name: string;
}

export default function Home() {
  const router = useRouter();
  const [mainView, setMainView] = useState<MainView>("chat");
  const [profileMode, setProfileMode] = useState<ProfileMode>("research");
  const [user, setUser] = useState<UserInfo | null>(null);

  // 로그인 상태 확인
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    const userId = localStorage.getItem("user_id");
    const email = localStorage.getItem("user_email");
    const name = localStorage.getItem("user_name");

    if (token && userId && email) {
      setUser({ userId, email, name: name || "" });
    }
  }, []);

  // 로그아웃
  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user_id");
    localStorage.removeItem("user_email");
    localStorage.removeItem("user_name");
    setUser(null);
  };

  return (
    <div className="app-shell">
      {/* 사이드바 */}
      <aside className="sidebar">
        {/* 로고 / 브랜드 */}
        <div className="mb-6 flex items-center gap-2 px-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-slate-900 text-xs font-semibold text-white">
            SA
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-semibold text-slate-900">
              Sermon AI
            </span>
            <span className="text-[11px] text-slate-500">
              설교·사역 지원 비서
            </span>
          </div>
        </div>

        {/* 네비게이션 */}
        <nav className="flex flex-1 flex-col gap-1">
          <button
            type="button"
            className={`sidebar-nav-item ${
              mainView === "home" ? "sidebar-nav-item-active" : ""
            }`}
            onClick={() => setMainView("home")}
          >
            <span className="text-[13px]">홈</span>
          </button>
          <button
            type="button"
            className={`sidebar-nav-item ${
              mainView === "chat" ? "sidebar-nav-item-active" : ""
            }`}
            onClick={() => setMainView("chat")}
          >
            <span className="text-[13px]">AI 채팅</span>
          </button>
          <button type="button" className="sidebar-nav-item">
            <span className="text-[13px]">설교 아카이브</span>
          </button>
          <button type="button" className="sidebar-nav-item">
            <span className="text-[13px]">설정</span>
          </button>
        </nav>

        {/* 하단 영역 */}
        <div className="mt-4 border-t border-slate-200 pt-4">
          {user ? (
            <>
              <div className="mb-3 px-2">
                <p className="text-xs font-medium text-slate-800 truncate">
                  {user.name || user.email}
                </p>
                <p className="text-[10px] text-slate-500 truncate">{user.email}</p>
              </div>
              <button
                type="button"
                onClick={handleLogout}
                className="w-full rounded-full border border-slate-200 px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100"
              >
                로그아웃
              </button>
            </>
          ) : (
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => router.push("/login")}
                className="flex-1 rounded-full border border-slate-200 px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100"
              >
                로그인
              </button>
              <button
                type="button"
                onClick={() => router.push("/signup")}
                className="flex-1 rounded-full bg-slate-900 px-3 py-2 text-xs font-medium text-white hover:bg-slate-800"
              >
                회원가입
              </button>
            </div>
          )}
        </div>
      </aside>

      {/* 메인 패널 */}
      <main className="main-panel">
        {/* 상단 헤더 */}
        <header className="mb-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-slate-900">
              AI 설교 지원 에이전트
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              축적된 설교와 주보를 기반으로 설교 준비, 상담, 교육을 도와드립니다.
            </p>
          </div>

          {/* 멀티 프로필 탭 */}
          <div className="flex items-center gap-2 rounded-full border border-slate-200 bg-white p-1 text-xs font-medium shadow-sm">
            <ProfileTab
              label="연구 모드"
              mode="research"
              current={profileMode}
              onChange={setProfileMode}
            />
            <ProfileTab
              label="상담 모드"
              mode="counseling"
              current={profileMode}
              onChange={setProfileMode}
            />
            <ProfileTab
              label="교육 모드"
              mode="education"
              current={profileMode}
              onChange={setProfileMode}
            />
          </div>
        </header>

        {/* 메인 콘텐츠 영역 */}
        {mainView === "home" ? (
          <HomeDashboard />
        ) : (
          <AiChatView profileMode={profileMode} />
        )}
      </main>
    </div>
  );
}

function ProfileTab(props: {
  label: string;
  mode: ProfileMode;
  current: ProfileMode;
  onChange: (mode: ProfileMode) => void;
}) {
  const { label, mode, current, onChange } = props;
  const active = mode === current;

  return (
    <button
      type="button"
      onClick={() => onChange(mode)}
      className={`rounded-full px-3 py-1 transition-colors ${
        active
          ? "bg-slate-900 text-white"
          : "text-slate-600 hover:bg-slate-100"
      }`}
    >
      {label}
    </button>
  );
}

function HomeDashboard() {
  return (
    <div className="flex h-full flex-col gap-4">
      {/* 상단 위젯들 */}
      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* 오늘의 묵상 */}
        <div className="card col-span-2">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              오늘의 묵상
            </span>
            <span className="chip">자동 제안</span>
          </div>
          <h2 className="mb-1 text-base font-semibold text-slate-900">
            “수고하고 무거운 짐 진 자들아 다 내게로 오라”
          </h2>
          <p className="text-xs text-slate-500">마태복음 11:28</p>
          <p className="mt-3 text-sm leading-relaxed text-slate-600">
            이번 주 설교와 연결될 수 있는 짧은 묵상을 제안합니다. 필요에 따라 내용을
            수정하거나 저장해 둘 수 있습니다.
          </p>
        </div>

        {/* 최근 수집된 설교 */}
        <div className="card">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              최근 수집된 설교
            </span>
            <button
              type="button"
              className="text-[11px] font-medium text-slate-500 hover:text-slate-800"
            >
              전체 보기
            </button>
          </div>
          <ul className="space-y-2 text-sm">
            <li className="flex items-center justify-between">
              <span className="truncate text-slate-700">
                고난 속에서 발견하는 은혜
              </span>
              <span className="text-[11px] text-slate-400">주일 오전</span>
            </li>
            <li className="flex items-center justify-between">
              <span className="truncate text-slate-700">
                시편 23편 – 여호와는 나의 목자시니
              </span>
              <span className="text-[11px] text-slate-400">수요 예배</span>
            </li>
            <li className="flex items-center justify-between">
              <span className="truncate text-slate-700">
                다음 세대를 세우는 교회
              </span>
              <span className="text-[11px] text-slate-400">청년부</span>
            </li>
          </ul>
        </div>
      </section>
    </div>
  );
}

function AiChatView(props: { profileMode: ProfileMode }) {
  const { profileMode } = props;
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentReferences, setCurrentReferences] = useState<SermonChatResponse["references"]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const profileLabel =
    profileMode === "research"
      ? "연구 모드 – 본문 연구와 설교 구조 제안에 최적화"
      : profileMode === "counseling"
      ? "상담 모드 – 성도 상담과 적용점에 초점"
      : "교육 모드 – 이해하기 쉬운 설명과 질문지 생성에 초점";

  // 스크롤 자동 이동
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // 메시지 전송 핸들러
  const handleSendMessage = async (content: string) => {
    if (!content.trim() || isLoading) return;

    // 사용자 메시지 추가
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await apiSermonChat({
        user_id: "guest",
        question: content,
        profile_mode: profileMode,
        session_id: "default",
      });

      // AI 응답 추가
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: response.answer,
        references: response.references,
        category: response.category,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);

      // 참고 설교 업데이트
      if (response.references && response.references.length > 0) {
        setCurrentReferences(response.references);
      }
    } catch (error) {
      // 에러 메시지 추가
      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        role: "assistant",
        content: `오류가 발생했습니다: ${error instanceof Error ? error.message : "알 수 없는 오류"}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-120px)] flex-col gap-4">
      {/* 프로필 설명 */}
      <section className="card flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            현재 프로필
          </p>
          <p className="mt-1 text-sm font-medium text-slate-900">
            {profileLabel}
          </p>
        </div>
        <div className="hidden items-center gap-2 md:flex">
          <span className="chip">LangGraph 에이전트</span>
          {isLoading && <span className="chip bg-blue-50 text-blue-600">응답 생성 중...</span>}
        </div>
      </section>

      {/* 중앙: 출처 카드 + 채팅 영역 */}
      <section className="grid flex-1 grid-cols-1 gap-4 lg:grid-cols-[minmax(0,2.2fr)_minmax(260px,1fr)]">
        {/* 채팅 영역 */}
        <div className="card flex flex-1 flex-col overflow-hidden">
          {/* 출처 카드 영역 */}
          <div className="mb-3 border-b border-slate-100 pb-3">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              참고 설교 ({currentReferences.length}개)
            </p>
            <div className="flex gap-3 overflow-x-auto pb-1">
              {currentReferences.length > 0 ? (
                currentReferences.map((ref, idx) => (
                  <div
                    key={ref.sermon_id || idx}
                    className="flex min-w-[180px] flex-col gap-2 rounded-xl border border-slate-200 bg-slate-50/70 p-2"
                  >
                    <div className="flex items-center gap-2">
                      <div className="relative h-8 w-8 overflow-hidden rounded-md bg-slate-200 flex items-center justify-center">
                        <span className="text-xs text-slate-500">{idx + 1}</span>
                      </div>
                      <div className="flex flex-col">
                        <span className="line-clamp-1 text-xs font-semibold text-slate-800">
                          {ref.title || "제목 없음"}
                        </span>
                        <span className="text-[10px] text-slate-500">
                          {ref.date || "날짜 미상"}
                        </span>
                      </div>
                    </div>
                    {ref.scripture && (
                      <p className="text-[11px] text-slate-600">
                        {ref.scripture}
                      </p>
                    )}
                  </div>
                ))
              ) : (
                <p className="text-xs text-slate-400">질문을 입력하면 관련 설교가 표시됩니다.</p>
              )}
            </div>
          </div>

          {/* 대화 영역 */}
          <div className="flex flex-1 flex-col gap-4 overflow-y-auto pr-1 text-sm">
            {messages.length === 0 ? (
              <div className="flex flex-1 items-center justify-center text-slate-400">
                <div className="text-center">
                  <p className="text-lg mb-2">대덕교회 설교 AI 에이전트</p>
                  <p className="text-sm">설교 준비, 성경 연구, 상담에 관한 질문을 입력해주세요.</p>
                </div>
              </div>
            ) : (
              messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm ${
                    msg.role === "user"
                      ? "bg-slate-900 text-slate-50 self-end"
                      : "bg-slate-50 text-slate-800 self-start"
                  }`}
                >
                  {msg.role === "assistant" && msg.category && (
                    <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                      [{msg.category}]
                    </p>
                  )}
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                </div>
              ))
            )}
            {isLoading && (
              <div className="max-w-[80%] rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-800 self-start">
                <div className="flex items-center gap-2">
                  <div className="animate-pulse">응답 생성 중...</div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* 하단 입력창 */}
          <div className="mt-3 border-t border-slate-200 pt-3">
            <ChatInput onSend={handleSendMessage} isLoading={isLoading} />
          </div>
        </div>

        {/* 우측 패널: 프로젝트/세션 리스트 */}
        <aside className="card flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              대화 기록 ({messages.length}개)
            </span>
            <button
              type="button"
              onClick={() => {
                setMessages([]);
                setCurrentReferences([]);
              }}
              className="text-[11px] font-medium text-slate-500 hover:text-slate-800"
            >
              대화 초기화
            </button>
          </div>
          <div className="space-y-2 text-xs max-h-[400px] overflow-y-auto">
            {messages.filter(m => m.role === "user").slice(-5).map((msg) => (
              <div
                key={msg.id}
                className="flex w-full flex-col rounded-xl border border-slate-200 bg-slate-50/70 px-3 py-2"
              >
                <span className="line-clamp-2 text-[12px] font-medium text-slate-800">
                  {msg.content}
                </span>
                <span className="mt-1 text-[11px] text-slate-500">
                  {msg.timestamp.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" })}
                </span>
              </div>
            ))}
            {messages.length === 0 && (
              <p className="text-slate-400 text-center py-4">아직 대화가 없습니다.</p>
            )}
          </div>
        </aside>
      </section>
    </div>
  );
}

function ChatInput(props: { onSend: (message: string) => void; isLoading: boolean }) {
  const { onSend, isLoading } = props;
  const [input, setInput] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSend(input.trim());
      setInput("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-2">
      <div className="flex items-center gap-2 text-[11px] text-slate-500">
        <span>무엇을 도와드릴까요?</span>
        <span className="rounded-full bg-slate-100 px-2 py-0.5">
          예) "하나님의 사랑에 대한 설교를 찾아줘"
        </span>
      </div>
      <div className="flex items-center rounded-2xl border border-slate-300 bg-white px-3 py-2 shadow-sm">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="질문을 입력하세요. 설교 본문, 상황, 대상을 함께 알려주면 더 정확하게 도와드려요."
          className="flex-1 bg-transparent text-sm outline-none placeholder:text-slate-400"
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={isLoading || !input.trim()}
          className="ml-2 flex h-8 w-8 items-center justify-center rounded-full bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span className="text-xs">{isLoading ? "..." : "▶"}</span>
        </button>
      </div>
      <div className="flex items-center justify-between text-[10px] text-slate-400">
        <div className="flex gap-2">
          <span>설교 검색</span>
          <span>·</span>
          <span>성경 연구</span>
          <span>·</span>
          <span>상담 지원</span>
        </div>
        <span>{input.length} / 3000</span>
      </div>
    </form>
  );
}

