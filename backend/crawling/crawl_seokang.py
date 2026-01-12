import requests
from bs4 import BeautifulSoup
import time
import re
import json
import os
import base64
from typing import Optional, Dict, Any, List
from io import BytesIO
from PIL import Image
from urllib.parse import urljoin, urlparse

# 크롤링할 기본 설정
BASE_URL = "http://www.seokang.or.kr/EZ/rb/"
LIST_URL = "http://www.seokang.or.kr/EZ/rb/board.asp"
PARAMS = {"BoardModule": "Board", "tbcode": "bible02"}

# 결과를 저장할 파일 이름
OUTPUT_FILE = "seokang_church_seroms_total.json"

# .env 파일에서 환경변수 로드
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    print(
        "Warning: python-dotenv not installed. Using system environment variables only."
    )

# Gemini API 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent"


def get_soup(url, params=None):
    """URL을 요청하고 BeautifulSoup 객체를 반환하는 함수"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.encoding = "euc-kr"

        if response.status_code == 200:
            return BeautifulSoup(response.text, "html.parser")
        else:
            print(f"Error: Status Code {response.status_code}")
            return None
    except Exception as e:
        print(f"Request Error: {e}")
        return None


def download_image(image_url: str) -> Optional[bytes]:
    """이미지 URL에서 이미지를 다운로드하여 bytes로 반환"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "http://www.seokang.or.kr/",
        }
        response = requests.get(image_url, headers=headers, timeout=30)
        if response.status_code == 200:
            # 이미지 파일인지 확인
            content_type = response.headers.get("Content-Type", "")
            if "image" in content_type or len(response.content) > 10000:  # 10KB 이상
                return response.content
        return None
    except Exception as e:
        print(f"    Image download error: {e}")
        return None


def generate_summary(content: str, title: str = "") -> Optional[str]:
    """Gemini API를 사용하여 설교 내용을 3줄 요약"""
    if not GEMINI_API_KEY or not content or len(content) < 100:
        return None

    try:
        prompt = f"""
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

        headers = {"Content-Type": "application/json"}

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 800,  # 토큰 수 증가
            },
        }

        response = requests.post(
            f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
            headers=headers,
            json=payload,
            timeout=30,
        )

        # Rate limit 처리
        if response.status_code == 429:
            retry_match = re.search(r"retry in (\d+\.?\d*)s", response.text)
            if retry_match:
                wait_time = float(retry_match.group(1)) + 2
                print(f"    ⏳ Rate limit (summary). Waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
                response = requests.post(
                    f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
                    headers=headers,
                    json=payload,
                    timeout=30,
                )

        if response.status_code == 200:
            result = response.json()
            if "candidates" in result and len(result["candidates"]) > 0:
                summary = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                # 불필요한 마크다운 제거
                summary = summary.replace("```", "").strip()

                # bullet point 정리
                lines = [line.strip() for line in summary.split("\n") if line.strip()]
                # •로 시작하지 않으면 추가
                formatted_lines = []
                for line in lines:
                    if (
                        line.startswith("•")
                        or line.startswith("-")
                        or line.startswith("*")
                    ):
                        formatted_lines.append(line)
                    elif line and not line.startswith("#"):  # 헤더 제외
                        formatted_lines.append(f"• {line}")

                return "\n".join(formatted_lines[:3])  # 정확히 3개만

        return None

    except Exception as e:
        print(f"    Summary generation error: {e}")
        return None


def extract_text_from_image(image_bytes: bytes) -> Optional[Dict[str, Any]]:
    """Gemini REST API를 사용하여 이미지에서 텍스트 추출 및 구조화"""
    if not GEMINI_API_KEY:
        print("    Warning: GEMINI_API_KEY not found. Skipping OCR.")
        return None

    try:
        # 이미지를 base64로 인코딩
        image_data = base64.b64encode(image_bytes).decode("utf-8")

        # 이미지 MIME 타입 자동 감지
        img = Image.open(BytesIO(image_bytes))
        mime_type = "image/jpeg" if img.format == "JPEG" else "image/png"

        print(f"    Image size: {img.size}, format: {img.format}")

        # 프롬프트: 주보 이미지에서 설교 정보를 구조화된 JSON으로 추출
        prompt = """
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

        # Gemini REST API 호출
        headers = {"Content-Type": "application/json"}

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": mime_type, "data": image_data}},
                    ]
                }
            ],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 8000},
        }

        response = requests.post(
            f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
            headers=headers,
            json=payload,
            timeout=60,
        )

        # Rate limit 에러 처리
        if response.status_code == 429:
            retry_match = re.search(r"retry in (\d+\.?\d*)s", response.text)
            if retry_match:
                wait_time = float(retry_match.group(1)) + 2  # 여유있게 2초 추가
                print(f"    ⏳ Rate limit hit. Waiting {wait_time:.1f} seconds...")
                time.sleep(wait_time)
                # 재시도
                response = requests.post(
                    f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
                    headers=headers,
                    json=payload,
                    timeout=60,
                )
            else:
                print(f"    ⏳ Rate limit exceeded. Waiting 15 seconds...")
                time.sleep(15)
                # 재시도
                response = requests.post(
                    f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
                    headers=headers,
                    json=payload,
                    timeout=60,
                )

        if response.status_code == 429:
            # 재시도 후에도 실패하면 더 길게 대기
            print(f"    ⏳ Still rate limited. Waiting 30 seconds...")
            time.sleep(30)
            return None

        if response.status_code != 200:
            print(f"    Gemini API Error: {response.status_code}")
            return None

        result = response.json()

        # 응답에서 텍스트 추출
        if "candidates" in result and len(result["candidates"]) > 0:
            text = result["candidates"][0]["content"]["parts"][0]["text"].strip()

            # JSON 부분만 추출 (마크다운 코드 블록 제거)
            text = text.replace("```json", "").replace("```", "").strip()
            json_match = re.search(r"\{.*\}", text, re.DOTALL)

            if json_match:
                json_str = json_match.group(0)
                parsed = json.loads(json_str)

                # 데이터 검증
                if parsed.get("summary") and len(parsed["summary"]) > 100:
                    return parsed
                else:
                    print(f"    Warning: OCR result too short or empty")
                    return None
            else:
                print(f"    Warning: Could not parse JSON from OCR result")
                return None

        return None

    except Exception as e:
        print(f"    OCR Error: {e}")
        import traceback

        traceback.print_exc()
        return None


