"""
설교 크롤러를 위한 커스텀 예외.
"""


class CrawlerException(Exception):
    """크롤러 오류에 대한 기본 예외."""
    pass


class HTTPRequestException(CrawlerException):
    """HTTP 요청이 실패했을 때 발생."""

    def __init__(self, url: str, status_code: int = None, message: str = None):
        self.url = url
        self.status_code = status_code
        self.message = message or f"HTTP request failed for {url}"
        if status_code:
            self.message += f" (status: {status_code})"
        super().__init__(self.message)


class ImageDownloadException(CrawlerException):
    """이미지 다운로드가 실패했을 때 발생."""

    def __init__(self, url: str, reason: str = None):
        self.url = url
        self.reason = reason or "Unknown error"
        message = f"Failed to download image from {url}: {self.reason}"
        super().__init__(message)


class OCRException(CrawlerException):
    """OCR 처리가 실패했을 때 발생."""

    def __init__(self, message: str = "OCR processing failed"):
        super().__init__(message)


class GeminiAPIException(CrawlerException):
    """Gemini API 호출이 실패했을 때 발생."""

    def __init__(self, status_code: int = None, message: str = None):
        self.status_code = status_code
        self.message = message or "Gemini API call failed"
        if status_code:
            self.message += f" (status: {status_code})"
        super().__init__(self.message)


class RateLimitException(GeminiAPIException):
    """속도 제한이 초과되었을 때 발생."""

    def __init__(self, retry_after: float = None):
        self.retry_after = retry_after
        message = "Rate limit exceeded"
        if retry_after:
            message += f" (retry after {retry_after}s)"
        super().__init__(status_code=429, message=message)


class ParseException(CrawlerException):
    """HTML/JSON 파싱이 실패했을 때 발생."""

    def __init__(self, content_type: str, reason: str = None):
        self.content_type = content_type
        self.reason = reason or "Unknown parsing error"
        message = f"Failed to parse {content_type}: {self.reason}"
        super().__init__(message)


class ConfigurationException(CrawlerException):
    """설정이 유효하지 않을 때 발생."""

    def __init__(self, message: str = "Invalid configuration"):
        super().__init__(message)


class StorageException(CrawlerException):
    """데이터 저장이 실패했을 때 발생."""

    def __init__(self, file_path: str = None, reason: str = None):
        self.file_path = file_path
        self.reason = reason or "Storage operation failed"
        message = f"Storage error"
        if file_path:
            message += f" for {file_path}"
        message += f": {self.reason}"
        super().__init__(message)
