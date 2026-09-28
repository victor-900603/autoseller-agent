import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from core.browser.driver import STEALTH_SCRIPT, BrowserDriver, DriverConfig, DriverError


class FakePage:
    def __init__(self):
        self.shots = []
        self.closed = False

    async def screenshot(self, path):
        self.shots.append(path)

    async def close(self):
        self.closed = True


class FakeContext:
    def __init__(self):
        self.scripts = []
        self.page = FakePage()
        self.kwargs = {}
        self.closed = False

    @property
    def pages(self):
        return [self.page]

    async def new_page(self):
        self.page = FakePage()
        return self.page

    async def add_init_script(self, script):
        self.scripts.append(script)

    async def close(self):
        self.closed = True


def _patched_driver(config=None):
    context = FakeContext()
    chromium = AsyncMock()
    chromium.launch_persistent_context.side_effect = lambda **kwargs: (
        context.kwargs.update(kwargs),
        context,
    )[1]
    playwright = AsyncMock()
    playwright.chromium = chromium
    starter = AsyncMock(return_value=playwright)
    patcher = patch("core.browser.driver.async_playwright")
    fake_factory = patcher.start()
    fake_factory.return_value.start = starter
    return context, playwright, patcher


def test_start_passes_launch_options(tmp_path):
    async def scenario():
        context, _, patcher = _patched_driver()
        try:
            config = DriverConfig(
                headless=True,
                profile_dir=tmp_path / "profile",
                viewports=[(1280, 800)],
            )
            driver = BrowserDriver(config)
            page = await driver.start()
            return context, page
        finally:
            patcher.stop()

    context, page = asyncio.run(scenario())
    assert context.kwargs["headless"] is True
    assert context.kwargs["user_data_dir"].endswith("profile")
    assert context.kwargs["viewport"] == {"width": 1280, "height": 800}
    assert any("webdriver" in script for script in context.scripts)
    assert "webdriver" in STEALTH_SCRIPT
    assert isinstance(page, FakePage)


def test_start_idempotent():
    async def scenario():
        _, _, patcher = _patched_driver()
        try:
            driver = BrowserDriver()
            first = await driver.start()
            second = await driver.start()
            return first is second
        finally:
            patcher.stop()

    assert asyncio.run(scenario()) is True


def test_get_page_before_start_rejected():
    with pytest.raises(DriverError):
        BrowserDriver().get_page()


def test_stop_without_start_ok():
    async def scenario():
        await BrowserDriver().stop()

    asyncio.run(scenario())


def test_screenshot_creates_dirs(tmp_path):
    async def scenario():
        context, _, patcher = _patched_driver()
        try:
            driver = BrowserDriver()
            await driver.start()
            target = tmp_path / "shots" / "a.png"
            return await driver.screenshot(target), context.page.shots
        finally:
            patcher.stop()

    target, shots = asyncio.run(scenario())
    assert Path(target).parent.is_dir()
    assert shots == [str(target)]


def test_human_delay_within_range():
    async def scenario():
        import time

        driver = BrowserDriver(DriverConfig(jitter_ms=(150, 350)))
        start = time.monotonic()
        await driver.human_delay()
        return time.monotonic() - start

    elapsed = asyncio.run(scenario())
    assert 0.1 <= elapsed <= 1.0
