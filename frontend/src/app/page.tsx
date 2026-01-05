"use client";

import { useState } from "react";
import Image from "next/image";

type MainView = "home" | "chat";
type ProfileMode = "research" | "counseling" | "education";

export default function Home() {
  const [mainView, setMainView] = useState<MainView>("chat");
  const [profileMode, setProfileMode] = useState<ProfileMode>("research");

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
          <button
            type="button"
            className="w-full rounded-full border border-slate-200 px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100"
          >
            로그아웃
          </button>
          <div className="mt-3 flex items-center justify-between rounded-full bg-slate-100 px-3 py-2">
            <span className="text-[11px] font-medium text-slate-600">
              라이트
            </span>
            <span className="h-6 w-11 rounded-full bg-white shadow-inner" />
          </div>
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

      {/* 퀵 업로드 존 */}
      <section className="card flex flex-1 flex-col items-center justify-center border-dashed border-slate-300 bg-slate-50/70 text-center">
        <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-900/90">
          <span className="text-lg text-white">+</span>
        </div>
        <h3 className="text-sm font-semibold text-slate-900">
          주보 사진을 드래그 앤 드롭하여 업로드
        </h3>
        <p className="mt-1 max-w-md text-xs text-slate-500">
          주보 이미지, 설교 요약 캡처 등을 올리면 자동으로 텍스트/OCR 분석 후 설교
          아카이브에 정리됩니다. (현재는 UI만 구성된 상태입니다.)
        </p>
        <div className="mt-4 flex gap-2">
          <button
            type="button"
            className="rounded-full bg-slate-900 px-4 py-2 text-xs font-medium text-white shadow-sm hover:bg-slate-800"
          >
            파일 선택
          </button>
          <button
            type="button"
            className="rounded-full border border-slate-300 px-4 py-2 text-xs font-medium text-slate-600 hover:bg-white"
          >
            예시 주보로 테스트
          </button>
        </div>
      </section>
    </div>
  );
}

