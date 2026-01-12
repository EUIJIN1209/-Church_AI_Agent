"""
OCR 및 텍스트 요약을 위한 Gemini API 클라이언트.
"""
import requests
import base64
import json
import time
import re
from typing import Optional
from io import BytesIO
from PIL import Image

from .config import GeminiConfig
from .models import OCRResult
from .exceptions import (
    GeminiAPIException,
    RateLimitException,
    OCRException,
    ConfigurationException,
)


class GeminiClient:
    """Gemini API와 상호작용하는 클라이언트."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or GeminiConfig.API_KEY
        if not self.api_key:
            raise ConfigurationException("GEMINI_API_KEY not found")

        self.api_url = GeminiConfig.API_URL

    def extract_text_from_image(self, image_bytes: bytes) -> Optional[OCRResult]:
        """
        OCR을 사용하여 설교 주보 이미지에서 구조화된 텍스트를 추출합니다.

        Args:
            image_bytes: 바이트 형태의 이미지 데이터

        Returns:
            OCRResult 객체 또는 추출 실패 시 None

        Raises:
            OCRException: OCR 처리가 실패한 경우
        """
        try:
            # 이미지를 base64로 인코딩
            image_data = base64.b64encode(image_bytes).decode("utf-8")

            # 이미지 MIME 타입 감지
            img = Image.open(BytesIO(image_bytes))
            mime_type = "image/jpeg" if img.format == "JPEG" else "image/png"

            print(f"    Image size: {img.size}, format: {img.format}")

            # 구조화된 추출을 위한 프롬프트 준비
            prompt = self._get_ocr_prompt()

            # API 호출
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt},
                            {"inline_data": {"mime_type": mime_type, "data": image_data}},
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": GeminiConfig.OCR_TEMPERATURE,
                    "maxOutputTokens": GeminiConfig.OCR_MAX_TOKENS,
                },
            }

            response = self._make_request(
                payload, timeout=GeminiConfig.OCR_TIMEOUT
            )

            # 응답 파싱
            if "candidates" in response and len(response["candidates"]) > 0:
                text = response["candidates"][0]["content"]["parts"][0]["text"].strip()
                return self._parse_ocr_response(text)

            return None

        except Exception as e:
            raise OCRException(f"OCR failed: {str(e)}")

    def generate_summary(self, content: str, title: str = "") -> Optional[str]:
        """
        설교 내용의 3줄 요약을 생성합니다.

        Args:
            content: 설교 내용 텍스트
            title: 설교 제목 (선택사항)

        Returns:
            형식화된 요약 문자열 또는 생성 실패 시 None
        """
        if not content or len(content) < GeminiConfig.MIN_CONTENT_LENGTH:
            return None

        try:
            prompt = self._get_summary_prompt(content, title)

            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": GeminiConfig.SUMMARY_TEMPERATURE,
                    "maxOutputTokens": GeminiConfig.SUMMARY_MAX_TOKENS,
                },
            }

            response = self._make_request(
                payload, timeout=GeminiConfig.SUMMARY_TIMEOUT
            )

            # 응답 파싱
            if "candidates" in response and len(response["candidates"]) > 0:
                summary = response["candidates"][0]["content"]["parts"][0]["text"].strip()
                return self._format_summary(summary)

            return None

        except Exception as e:
            print(f"    Summary generation error: {e}")
            return None

    def _make_request(
        self, payload: dict, timeout: int, max_retries: int = 2
    ) -> dict:
        """
        속도 제한 처리와 함께 API 요청을 수행합니다.

        Args:
            payload: 요청 페이로드
            timeout: 요청 타임아웃
            max_retries: 최대 재시도 횟수

        Returns:
            응답 JSON

        Raises:
            GeminiAPIException: 요청이 실패한 경우
            RateLimitException: 속도 제한이 초과된 경우
        """
        headers = {"Content-Type": "application/json"}

        for attempt in range(max_retries + 1):
            try:
                response = requests.post(
                    f"{self.api_url}?key={self.api_key}",
                    headers=headers,
                    json=payload,
                    timeout=timeout,
                )

                # 속도 제한 처리
                if response.status_code == 429:
                    if attempt < max_retries:
                        wait_time = self._get_rate_limit_wait_time(response.text)
                        print(f"    ⏳ Rate limit hit. Waiting {wait_time:.1f}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise RateLimitException()

                # 기타 오류 처리
                if response.status_code != 200:
                    raise GeminiAPIException(
                        response.status_code, response.text[:200]
                    )

                return response.json()

            except requests.exceptions.Timeout:
                if attempt < max_retries:
                    print(f"    ⏳ Request timeout. Retrying...")
                    time.sleep(2)
                    continue
                raise GeminiAPIException(message="Request timeout")

            except requests.exceptions.RequestException as e:
                raise GeminiAPIException(message=str(e))

        raise GeminiAPIException(message="Max retries exceeded")

    def _get_rate_limit_wait_time(self, error_text: str) -> float:
        """속도 제한 오류 메시지에서 대기 시간을 추출합니다."""
        retry_match = re.search(r"retry in (\d+\.?\d*)s", error_text)
        if retry_match:
            return float(retry_match.group(1)) + GeminiConfig.RATE_LIMIT_RETRY_BUFFER

        return GeminiConfig.RATE_LIMIT_WAIT

    def _get_ocr_prompt(self) -> str:
        """OCR 추출 프롬프트를 가져옵니다."""
        return """
