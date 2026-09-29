import asyncio
from pathlib import Path

from config.platform_selectors import LOGIN_QR

LOGIN_URL = "https://tw.carousell.com/login/"
HOME_URL = "https://tw.carousell.com/"
POLL_INTERVAL_SECONDS = 10
LOGIN_TIMEOUT_SECONDS = 300


class LoginError(Exception):
    pass


async def _find_qr_element(page):
    """依集中管理的選擇器定位 QR，找不到回空值。"""
    return await page.query_selector(LOGIN_QR)


async def _capture_qr(driver, screenshot_path: str | Path) -> Path:
    """擷取 QR 區域，找不到退回整頁截圖。"""
    target = await _find_qr_element(driver.get_page())
    if target is None:
        return Path(await driver.screenshot(screenshot_path))
    await target.screenshot(path=str(screenshot_path))
    return Path(screenshot_path)


async def _left_login_page(page) -> bool:
    return "/login" not in page.url


async def _homepage_verified(page) -> bool:
    await page.goto(HOME_URL, wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(4)
    for _ in range(2):
        text = await page.evaluate("() => document.body.innerText")
        if "登入" in text or "註冊" in text:
            return False
        await asyncio.sleep(3)
    return True


async def is_session_valid(driver) -> bool:
    """首頁雙重確認登入態，出現登入或註冊即無效。"""
    page = driver.get_page()
    await page.goto(HOME_URL, wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(4)
    for _ in range(2):
        text = await page.evaluate("() => document.body.innerText")
        if "登入" in text or "註冊" in text:
            return False
        await asyncio.sleep(3)
    return True


async def qr_login(
    driver, screenshot_path: str | Path, notifier, timeout: int = LOGIN_TIMEOUT_SECONDS
) -> Path:
    """掃碼登入：截圖傳圖、輪詢跳轉、首頁驗證，超時拋錯。"""
    page = driver.get_page()
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(5)
    shot = await _capture_qr(driver, screenshot_path)
    await notifier(shot)
    elapsed = 0
    while elapsed < timeout:
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        elapsed += POLL_INTERVAL_SECONDS
        try:
            left = await _left_login_page(page)
        except Exception:
            raise LoginError("瀏覽器已關閉")
        if left and await _homepage_verified(page):
            return shot
    raise LoginError("掃碼登入超時")
