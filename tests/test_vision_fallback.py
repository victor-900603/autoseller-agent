import asyncio

from core.browser.vision_fallback import (
    click_by_vision,
    parse_coordinates,
    resolve_coordinates,
)


def test_parse_json_coordinates():
    assert parse_coordinates('{"x": 500, "y": 300}') == (500, 300)


def test_parse_comma_coordinates():
    assert parse_coordinates("按鈕位於 500, 300") == (500, 300)


def test_parse_failure_returns_none():
    assert parse_coordinates("找不到目標") is None


def test_resolve_to_pixels():
    assert resolve_coordinates(500, 250, 1280, 800) == (640, 200)


class FakeMouse:
    def __init__(self):
        self.clicks = []

    async def click(self, x, y):
        self.clicks.append((x, y))


class FakePage:
    def __init__(self):
        self.mouse = FakeMouse()
        self.viewport_size = {"width": 1280, "height": 800}


class FakeDriver:
    def __init__(self, page):
        self._page = page
        self.shots = []

    def get_page(self):
        return self._page

    async def screenshot(self, path):
        self.shots.append(str(path))
        return path


class FakeGateway:
    def __init__(self, reply):
        self._reply = reply

    def analyze(self, prompt_id, images, params):
        return self._reply


def test_click_success():
    async def scenario():
        page = FakePage()
        driver = FakeDriver(page)
        gateway = FakeGateway('{"x": 500, "y": 400}')
        ok = await click_by_vision(driver, gateway, "p", "提交鈕", "s.png")
        return ok, page.mouse.clicks, driver.shots

    ok, clicks, shots = asyncio.run(scenario())
    assert ok is True
    assert clicks == [(640, 320)]
    assert shots == ["s.png"]


def test_click_parse_failure():
    async def scenario():
        page = FakePage()
        driver = FakeDriver(page)
        gateway = FakeGateway("找不到")
        return await click_by_vision(driver, gateway, "p", "提交鈕", "s.png"), page.mouse.clicks

    ok, clicks = asyncio.run(scenario())
    assert ok is False
    assert clicks == []