def extract_all_images_from_page(soup: BeautifulSoup, page_url: str) -> List[str]:
    """페이지에서 모든 이미지 URL 추출"""
    images = []
    seen_urls = set()

    # 모든 img 태그 찾기
    img_tags = soup.find_all("img")

    for img in img_tags:
        src = img.get("src") or img.get("data-src")
        if not src:
            continue

        # 절대 URL로 변환
        image_url = urljoin(page_url, src)

        # 중복 제거
        if image_url in seen_urls:
            continue
        seen_urls.add(image_url)

        # 작은 아이콘/로고 제외 (너비/높이가 명시된 경우)
        width = img.get("width")
        height = img.get("height")
        if width and height:
            try:
                if int(width) < 100 or int(height) < 100:
                    continue
            except:
                pass

        # 파일명에서 작은 이미지 제외
        if any(
            keyword in image_url.lower()
            for keyword in ["icon", "logo", "banner", "btn", "bullet"]
        ):
            continue

        images.append(image_url)

    # 우선순위: 파일명에 설교/주보 관련 키워드가 있는 것을 먼저
    priority_images = []
    other_images = []

    for img_url in images:
        if any(
            keyword in img_url.lower()
            for keyword in ["sermon", "설교", "주보", "bulletin", "content", "board"]
        ):
            priority_images.append(img_url)
        else:
            other_images.append(img_url)

    return priority_images + other_images


