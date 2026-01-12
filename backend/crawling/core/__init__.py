"""
Seokang Church Sermon Crawler - Core Module

A modular web crawler for extracting sermon data from Seokang Church website
with OCR capabilities using Google Gemini API.
"""

from .config import CrawlerConfig, GeminiConfig, StorageConfig, ChurchConfig, validate_config
from .models import SermonData, OCRResult, CrawlStats
from .exceptions import (
    CrawlerException,
    HTTPRequestException,
    ImageDownloadException,
    OCRException,
    GeminiAPIException,
    RateLimitException,
    ParseException,
    ConfigurationException,
    StorageException,
)
from .http_client import HTTPClient
from .image_processor import ImageProcessor
from .gemini_client import GeminiClient
from .storage import SermonStorage
from .crawler import SeokangCrawler

__version__ = "2.0.0"
__author__ = "Seokang Church Dev Team"

__all__ = [
    # Main crawler
    "SeokangCrawler",
    # Configuration
    "CrawlerConfig",
    "GeminiConfig",
    "StorageConfig",
    "ChurchConfig",
    "validate_config",
    # Data models
    "SermonData",
    "OCRResult",
    "CrawlStats",
    # Exceptions
    "CrawlerException",
    "HTTPRequestException",
    "ImageDownloadException",
    "OCRException",
    "GeminiAPIException",
    "RateLimitException",
    "ParseException",
    "ConfigurationException",
    "StorageException",
    # Components
    "HTTPClient",
    "ImageProcessor",
    "GeminiClient",
    "SermonStorage",
]