function AiChatView(props: { profileMode: ProfileMode }) {
  const { profileMode } = props;

  const profileLabel =
    profileMode === "research"
      ? "연구 모드 – 본문 연구와 설교 구조 제안에 최적화"
      : profileMode === "counseling"
      ? "상담 모드 – 성도 상담과 적용점에 초점"
      : "교육 모드 – 이해하기 쉬운 설명과 질문지 생성에 초점";

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
          <span className="chip">실시간 스트리밍 예정</span>
          <span className="chip">LangGraph 에이전트</span>
        </div>
      </section>

      {/* 중앙: 출처 카드 + 채팅 영역 */}
      <section className="grid flex-1 grid-cols-1 gap-4 lg:grid-cols-[minmax(0,2.2fr)_minmax(260px,1fr)]">
        {/* 채팅 영역 */}
        <div className="card flex flex-1 flex-col overflow-hidden">
          {/* 출처 카드 영역 */}
          <div className="mb-3 border-b border-slate-100 pb-3">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              참고 설교 / 주보
            </p>
            <div className="flex gap-3 overflow-x-auto pb-1">
              {[1, 2, 3].map((idx) => (
                <div
                  key={idx}
                  className="flex min-w-[180px] flex-col gap-2 rounded-xl border border-slate-200 bg-slate-50/70 p-2"
                >
                  <div className="flex items-center gap-2">
                    <div className="relative h-8 w-8 overflow-hidden rounded-md bg-slate-200">
                      <Image
                        src="/window.svg"
                        alt=""
                        fill
                        className="object-cover opacity-60"
                      />
                    </div>
                    <div className="flex flex-col">
                      <span className="line-clamp-1 text-xs font-semibold text-slate-800">
                        고난 속에서 발견하는 은혜
                      </span>
                      <span className="text-[10px] text-slate-500">
                        2024-03-10 · 주보 이미지
                      </span>
                    </div>
                  </div>
                  <p className="line-clamp-2 text-[11px] text-slate-600">
                    시편 23편을 중심으로, 고난의 골짜기를 지날 때 함께
                    하시는 하나님을 묵상한 설교입니다.
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* 대화 영역 (목업) */}
          <div className="flex flex-1 flex-col gap-4 overflow-y-auto pr-1 text-sm">
            <div className="rounded-2xl bg-slate-900 px-4 py-3 text-sm text-slate-50 max-w-[80%]">
              다음 주일에 “고난과 위로” 주제로 설교를 준비하려고 하는데, 기존
              설교와 연결해서 도와줄 수 있을까요?
            </div>
            <div className="max-w-[80%] rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-800">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                제안 outline
              </p>
              <p className="mb-2 text-sm">
                <span className="font-semibold">
                  1. 고난의 현실 – “사망의 음침한 골짜기”
                </span>
                <br />
                시편 23편 설교(2024.03.10)에서 사용하신 예화를 다시 연결하여,
                성도들이 실제로 겪는 고난의 구체적인 모습을 떠올리게 합니다.
              </p>
              <p className="mb-2 text-sm">
                <span className="font-semibold">
                  2. 함께 하시는 주님 – 임마누엘의 위로
                </span>
                <br />
                고린도후서 1장 3–4절을 추가 본문으로 제안하며, “위로받은 자가
                또 다른 이의 위로가 된다”는 흐름으로 이어갈 수 있습니다.
              </p>
              <p className="mb-1 text-xs text-slate-500">
                성경 구절:{" "}
                <span className="font-semibold">
                  시편 23편, 고린도후서 1장 3-4절
                </span>
              </p>
            </div>
          </div>

          {/* 하단 입력창 */}
          <div className="mt-3 border-t border-slate-200 pt-3">
            <ChatInput />
          </div>
        </div>

        {/* 우측 패널: 프로젝트/세션 리스트(목업) */}
        <aside className="card flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              최근 세션
            </span>
            <button
              type="button"
              className="text-[11px] font-medium text-slate-500 hover:text-slate-800"
            >
              새 프로젝트
            </button>
          </div>
          <div className="space-y-2 text-xs">
            {[
              "사순절 시리즈 – 십자가 묵상",
              "청년부 수련회 프로그램",
              "고난주간 특별새벽기도회",
              "새가족반 교육 커리큘럼",
            ].map((title) => (
              <button
                key={title}
                type="button"
                className="flex w-full flex-col rounded-xl border border-slate-200 bg-slate-50/70 px-3 py-2 text-left hover:bg-white"
              >
                <span className="line-clamp-1 text-[12px] font-medium text-slate-800">
                  {title}
                </span>
                <span className="mt-1 text-[11px] text-slate-500">
                  최근 대화 요약가 여기에 표시됩니다.
                </span>
              </button>
            ))}
          </div>
        </aside>
      </section>
    </div>
  );
}

function ChatInput() {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2 text-[11px] text-slate-500">
        <span>무엇을 도와드릴까요?</span>
        <span className="rounded-full bg-slate-100 px-2 py-0.5">
          예) “마태복음 5장 3절로 청년부 설교 outline 만들어줘”
        </span>
      </div>
      <div className="flex items-center rounded-2xl border border-slate-300 bg-white px-3 py-2 shadow-sm">
        <button
          type="button"
          className="rounded-full px-2 py-1 text-[11px] font-medium text-slate-600 hover:bg-slate-100"
        >
          파일 첨부
        </button>
        <input
          type="text"
          placeholder="질문을 입력하세요. 설교 본문, 상황, 대상(청년/청소년/장년)을 함께 알려주면 더 정확하게 도와드려요."
          className="ml-2 flex-1 bg-transparent text-sm outline-none placeholder:text-slate-400"
        />
        <button
          type="button"
          className="ml-2 flex h-8 w-8 items-center justify-center rounded-full bg-slate-900 text-white hover:bg-slate-800"
        >
          <span className="text-xs">▶</span>
        </button>
      </div>
      <div className="flex items-center justify-between text-[10px] text-slate-400">
        <div className="flex gap-2">
          <span>나눔 질문 자동 생성</span>
          <span>·</span>
          <span>과거 설교 연결</span>
          <span>·</span>
          <span>성도 상담용 답변</span>
        </div>
        <span>0 / 3000</span>
      </div>
    </div>
  );
}

