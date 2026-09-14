import asyncio
import logging
import re
from collections.abc import Callable
from urllib.parse import urlencode

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import (
    InvalidSessionIdException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as conditions
from selenium.webdriver.support.ui import WebDriverWait

from app.core.config import Settings
from app.core.errors import UpstreamError
from app.modules.wordstat.domain.entities import PhraseStat, WordstatTop


DriverFactory = Callable[[], WebDriver]


class WordstatBrowserGateway:
    def __init__(
        self,
        settings: Settings,
        driver_factory: DriverFactory | None = None,
    ) -> None:
        self._settings = settings
        self._driver_factory = driver_factory or self._create_driver
        self._driver: WebDriver | None = None
        self._lock = asyncio.Lock()
        self._logger = logging.getLogger("wordstat.browser")

    async def get_top(self, phrase: str) -> WordstatTop:
        async with self._lock:
            return await asyncio.to_thread(self._get_top_sync, phrase)

    async def close(self) -> None:
        async with self._lock:
            driver, self._driver = self._driver, None
            if driver is not None:
                await asyncio.to_thread(driver.quit)

    def _get_top_sync(self, phrase: str) -> WordstatTop:
        try:
            return self._query(self._get_driver(), phrase)
        except InvalidSessionIdException:
            self._driver = None
            return self._query(self._get_driver(), phrase)
        except TimeoutException as error:
            self._logger.warning("Wordstat page timed out")
            raise UpstreamError(
                504, "wordstat_timeout", "Wordstat did not respond in time"
            ) from error
        except UpstreamError:
            raise
        except WebDriverException as error:
            self._logger.warning("Wordstat browser failed: %s", type(error).__name__)
            raise UpstreamError(
                503, "browser_unavailable", "Wordstat browser is unavailable"
            ) from error

    def _query(self, driver: WebDriver, phrase: str) -> WordstatTop:
        query = urlencode({"region": "all", "view": "table", "words": phrase})
        driver.get(f"{str(self._settings.WORDSTAT_SITE_URL).rstrip('/')}?{query}")
        wait = WebDriverWait(driver, self._settings.WORDSTAT_TIMEOUT_SECONDS)
        wait.until(lambda current: self._page_ready_or_blocked(current))
        self._raise_for_blocked_page(driver)

        self._select_mode(driver, wait, "popular")
        results = self._parse_table(driver.page_source)
        self._select_mode(driver, wait, "associations")
        associations = self._parse_table(driver.page_source)

        if not results:
            raise UpstreamError(
                502, "wordstat_layout_changed", "Wordstat result format changed"
            )

        limit = self._settings.WORDSTAT_NUM_PHRASES
        return WordstatTop(
            query=phrase,
            total_count=results[0].count,
            results=tuple(results[:limit]),
            associations=tuple(associations[:limit]),
        )

    def _get_driver(self) -> WebDriver:
        if self._driver is None:
            self._driver = self._driver_factory()
            self._driver.set_page_load_timeout(self._settings.WORDSTAT_TIMEOUT_SECONDS)
        return self._driver

    def _create_driver(self) -> WebDriver:
        options = webdriver.ChromeOptions()
        options.binary_location = "/usr/bin/chromium"
        options.add_argument("--lang=ru-RU")
        options.add_argument("--window-size=1440,1000")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--user-data-dir=/var/lib/wordstat-browser/profile")
        return webdriver.Chrome(
            service=Service(executable_path="/usr/bin/chromedriver"),
            options=options,
        )

    @staticmethod
    def _page_ready_or_blocked(driver: WebDriver) -> bool:
        url = driver.current_url.lower()
        source = driver.page_source.lower()
        return bool(driver.find_elements(By.CSS_SELECTOR, "table[role='table']")) or any(
            marker in url or marker in source
            for marker in ("passport.yandex", "showcaptcha", "smart-captcha", "captcha")
        )

    @staticmethod
    def _raise_for_blocked_page(driver: WebDriver) -> None:
        url = driver.current_url.lower()
        source = driver.page_source.lower()
        if "showcaptcha" in url or "smart-captcha" in source or "captcha" in url:
            raise UpstreamError(
                503,
                "yandex_captcha_required",
                "Yandex requires a manual CAPTCHA",
            )
        if "passport.yandex" in url or not driver.find_elements(
            By.PARTIAL_LINK_TEXT, "Выйти"
        ):
            raise UpstreamError(
                503, "yandex_auth_required", "Yandex login is required"
            )

    @staticmethod
    def _select_mode(driver: WebDriver, wait: WebDriverWait, mode: str) -> None:
        radio = driver.find_element(By.ID, mode)
        if radio.is_selected():
            return
        previous_table = driver.find_element(By.CSS_SELECTOR, "table[role='table']")
        previous_html = previous_table.get_attribute("innerHTML")
        driver.find_element(By.XPATH, f"//input[@id='{mode}']/parent::label").click()
        wait.until(conditions.element_to_be_selected((By.ID, mode)))
        wait.until(
            lambda current: current.find_element(
                By.CSS_SELECTOR, "table[role='table']"
            ).get_attribute("innerHTML")
            != previous_html
        )

    @staticmethod
    def _parse_table(html: str) -> list[PhraseStat]:
        soup = BeautifulSoup(html, "html.parser")
        statistics: list[PhraseStat] = []
        for row in soup.select("table[role='table'] tbody tr"):
            cells = row.select("[role='cell']")
            if len(cells) < 2:
                continue
            phrase = cells[0].get_text(" ", strip=True)
            raw_count = re.sub(r"[^0-9]", "", cells[1].get_text(" ", strip=True))
            if phrase and raw_count:
                statistics.append(PhraseStat(phrase=phrase, count=int(raw_count)))
        return statistics
