import json

import pytest

from core.brain.llm_gateway import LlmGateway, MockProvider
from core.brain.vision_agent import (
    VisionError,
    analyze_images,
    grade_to_condition,
)


class JsonProvider(MockProvider):
    def __init__(self, payload: str) -> None:
        self._payload = payload

    def analyze(self, prompt_id, images, params):
        return self._payload


def _gateway(payload: str) -> LlmGateway:
    return LlmGateway(JsonProvider(payload))


def _valid_payload(**overrides):
    data = {
        "detected_brand": "Logitech",
        "detected_model": "MX Master 3S",
        "condition_grade": "9_out_of_10",
        "defects_noted": ["底部腳貼有輕微摩擦痕跡"],
        "inclusions": ["原廠接收器", "USB-C 充電線"],
    }
    data.update(overrides)
    return json.dumps(data)


def test_valid_analysis():
    result = analyze_images(_gateway(_valid_payload()), ["a.jpg"])
    assert result.detected_brand == "Logitech"
    assert result.condition_grade == "9_out_of_10"


def test_non_json_rejected():
    with pytest.raises(VisionError):
        analyze_images(_gateway("[mock:vision]"), ["a.jpg"])


def test_incomplete_result_rejected():
    with pytest.raises(VisionError):
        analyze_images(_gateway(_valid_payload(detected_brand="")), ["a.jpg"])


def test_unknown_grade_rejected():
    with pytest.raises(VisionError):
        analyze_images(_gateway(_valid_payload(condition_grade="7_out_of_10")), ["a.jpg"])


def test_empty_images_rejected():
    with pytest.raises(VisionError):
        analyze_images(_gateway(_valid_payload()), [])


def test_grade_mapping():
    assert grade_to_condition("10_out_of_10") == "全新"
    assert grade_to_condition("9_out_of_10") == "9成新"
    assert grade_to_condition("8_out_of_10") == "輕微使用痕跡"
    with pytest.raises(VisionError):
        grade_to_condition("7_out_of_10")
