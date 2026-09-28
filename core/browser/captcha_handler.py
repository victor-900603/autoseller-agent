from pathlib import Path
from typing import Protocol


class Notifier(Protocol):
    async def __call__(self, screenshot_path: Path) -> None:
        ...


CAPTCHA_URL_MARKERS = (
    "challenge",
    "captcha",
    "geetest",
    "cloudflare",
    "verify-you-are-human",
)

CAPTCHA_CONTENT_MARKERS = (
    "geetest",
    "cf-challenge",
    "__cf_chl",
    "challenge-form",
    "cloudflare",
    "attention required",
    "ray id",
    "正在執行安全驗證",
    "驗證你是人類",
)


def detect_captcha(url: str, html: str) -> bool:
    """網址或內容命中任一驗證特徵即判定為驗證頁。"""
    lowered_url = url.lower()
    if any(marker in lowered_url for marker in CAPTCHA_URL_MARKERS):
        return True
    lowered_html = html.lower()
    return any(marker in lowered_html for marker in CAPTCHA_CONTENT_MARKERS)


async def handle_captcha(
    driver, scheduler, screenshot_path: str | Path, notifier: Notifier
) -> Path:
    """暫停刊登消費、截圖、通知人工，回傳截圖路徑。"""
    scheduler.pause()
    shot = await driver.screenshot(screenshot_path)
    await notifier(shot)
    return shot
