import json

from core.brain.llm_gateway import GatewayError, LlmGateway
from core.contracts import Condition, VisionResult

VISION_PROMPT_ID = "vision.describe_item"

_GRADE_TO_CONDITION = {
    "10_out_of_10": "全新",
    "9_out_of_10": "9成新",
    "8_out_of_10": "輕微使用痕跡",
}


class VisionError(Exception):
    pass


def grade_to_condition(grade: str) -> Condition:
    """等級轉刊登成色，未知等級拋錯。"""
    try:
        return _GRADE_TO_CONDITION[grade]
    except KeyError as exc:
        raise VisionError(f"未知成色等級：{grade}") from exc


def analyze_images(gateway: LlmGateway, image_paths: list[str]) -> VisionResult:
    """經網關解析圖片並以契約驗證，失敗皆轉視覺錯誤。"""
    if not image_paths:
        raise VisionError("缺少商品圖片")
    try:
        raw = gateway.analyze(VISION_PROMPT_ID, image_paths)
    except GatewayError as exc:
        raise VisionError("視覺解析呼叫失敗") from exc
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise VisionError("視覺解析回覆非結構化") from exc
    if not isinstance(data, dict):
        raise VisionError("視覺解析回覆非結構化")
    try:
        return VisionResult(**data)
    except ValueError as exc:
        raise VisionError("視覺解析結果不完整") from exc
