import pytest
from pydantic import SecretStr
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By

from app.core.config import Settings
from app.core.errors import UpstreamError
from app.modules.wordstat.domain.entities import PhraseStat, WordstatTop
from app.modules.wordstat.infrastructure.browser_gateway import WordstatBrowserGateway


class FakeDriver:
    def __init__(self, *, url: str = "https://wordstat.yandex.ru/", html: str = "") -> None:
        self.current_url = url
        self.page_source = html
        self.timeout: float | None = None
        self.quit_called = False

    def find_elements(self, by: str, value: str) -> list[object]:
        if by == By.CSS_SELECTOR and value == "table[role='table']":
            return [object()] if "<table" in self.page_source else []
        if by == By.PARTIAL_LINK_TEXT and value == "Выйти":
            return [object()] if "Выйти" in self.page_source else []
        return []

    def set_page_load_timeout(self, timeout: float) -> None:
        self.timeout = timeout

    def quit(self) -> None:
        self.quit_called = True


def make_settings() -> Settings:
    return Settings(PROXY_API_KEY=SecretStr("p" * 32))


def test_parse_table_normalizes_counts() -> None:
    html = """
    <table role="table"><tbody>
      <tr role="row">
        <td role="cell"><a>купить базу клиентов</a></td>
        <td role="cell">90 813</td>
      </tr>
      <tr role="row">
        <td role="cell"><a>база лидов</a></td>
        <td role="cell">1\u00a0568</td>
      </tr>
    </tbody></table>
    """

    statistics = WordstatBrowserGateway._parse_table(html)

    assert [(item.phrase, item.count) for item in statistics] == [
        ("купить базу клиентов", 90_813),
        ("база лидов", 1_568),
    ]


def test_parse_table_ignores_invalid_rows() -> None:
    html = """
    <table role="table"><tbody>
      <tr><td role="cell">нет значения</td><td role="cell">—</td></tr>
      <tr><td role="cell"></td></tr>
    </tbody></table>
    """

    assert WordstatBrowserGateway._parse_table(html) == []


def test_page_state_detection_and_auth_validation() -> None:
    ready = FakeDriver(html="<a>Выйти</a><table role='table'></table>")
    login = FakeDriver(url="https://passport.yandex.ru/auth")
    captcha = FakeDriver(url="https://wordstat.yandex.ru/showcaptcha")

    assert WordstatBrowserGateway._page_ready_or_blocked(ready)
    assert WordstatBrowserGateway._page_ready_or_blocked(login)
    assert WordstatBrowserGateway._page_ready_or_blocked(captcha)
    WordstatBrowserGateway._raise_for_blocked_page(ready)

    with pytest.raises(UpstreamError, match="login") as login_error:
        WordstatBrowserGateway._raise_for_blocked_page(login)
    assert login_error.value.code == "yandex_auth_required"

    with pytest.raises(UpstreamError, match="CAPTCHA") as captcha_error:
        WordstatBrowserGateway._raise_for_blocked_page(captcha)
    assert captcha_error.value.code == "yandex_captcha_required"


@pytest.mark.asyncio
async def test_gateway_runs_query_and_closes_driver(monkeypatch: pytest.MonkeyPatch) -> None:
    driver = FakeDriver()
    gateway = WordstatBrowserGateway(make_settings(), driver_factory=lambda: driver)  # type: ignore[arg-type]
    expected = WordstatTop("test", 7, (PhraseStat("test", 7),), ())
    monkeypatch.setattr(gateway, "_query", lambda current, phrase: expected)

    result = await gateway.get_top("test")
    await gateway.close()

    assert result == expected
    assert driver.timeout == 30
    assert driver.quit_called


@pytest.mark.asyncio
async def test_gateway_maps_browser_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    driver = FakeDriver()
    gateway = WordstatBrowserGateway(make_settings(), driver_factory=lambda: driver)  # type: ignore[arg-type]

    def raise_timeout(current: object, phrase: str) -> WordstatTop:
        raise TimeoutException()

    monkeypatch.setattr(gateway, "_query", raise_timeout)

    with pytest.raises(UpstreamError) as raised:
        await gateway.get_top("test")

    assert raised.value.status_code == 504
    assert raised.value.code == "wordstat_timeout"
