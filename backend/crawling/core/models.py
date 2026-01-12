"""
설교 크롤링을 위한 데이터 모델.
"""
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class OCRResult:
    """이미지 처리에서 추출된 구조화된 OCR 결과."""

    title: str
    date: str
    scripture: str
    summary: str
    discussion_questions: List[str] = field(default_factory=list)
    church_name: str = ""

    def is_valid(self, min_length: int = 100) -> bool:
        """OCR 결과가 유효한지 확인."""
        return bool(self.summary and len(self.summary) > min_length)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환."""
        return asdict(self)


@dataclass
class SermonData:
    """완전한 설교 데이터 구조."""

    seq: str
    title: str
    content: str
    date: str
    link: str
    church_name: str = "서강감리교회"
    summary: Optional[str] = None
    scripture: str = ""
    discussion_questions: List[str] = field(default_factory=list)
    ocr_used: bool = False
    image_urls: List[str] = field(default_factory=list)

    @classmethod
    def from_ocr(
        cls,
        seq: str,
        link: str,
        ocr_result: OCRResult,
        summary: Optional[str] = None,
        image_urls: List[str] = None,
    ) -> "SermonData":
        """OCR 결과로부터 SermonData 생성."""
        return cls(
            seq=seq,
            title=ocr_result.title,
            content=ocr_result.summary,
            date=ocr_result.date,
            link=link,
            church_name=ocr_result.church_name or "서강감리교회",
            summary=summary,
            scripture=ocr_result.scripture,
            discussion_questions=ocr_result.discussion_questions,
            ocr_used=True,
            image_urls=image_urls or [],
        )

    @classmethod
    def from_html(
        cls,
        seq: str,
        title: str,
        content: str,
        date: str,
        link: str,
        image_urls: List[str] = None,
    ) -> "SermonData":
        """HTML 파싱으로부터 SermonData 생성 (대체 방법)."""
        return cls(
            seq=seq,
            title=title,
            content=content,
            date=date,
            link=link,
            church_name="서강감리교회",
            summary=None,
            scripture="",
            discussion_questions=[],
            ocr_used=False,
            image_urls=image_urls or [],
        )

    def to_dict(self) -> Dict[str, Any]:
        """JSON 직렬화를 위해 딕셔너리로 변환."""
        return asdict(self)

    def __repr__(self) -> str:
        """문자열 표현."""
        return (
            f"SermonData(seq={self.seq}, title={self.title[:30]}..., "
            f"date={self.date}, ocr_used={self.ocr_used})"
        )


@dataclass
class CrawlStats:
    """크롤링 세션에 대한 통계."""

    total_pages: int = 0
    total_posts: int = 0
    successful_posts: int = 0
    failed_posts: int = 0
    ocr_success: int = 0
    ocr_failed: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def start(self):
        """크롤링 시작 시간 기록."""
        self.start_time = datetime.now()

    def finish(self):
        """크롤링 종료 시간 기록."""
        self.end_time = datetime.now()

    def add_success(self, ocr_used: bool = False):
        """성공한 게시물 기록."""
        self.successful_posts += 1
        if ocr_used:
            self.ocr_success += 1
        else:
            self.ocr_failed += 1

    def add_failure(self):
        """실패한 게시물 기록."""
        self.failed_posts += 1

    @property
    def duration(self) -> Optional[float]:
        """소요 시간을 초 단위로 반환."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    @property
    def ocr_success_rate(self) -> float:
        """OCR 성공률 계산."""
        total = self.successful_posts
        if total == 0:
            return 0.0
        return (self.ocr_success / total) * 100

    def print_summary(self):
        """크롤링 통계 출력."""
        print("\n" + "=" * 60)
        print("Crawling Completed!")
        print(f"Total pages processed: {self.total_pages}")
        print(f"Total posts found: {self.total_posts}")
        print(f"Successful: {self.successful_posts}")
        print(f"Failed: {self.failed_posts}")
        print(
            f"OCR successful: {self.ocr_success}/{self.successful_posts} "
            f"({self.ocr_success_rate:.1f}%)"
        )
        if self.duration:
            print(f"Duration: {self.duration:.1f} seconds")
        print("=" * 60)
