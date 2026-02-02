# backend/crawling/core/driver.py
"""
Selenium WebDriver 관리
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver


def create_driver(headless: bool = True) -> WebDriver:
    """
    Selenium WebDriver 생성 (Chrome)

    Args:
        headless: 헤드리스 모드 여부 (기본값: True)

    Returns:
        WebDriver 인스턴스
    """
    options = Options()

    if headless:
        options.add_argument("--headless=new")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    # Selenium 4.6+는 자동으로 ChromeDriver 관리
    driver = webdriver.Chrome(options=options)

    return driver
