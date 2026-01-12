"""
크롤러를 위한 로깅 유틸리티.
"""
import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


def setup_logger(
    name: str = "crawler",
    log_file: Optional[Path] = None,
    level: int = logging.INFO,
    console: bool = True,
) -> logging.Logger:
    """
    로거를 설정합니다.

    Args:
        name: 로거 이름
        log_file: 로그 파일 경로 (None이면 파일에 기록하지 않음)
        level: 로그 레벨 (기본값: INFO)
        console: 콘솔 출력 여부

    Returns:
        설정된 로거 객체
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 기존 핸들러 제거 (중복 방지)
    logger.handlers.clear()

    # 포맷터 설정
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 콘솔 핸들러
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # 파일 핸들러
    if log_file:
        # 로그 디렉토리 생성
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "crawler") -> logging.Logger:
    """
    기존 로거를 가져오거나 새로 생성합니다.

    Args:
        name: 로거 이름

    Returns:
        로거 객체
    """
    logger = logging.getLogger(name)

    # 로거가 설정되지 않은 경우 기본 설정
    if not logger.handlers:
        setup_logger(name)

    return logger


def create_crawl_logger(output_dir: Path) -> logging.Logger:
    """
    크롤링 세션을 위한 로거를 생성합니다.

    Args:
        output_dir: 출력 디렉토리

    Returns:
        크롤링 로거
    """
    # 타임스탬프가 포함된 로그 파일명
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = output_dir / f"crawl_{timestamp}.log"

    return setup_logger(
        name="crawler",
        log_file=log_file,
        level=logging.INFO,
        console=True,
    )
