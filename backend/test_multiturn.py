# # backend/test_multiturn.py
# # -*- coding: utf-8 -*-
# """멀티턴 대화 테스트"""

# import os
# import sys

# PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# if PROJECT_ROOT not in sys.path:
#     sys.path.insert(0, PROJECT_ROOT)

# from dotenv import load_dotenv
# load_dotenv()

# from backend.agents.new_pipeline import run_pipeline, get_session, clear_session

# def test_multiturn():
#     """멀티턴 대화 테스트."""
#     session_id = "test_session"
#     clear_session(session_id)

#     print("=" * 60)
#     print("멀티턴 대화 테스트")
#     print("=" * 60)

#     # 턴 1: 첫 번째 질문
#     print("\n[턴 1] 질문: 하나님의 사랑에 대한 설교가 있나요?")
#     print("-" * 40)

#     result1 = run_pipeline(
#         question="하나님의 사랑에 대한 설교가 있나요?",
#         profile_mode="research",
#         session_id=session_id,
#     )

#     print(f"카테고리: {result1['category']}")
#     print(f"RAG 사용: {result1['used_rag']}")
#     print(f"턴 수: {result1['turn_count']}")

#     if result1['citations']:
#         print("\n참고 설교:")
#         for i, ref in enumerate(result1['citations'][:3], 1):
#             print(f"  {i}. [{ref.get('date')}] {ref.get('title')}")

#     print(f"\n답변 (처음 500자):")
#     print(result1['answer'][:500] + "..." if len(result1['answer']) > 500 else result1['answer'])

#     # 세션 상태 확인
#     session = get_session(session_id)
#     print(f"\n[세션 상태] 대화 이력: {len(session.history)}개 메시지")

#     # 턴 2: 후속 질문 (대화 컨텍스트 사용)
#     print("\n" + "=" * 60)
#     print("\n[턴 2] 후속 질문: 그 설교에서 언급된 성경 구절은 뭐야?")
#     print("-" * 40)

#     result2 = run_pipeline(
#         question="그 설교에서 언급된 성경 구절은 뭐야?",
#         profile_mode="research",
#         session_id=session_id,
#     )

#     print(f"카테고리: {result2['category']}")
#     print(f"RAG 사용: {result2['used_rag']}")
#     print(f"턴 수: {result2['turn_count']}")

#     print(f"\n답변 (처음 500자):")
#     print(result2['answer'][:500] + "..." if len(result2['answer']) > 500 else result2['answer'])

#     # 세션 상태 확인
#     session = get_session(session_id)
#     print(f"\n[세션 상태] 대화 이력: {len(session.history)}개 메시지")

#     print("\n" + "=" * 60)
#     print("테스트 완료!")
#     print("=" * 60)


# if __name__ == "__main__":
#     test_multiturn()

# # 질문 1 : 하나님의 사랑에 대한 설교가 있나요 ?
# # 답변 : 