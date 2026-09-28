import asyncio
import random
from dataclasses import dataclass, field
from pathlib import Path

from playwright.async_api import BrowserContext, Page, async_playwright

STEALTH_SCRIPT = (
    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
)

_DEFAULT_VIEWPORTS = [(1280, 800), (1920, 1080)]


class DriverError(Exception):
    pass


@dataclass
class DriverConfig:
    """驅動啟動參數，路徑為空時由 Playwright 自行解析。"""

    headless: bool = True
    profile_dir: Path = Path("storage/user_data")
    viewports: list = field(default_factory=lambda: list(_DEFAULT_VIEWPORTS))
    jitter_ms: tuple = (150, 350)
    executable_path: str | None = None


class BrowserDriver:
    """Playwright 單例，唯一持有瀏覽器實例者。"""

    def __init__(self, config: DriverConfig | None = None) -> None:
        """保存啟動參數，不啟動瀏覽器。"""
        self._config = config or DriverConfig()
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._playwright = None

    async def start(self) -> Page:
        """啟動持久化 context 並回傳首頁，已啟動直接回傳。"""
        if self._page is not None:
            return self._page
        width, height = random.choice(self._config.viewports)
        playwright = await async_playwright().start()
        launch_options = {
            "user_data_dir": str(self._config.profile_dir),
            "headless": self._config.headless,
            "viewport": {"width": width, "height": height},
        }
        if self._config.executable_path:
            launch_options["executable_path"] = self._config.executable_path
        self._context = await playwright.chromium.launch_persistent_context(**launch_options)
        await self._context.add_init_script(STEALTH_SCRIPT)
        self._page = await self._context.new_page()
        for old_page in self._context.pages:
            if old_page is not self._page:
                await old_page.close()
        self._playwright = playwright
        return self._page

    async def stop(self) -> None:
        """關閉瀏覽器並清空狀態，未啟動直接返回。"""
        if self._context is None:
            return
        await self._context.close()
        await self._playwright.stop()
        self._context = None
        self._page = None

    def get_page(self) -> Page:
        """回傳作用中頁面，未啟動拋錯。"""
        if self._page is None:
            raise DriverError("瀏覽器尚未啟動")
        return self._page

    async def screenshot(self, path: str | Path) -> Path:
        """截圖存檔並回傳路徑，自動建立目錄。"""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        await self.get_page().screenshot(path=str(target))
        return target

    async def human_delay(self) -> None:
        """隨機短延遲，模擬人工操作間隔。"""
        low, high = self._config.jitter_ms
        await asyncio.sleep(random.uniform(low, high) / 1000)
