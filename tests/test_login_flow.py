import asyncio

import pytest

import core.browser.login_flow as flow
from core.browser.login_flow import LoginError, is_session_valid, qr_login


class FakeElement:
    def __init__(self):
        self.shots = []

    async def screenshot(self, path):
        self.shots.append(path)


class FakePage:
    def __init__(self, element=None, home_after=0, body_text="首頁內容"):
        self._element = element
        self._home_after = home_after
        self._body_text = body_text
        self._url_reads = 0
        self.visits = []
        self.selectors = []

    @property
    def url(self):
        self._url_reads += 1
        if self._url_reads > self._home_after:
            return "https://tw.carousell.com/"
        return "https://tw.carousell.com/login/"

    async def goto(self, url, **kwargs):
        self.visits.append(url)

    async def evaluate(self, script):
        return self._body_text

    async def query_selector(self, selector):
        self.selectors.append(selector)
        return self._element


class FakeDriver:
    def __init__(self, page):
        self._page = page
        self.shots = []

    def get_page(self):
        return self._page

    async def screenshot(self, path):
        self.shots.append(str(path))
        return path


def test_login_success_on_redirect(monkeypatch):
    async def scenario():
        notified = []
        page = FakePage(home_after=1)
        driver = FakeDriver(page)
        monkeypatch.setattr(flow, "POLL_INTERVAL_SECONDS", 0)

        async def notifier(shot):
            notified.append(shot)

        shot = await qr_login(driver, "qr.png", notifier, timeout=30)
        return shot, notified

    monkeypatch.setattr(flow, "POLL_INTERVAL_SECONDS", 0)
    shot, notified = asyncio.run(scenario())
    assert str(shot) == "qr.png"
    assert notified == [shot]


def test_login_timeout(monkeypatch):
    async def scenario():
        driver = FakeDriver(FakePage(home_after=999))
        monkeypatch.setattr(flow, "POLL_INTERVAL_SECONDS", 0)

        async def notifier(shot):
            pass

        with pytest.raises(LoginError):
            await qr_login(driver, "qr.png", notifier, timeout=0)

    asyncio.run(scenario())


def test_qr_region_captured():
    async def scenario():
        qr = FakeElement()
        page = FakePage(element=qr)
        driver = FakeDriver(page)
        shot = await flow._capture_qr(driver, "qr.png")
        return shot, qr.shots, driver.shots, page.selectors

    shot, qr_shots, full_shots, selectors = asyncio.run(scenario())
    assert str(shot) == "qr.png"
    assert qr_shots == ["qr.png"]
    assert full_shots == []
    assert selectors == ['svg[width="148"][height="148"]']


def test_qr_fallback_to_full_page():
    async def scenario():
        page = FakePage(element=None)
        driver = FakeDriver(page)
        shot = await flow._capture_qr(driver, "qr.png")
        return shot, driver.shots

    shot, full_shots = asyncio.run(scenario())
    assert str(shot) == "qr.png"
    assert full_shots == ["qr.png"]


def test_session_valid_without_login_buttons():
    async def scenario():
        page = FakePage(body_text="首頁內容")
        driver = FakeDriver(page)
        return await is_session_valid(driver)

    assert asyncio.run(scenario()) is True


def test_session_invalid_with_login_button():
    async def scenario():
        page = FakePage(body_text="歡迎使用，請登入或註冊")
        driver = FakeDriver(page)
        return await is_session_valid(driver)

    assert asyncio.run(scenario()) is False
