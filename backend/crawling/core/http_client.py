"""
웹 요청을 수행하는 HTTP 클라이언트.
"""
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any

from .config import CrawlerConfig
from .exceptions import HTTPRequestException, ImageDownloadException


class HTTPClient:
    """웹 스크래핑을 위한 HTTP 클라이언트."""

    def __init__(
        self,
        timeout: int = CrawlerConfig.REQUEST_TIMEOUT,
        encoding: str = CrawlerConfig.REQUEST_ENCODING,
    ):
        self.timeout = timeout
        self.encoding = encoding
        self.session = requests.Session()

    def get_soup(
        self, url: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[BeautifulSoup]:
        """
        HTTP GET 요청을 수행하고 BeautifulSoup 객체 반환.

        Args:
            url: 요청할 URL
            params: 쿼리 파라미터

        Returns:
            BeautifulSoup 객체 또는 요청 실패 시 None

        Raises:
            HTTPRequestException: 요청이 실패했을 때
        """
        try:
            response = self.session.get(
                url,
                params=params,
                headers=CrawlerConfig.HTTP_HEADERS,
                timeout=self.timeout,
            )

            # 인코딩 설정
            response.encoding = self.encoding

            if response.status_code == 200:
                return BeautifulSoup(response.text, "html.parser")
            else:
                raise HTTPRequestException(url, response.status_code)

        except requests.exceptions.Timeout:
            raise HTTPRequestException(url, message=f"Request timeout after {self.timeout}s")
        except requests.exceptions.RequestException as e:
            raise HTTPRequestException(url, message=str(e))

    def download_image(self, image_url: str) -> Optional[bytes]:
        """
        URL에서 이미지를 다운로드하여 바이트로 반환.

        Args:
            image_url: 이미지의 URL

        Returns:
            바이트 형태의 이미지 데이터 또는 다운로드 실패 시 None

        Raises:
            ImageDownloadException: 이미지 다운로드가 실패했을 때
        """
        try:
            response = self.session.get(
                image_url,
                headers=CrawlerConfig.IMAGE_HEADERS,
                timeout=self.timeout,
            )

            if response.status_code == 200:
                # 이미지 콘텐츠 유효성 검사
                content_type = response.headers.get("Content-Type", "")
                content_length = len(response.content)

                # 실제 이미지인지 확인
                if "image" in content_type or content_length > CrawlerConfig.MIN_IMAGE_BYTES:
                    return response.content
                else:
                    raise ImageDownloadException(
                        image_url,
                        reason=f"Content too small ({content_length} bytes) or invalid type",
                    )
            else:
                raise ImageDownloadException(
                    image_url, reason=f"HTTP {response.status_code}"
                )

        except requests.exceptions.Timeout:
            raise ImageDownloadException(image_url, reason="Timeout")
        except requests.exceptions.RequestException as e:
            raise ImageDownloadException(image_url, reason=str(e))

    def close(self):
        """HTTP 세션 종료."""
        self.session.close()

    def __enter__(self):
        """컨텍스트 매니저 진입."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료."""
        self.close()
