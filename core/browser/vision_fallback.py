import json
import re
from pathlib import Path

_COORD_RE = re.compile(r"(\d{1,4})\s*[,，]\s*(\d{1,4})")


def parse_coordinates(text: str) -> tuple[int, int] | None:
    """解析模型回覆的千分比座標，支援 JSON 與逗號兩種格式。"""
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        data = None
    if isinstance(data, dict) and "x" in data and "y" in data:
        return int(data["x"]), int(data["y"])
    match = _COORD_RE.search(text)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None


def resolve_coordinates(x: int, y: int, width: int, height: int) -> tuple[int, int]:
    """千分比相對座標轉絕對像素。"""
    return round(x * width / 1000), round(y * height / 1000)


async def click_by_vision(
    driver,
    gateway,
    prompt_id: str,
    description: str,
    screenshot_path: str | Path,
) -> bool:
    """截圖送模型取座標並點擊，解析失敗回假（升級由呼叫端計數）。"""
    shot = await driver.screenshot(screenshot_path)
    raw = gateway.analyze(prompt_id, [str(shot)], {"target": description})
    coords = parse_coordinates(raw)
    if coords is None:
        return False
    page = driver.get_page()
    viewport = page.viewport_size
    x, y = resolve_coordinates(coords[0], coords[1], viewport["width"], viewport["height"])
    await page.mouse.click(x, y)
    return True