이 이미지는 교회 주보 또는 설교 요약문입니다. 이미지에서 모든 텍스트를 정확하게 추출하여 다음 JSON 형식으로 반환해주세요:

{
  "title": "설교 제목 (전체)",
  "date": "날짜 (YYYY-MM-DD 형식, 예: 2026-01-04)",
  "scripture": "성경 구절 (예: 창세기 1:1-5, 사무엘하 7:22)",
  "summary": "설교 요약 본문 전체 (모든 문단과 내용을 빠짐없이 포함)",
  "discussion_questions": ["나눔 질문 1", "나눔 질문 2"],
  "church_name": "교회 이름"
}

중요한 지침:
1. summary에는 설교의 모든 본문 내용을 빠짐없이 포함해야 합니다
2. 문단 구분과 줄바꿈을 유지하세요
3. 성경 구절은 정확하게 추출하세요 (예: 창세기 1:1-5)
4. 날짜는 이미지 상단에 있는 날짜를 YYYY-MM-DD 형식으로 변환하세요
5. 나눔 질문이나 토의 질문이 있으면 배열로 모두 포함하세요
6. JSON만 반환하고 설명은 붙이지 마세요
7. 한글을 정확하게 인식하세요

반드시 위 JSON 형식으로만 응답하세요.
"""

    def _get_summary_prompt(self, content: str, title: str) -> str:
        """요약 생성 프롬프트를 가져옵니다."""
        return f"""
다음은 교회 설교 내용입니다. 설교의 핵심 메시지를 **정확히 3개의 포인트**로 요약해주세요.

설교 제목: {title}

설교 내용:
{content}

요구사항:
1. 설교에서 "첫째", "둘째", "셋째" 또는 주요 논점이 있다면 그것을 중심으로 요약
2. 각 포인트는 한 문장으로 명확하게 작성
3. 형식: "• 포인트 내용" (bullet point 사용)
4. 성경적 교훈과 적용점 포함
5. 총 3개 포인트만 작성
6. 불필요한 설명 없이 요약문만 출력

출력 형식 예시:
• 첫 번째 핵심 포인트를 한 문장으로
• 두 번째 핵심 포인트를 한 문장으로
• 세 번째 핵심 포인트를 한 문장으로
"""

    def _parse_ocr_response(self, text: str) -> Optional[OCRResult]:
        """OCR 응답 텍스트를 OCRResult 객체로 파싱합니다."""
        try:
            # 마크다운 코드 블록 제거
            text = text.replace("```json", "").replace("```", "").strip()

            # JSON 추출
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if not json_match:
                print("    Warning: Could not find JSON in OCR response")
                return None

            json_str = json_match.group(0)
            data = json.loads(json_str)

            # 필수 필드 검증
            if not data.get("summary") or len(data["summary"]) < GeminiConfig.MIN_CONTENT_LENGTH:
                print("    Warning: OCR result too short or empty")
                return None

            # OCRResult 생성
            return OCRResult(
                title=data.get("title", ""),
                date=data.get("date", "Unknown"),
                scripture=data.get("scripture", ""),
                summary=data.get("summary", ""),
                discussion_questions=data.get("discussion_questions", []),
                church_name=data.get("church_name", ""),
            )

        except json.JSONDecodeError as e:
            print(f"    Warning: JSON parse error: {e}")
            return None
        except Exception as e:
            print(f"    Warning: OCR response parsing failed: {e}")
            return None

    def _format_summary(self, summary: str) -> str:
        """요약을 글머리 기호로 형식화합니다."""
        # 마크다운 코드 블록 제거
        summary = summary.replace("```", "").strip()

        # 줄로 분할
        lines = [line.strip() for line in summary.split("\n") if line.strip()]

        # 글머리 기호로 형식화
        formatted_lines = []
        for line in lines:
            # 헤더 건너뛰기
            if line.startswith("#"):
                continue

            # 글머리 기호가 없으면 추가
            if line.startswith("•") or line.startswith("-") or line.startswith("*"):
                formatted_lines.append(line)
            elif line:
                formatted_lines.append(f"• {line}")

        # 정확히 3개 포인트 반환
        return "\n".join(formatted_lines[: GeminiConfig.SUMMARY_POINTS_COUNT])