def crawl_sermons():
    # 데이터를 저장할 리스트 초기화
    sermons = []

    if not GEMINI_API_KEY:
        print("\n" + "=" * 60)
        print("WARNING: GEMINI_API_KEY not found!")
        print("OCR will be skipped. Please set your API key:")
        print("  export GEMINI_API_KEY='your_api_key'")
        print("=" * 60 + "\n")

    # 테스트: 페이지 1~2만 크롤링 (전체는 1~17로 변경)
    for page in range(1, 17):  # 전체 크롤링용: 1~16페이지
        print(f"\n{'='*60}")
        print(f"Processing List Page: {page}/16")
        print(f"{'='*60}")

        current_params = PARAMS.copy()
        current_params["page"] = page

        soup = get_soup(LIST_URL, current_params)
        if not soup:
            continue

        # 목록에서 상세 페이지 링크 추출
        links = soup.find_all("a", href=lambda href: href and "view.asp" in href)

        # 중복 링크 제거
        unique_links = []
        seen_seq = set()

        for link in links:
            href = link["href"]
            seq_match = re.search(r"seq=(\d+)", href)
            if seq_match:
                seq_id = seq_match.group(1)
                if seq_id not in seen_seq:
                    seen_seq.add(seq_id)
                    unique_links.append((seq_id, href))

        print(f"Found {len(unique_links)} posts on this page")

        # 테스트: 각 페이지에서 처음 3개 게시글만 처리
        unique_links = unique_links[:3]  # 테스트용: 3개만
        # unique_links = unique_links[::]  # 전체 크롤링용 (나중에 주석 해제)

        # 각 상세 페이지 방문
        for idx, (seq_id, href) in enumerate(unique_links, 1):
            if href.startswith("http"):
                detail_url = href
            else:
                detail_url = urljoin(BASE_URL, href)

            print(f"\n[{idx}/{len(unique_links)}] Scraping Post Seq: {seq_id}")
            print(f"URL: {detail_url}")

            detail_soup = get_soup(detail_url)
            if detail_soup:
                try:
                    # 제목 추출 시도
                    title_tag = detail_soup.find(
                        "td", class_="subject"
                    ) or detail_soup.find("font", class_="title")
                    if not title_tag:
                        # 다른 방법으로 제목 찾기
                        title_candidates = detail_soup.find_all(
                            "td", class_=lambda x: x and "subject" in x.lower()
                        )
                        if title_candidates:
                            title = title_candidates[0].get_text(strip=True)
                        else:
                            title = (
                                detail_soup.title.text.strip()
                                if detail_soup.title
                                else f"Post {seq_id}"
                            )
                    else:
                        title = title_tag.get_text(strip=True)

                    print(f"  Title: {title}")

                    # 이미지 크롤링 - 모든 이미지 시도
                    ocr_data = None
                    image_urls = extract_all_images_from_page(detail_soup, detail_url)

                    print(f"  Found {len(image_urls)} image(s)")

                    if image_urls and GEMINI_API_KEY:
                        for img_idx, img_url in enumerate(image_urls, 1):
                            print(
                                f"  Trying image {img_idx}/{len(image_urls)}: {img_url}"
                            )
                            img_bytes = download_image(img_url)

                            if img_bytes:
                                print(f"    Downloaded {len(img_bytes)} bytes")
                                ocr_data = extract_text_from_image(img_bytes)

                                if (
                                    ocr_data
                                    and ocr_data.get("summary")
                                    and len(ocr_data["summary"]) > 100
                                ):
                                    print(f"    ✓ OCR successful!")
                                    print(f"    Title: {ocr_data.get('title', 'N/A')}")
                                    print(f"    Date: {ocr_data.get('date', 'N/A')}")
                                    print(
                                        f"    Summary length: {len(ocr_data.get('summary', ''))} chars"
                                    )
                                    break
                                else:
                                    print(f"    ✗ OCR failed or result too short")

                            time.sleep(10)  # 이미지 간 3초 대기 (Rate limit 방지 강화)

                    # 데이터 저장
                    if ocr_data:
                        # OCR 성공: OCR 데이터 사용
                        final_content = ocr_data.get("summary", "")

                        # 3줄 요약 생성
                        print(f"  Generating 3-line summary...")
                        brief_summary = generate_summary(
                            final_content, ocr_data.get("title", title)
                        )
                        if brief_summary:
                            print(f"  ✓ Summary generated")
                        else:
                            print(f"  ⚠ Summary generation failed")

                        sermon_data = {
                            "seq": seq_id,
                            "title": ocr_data.get("title", title),
                            "content": final_content,
                            "summary": brief_summary,  # 3줄 요약 추가
                            "date": ocr_data.get("date", "Unknown"),
                            "link": detail_url,
                            "scripture": ocr_data.get("scripture", ""),
                            "discussion_questions": ocr_data.get(
                                "discussion_questions", []
                            ),
                            "church_name": ocr_data.get("church_name", "서강감리교회"),
                            "ocr_used": True,
                            "image_urls": image_urls[:3],  # 처음 3개만 저장
                        }
                        print(f"  ✓ Saved with OCR data")
                    else:
                        # OCR 실패: HTML 텍스트 사용
                        content_tag = detail_soup.find(
                            "td", class_="content"
                        ) or detail_soup.find("div", id="content")
                        if content_tag:
                            content = content_tag.get_text(separator="\n", strip=True)
                        else:
                            content = ""

                        date_match = re.search(r"\d{4}-\d{2}-\d{2}", detail_soup.text)
                        date = date_match.group(0) if date_match else "Unknown"

                        sermon_data = {
                            "seq": seq_id,
                            "title": title,
                            "content": content,
                            "summary": None,  # OCR 실패 시 요약 없음
                            "date": date,
                            "link": detail_url,
                            "scripture": "",
                            "discussion_questions": [],
                            "church_name": "서강감리교회",
                            "ocr_used": False,
                            "image_urls": image_urls[:3],
                        }
                        print(f"  ⚠ Saved without OCR (HTML only)")

                    sermons.append(sermon_data)

                except Exception as e:
                    print(f"  ✗ Error parsing seq {seq_id}: {e}")
                    import traceback

                    traceback.print_exc()

            # 서버 부하 방지
            time.sleep(10)  # 게시글 간 10초 대기

        # 페이지 간 대기
        time.sleep(15)  # 페이지 간 15초 대기 (Rate limit 방지 강화)

    # JSON 파일로 저장
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(sermons, f, ensure_ascii=False, indent=2)

    # 결과 요약
    print("\n" + "=" * 60)
    print("Crawling Completed!")
    print(f"Total sermons collected: {len(sermons)}")
    ocr_success = sum(1 for s in sermons if s["ocr_used"])
    print(
        f"OCR successful: {ocr_success}/{len(sermons)} ({ocr_success/len(sermons)*100:.1f}%)"
    )
    print(f"Data saved to: {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    crawl_sermons()
