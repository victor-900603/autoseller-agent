import asyncio
from pathlib import Path

from core.browser.captcha_handler import detect_captcha, handle_captcha


def test_url_marker_detected():
    assert detect_captcha("https://example.com/cdn-cgi/challenge-platform", "<html></html>") is True


def test_geetest_marker_detected():
    assert detect_captcha("https://example.com/", "<div>geetest_widget</div>") is True


def test_normal_page_passes():
    assert detect_captcha("https://example.com/item/1", "<div>商品</div>") is False


class FakeDriver:
    def __init__(self, tmp_path):
        self.shot = Path(tmp_path) / "captcha.png"

    async def screenshot(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text("fake", encoding="utf-8")
        return Path(path)


class FakeScheduler:
    def __init__(self):
        self.paused = False

    def pause(self):
        self.paused = True


def test_handle_pauses_screenshots_notifies(tmp_path):
    async def scenario():
        notified = []
        driver = FakeDriver(tmp_path)
        scheduler = FakeScheduler()

        async def notifier(path):
            notified.append(path)

        shot = await handle_captcha(driver, scheduler, tmp_path / "s.png", notifier)
        return scheduler.paused, shot, notified

    paused, shot, notified = asyncio.run(scenario())
    assert paused is True
    assert shot.exists()
    assert notified == [shot]
